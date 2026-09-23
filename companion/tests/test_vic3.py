import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from paradox_rich_presence.app import DEFAULT_CONFIG, game_config  # noqa: E402
from paradox_rich_presence.games import vic3  # noqa: E402
from paradox_rich_presence.logtail import LogTailer  # noqa: E402

PREFIX = "[20:30:29][jomini_effect_impl.cpp:454]: common/on_actions/drp_on_actions.txt:25: DRP|2|"
BASE = [
    "local|GBR", "begin|GBR",
    "kv|GBR|country|Great Britain", "kv|GBR|date|April 1, 1839",
    "kv|GBR|gdp|29.4M", "kv|GBR|gdp_rank|2", "kv|GBR|population|25.86M", "kv|GBR|rank|great_power",
]


def presence(extra, flags=None):
    p = vic3.Vic3Presence(game_config(DEFAULT_CONFIG, vic3.SPEC), flags or {})
    p.feed(vic3.parse_line("[x][pdx_transition_task.cpp:328]: Transition Empty->Game took: 3 seconds"))
    for line in BASE + extra + ["end|GBR"]:
        p.feed(vic3.parse_line(PREFIX + line))
    return p


class ParseTests(unittest.TestCase):
    def test_kv_and_item(self):
        self.assertEqual(vic3.parse_line(PREFIX + "kv|GBR|gdp|25.4M"),
                         {"event": "kv", "tag": "GBR", "key": "gdp", "value": "25.4M"})
        self.assertEqual(vic3.parse_line(PREFIX + "item|GBR|enemy|Russia")["value"], "Russia")

    def test_format_codes_are_stripped(self):
        ev = vic3.parse_line(PREFIX + "kv|TUR|country|#v Ottoman Empire#!")
        self.assertEqual(ev["value"], "Ottoman Empire")

    def test_unrelated_and_old_protocol_lines_are_ignored(self):
        self.assertIsNone(vic3.parse_line("[20:00][x.cpp:1]: Total time mesh in 0 ms"))
        self.assertIsNone(vic3.parse_line("x: DRP|1|month|GBR|Great Britain|..."))

    def test_year_of(self):
        self.assertEqual(vic3.year_of("June 1, 1836"), "1836")
        self.assertEqual(vic3.year_of("1 Mart 1901"), "1901")  # other localizations


class ActivityTests(unittest.TestCase):
    def test_peace(self):
        act = presence(["kv|GBR|war|no"], {"GBR": {"iso": "gb"}}).activity()
        self.assertEqual(act["details"], "Great Britain · Great Power")
        self.assertEqual(act["state"], "1839 · £29.4M · 25.86M pop")
        self.assertEqual(act["assets"]["large_image"], "https://flagcdn.com/w320/gb.png")
        self.assertEqual(act["assets"]["large_text"], "GDP £29.4M (#2) · Population 25.86M")
        self.assertEqual(act["assets"]["small_text"], "At peace")

    def test_war_replaces_economy(self):
        act = presence(["kv|GBR|war|yes", "item|GBR|enemy|Russia", "item|GBR|enemy|Prussia",
                        "item|GBR|enemy|Austria"]).activity()
        self.assertEqual(act["state"], "1839 · ⚔ At war: Russia, Prussia +1")
        self.assertEqual(act["assets"]["small_text"], "At war: Russia, Prussia +1")

    def test_revolution_and_play(self):
        act = presence(["kv|GBR|war|yes", "item|GBR|enemy|Revolutionaries",
                        "item|GBR|enemy_rev|Revolutionaries"]).activity()
        self.assertIn("🔥 Civil war: Revolutionaries", act["state"])
        act = presence(["kv|GBR|war|no", "item|GBR|play_enemy|France"]).activity()
        self.assertEqual(act["state"], "1839 · 🎯 Diplomatic play: France")

    def test_unknown_flag_falls_back_to_logo(self):
        act = presence(["kv|GBR|war|no"]).activity()
        self.assertEqual(act["assets"]["large_image"], DEFAULT_CONFIG["large_image"])

    def test_menu_and_waiting(self):
        p = vic3.Vic3Presence(game_config(DEFAULT_CONFIG, vic3.SPEC))
        self.assertEqual(p.activity()["details"], "Main menu")
        p.feed({"event": "entered_game"})
        self.assertEqual(p.activity()["state"], "Waiting for the first month…")

    def test_wikimedia_flag_url(self):
        url = vic3.flag_url({"wiki": "Flag of Russia.svg"})
        self.assertEqual(url, "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f3/"
                              "Flag_of_Russia.svg/330px-Flag_of_Russia.svg.png")


class LogTailerTests(unittest.TestCase):
    def test_reads_appended_lines_and_follows_rotation(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "debug.log"
            path.write_text("a\nb\n", encoding="utf-8")
            t = LogTailer(path)
            self.assertEqual(t.read_lines(), ["a", "b"])
            with open(str(path), "a", encoding="utf-8") as f:
                f.write("c\npartial")
            self.assertEqual(t.read_lines(), ["c"])
            t.close()
            # On launch the game moves the old file away and creates a new one
            os.replace(str(path), str(Path(d) / "debug.1.log"))
            path.write_text("new\n", encoding="utf-8")
            self.assertEqual(t.read_lines(), ["new"])
            t.close()


class ConfigTests(unittest.TestCase):
    def test_game_overrides(self):
        cfg = dict(DEFAULT_CONFIG, games={"vic3": {"client_id": "42", "country_tag": "TUR"}})
        merged = game_config(cfg, vic3.SPEC)
        self.assertEqual(merged["client_id"], "42")
        self.assertEqual(merged["country_tag"], "TUR")
        self.assertEqual(merged["large_text"], "Victoria 3")
        self.assertEqual(game_config(DEFAULT_CONFIG, vic3.SPEC)["client_id"], vic3.SPEC.client_id)


if __name__ == "__main__":
    unittest.main()
