# Modlar

Her klasör bir oyunun modudur. Oyunlar modu doğrudan buradan okumaz. Güncelleme yaparken klasörün içeriğini oyunun mod klasörüne elle kopyala:

| Oyun | Kaynak | Hedef |
|---|---|---|
| Victoria 3 | `mods/vic3/` | `Belgeler/Paradox Interactive/Victoria 3/mod/Discord Rich Presence/` |

Mod dosyaları yardımcı programla aynı protokol sürümünü kullanmalı (Victoria 3 için `DRP|2|...`). Protokolü değiştiren bir güncellemede mod ve yardımcı program birlikte yayınlanmalı.

Planlanan oyunlar (CK3, EU5, HOI4) için bkz. [docs/adding-a-game.md](../docs/adding-a-game.md).
