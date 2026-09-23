# Yeni oyun ekleme

Victoria 3 örnek alınarak (`mods/vic3`, `companion/paradox_rich_presence/games/vic3.py`) yeni bir Paradox oyunu şu adımlarla eklenir.

## 1. Discord uygulaması

[Discord Developer Portal](https://discord.com/developers/applications)'da oyunun adıyla yeni bir uygulama aç, ör. "Crusader Kings III". Discord bu adı profilde "… oynuyor" başlığı olarak gösterir.

- **Application ID**'yi kopyala.
- **Rich Presence → Art Assets** altına `logo` adıyla oyunun logosunu yükle. Bayrak ya da portre bulunamadığında bu görsel gösterilir.

## 2. Mod (`mods/<oyun>/`)

Mod, oyunun `debug.log` dosyasına `debug_log` efektiyle `DRP|<sürüm>|...` satırları yazar. Victoria 3'teki protokol:

```
DRP|2|local|<yerel oyuncu>
DRP|2|begin|<kimlik>
DRP|2|kv|<kimlik>|<anahtar>|<değer>
DRP|2|item|<kimlik>|<anahtar>|<değer>
DRP|2|end|<kimlik>
```

Dikkat edilecekler:

- **Tooltip döndüren veri fonksiyonları** (ör. Victoria 3'te `GetRank`) log'a işaretleme kodlarıyla yazılır. Bunların yerine koşullarla sabit anahtarlar logla, çeviriyi yardımcı programda yap.
- **Tetikleyici seç.** Oyuncuya özgü ve seyrek çalışan bir `on_action` kullan: Victoria 3'te `on_monthly_pulse`. Bütün ülkeler için çalışan tetikleyicilerde mutlaka oyuncuyla sınırla (`is_player = yes` / `is_ai = no`).
- **Klasör yapısı oyuna göre değişir.** Victoria 3 `.metadata/metadata.json` kullanır. CK3, EU4 ve HOI4 ise `descriptor.mod` dosyası ile `mod/` klasöründe bir `.mod` dosyası kullanır.
- **Önce doğrula.** Oyunda bir ay ilerletip `Belgeler/Paradox Interactive/<Oyun>/logs/debug.log` içinde satırların doğru çıktığını kontrol et.

## 3. Yardımcı program (`companion/paradox_rich_presence/games/<oyun>.py`)

Modülde iki şey olmalı: satırları olaylara çeviren bir `parse_line(line)` fonksiyonu ve `feed(ev)` ile `activity()` yöntemlerini sağlayan bir durum sınıfı. Sonunda bir `GameSpec` tanımlanır:

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

Ardından `games/__init__.py` içindeki `all_games()` listesine ekle.

- `process_names`: Windows'taki `.exe` adı ve Mac/Linux'taki süreç adı, küçük harfle.
- `docs_folder`: `Belgeler/Paradox Interactive` altındaki klasörün tam adı.
- Oyun menüye dönüş ve kayıt yükleme gibi durumları kendi log'unda farklı yazabilir. Victoria 3'te `Transition Empty->Game` ve `Transition Game->Empty` satırları kullanılıyor.

## 4. Test

`companion/tests/test_<oyun>.py` altına gerçek log satırlarından örneklerle testler ekle ve dene:

```sh
python3 -m unittest discover -s companion/tests
python3 companion/run.py --game ck3 --log debug.log --dry-run
```

## 5. README

README'deki oyun tablosunu güncelle.
