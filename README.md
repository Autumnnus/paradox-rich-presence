# Paradox Rich Presence

Paradox oyunlarında oynadığın ülkeyi Discord profilinde gösterir.

```
Victoria 3
[bayrak]  Büyük Britanya · Üstün Güç
  [⚔]     1839 · ⚔ Savaşta: Rusya
          ⏱ 01:12:05
```

| Oyun | Durum |
|---|---|
| Victoria 3 | ✅ |
| Crusader Kings III | Planlandı |
| Europa Universalis V | Planlandı |
| Hearts of Iron IV | Planlandı |

## Kurulum

İki parçadan oluşur: oyundaki **mod** ve Discord'a bağlanan küçük bir **yardımcı program**. Paradox modları Discord'a doğrudan ulaşamadığı için yardımcı program gerekli. Program bir kez kurulur ve bütün desteklenen oyunlarda çalışır.

### 1. Mod

Steam Workshop'tan moda abone ol ve launcher'da etkinleştir.

### 2. Yardımcı program

**Windows**

1. [Sürümler](https://github.com/Autumnnus/paradox-rich-presence/releases/latest) sayfasından `ParadoxRichPresence.exe` dosyasını indir ve çalıştır.
2. Windows açılışında kendiliğinden başlasın mı diye sorar. Evet dersen bir daha uğraşman gerekmez.

Program arka planda çalışır, penceresi yoktur. **Durdurmak ya da otomatik başlatmayı kaldırmak** için programı yeniden açman yeterli, sana sorar.

**macOS**

Terminal'i aç ve şu komutu yapıştır:

```sh
curl -fsSL https://raw.githubusercontent.com/Autumnnus/paradox-rich-presence/main/packaging/macos/install.sh | bash
```

- Program arka planda çalışır ve oturum açılışında kendiliğinden başlar.
- İlk seferde macOS "python3 Belgeler klasörüne erişmek istiyor" diye sorarsa **İzin Ver**'e bas. Oyunun log dosyası Belgeler klasöründe.
- Python yoksa macOS Komut Satırı Araçları'nı kurmayı önerir. Kurulum bitince komutu yeniden çalıştır.

Kaldırmak için:

```sh
curl -fsSL https://raw.githubusercontent.com/Autumnnus/paradox-rich-presence/main/packaging/macos/uninstall.sh | bash
```

Bu betikler yalnızca yardımcı programı `~/Library/Application Support/ParadoxRichPresence` klasörüne kopyalar ve bir LaunchAgent ekler. Yönetici izni istemez. Çalıştırmadan önce içeriğini [buradan](packaging/macos/install.sh) okuyabilirsin.

## Ayarlar (isteğe bağlı)

Ayar dosyası gerekmez. Değiştirmek istersen `config.json` dosyasını şu klasörde oluştur:

- Windows: `%LOCALAPPDATA%\ParadoxRichPresence\`
- macOS: `~/Library/Application Support/ParadoxRichPresence/`

```json
{
  "flags": true,
  "status_icons": true,
  "status_display": "details",
  "country_tag": "",
  "pause_after_seconds": 180,
  "buttons": [],
  "games": { "vic3": { "country_tag": "TUR" } }
}
```

| Anahtar | Açıklama |
|---|---|
| `flags` / `status_icons` | Bayrak ve durum ikonunu aç/kapat |
| `status_display` | Discord üye listesinde oyun adı yerine görünecek satır: `name`, `details`, `state` |
| `country_tag` | Çok oyunculuda gösterilecek ülke (boşsa kendi ülken) |
| `pause_after_seconds` | Bu süre boyunca oyun tarihi ilerlemezse ⏸ gösterilir |
| `buttons` | Profilde en fazla 2 buton: `[{"label": "...", "url": "https://..."}]` |
| `games` | Oyuna özel ayarlar, ör. `{"vic3": {"country_tag": "TUR"}}` |

Loglar aynı klasördeki `companion.log` dosyasına yazılır.

## Nasıl çalışır

1. **Mod** her oyun ayında oyuncunun ülkesiyle ilgili birkaç satırı oyunun kendi `debug.log` dosyasına yazar (`debug_log` script efekti). Oyun mantığına hiçbir etkisi yoktur.
2. **Yardımcı program** hangi Paradox oyununun açık olduğunu algılar, o oyunun log dosyasını okur ve bilgisayarındaki Discord uygulamasına yerel bağlantı üzerinden iletir.

Bilinen sınırlamalar:
- **Başarımlar:** Script içeren her mod gibi bu mod da başarımları kapatır.
- **Güncelleme sıklığı:** Bilgi oyun ayı başına bir kez güncellenir.
- **Duraklatma:** Oyunun duraklatıldığı doğrudan algılanamıyor. Tarih bir süre ilerlemezse ⏸ gösterilir.
- **Bayraklar:** Oyundaki bayraklar değil, gerçek dünyadaki tarihî bayraklar gösterilir. Bayrağı bilinmeyen ülkelerde oyunun logosu çıkar.

## Geliştirme

```
companion/                     yardımcı program (Python 3.8+, yalnızca standart kütüphane)
  paradox_rich_presence/
    app.py                     ana döngü, oyun algılama, Discord gönderimi
    system.py                  işletim sistemine özgü işler (klasörler, süreçler, Windows)
    discord_ipc.py             Discord yerel RPC istemcisi
    logtail.py                 log takibi
    games/                     oyuna özgü ayrıştırma ve görünüm (vic3.py, ...)
    data/                      bayrak eşlemeleri
  tests/
mods/                          oyun modları (vic3/, ...), oyunun mod klasörüne elle kopyalanır
packaging/                     Windows derleme ve macOS kurulum betikleri
docs/                          SignPath kurulumu, yeni oyun ekleme
```

```sh
python3 -m unittest discover -s companion/tests                  # testler
python3 companion/run.py -v                                      # çalıştır
python3 companion/run.py --game vic3 --log debug.log --dry-run   # Discord'a göndermeden dene
```

Sürüm yayınlamak için `companion/paradox_rich_presence/__init__.py` içindeki `__version__` değerini güncelleyip aynı sürümle `v` önekli bir etiket gönder (ör. `v0.1.0`). GitHub Actions Windows derlemesini yapar, SignPath ile imzalar ve sürümü yayınlar. Ayrıntılar: [docs/signpath.md](docs/signpath.md). Yeni oyun eklemek için: [docs/adding-a-game.md](docs/adding-a-game.md).

## Code signing policy

Free code signing provided by [SignPath.io](https://about.signpath.io), certificate by [SignPath Foundation](https://signpath.org).

- Committers and reviewers: [Autumnnus](https://github.com/Autumnnus)
- Approvers: [Autumnnus](https://github.com/Autumnnus)

Windows builds are produced from this repository by GitHub Actions ([release.yml](.github/workflows/release.yml)) and every release signing request is approved manually.

## Privacy policy

This program will not transfer any information to other networked systems unless specifically requested by the user or the person installing or operating it.

The program only reads the game's local log file and sends the resulting status (country name, rank, in-game year, GDP, population, war status) to the Discord desktop application running on the same computer through Discord's local RPC interface. It makes no network requests of its own. Displaying that status on your profile is subject to [Discord's privacy policy](https://discord.com/privacy). Flag and icon images are referenced by URL (flagcdn.com, Wikimedia Commons, jsDelivr) and are fetched by Discord, not by this program.

## Lisans

[MIT](LICENSE)
