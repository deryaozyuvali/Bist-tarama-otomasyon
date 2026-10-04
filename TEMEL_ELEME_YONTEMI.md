# Temel Eleme Yöntemi

Bu yöntem, Doç. Dr. Serkan Ünal'ın
[Borsa Eğitimi playlist'indeki](https://youtube.com/playlist?list=PL8qjUdvMNhlax9_Dl8MEKn6J-1TDGfGrg)
32 videodan çıkarıldı. Kod: `temel_eleme.py`. Transkriptler: `kaynak/transkript/`.

Videoların ana fikri teknik al-sat değil, **iyi şirkete uzun vadeli ortaklık**.
Hocanın kendisi de "2-3 rasyoya bakmak kadar kolay olsaydı herkes zengin olurdu"
diyor. Bu yüzden script bir "al" listesi üretmez. **Kötüleri eler, kalanları
sıralar.** Kurumsallık, yönetim kalitesi ve teknolojik dönüşüm riski gibi nitel
kontroller yine sende.

## 1. Kesin eleme (bir tanesi yeterli → ❌ ELENDİ)

| Kural | Eşik | Kaynak video |
|---|---|---|
| Hakim ortak payı düşük (halka açıklık yüksek) | hakim pay < %30 | *Borsanın 12 Dersi*: "Hakim ortak payı %50'den, hatta %70'ten yüksekse pozitif; halka açıklık %70'ten yüksekse çok daha dikkatli olmalıyız." *8 Kriter*: "Kurumsallık taviz vermememiz gereken kriterdir." |
| Negatif özkaynak | özkaynak ≤ 0 | *İflas Edecek Firmalar* |
| Son yıl hem faaliyet hem net zarar | ikisi de < 0 | *İflas Edecek Firmalar*, *8 Kriter* (kâr istikrarı) |
| Finansal borç / özkaynak yüksek | > 1,5 | *İflas Edecek Firmalar*: borç özkaynağın yarısı "güvenli seviye" (0,5) |
| Borç faaliyet kârıyla kaç yılda ödenir | net borç / faaliyet kârı > 5 yıl, ya da net borçlu iken faaliyet kârı yok | *İflas Edecek Firmalar*: "Faaliyet kârı ile bu borcu kaç yılda servis edebiliyor?" |
| Likidite (Meg-up örneği) | kısa vadeli finansal borç > nakit **ve** cari oran < 1 | *İflas Edecek Firmalar*: "Nakit rezervi kısa vadeli finansal borca kıyasla yetersiz kaldı." |
| Ölümcül kombinasyon | döngüsel sektör + net borç/özkaynak > 0,5 + faaliyet marjı sektör medyanının altında | *İflas Edecek Firmalar*: "Yüksek finansal borcu varsa, kâr marjı düşükse, bir de döngüsel sektördeyse muhtemelen varlığını koruyamayacak." |

Bankalar, sigortacılar ve holdingler (Conglomerates) borç ve likidite
kurallarından muaf tutulur. Bilançoları doğası gereği borçludur ya da banka
iştiraki konsolide edilir. Muafiyet "Uyarı" sütununda yazar.

## 2. Sekiz kriter puanı (her biri 0–10, toplam 100'e ölçeklenir)

Kaynak: *İyi Hisseleri Diğerlerinden Ayıran 8 Kriter*.

| # | Kriter | Nasıl ölçülüyor |
|---|---|---|
| K1 | Kurumsallık | Hakim ortak payı: ≥%70 → 10, ≥%50 → 8, ≥%30 → 5. Veri yoksa 3. |
| K2 | Risk ve belirsizlik | Savunmacı sektör (gıda, perakende, telekom, enerji dağıtım, sağlık) → 10, döngüsel (otomotiv, beyaz eşya, sanayi, ham madde) → 3, diğerleri → 6. |
| K3 | Kâr istikrarı | Son 4 yılda kârlı yıl oranı × 7, kâr oynaklığı düşükse ve hiç zarar yılı yoksa +3. |
| K4 | Kâr marjı | Faaliyet marjının **sektör içindeki** yüzdelik sırası. Finansallarda net marj kullanılır. |
| K5 | Finansal borç | Net borç/özkaynak: net nakit → 10, <0,25 → 8, <0,5 → 6, <1 → 3. Borç satışlardan hızlı artıyorsa −2 (*İflas* videosu: "borçta artış trendi alarm zilidir"). |
| K6 | Büyüme | Satış ve özkaynak yıllık bileşik büyümesinin yüzdelik sırası. Sıralama kullanıldığı için nominal TL enflasyonu nötrlenir. |
| K7 | Çarpanlar | Sektör içinde düşük F/K, düşük PD/DD, yüksek temettü verimi (*PD/DD*, *Değerlemeye Giriş* videoları). |
| K8 | Sürdürülebilir rekabet avantajı | Doğrudan ölçülemez. Vekil olarak yüksek ortalama ROE ve istikrarlı brüt marj kullanılır (fiyatlama gücü). |

Puanı **60 ve üzeri** olan ve elenmeyen şirket → **ADAY**.

## 3. Güvenlik marjı

Kaynak: *5 Kriterde Güvenlik Marjı*, *Değer Yatırımcılığı*.

- **İçsel değer** = sektör medyan F/K (en fazla 15) × son yıl net kâr.
  Videodaki çarpan yöntemi: "100 lira kâr eden işletmeye 1.000 lira verebilirim."
- **Güvenlik marjı** = 1 − piyasa değeri / içsel değer.
- **Gerekli marj** riske göre artar. Taban %30 (videodaki örnek: 100 TL değere
  %30 marj → 70 TL'den ucuzsa al). Kurumsallık zayıfsa +%20 (videoda aynen
  geçiyor), döngüsel sektörse +%10, son 4 yılda zarar yılı varsa +%10.

Aday + güvenlik marjı ≥ gerekli marj → **🟢 ADAY + ALIM BÖLGESİ**.
Aday ama marj yetersiz → **🟡 ADAY (pahalı)**.

## Çıktı

`temel_eleme_tum.csv` tüm hisseleri içerir. `temel_eleme_aday.csv` sadece
adayları içerir. Workflow her cumartesi çalışır ve `results/temel/` altına arşivler.

Durum sırası: 🟢 → 🟡 → ⚪ Zayıf puan → ❌ ELENDİ (gerekçesi "Eleme Nedeni"
sütununda).

## Videolardan gelen, koda dökülmeyen kurallar

- **Çeşitlendirme**: en az 10–15 hisse (*Kaç Farklı Hisseye*, *12 Ders*).
- **Nakit yedek**: portföyün bir kısmı (hocada %30) sert düşüşler için nakitte.
  Para tek seferde değil, parçalara bölünerek girilir (*9 Hata*: %40 + %30 zamana
  yayılarak + %30 sert düşüş için).
- **Stop-loss ve hedef fiyatla satış yok.** Satış sadece şu durumlarda:
  1. Yönetim veya hakim ortak değişti ya da güven kaybı oldu
  2. Hakim ortak satıyor
  3. Şüpheli ilişkili taraf işlemleri var
  4. Sektörde yapısal ya da teknolojik dönüşüm riski oluştu
  5. Analiz hatası fark edildi

  Kaynak: *Bir Hisseyi Ne Zaman Satmalıyım?*
- **İçeriden öğrenen alımları** olumlu, hakim ortak satışları olumsuz sinyaldir
  (*İçeriden Öğrenenleri Taklit*). KAP bildirimleri elle takip edilmeli.
- Haber akışı ve makro tahminle işlem yapılmaz. Teknik analiz ve sık al-sat
  getiriyi düşürür (*Teknik Analiz İşe Yarıyor mu?*, *Piyasa Zamanlaması*).

## Sınırlamalar

- Playlist'teki 32 videonun 9'unda YouTube altyazısı yok: *Borsa Nasıl
  Öğrenilir*, *Buffett'ın Stratejileri*, *Buffett'ın Seçim Kriterleri*, *En İyi
  Borsa Stratejisi*, *En İyi Borsa Yatırımcılarının Özellikleri*, *F/K Nasıl
  Kullanılır*, *Akıllı Yatırımcı Bölüm 1–2*, *Borsada Nasıl Para Kazanılır*.
  Bu videolar yöntemde doğrudan kullanılmadı. Konuları, diğer videolardaki
  Buffett/Graham anlatımlarıyla (güvenlik marjı, rekabet avantajı, değer +
  büyüme bir bütün) büyük ölçüde örtüşüyor.
- Hakim ortak payı yfinance'in `heldPercentInsiders` alanından gelir. KAP
  ortaklık yapısıyla birebir aynı olmayabilir.
- Veriler yıllık tablolardır (son 4 yıl). Çeyreklik ani bozulmaları yakalamaz.
- TMS 29 enflasyon muhasebesi nedeniyle yıllar arası nominal kıyaslar
  yanıltıcı olabilir. Büyüme bu yüzden mutlak değil, şirketler arası sıra
  olarak puanlanır.
