# BIST Tarama Otomasyonu

Bu repo, Kaggle'da manuel çalıştırdığın 3 tarama scriptini GitHub Actions ile
**otomatik ve zamanlanmış** hale getirir. Script'lerin içindeki hesaplama
mantığına (RSI/MACD/OBV, mum formasyonları vb.) hiç dokunulmadı — sadece
"ne zaman, nasıl çalışsın ve sonuç nereye kaydedilsin" kısmı eklendi.

## Ne zaman ne çalışıyor?

| İş | Dosyalar | Zamanlama |
|---|---|---|
| **Günlük tarama** | `xutum_tarama_v2.py`, `xutum_tarama_haftalik_son.py` | Her hafta içi gün 09:30 (İstanbul) |
| **Mum tarama** | `mum_tarama_v1_7_strict_raw_ohlc.py` | Sadece haftanın SON işlem günü ve ayın SON işlem günü, kapanıştan sonra (18:30 İstanbul) |

Mum taramanın "hafta/ay sonu mu?" kararını `gate.py` veriyor. Bu, resmi BIST
(XIST) takvimini kullanıyor — yani resmi tatil yüzünden hafta Cuma yerine
Perşembe bitse bile doğru günü yakalıyor. Mesai günü olmayan (hafta sonu,
resmi tatil) günlerde iş otomatik olarak atlanıyor, boşuna çalışmıyor.

> Not: Türkiye 2016'dan beri yaz saati uygulamıyor (yıl boyu UTC+3), o yüzden
> cron saatleri (`06:30 UTC` ve `15:30 UTC`) yıl boyunca sabit kalıyor,
> ayarlama gerekmiyor.

## Kurulum (tek seferlik, ~10 dakika)

1. **GitHub'da yeni bir repo oluştur**
   - github.com'da sağ üstten **New repository**.
   - İsim: örneğin `bist-tarama-otomasyon`.
   - **Public** seçmeni öneririm (Private de olur ama sonuçları dışarıdan
     okuyup sana bildirim göndermemi kolaylaştırıyor; hassas bir veri değil,
     sadece hisse sinyalleri).
   - "Add a README" kutusunu **işaretleme** (bende zaten hazır bir tane var).

2. **Bu klasördeki dosyaları yükle**
   - Yeni repo sayfasında **"uploading an existing file"** linkine tıkla.
   - Bu pakette (zip) yer alan tüm dosya ve klasörleri (özellikle gizli
     `.github` klasörünü) sürükleyip bırak. (`.github/workflows` klasörünü
     GitHub web arayüzü bazen tek tek dosya sürüklemeni ister; zip'i açtıktan
     sonra `.github/workflows/gunluk-tarama.yml` ve `mum-tarama.yml`
     dosyalarını ayrı ayrı sürükleyebilirsin.)
   - "Commit changes" ile kaydet.

3. **Actions'a yazma izni ver**
   - Repo içinde **Settings → Actions → General** sayfasına git.
   - En altta **"Workflow permissions"** bölümünde
     **"Read and write permissions"** seçeneğini işaretle → Save.
   - (Bu adım atlanırsa, iş sonuçları hesaplar ama repoya kaydedemez.)

4. **Actions'ın açık olduğunu doğrula**
   - Repo üstünde **Actions** sekmesine tıkla. "I understand my workflows,
     go ahead and enable them" gibi bir onay çıkarsa onayla.
   - Sol tarafta iki workflow görmelisin: **"Günlük Tarama (09:30 İstanbul)"**
     ve **"Mum Tarama (Hafta/Ay Sonu Kapanışı)"**.

5. **Bana repo adresini gönder**
   - Repo URL'sini (örn. `https://github.com/kullaniciadi/bist-tarama-otomasyon`)
     bana ilet. Ben de her çalışmadan sonra sonuç tablosunu buradan okuyup
     sana bildirim olarak göndereceğim.

## Elle test etmek istersen

Bir workflow'un zamanlamasını beklemeden hemen çalıştırmak için:
- **Actions** sekmesi → soldan ilgili workflow'u seç → sağ üstte
  **"Run workflow"** butonu → **Run workflow**.
- Birkaç dakika sonra `results/` klasöründe yeni bir tarih klasörü ve
  güncellenmiş CSV'ler oluşur.

## Sonuçlar nerede duruyor?

- `results/gunluk/<TARİH>/` → o günün xutum tarama çıktıları
- `results/gunluk/latest_*.csv` → en güncel günlük tarama sonucu
- `results/mum/<TARİH>/` → o hafta/ay sonu mum tarama çıktıları
- `results/mum/latest.csv` → en güncel mum tarama sonucu

Bu dosyalar repo geçmişinde kalıcı olarak birikir, yani istediğin zaman
geçmiş tarihli bir taramaya da bakabilirsin.

## Dosyalar

- `xutum_tarama_v2.py`, `xutum_tarama_haftalik_son.py`,
  `mum_tarama_v1_7_strict_raw_ohlc.py` — orijinal script'lerin, **değiştirilmeden**.
- `gate.py` — mum taramanın hafta/ay sonu kontrolü (yeni).
- `.github/workflows/*.yml` — zamanlama tanımları (yeni).
- `requirements.txt` — gerekli Python paketleri.

## Temel analiz ön eleme (`temel/`)

Bir yatırımcının "şirket incelerken nelere dikkat ediyorum" videosundaki
**veriden otomatik hesaplanabilen** kriterlerin taraması. Bu bir **ön eleme**:
listeye girmek "al" demek değildir, elle inceleme listesini daraltır.

- **Veri:** EVO / Fintables MCP (`temel/sorgular.sql`). Bu veri kaynağı GitHub
  Actions'tan erişilebilir değil; veri Claude oturumunda çekilip
  `temel/ham/*.csv` olarak kaydedilir. Bilançolar çeyreklik açıklandığı için
  çeyrekte bir güncellemek yeterli.
- **Çalıştırma:** `python temel/temel_tarama.py --tarih 2026-11-25 [--wacc 0.10] [--fd-sna 10]`
- **Çekirdek 4 kriter** (videoda "bu dördü tutuyorsa yatırım sinyalleri başlıyor"):
  K1 ROIC > WACC · K2 sürdürülebilir pozitif serbest nakit · K3 FD/SNA < 10 ·
  K4 işlerde daralma yok (vekil gösterge).
- **Kesin eleme:** finansal yapılar (aracı kurum, MKYO, GSYO; bankalar zaten
  kapsam dışı), halka arzı 1 yıldan yeni olanlar.
- **Kırmızı bayraklar / artılar:** sürekli bedelli, alacak şişmesi, değer
  tuzağı (PD/DD<1 ama ROIC<WACC), borçluyken temettü, zirve kâr, azınlık payı,
  aktifleştirme, kira ağırlığı; temettü, brüt marj, borç azaltma hikâyesi vb.
- **Çıktı:** `results/temel/<TARİH>/ozet.md` (okunabilir rapor),
  `on_eleme.csv` (A: 4/4, B: 3/4 adaylar), `tum_sirketler.csv`,
  `results/temel/latest_on_eleme.csv`.
- Varsayımlar (WACC, bakım yatırımı = min(capex, amortisman), kira
  düzeltmesi) `temel/temel_tarama.py` başındaki açıklamada.
- **Patron/yönetici işlemleri (KAP):** `temel/kap_icerden.py`, aday şirketlerin son 12 aylık
  "Pay Alım Satım Bildirimi"lerini (MKK PDF ekleri dahil) ayrıştırır. Kurumlar/fonlar sayılmaz,
  aile içi devir/virman satış sayılmaz. Net satış ≥ sermayenin %0,25'i veya ≥25 mn TL ise
  `⛔ PATRON/YÖNETİCİ NET SATIŞ` bayrağı; net alım artı olarak yazılır. Ham veri `temel/ham/kap/`.
- **Guidance (beklenti) kontrolü:** EVO guidance tablosundaki beklentiler gerçekleşenle karşılaştırıldı
  (`temel/guidance_degerlendirme.csv`, her satır gerekçeli; ham metin `temel/ham/guidance_ham.csv`).
  Eleme kriteri değil: beklenti açıklamak artı, son iki yıl üst üste tutturamamak bayrak.
- **Azınlık hakları:** `temel/azinlik_karpayi.py`, KAP "Kâr Payı Dağıtım Tablosu"ndan kâr payı
  imtiyazını, bağışları ve YK üyelerine/çalışanlara kârdan payı çıkarır
  (`temel/ham/azinlik/karpayi_ozet.csv`). Üst yönetim ücreti + huzur hakkı 2025/12 dipnotlarından
  elle okundu (`temel/ham/azinlik/yonetici_ucret.csv`, kaynak chunk id'li). Eleme değil, bayrak:
  imtiyaz varsa, bağış net kârın ≥%5'i ise (alıcısı elle bakılır), yönetim ücretleri hem net
  kârın hem esas faaliyet kârının ≥%10'u ise.
