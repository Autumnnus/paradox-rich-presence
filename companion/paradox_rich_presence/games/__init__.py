"""Registry of supported games.

To add a game, define a GameSpec in games/<game>.py and add it to the list below
(see docs/adding-a-game.md).
"""

from dataclasses import dataclass, field
from typing import Callable, FrozenSet


@dataclass(frozen=True)
class GameSpec:
    key: str                       # short name used in config and logs, e.g. "vic3"
    name: str                      # display name
    client_id: str                 # Discord Application ID for this game
    process_names: FrozenSet[str]  # lowercase process names (Windows and macOS/Linux)
    docs_folder: str               # folder name under Documents/Paradox Interactive
    create_presence: Callable      # (cfg) -> object with feed(ev) and activity()
    parse_line: Callable           # (line) -> event dict or None
    log_file: str = "debug.log"
    extra: dict = field(default_factory=dict)


def all_games():
    from . import vic3
    return [vic3.SPEC]
