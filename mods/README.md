# Mods

One folder per game. Games do not load mods from here; copy a folder's contents into the game's mod folder when releasing an update:

| Game | Source | Target |
|---|---|---|
| Victoria 3 | `mods/vic3/` | `Documents/Paradox Interactive/Victoria 3/mod/<mod name>/` |

The mod and the companion must use the same protocol version (`DRP|2|...` for Victoria 3). Release both together when the protocol changes.
