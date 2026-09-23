# Adding a game

Use Victoria 3 as the reference: `mods/vic3` and `companion/paradox_rich_presence/games/vic3.py`.

## 1. Discord application

Create an application named after the game in the [Discord Developer Portal](https://discord.com/developers/applications), e.g. "Crusader Kings III". Discord shows this name as the "Playing" title.

- Copy the **Application ID**.
- Under **Rich Presence → Art Assets**, upload the game logo with the name `logo`. It is shown when no better image is available.

## 2. Mod (`mods/<game>/`)

The mod writes `DRP|<version>|...` lines to the game's `debug.log` with the `debug_log` effect. Victoria 3 uses:

```
DRP|2|local|<local player>
DRP|2|begin|<id>
DRP|2|kv|<id>|<key>|<value>
DRP|2|item|<id>|<key>|<value>
DRP|2|end|<id>
```

- Data functions that return tooltip markup (Victoria 3's `GetRank`) come out garbled in the log. Log fixed keys through triggers instead and translate them in the companion.
- Use an infrequent `on_action` (Victoria 3: `on_monthly_pulse`) and limit it to players.
- Victoria 3 uses `.metadata/metadata.json`; CK3, EU4 and HOI4 use `descriptor.mod`.
- Check the output in `Documents/Paradox Interactive/<Game>/logs/debug.log` before writing the parser.

## 3. Companion (`companion/paradox_rich_presence/games/<game>.py`)

Provide a `parse_line(line)` function and a state class with `feed(ev)` and `activity()`, then define a `GameSpec`:

```python
SPEC = GameSpec(
    key="ck3",
    name="Crusader Kings III",
    client_id="<Application ID>",
    process_names=frozenset({"ck3", "ck3.exe"}),
    docs_folder="Crusader Kings III",
    create_presence=_create_presence,
    parse_line=parse_line,
)
```

Add it to `all_games()` in `games/__init__.py`.

- `process_names`: lowercase process names for Windows (`.exe`) and macOS/Linux.
- `docs_folder`: exact folder name under `Documents/Paradox Interactive`.

## 4. Test

Add `companion/tests/test_<game>.py` with real log lines, then:

```sh
python3 -m unittest discover -s companion/tests
python3 companion/run.py --game ck3 --log debug.log --dry-run
```

Finally, add the game to the supported list in the README.
