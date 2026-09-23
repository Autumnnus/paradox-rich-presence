#!/bin/bash
# Paradox Rich Presence - macOS uninstaller
#
#   curl -fsSL https://raw.githubusercontent.com/Autumnnus/paradox-rich-presence/main/packaging/macos/uninstall.sh | bash
set -euo pipefail

LABEL="io.github.autumnnus.paradox-rich-presence"
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
rm -f "$HOME/Library/LaunchAgents/$LABEL.plist"
rm -rf "$HOME/Library/Application Support/ParadoxRichPresence"
echo "Paradox Rich Presence has been uninstalled."
