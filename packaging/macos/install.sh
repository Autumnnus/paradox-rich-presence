#!/bin/bash
# Paradox Rich Presence - macOS kurulumu
#
#   curl -fsSL https://raw.githubusercontent.com/Autumnnus/paradox-rich-presence/main/packaging/macos/install.sh | bash
#
# Yardimci programi ~/Library/Application Support/ParadoxRichPresence altina kurar ve
# oturum acilisinda arka planda baslatan bir LaunchAgent ekler. Terminal uzerinden
# indirildigi icin Gatekeeper uyarisi cikmaz; yonetici izni gerekmez.
set -euo pipefail

REPO="Autumnnus/paradox-rich-presence"
LABEL="io.github.autumnnus.paradox-rich-presence"
BASE="$HOME/Library/Application Support/ParadoxRichPresence"
APP="$BASE/app"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

say() { printf '\033[1m==>\033[0m %s\n' "$*"; }
fail() { printf '\033[31mHata:\033[0m %s\n' "$*" >&2; exit 1; }

[ "$(uname)" = "Darwin" ] || fail "Bu betik yalnizca macOS icindir."

# Python 3.8+ (macOS Komut Satiri Araclari ile gelir)
PY=""
for candidate in /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3; do
    if [ -x "$candidate" ] && "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 8))' 2>/dev/null; then
        PY="$candidate"
        break
    fi
done
if [ -z "$PY" ]; then
    xcode-select --install 2>/dev/null || true
    fail "Python 3 bulunamadi. Acilan pencereden 'Yukle'ye basin; kurulum bitince bu komutu yeniden calistirin."
fi

# Kaynak: PRP_SOURCE ile yerel klasor (gelistirme), yoksa son GitHub surumu
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
if [ -n "${PRP_SOURCE:-}" ]; then
    SRC="$PRP_SOURCE"
    say "Yerel kaynak kullaniliyor: $SRC"
else
    TAG="$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" 2>/dev/null \
        | "$PY" -c 'import json,sys; print(json.load(sys.stdin).get("tag_name",""))' 2>/dev/null || true)"
    REF="${PRP_REF:-${TAG:-main}}"
    say "Indiriliyor: $REPO ($REF)"
    curl -fsSL "https://codeload.github.com/$REPO/tar.gz/$REF" | tar -xz -C "$TMP" --strip-components=1
    SRC="$TMP"
fi
[ -d "$SRC/companion/paradox_rich_presence" ] || fail "Kaynakta companion/paradox_rich_presence bulunamadi."

say "Kuruluyor: $APP"
mkdir -p "$APP" "$HOME/Library/LaunchAgents"
rm -rf "$APP/paradox_rich_presence"
cp -R "$SRC/companion/paradox_rich_presence" "$APP/"

cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>$LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PY</string>
        <string>-m</string>
        <string>paradox_rich_presence</string>
    </array>
    <key>WorkingDirectory</key><string>$APP</string>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><dict><key>SuccessfulExit</key><false/></dict>
    <key>ProcessType</key><string>Background</string>
    <key>StandardErrorPath</key><string>$BASE/launchd.log</string>
</dict>
</plist>
PLIST

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"

say "Kurulum tamam. Paradox Rich Presence arka planda calisiyor ve oturum acilisinda kendiliginden baslar."
echo "    macOS 'python3 Belgeler klasorune erismek istiyor' diye sorarsa Izin Ver'e basin"
echo "    (oyunun log dosyasi Belgeler/Paradox Interactive altindadir)."
echo "    Log: $BASE/companion.log"
echo "    Kaldirmak icin:"
echo "    curl -fsSL https://raw.githubusercontent.com/$REPO/main/packaging/macos/uninstall.sh | bash"
