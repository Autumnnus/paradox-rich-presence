#!/bin/bash
# Paradox Rich Presence - macOS installer
#
#   curl -fsSL https://raw.githubusercontent.com/Autumnnus/paradox-rich-presence/main/packaging/macos/install.sh | bash
#
# Installs the companion to ~/Library/Application Support/ParadoxRichPresence and adds a
# LaunchAgent that runs it in the background at login. Downloaded through the terminal,
# so Gatekeeper does not block it; no administrator rights needed.
set -euo pipefail

REPO="Autumnnus/paradox-rich-presence"
LABEL="io.github.autumnnus.paradox-rich-presence"
BASE="$HOME/Library/Application Support/ParadoxRichPresence"
APP="$BASE/app"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

say() { printf '\033[1m==>\033[0m %s\n' "$*"; }
fail() { printf '\033[31mError:\033[0m %s\n' "$*" >&2; exit 1; }

[ "$(uname)" = "Darwin" ] || fail "This script is for macOS only."

# Python 3.8+ (ships with the Xcode Command Line Tools)
PY=""
for candidate in /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3; do
    if [ -x "$candidate" ] && "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 8))' 2>/dev/null; then
        PY="$candidate"
        break
    fi
done
if [ -z "$PY" ]; then
    xcode-select --install 2>/dev/null || true
    fail "Python 3 not found. Click 'Install' in the dialog that opened, then run this command again."
fi

# Source: a local folder via PRP_SOURCE (development), otherwise the latest GitHub release
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
if [ -n "${PRP_SOURCE:-}" ]; then
    SRC="$PRP_SOURCE"
    say "Using local source: $SRC"
else
    TAG="$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" 2>/dev/null \
        | "$PY" -c 'import json,sys; print(json.load(sys.stdin).get("tag_name",""))' 2>/dev/null || true)"
    REF="${PRP_REF:-${TAG:-main}}"
    say "Downloading $REPO ($REF)"
    curl -fsSL "https://codeload.github.com/$REPO/tar.gz/$REF" | tar -xz -C "$TMP" --strip-components=1
    SRC="$TMP"
fi
[ -d "$SRC/companion/paradox_rich_presence" ] || fail "companion/paradox_rich_presence not found in source."

say "Installing to $APP"
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

say "Done. Paradox Rich Presence is running in the background and starts at login."
echo "    If macOS asks whether python3 may access your Documents folder, click Allow"
echo "    (the game's log file is under Documents/Paradox Interactive)."
echo "    Log: $BASE/companion.log"
echo "    To uninstall:"
echo "    curl -fsSL https://raw.githubusercontent.com/$REPO/main/packaging/macos/uninstall.sh | bash"
