# Windows kod imzalama: SignPath Foundation

Windows sürümleri [SignPath Foundation](https://signpath.org)'ın açık kaynak projelere ücretsiz verdiği sertifikayla imzalanır. İmzalı dosyada "bilinmeyen yayıncı" uyarısı çıkmaz.

Kurulum bir kez yapılır. Sıra önemli, çünkü SignPath başvuru için projenin önceden yayınlanmış olmasını istiyor.

## 1. Ön koşullar

- [ ] Repo GitHub'da **herkese açık** olmalı, OSI onaylı bir lisans taşımalı (MIT, `LICENSE`).
- [ ] GitHub hesabında **iki aşamalı doğrulama** açık olmalı. SignPath hesabında da açılacak.
- [ ] README'de "Code signing policy" ve "Privacy policy" bölümleri olmalı (hazır).
- [ ] İndirme sayfasında programın ne yaptığı anlatılmalı (README ve sürüm notları).

## 2. İmzasız ilk sürüm

SignPath yapılandırılmadan gönderilen bir `v*` etiketi, imzasız exe'yi **ön sürüm** (pre-release) olarak yayınlar:

```sh
git tag v0.1.0 && git push origin v0.1.0
```

Bu sürüm başvuruda "projenin yayınlanmış hâli" olarak gösterilir.

## 3. Başvuru

1. <https://signpath.org/apply> adresindeki formu doldur.
   - Proje: `Paradox Rich Presence`, repo: `https://github.com/Autumnnus/paradox-rich-presence`
   - Derleme sistemi: GitHub Actions, imzalanacak dosya: `ParadoxRichPresence.exe`
   - Açıklama: Paradox oyunları için Discord Rich Presence yardımcı programı. Oyunun yerel log dosyasını okur ve yerel Discord uygulamasına iletir, ağ isteği yapmaz.
2. Onay gelince SignPath bir organizasyon açar ve davet gönderir.

Onay süreci birkaç gün ile birkaç hafta arasında sürebilir.

## 4. SignPath paneli

Onaydan sonra <https://app.signpath.io> üzerinde:

1. **Trusted build system:** GitHub.com bağlantısının organizasyona eklendiğini kontrol et. SignPath Foundation projelerinde genelde hazır gelir.
2. **Project:** slug `paradox-rich-presence`, repository URL yukarıdaki adres.
3. **Artifact configuration:** Yeni bir yapılandırma oluştur ve [`.signpath/artifact-configuration.xml`](../.signpath/artifact-configuration.xml) içeriğini yapıştır. Slug'ı not et; varsayılan `initial`.
4. **Signing policies:** `test-signing` ve `release-signing` politikalarının olduğunu kontrol et. Release politikasında onaylayıcı olarak kendini seç.
5. **API token:** Sağ üstten kullanıcı menüsü → *My profile* → *API tokens*, ya da bir CI kullanıcısı oluşturup ona token ver. Bu kullanıcıya projede **Submitter** rolü verilmeli.
6. Organizasyon kimliğini (Organization ID) not et. *Settings* sayfasında görünür.

## 5. GitHub ayarları

Repo → *Settings* → *Secrets and variables* → *Actions*:

| Tür | Ad | Değer |
|---|---|---|
| Secret | `SIGNPATH_API_TOKEN` | 4. adımdaki token |
| Variable | `SIGNPATH_ORGANIZATION_ID` | Organizasyon kimliği |
| Variable | `SIGNPATH_PROJECT_SLUG` | Varsayılan `paradox-rich-presence` ise gerekmez |
| Variable | `SIGNPATH_ARTIFACT_CONFIGURATION_SLUG` | Varsayılan `initial` ise gerekmez |

`SIGNPATH_ORGANIZATION_ID` tanımlandığı andan itibaren iş akışı imzalamaya başlar.

## 6. Test

*Actions* → *Release* → *Run workflow* ile elle çalıştır. Bu çalıştırma `test-signing` politikasını kullanır ve sonucu yalnızca artifact olarak yükler, sürüm yayınlamaz.

## 7. İmzalı sürüm

1. `companion/paradox_rich_presence/__init__.py` içindeki `__version__` değerini yükselt ve commit et.
2. Etiketi gönder: `git tag v0.2.0 && git push origin v0.2.0`
3. İş akışı imzalama isteğini gönderir ve bekler. **SignPath panelinde isteği onayla.** Foundation kuralı gereği her sürüm elle onaylanır. İş akışı onay için varsayılan olarak 10 dakika bekler.
4. Onaydan sonra imzalı exe sürüme eklenir.

## Kurallar (özet)

Tam metin: <https://signpath.org/terms>

- Yalnızca bu repodan, GitHub Actions'ta derlenen dosyalar imzalanır. Elle derlenen dosya imzalanamaz.
- Program kullanıcıya sormadan sistem ayarı değiştirmez. Otomatik başlatma ilk açılışta sorulur.
- Kaldırma yolu belgelenmiş olmalı: Programı yeniden açınca durdurma ve otomatik başlatmayı kaldırma seçeneği çıkar.
- Programa kullanıcı verisini dışarı gönderen bir özellik eklenirse gizlilik politikası güncellenmeli ve kurulumda gösterilmeli.
