"""Main loop: detects which Paradox game is running, follows that game's log file
and updates the Discord activity with the game's own Application ID.

Usage:
    python3 companion/run.py                      # normal run
    python3 companion/run.py --dry-run            # log the activity instead of sending it
    python3 companion/run.py --game vic3 --log /path/debug.log --dry-run   # testing
The packaged Windows .exe asks about starting at sign-in on first launch and offers
to stop when launched again while running.
"""

import argparse
import json
import logging
import logging.handlers
import sys
import time
from pathlib import Path

from . import APP_NAME, __version__, system
from .discord_ipc import DiscordIPC
from .games import all_games
from .logtail import LogTailer

log = logging.getLogger("prp")

DEFAULT_CONFIG = {
    # Image shown when there is no flag: an asset name from the Developer Portal or an https URL
    "large_image": "logo",
    "flags": True,
    "status_icons": True,
    # Which line replaces the game name in Discord's member list: name, details, state
    "status_display": "details",
    # Country to show in multiplayer (e.g. "TUR"); empty means the local player
    "country_tag": "",
    # Show a pause marker when the in-game date has not advanced for this many seconds
    "pause_after_seconds": 180,
    # Up to 2 profile buttons: [{"label": "...", "url": "https://..."}]
    "buttons": [],
    # Per-game overrides, including Application IDs: {"vic3": {"client_id": "..."}}
    "games": {},
}

POLL_SECONDS = 1.0
PROCESS_CHECK_SECONDS = 5.0
MIN_UPDATE_INTERVAL = 15  # Discord rate-limits activity updates to roughly one per 15 s
STATUS_DISPLAY_TYPES = {"name": 0, "state": 1, "details": 2}


# --------------------------------------------------------------------------- setup

def setup_logging(verbose):
    handlers = [logging.handlers.RotatingFileHandler(
        str(system.data_dir() / "companion.log"), maxBytes=512 * 1024, backupCount=1, encoding="utf-8")]
    if sys.stdout is not None:  # the windowless Windows build has no stdout
        handlers.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO, handlers=handlers,
                        format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")


def load_config(path=None):
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    path = path or system.data_dir() / "config.json"
    try:
        with open(str(path), encoding="utf-8") as f:
            cfg.update(json.load(f))
    except FileNotFoundError:
        pass
    except (OSError, ValueError) as e:
        log.warning("Could not read config file (%s): %s", path, e)
    return cfg


def game_config(cfg, game):
    """Global settings with the game's overrides applied."""
    merged = {k: v for k, v in cfg.items() if k != "games"}
    merged.setdefault("large_text", game.name)
    merged.update(cfg.get("games", {}).get(game.key, {}))
    merged.setdefault("client_id", game.client_id)
    return merged


def finalize(act, cfg, status_display_ok):
    """Last additions before sending (buttons, member list display)."""
    act = dict(act)
    buttons = [b for b in cfg.get("buttons", []) if b.get("label") and b.get("url")][:2]
    if buttons:
        act["buttons"] = buttons
    if status_display_ok and cfg.get("status_display") in STATUS_DISPLAY_TYPES:
        act["status_display_type"] = STATUS_DISPLAY_TYPES[cfg["status_display"]]
    return act


# --------------------------------------------------------------------------- session

class GameSession:
    """Log tailing, state and Discord connection for one running game."""

    def __init__(self, game, cfg, log_path=None, dry_run=False):
        self.game = game
        self.cfg = game_config(cfg, game)
        self.dry_run = dry_run
        if log_path:
            path = Path(log_path)
        else:
            path = system.documents_dir() / "Paradox Interactive" / game.docs_folder / "logs" / game.log_file
        self.tailer = LogTailer(path)
        self.state = game.create_presence(self.cfg)
        self.state.session_start = time.time()
        self.ipc = DiscordIPC(self.cfg["client_id"])
        self.last_sent = None
        self.next_send_at = 0.0
        self.status_display_ok = True
        log.info("%s detected, log: %s", game.name, path)

    def tick(self):
        for line in self.tailer.read_lines():
            ev = self.game.parse_line(line)
            if ev:
                self.state.feed(ev)

        act = finalize(self.state.activity(), self.cfg, self.status_display_ok)
        if act == self.last_sent or time.time() < self.next_send_at:
            return
        self.next_send_at = time.time() + MIN_UPDATE_INTERVAL
        if self.dry_run:
            log.info("Activity: %s", json.dumps(act, ensure_ascii=False))
            self.last_sent = act
            return
        try:
            if not self.ipc.connected and not self.ipc.connect():
                raise ConnectionError("Discord IPC socket not found (is Discord running?)")
            self.ipc.set_activity(act)
            log.info("Updated: %s | %s", act.get("details"), act.get("state", ""))
            self.last_sent = act
        except ValueError as e:
            # Older Discord versions may not know status_display_type
            if self.status_display_ok and "status_display_type" in act:
                log.warning("status_display_type rejected, retrying without it: %s", e)
                self.status_display_ok = False
                self.next_send_at = 0.0
            else:
                log.warning("Discord rejected the activity: %s", e)
        except (OSError, ConnectionError) as e:
            log.info("Could not reach Discord: %s (will retry)", e)
            self.ipc.close()

    def close(self):
        log.info("%s closed", self.game.name)
        self.tailer.close()
        if self.ipc.connected:
            try:
                self.ipc.set_activity(None)
            except (OSError, ValueError, ConnectionError):
                pass
            self.ipc.close()


def detect_game(games):
    names = system.running_process_names()
    for game in games:
        if names & game.process_names:
            return game
    return None


def run(cfg, games, forced_game=None, log_path=None, dry_run=False, stop_requested=lambda: False):
    session = None
    next_check = 0.0
    try:
        while not stop_requested():
            if time.time() >= next_check:
                next_check = time.time() + PROCESS_CHECK_SECONDS
                game = forced_game or detect_game(games)
                if session and session.game is not game:
                    session.close()
                    session = None
                if game and session is None:
                    session = GameSession(game, cfg, log_path, dry_run)
            if session:
                session.tick()
            time.sleep(POLL_SECONDS)
    finally:
        if session:
            session.close()


# --------------------------------------------------------------------------- entry point

def _windows_startup(args):
    """Single instance, autostart and stop flow of the packaged Windows app.

    Returns the WindowsInstance to keep running, or None to exit.
    """
    inst = system.WindowsInstance()
    if args.uninstall:
        system.set_autostart(False)
        inst.request_stop()
        system.message_box("%s has been stopped and will no longer start with Windows." % APP_NAME)
        return None
    if inst.already_running:
        if system.message_box(
                "%s is already running in the background.\n\n"
                "Do you want to stop it and remove it from Windows startup?" % APP_NAME,
                yes_no=True):
            system.set_autostart(False)
            inst.request_stop()
        return None
    asked = system.data_dir() / "autostart_asked"
    if not system.autostart_enabled() and not args.no_autostart and not asked.exists():
        # Ask before changing system settings (SignPath Foundation requirement); the
        # answer is remembered so "No" is not asked again on every launch.
        asked.touch()
        autostart = system.message_box(
            "%s is now running in the background.\n\n"
            "Your status appears on your Discord profile when you play a supported "
            "Paradox game with the mod enabled.\n\n"
            "Start it automatically with Windows?\n"
            "(To stop it or remove it from startup, just open the program again.)" % APP_NAME,
            yes_no=True)
        if autostart:
            system.set_autostart(True)
    return inst


def main(argv=None):
    ap = argparse.ArgumentParser(prog="paradox-rich-presence", description=APP_NAME)
    ap.add_argument("--version", action="version", version=__version__)
    ap.add_argument("--dry-run", action="store_true", help="log the activity instead of sending it to Discord")
    ap.add_argument("--game", help="assume this game is running, skipping process detection (e.g. vic3)")
    ap.add_argument("--log", help="path to the game log file (for testing)")
    ap.add_argument("--config", help="path to the config file")
    ap.add_argument("--no-autostart", action="store_true", help="Windows: do not offer to start with Windows")
    ap.add_argument("--uninstall", action="store_true", help="Windows: stop and remove from startup")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    setup_logging(args.verbose)
    games = all_games()
    forced = None
    if args.game:
        forced = next((g for g in games if g.key == args.game), None)
        if forced is None:
            ap.error("unknown game: %s (supported: %s)" % (args.game, ", ".join(g.key for g in games)))

    stop_requested = lambda: False  # noqa: E731
    if system.IS_WINDOWS and getattr(sys, "frozen", False):
        inst = _windows_startup(args)
        if inst is None:
            return
        stop_requested = inst.stop_requested

    log.info("%s %s started (%s)", APP_NAME, __version__, ", ".join(g.name for g in games))
    try:
        run(load_config(args.config), games, forced, args.log, args.dry_run, stop_requested)
    except KeyboardInterrupt:
        pass
    log.info("Stopped")
