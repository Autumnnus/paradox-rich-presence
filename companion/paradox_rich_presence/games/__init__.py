"""Desteklenen oyunlarin kaydi.

Yeni bir oyun eklemek icin games/<oyun>.py icinde bir GameSpec tanimlanir ve
asagidaki listeye eklenir (bkz. docs/adding-a-game.md).
"""

from dataclasses import dataclass, field
from typing import Callable, FrozenSet


@dataclass(frozen=True)
class GameSpec:
    key: str                       # kisa ad; ayarlarda ve loglarda kullanilir (ornegin "vic3")
    name: str                      # gorunen ad
    client_id: str                 # oyuna ozel Discord Application ID
    process_names: FrozenSet[str]  # kucuk harfli surec adlari (Windows ve Mac/Linux)
    docs_folder: str               # Belgeler/Paradox Interactive altindaki klasor adi
    create_presence: Callable      # (cfg) -> feed(ev), activity() arayuzlu nesne
    parse_line: Callable           # (satir) -> olay sozlugu ya da None
    log_file: str = "debug.log"
    extra: dict = field(default_factory=dict)


def all_games():
    from . import vic3
    return [vic3.SPEC]
