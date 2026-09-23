"""Ana dongu: hangi Paradox oyununun acik oldugunu algilar, o oyunun log dosyasini
takip eder ve Discord etkinligini oyuna ozel Application ID ile gunceller.

Kullanim:
    python3 companion/run.py                      # normal calisma
    python3 companion/run.py --dry-run            # Discord'a gondermeden etkinligi yazdir
    python3 companion/run.py --game vic3 --log /yol/debug.log --dry-run   # test
Windows'ta paketlenmis .exe ilk acilista oturum acilisinda baslatmayi sorar;
calisirken yeniden acilirsa durdurma secenegi sunar.
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
    # Bayragi bilinmeyen ulkelerde gosterilecek gorsel: Developer Portal'daki asset adi ya da https adresi
    "large_image": "logo",
    "flags": True,
    "status_icons": True,
    # Discord uye listesinde uygulama adi yerine hangi satir gorunsun: name, details, state
    "status_display": "details",
    # Cok oyunculuda gosterilecek ulke (ornegin "TUR"); bos ise yerel oyuncu
    "country_tag": "",
    # Bu kadar saniye yeni ay gelmezse oyunun duraklatildigi varsayilir
    "pause_after_seconds": 180,
    # Profilde gorunecek butonlar: [{"label": "...", "url": "https://..."}], en fazla 2
    "buttons": [],
    # Oyuna ozel ayarlar ve Application ID degisiklikleri: {"vic3": {"client_id": "..."}}
    "games": {},
}

POLL_SECONDS = 1.0
PROCESS_CHECK_SECONDS = 5.0
MIN_UPDATE_INTERVAL = 15  # Discord etkinlik guncellemelerini yaklasik 15 sn'de bire sinirliyor
STATUS_DISPLAY_TYPES = {"name": 0, "state": 1, "details": 2}


# --------------------------------------------------------------------------- kurulum

def setup_logging(verbose):
    handlers = [logging.handlers.RotatingFileHandler(
        str(system.data_dir() / "companion.log"), maxBytes=512 * 1024, backupCount=1, encoding="utf-8")]
    if sys.stdout is not None:  # konsolsuz Windows derlemesinde stdout yok
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
        log.warning("Ayar dosyasi okunamadi (%s): %s", path, e)
    return cfg


def game_config(cfg, game):
    """Genel ayarlarin uzerine oyuna ozel ayarlar."""
    merged = {k: v for k, v in cfg.items() if k != "games"}
    merged.setdefault("large_text", game.name)
    merged.update(cfg.get("games", {}).get(game.key, {}))
    merged.setdefault("client_id", game.client_id)
    return merged


def finalize(act, cfg, status_display_ok):
    """Discord'a gidecek son eklemeler (butonlar, uye listesi gorunumu)."""
    act = dict(act)
    buttons = [b for b in cfg.get("buttons", []) if b.get("label") and b.get("url")][:2]
    if buttons:
        act["buttons"] = buttons
    if status_display_ok and cfg.get("status_display") in STATUS_DISPLAY_TYPES:
        act["status_display_type"] = STATUS_DISPLAY_TYPES[cfg["status_display"]]
    return act


# --------------------------------------------------------------------------- oturum

class GameSession:
    """Acik olan tek bir oyun icin log takibi, durum ve Discord baglantisi."""

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
        log.info("%s algilandi, log: %s", game.name, path)

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
            log.info("Etkinlik: %s", json.dumps(act, ensure_ascii=False))
            self.last_sent = act
            return
        try:
            if not self.ipc.connected and not self.ipc.connect():
                raise ConnectionError("Discord IPC soketi bulunamadi (Discord acik mi?)")
            self.ipc.set_activity(act)
            log.info("Guncellendi: %s | %s", act.get("details"), act.get("state", ""))
            self.last_sent = act
        except ValueError as e:
            # Eski Discord surumleri status_display_type alanini tanimayabilir
            if self.status_display_ok and "status_display_type" in act:
                log.warning("status_display_type reddedildi, alan olmadan denenecek: %s", e)
                self.status_display_ok = False
                self.next_send_at = 0.0
            else:
                log.warning("Discord etkinligi reddetti: %s", e)
        except (OSError, ConnectionError) as e:
            log.info("Discord'a ulasilamadi: %s (tekrar denenecek)", e)
            self.ipc.close()

    def close(self):
        log.info("%s kapandi", self.game.name)
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


# --------------------------------------------------------------------------- giris

def _windows_startup(args):
    """Paketlenmis Windows uygulamasinin tek ornek, otomatik baslatma ve durdurma akisi.

    Donus: calismaya devam edilecekse WindowsInstance, cikilacaksa None.
    """
    inst = system.WindowsInstance()
    if args.uninstall:
        system.set_autostart(False)
        inst.request_stop()
        system.message_box("%s durduruldu ve otomatik başlatma kaldırıldı." % APP_NAME)
        return None
    if inst.already_running:
        if system.message_box(
                "%s zaten arka planda çalışıyor.\n\n"
                "Durdurmak ve Windows açılışında otomatik başlatmayı kaldırmak ister misiniz?" % APP_NAME,
                yes_no=True):
            system.set_autostart(False)
            inst.request_stop()
        return None
    asked = system.data_dir() / "autostart_asked"
    if not system.autostart_enabled() and not args.no_autostart and not asked.exists():
        # Sistem ayari degistirilmeden once kullaniciya sorulur (SignPath Foundation kosulu);
        # cevap hatirlanir, "Hayir" diyene her acilista yeniden sorulmaz.
        asked.touch()
        autostart = system.message_box(
            "%s arka planda çalışmaya başladı.\n\n"
            "Desteklenen bir Paradox oyununu modu etkin olarak açtığınızda Discord profilinizde görünür.\n\n"
            "Windows her açıldığında kendiliğinden başlasın mı?\n"
            "(Durdurmak ya da bu ayarı kaldırmak için programı yeniden açmanız yeterli.)" % APP_NAME,
            yes_no=True)
        if autostart:
            system.set_autostart(True)
    return inst


def main(argv=None):
    ap = argparse.ArgumentParser(prog="paradox-rich-presence", description=APP_NAME)
    ap.add_argument("--version", action="version", version=__version__)
    ap.add_argument("--dry-run", action="store_true", help="Discord'a gonderme, etkinligi logla")
    ap.add_argument("--game", help="surec kontrolu yapmadan bu oyunu varsay (test icin), ornegin vic3")
    ap.add_argument("--log", help="log dosyasi yolu (test icin)")
    ap.add_argument("--config", help="ayar dosyasi yolu")
    ap.add_argument("--no-autostart", action="store_true", help="Windows'ta otomatik baslatmayi kurma")
    ap.add_argument("--uninstall", action="store_true", help="Windows'ta durdur ve otomatik baslatmayi kaldir")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    setup_logging(args.verbose)
    games = all_games()
    forced = None
    if args.game:
        forced = next((g for g in games if g.key == args.game), None)
        if forced is None:
            ap.error("bilinmeyen oyun: %s (desteklenenler: %s)" % (args.game, ", ".join(g.key for g in games)))

    stop_requested = lambda: False  # noqa: E731
    if system.IS_WINDOWS and getattr(sys, "frozen", False):
        inst = _windows_startup(args)
        if inst is None:
            return
        stop_requested = inst.stop_requested

    log.info("%s %s basladi (%s)", APP_NAME, __version__, ", ".join(g.name for g in games))
    try:
        run(load_config(args.config), games, forced, args.log, args.dry_run, stop_requested)
    except KeyboardInterrupt:
        pass
    log.info("Durduruldu")
