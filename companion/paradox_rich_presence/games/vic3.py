"""Victoria 3: turns the mod's log lines into a Discord activity.

Every month the mod writes a begin/kv/item/end block per player country (see
mods/vic3/common/on_actions/drp_on_actions.txt). The blocks are collected into
reports and the latest report is rendered as a compact, fixed activity.
"""

import hashlib
import json
import re
import time
import urllib.parse

PROTOCOL_VERSION = "2"

# --------------------------------------------------------------------------- parsing

# Localization formatting codes ("#v text#!", "@money!"), control and replacement characters
_FORMAT_RE = re.compile(r"#[A-Za-z_]+[ ;]?|#!|@[A-Za-z_]+!|[\x00-\x1f\x7f�]")
# Error text the game prints when a data function hits an empty object; such values
# are treated as missing.
_INVALID_RE = re.compile(r"\(null\)|invalid|unknown|not found|^\?+$|^\[.*\]$", re.IGNORECASE)


def clean(text):
    return _FORMAT_RE.sub("", text).strip()


def valid(value):
    return bool(value) and not _INVALID_RE.search(value)


def parse_line(line):
    """Extract an event from a debug.log line, or None for unrelated lines."""
    if "Transition Empty->Game" in line:
        return {"event": "entered_game"}
    if "Transition Game->Empty" in line:
        return {"event": "left_game"}
    idx = line.find("DRP|")
    if idx < 0:
        return None
    parts = line[idx:].rstrip("\r\n").split("|")
    if len(parts) < 4 or parts[1] != PROTOCOL_VERSION:
        return None
    kind, tag = parts[2], clean(parts[3])
    if kind == "local":
        return {"event": "local", "tag": tag}
    if kind in ("begin", "end"):
        return {"event": kind, "tag": tag}
    if kind in ("kv", "item") and len(parts) >= 6:
        # A value containing '|' (e.g. a formatting code) is joined back together
        value = clean("|".join(parts[5:]))
        return {"event": kind, "tag": tag, "key": parts[4], "value": value if valid(value) else ""}
    return None


# --------------------------------------------------------------------------- formatting

RANK_NAMES = {
    "great_power": "Great Power",
    "major_power": "Major Power",
    "minor_power": "Minor Power",
    "insignificant_power": "Insignificant Power",
    "unrecognized_major_power": "Unrecognized Major Power",
    "unrecognized_regional_power": "Unrecognized Regional Power",
    "unrecognized_power": "Unrecognized Power",
    "decentralized_power": "Decentralized Nation",
}


def year_of(text):
    """Year from an in-game date in any localization ('June 1, 1836' -> '1836')."""
    m = re.search(r"\b(\d{3,4})\b\s*$", text or "")
    return m.group(1) if m else ""


def join_names(names, limit=2):
    names = list(names)
    text = ", ".join(names[:limit])
    return text + (" +%d" % (len(names) - limit) if len(names) > limit else "")


# --------------------------------------------------------------------------- images

TWEMOJI = "https://cdn.jsdelivr.net/gh/jdecked/twemoji@15.1.0/assets/72x72/%s.png"
ICONS = {
    "revolution": "1f525",
    "war": "2694",
    "play": "1f3af",
    "election": "1f5f3",
    "peace": "1f54a",
}


def flag_url(entry):
    if not entry:
        return None
    if entry.get("iso"):
        return "https://flagcdn.com/w320/%s.png" % entry["iso"]
    if entry.get("wiki"):
        name = entry["wiki"].replace(" ", "_")
        h = hashlib.md5(name.encode("utf-8")).hexdigest()
        q = urllib.parse.quote(name)
        return "https://upload.wikimedia.org/wikipedia/commons/thumb/%s/%s/%s/330px-%s.png" % (h[0], h[:2], q, q)
    return None


def load_flags(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


# --------------------------------------------------------------------------- state

class Vic3Presence:
    def __init__(self, cfg, flags=None):
        self.cfg = cfg
        self.flags = flags or {}
        self.in_game = False
        self.reports = {}   # tag -> this month's report
        self.pending = {}   # tag -> fields collected between begin and end
        self.local_tag = ""
        self.last_report_at = 0.0
        self.last_date = None
        self.session_start = None

    def feed(self, ev):
        kind = ev["event"]
        if kind == "entered_game":
            self.in_game = True
            self.reports.clear()
            self.pending.clear()
            self.last_report_at = time.time()
        elif kind == "left_game":
            self.in_game = False
            self.reports.clear()
            self.pending.clear()
        elif kind == "local":
            if ev["tag"]:
                self.local_tag = ev["tag"]
        elif kind == "begin":
            self.pending[ev["tag"]] = {"tag": ev["tag"]}
        elif kind == "kv" and ev["tag"] in self.pending:
            if ev["value"]:
                self.pending[ev["tag"]][ev["key"]] = ev["value"]
        elif kind == "item" and ev["tag"] in self.pending:
            if ev["value"]:
                self.pending[ev["tag"]].setdefault(ev["key"], []).append(ev["value"])
        elif kind == "end" and ev["tag"] in self.pending:
            report = self.pending.pop(ev["tag"])
            self.in_game = True
            if report.get("date") != self.last_date:
                # New month: drop players that did not report (left the game)
                self.reports = {}
                self.last_date = report.get("date")
            self.reports[report["tag"]] = report
            self.last_report_at = time.time()

    def selected_tag(self):
        want = (self.cfg.get("country_tag") or "").upper()
        for tag in (want, self.local_tag):
            if tag and tag in self.reports:
                return tag
        return next(iter(self.reports), None)

    @staticmethod
    def _status(r):
        """(icon key, icon tooltip, text for the second line or None)."""
        if r.get("enemy_rev"):
            text = "Civil war: " + join_names(r["enemy_rev"])
            return "revolution", text, "🔥 " + text
        if r.get("war") == "yes":
            text = "At war" + (": " + join_names(r["enemy"]) if r.get("enemy") else "")
            return "war", text, "⚔ " + text
        if r.get("play_enemy"):
            text = "Diplomatic play: " + join_names(r["play_enemy"])
            return "play", text, "🎯 " + text
        if r.get("election"):
            return "election", "Election campaign", None
        return "peace", "At peace", None

    def activity(self, now=None):
        now = now or time.time()
        cfg = self.cfg
        act = {"assets": {"large_image": cfg["large_image"], "large_text": cfg["large_text"]}}
        if self.session_start:
            act["timestamps"] = {"start": int(self.session_start)}
        if not self.in_game:
            act["details"] = "Main menu"
            return act
        tag = self.selected_tag()
        r = self.reports.get(tag)
        if r is None:
            act["details"] = "In game"
            act["state"] = "Waiting for the first month…"
            return act

        details = r.get("country") or tag
        rank = RANK_NAMES.get(r.get("rank", ""))
        if rank:
            details += " · " + rank
        if now - self.last_report_at > cfg["pause_after_seconds"]:
            details = "⏸ " + details

        gdp = "£" + r["gdp"] if r.get("gdp") else ""
        pop = r["population"] + " pop" if r.get("population") else ""
        icon_key, icon_text, conflict = self._status(r)
        # Second line: year + the conflict if there is one, otherwise GDP and population
        state = [year_of(r.get("date", ""))]
        state += [conflict] if conflict else [gdp, pop]

        act["details"] = details[:128]
        act["state"] = " · ".join(p for p in state if p)[:128] or "In game"

        flag = flag_url(self.flags.get(tag)) if cfg.get("flags", True) else None
        if flag:
            act["assets"]["large_image"] = flag
        hover = []
        if gdp:
            hover.append("GDP %s" % gdp + (" (#%s)" % r["gdp_rank"] if r.get("gdp_rank") else ""))
        if r.get("population"):
            hover.append("Population %s" % r["population"])
        if hover:
            act["assets"]["large_text"] = " · ".join(hover)[:128]
        if cfg.get("status_icons", True):
            act["assets"]["small_image"] = TWEMOJI % ICONS[icon_key]
            act["assets"]["small_text"] = icon_text[:128]

        players = len(self.reports)
        if players > 1:
            act["party"] = {"id": "vic3-mp", "size": [players, players]}
        return act


# --------------------------------------------------------------------------- game definition

def _create_presence(cfg):
    from pathlib import Path
    flags = load_flags(Path(__file__).resolve().parent.parent / "data" / "vic3_flags.json")
    return Vic3Presence(cfg, flags)


def _spec():
    from . import GameSpec
    return GameSpec(
        key="vic3",
        name="Victoria 3",
        client_id="1552370224647381013",
        process_names=frozenset({"victoria3", "victoria3.exe"}),
        docs_folder="Victoria 3",
        create_presence=_create_presence,
        parse_line=parse_line,
    )


SPEC = _spec()
