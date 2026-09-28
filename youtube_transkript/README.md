# YouTube Oynatma Listesi → Transkript

Bir YouTube oynatma listesindeki **tüm videoların** yazıya dökülmüş hâlini
(.txt) indirir. Kanal üyelerine özel ("Katıl" ile açılan) videolar da dahil.

## Neden hazır araçlar çalışmıyordu?

Üyelere özel videolar sadece **üye olan hesapla giriş yapınca** açılır.
Transkript siteleri, tarayıcı eklentileri ve `youtube-transcript-api` gibi
araçlar senin hesabınla giriş yapmadığı için bu videolarda
*"Join this channel to get access to members-only content"* hatası alır.

Bu script [yt-dlp](https://github.com/yt-dlp/yt-dlp)'yi **senin tarayıcındaki
YouTube oturumunla** (çerezlerle) çalıştırır. Bu yüzden **kendi bilgisayarında**
çalıştırılmalı. GitHub Actions, Colab ya da Kaggle'da çalıştırma: çerezlerini
oraya yüklemen gerekir ve YouTube sunucu IP'lerini "bot" diye engelliyor.

## 1. Kurulum (tek seferlik)

1. **Python 3.10 veya üstünü** kur: <https://www.python.org/downloads/>
   (Windows'ta kurulumun ilk ekranında **"Add python.exe to PATH"** kutusunu işaretle.)
2. Bu klasördeki **`transkript_indir.py`** dosyasını indir (GitHub'da dosyayı
   aç → sağ üstteki indirme düğmesi, "Download raw file"). Örneğin Masaüstü'nde
   `transkript` adlı bir klasöre koy.
3. O klasörde komut satırı aç:
   - **Windows:** Klasörü Dosya Gezgini'nde aç, üstteki adres çubuğuna `cmd`
     yazıp Enter'a bas.
   - **macOS:** Terminal'i aç, `cd ` yazıp (sonunda boşluk var) klasörü
     pencereye sürükle, Enter'a bas.
4. Gerekli paketleri kur (yt-dlp + YouTube için gereken JavaScript motoru deno):

   ```
   Windows:  py -m pip install -U "yt-dlp[default,deno,curl-cffi]"
   macOS:    python3 -m pip install -U "yt-dlp[default,deno,curl-cffi]"
   ```

   (Unutursan script eksik paketleri ilk çalışmada kendisi kurmaya çalışır.)

## 2. Tarayıcıda giriş

- Kanala **üye olan hesapla** youtube.com'a giriş yap ve bir üyelere özel
  videonun açıldığını kontrol et.
- Önerilen tarayıcı **Firefox**. Windows'ta Chrome'un çerezleri dışarıdan
  okunamıyor. Chrome kullanıyorsan aşağıdaki [cookies.txt yöntemine](#çerezler-okunamadı-chrome--edge--brave) bak.

## 3. Çalıştır

Önce 2 videoyla dene:

```
Windows:  py transkript_indir.py --tarayici firefox --sadece 1-2
macOS:    python3 transkript_indir.py --tarayici firefox --sadece 1-2
```

Sorun yoksa hepsini indir (link verilmezse kurs listesini kullanır):

```
py transkript_indir.py --tarayici firefox
```

Başka bir liste ya da tek video için linki başa yaz:

```
py transkript_indir.py "https://www.youtube.com/playlist?list=..." --tarayici firefox
```

Başta **"YouTube oturum çerezleri bulundu."** yazısını görmelisin. Video başına
~15-20 saniye sürer (YouTube'u yormamak için bilerek bekliyor), yani 50 video
yaklaşık 15 dakika. İstediğin an Ctrl+C ile durdurabilirsin; aynı komutu tekrar
çalıştırınca **kaldığı yerden devam eder**.

## Çıktılar

Script'in yanındaki `transkriptler/` klasörüne yazılır:

| Dosya | İçerik |
|---|---|
| `001 - <Başlık>.txt`, `002 - ...` | Her ders: başlık, link, kaynak ve `[dk:sn]` zaman damgalı paragraflar |
| `_TUM_TRANSKRIPTLER.txt` | Hepsi tek dosyada, liste sırasıyla. NotebookLM, Claude ya da ChatGPT'ye yükleyip soru sormak/özet çıkarmak için |
| `_durum.csv` | Hangi video tamam, hangisi neden hatalı (Excel'de açılır) |
| `_ham/` | İndirilen ham altyazılar. Tekrar indirmemek için saklanıyor, silme |

- Kanal kendi altyazısını eklediyse o, yoksa YouTube'un otomatik altyazısı kullanılır.
- YouTube'un Türkçe otomatik altyazısında **noktalama yok**; metin ~30 saniyelik
  paragraflara bölünür.
- Listeye yeni ders eklenince aynı komutu tekrar çalıştır; sadece yeniler iner.

## Altyazısı olmayan videolar (Whisper)

Bazı videolarda altyazı hiç olmayabilir (`_durum.csv`'de "altyazısı yok" yazar).
Onlar için sesi indirip **kendi bilgisayarında** yazıya döken Whisper'ı aç:

```
py transkript_indir.py --tarayici firefox --whisper yedek
```

- Gerekli paket (faster-whisper) otomatik kurulur, model ilk seferde (~1,6 GB) iner.
- İşlemcide (CPU) yavaştır: 1 saatlik ders bilgisayarına göre 20-60 dakika sürebilir.
  Daha hızlı ama daha az doğru: `--whisper-model small`.
- NVIDIA ekran kartın varsa `--whisper-gpu` (CUDA 12 ve cuDNN 9 kurulu olmalı).
- `--whisper hepsi`: YouTube altyazısı yerine her video için Whisper kullanır.
  Noktalamalı ve genelde daha düzgün metin verir ama çok daha uzun sürer.

## Tüm seçenekler

| Seçenek | Açıklama |
|---|---|
| `--tarayici firefox` | Çerezleri bu tarayıcıdan al: `firefox`, `chrome`, `edge`, `brave`, `opera`, `safari`, `vivaldi`. Belirli profil: `"chrome:Profile 1"` |
| `--cerez cookies.txt` | Tarayıcıdan dışa aktarılmış çerez dosyası |
| `--sadece 1-3` | Sadece bu sıradaki videolar (`1,4,7` de olur) |
| `--dil tr` | Tercih edilen altyazı dili (varsayılan `tr`) |
| `--cikti KLASOR` | Çıktı klasörü (varsayılan `transkriptler/`) |
| `--bekleme 5` | Videolar arası bekleme (saniye). Hız sınırına takılırsan artır |
| `--whisper yedek` / `hepsi` | Bkz. yukarı |
| `--zamansiz` | `[dk:sn]` zaman damgalarını koyma |
| `--yeniden` | Daha önce inenleri de baştan indir |
| `--ayrinti` | yt-dlp'nin tüm mesajlarını göster (hata ararken) |
| `--ytdlp="..."` | yt-dlp'ye aynen geçecek ek seçenekler (ileri düzey) |

## Sorun giderme

İlk iş **yt-dlp'yi güncelle**. YouTube sık değişiyor, çoğu hata bununla geçer:

```
py -m pip install -U "yt-dlp[default,deno,curl-cffi]"
```

### "Üyelere özel video açılamadı" / "Join this channel..."

- Başta "YouTube oturum çerezleri bulundu." yazıyor mu? Yazmıyorsa o tarayıcıda
  giriş yapılmamış ya da yanlış profil okunuyor.
- Tarayıcıda birden fazla Google hesabı açıksa en garantisi, **sadece üye olan
  hesapla giriş yapılmış** ayrı bir tarayıcı/profil kullanmak.
- Üyelik seviyen bazı videoları kapsamıyorsa o videolar bu hatayı vermeye devam eder.

### Çerezler okunamadı (Chrome / Edge / Brave)

Windows'ta Chrome çerezlerini şifreliyor ve dışarıdan okunmasına izin vermiyor.
İki çözüm var:

1. **Firefox kullan** (en kolayı): Firefox'ta üye hesapla YouTube'a giriş yap,
   `--tarayici firefox` ile çalıştır.
2. **cookies.txt dışa aktar:**
   1. Tarayıcına **"Get cookies.txt LOCALLY"** eklentisini kur. Benzer adlı başka
      eklentiler çerez çalabiliyor, tam adına dikkat et. Eklenti ayarlarından
      gizli pencerede çalışmasına izin ver.
   2. **Gizli pencere** aç, youtube.com'a üye hesapla giriş yap, eklentiyle
      youtube.com çerezlerini **Export** et. Dosyayı script'in yanına
      `cookies.txt` adıyla kaydet ve gizli pencereyi hemen kapat. (Açık
      YouTube sekmeleri çerezleri yeniler; gizli pencereyle alınan dosya daha
      uzun süre geçerli kalır.)
   3. `py transkript_indir.py --cerez cookies.txt`

### "Sign in to confirm you're not a bot"

Çerezle çalıştırdığından emin ol, VPN açıksa kapat, bir süre bekleyip tekrar dene.

### Hız sınırı (429 / "rate-limited")

Script kendiliğinden durur. ~1 saat bekleyip aynı komutu tekrar çalıştır
(kaldığı yerden devam eder). Sık oluyorsa `--bekleme 15` kullan.

### "PO token" uyarısı ya da "altyazıyı boş döndürdü"

yt-dlp'yi güncelle. Devam ederse o videolar için `--whisper yedek` kullan.
İleri düzey çözüm: yt-dlp'nin [PO Token rehberi](https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide).

### Başka bir hata

`--ayrinti` ile çalıştırıp çıkan mesajı paylaş. **cookies.txt içeriğini asla paylaşma.**

## Güvenlik ve kullanım notu

- **cookies.txt hesabının anahtarıdır:** kimseyle paylaşma, GitHub'a yükleme,
  işin bitince sil. (Bu klasördeki `.gitignore` git ile yüklenmesini engeller
  ama GitHub web sayfasından elle yüklersen korumaz.)
- **Transkriptler kanalın üyelere özel içeriğidir:** kişisel çalışman için
  kullan, paylaşma ve bu repoya yükleme. `transkriptler/` klasörü de
  `.gitignore`'da.
- Script hesabını riske atmamak için istekler arasında bilerek bekliyor;
  beklemeleri kısaltma.
