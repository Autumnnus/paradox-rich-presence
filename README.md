# Paradox Rich Presence

Show your country and campaign status on your Discord profile while playing Paradox games.

**Supported games:** Victoria 3 · more coming

## Installation

**1. Mod** — Subscribe to the mod on Steam Workshop and enable it in the launcher.

**2. Companion app** — Paradox mods cannot talk to Discord directly, so a small background app does it. Install it once; it works for every supported game.

- **Windows:** Download `ParadoxRichPresence.exe` from the [latest release](https://github.com/Autumnnus/paradox-rich-presence/releases/latest) and run it.
- **macOS:** Paste this into Terminal:
  ```sh
  curl -fsSL https://raw.githubusercontent.com/Autumnnus/paradox-rich-presence/main/packaging/macos/install.sh | bash
  ```
  If macOS asks whether python3 may access your Documents folder, click **Allow**.

That's it. Keep Discord open and start the game.

### Uninstall

- **Windows:** Run `ParadoxRichPresence.exe` again and choose to stop it.
- **macOS:**
  ```sh
  curl -fsSL https://raw.githubusercontent.com/Autumnnus/paradox-rich-presence/main/packaging/macos/uninstall.sh | bash
  ```

## How it works

The mod writes a few lines about your country to the game's own log file once per in-game month. The companion app detects which game is running, reads those lines and sends them to the Discord app on your computer over Discord's local connection. It makes no network requests of its own.

Like any mod with scripts, the mod disables achievements.

<details>
<summary>Configuration</summary>

Optional. Create `config.json` in `%LOCALAPPDATA%\ParadoxRichPresence` (Windows) or `~/Library/Application Support/ParadoxRichPresence` (macOS):

```json
{
  "flags": true,
  "status_icons": true,
  "status_display": "details",
  "buttons": [],
  "games": { "vic3": { "country_tag": "TUR" } }
}
```

- `flags`, `status_icons`: turn the flag and the status icon on or off
- `status_display`: what replaces the game name in the member list: `name`, `details` or `state`
- `buttons`: up to two profile buttons, `[{"label": "...", "url": "https://..."}]`
- `games.<game>.country_tag`: country to show in multiplayer (defaults to your own)

Logs are written to `companion.log` in the same folder.
</details>

## Development

```sh
python3 -m unittest discover -s companion/tests                  # tests
python3 companion/run.py --game vic3 --log debug.log --dry-run   # try without Discord
```

- `companion/`: the app (Python 3.8+, standard library only)
- `mods/`: one folder per game
- [Adding a game](docs/adding-a-game.md) · [Releasing and code signing](docs/signpath.md)

## Code signing policy

Free code signing provided by [SignPath.io](https://about.signpath.io), certificate by [SignPath Foundation](https://signpath.org).

- Committers and reviewers: [Autumnnus](https://github.com/Autumnnus)
- Approvers: [Autumnnus](https://github.com/Autumnnus)

Windows builds are produced from this repository by GitHub Actions and every release is approved manually before signing.

## Privacy policy

This program will not transfer any information to other networked systems unless specifically requested by the user or the person installing or operating it.

It only reads the game's local log file and passes the resulting status to the Discord app on the same computer. What Discord shows on your profile is subject to [Discord's privacy policy](https://discord.com/privacy). Flag and icon images are referenced by URL and loaded by Discord, not by this program.

## License

[MIT](LICENSE)
