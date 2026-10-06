# KURULU YAY — Funnel V8.2 için öncü radar (v1)
Soru: "Bir sonraki bilanço açıklandığında Funnel puanında en güçlü pozitif sıçrama hangi şirketlerde birikmiş?"
Funnel'ın yerine geçmez; Funnel tanımları ve puanlama kuralları aynen kullanılır, değiştirilmez.

# Veri
Yalnız FCF_MASTER.xlsx: FUNNEL sayfası (11 metriğin değeri + puanı, 5 dönem: 2025/06–2026/06), ANA, FCF. Evren: Kapsam = STANDART ve PUANLANIR (Tier 0 / 0,5 / veri yetersiz hariç).
5 dönem = 4 gerçekleşmiş geçiş (06→09, 09→12, 12→03, 03→06), ~1.900 şirket-geçiş gözlemi.

# Fikir: Funnel bant yapısından doğan "kurulu yay"
Funnel puanı sürekli değil, basamaklıdır: her metrik eşiği geçince birden 3–15 puan kazanır/kaybeder. Bir şirketin "yayı",
metriklerinin bir üst banda ne kadar yakın olduğu (ve ne kadar uzaktan düşebileceği) ile belirlenir.
1. Eşik uzaklığı: her metrik için mevcut değerin bir üst bandın eşiğine (z_up) ve mevcut bandın alt eşiğine (z_dn) uzaklığı.
   Uzaklık, o metriğin evrendeki tipik çeyreklik hareketiyle ölçeklenir (σ = çeyreklik iyi-yön değişiminin medyan mutlak değeri);
   böylece "ROE'de 1 puan" ile "CFO/NK'da 1 puan" karşılaştırılabilir hale gelir. (M11'in tepe bandı [1,3] aralığıdır; ayrı ele alınır.)
2. İvme: son çeyrekteki değişim, iyileşme yönünde, aynı σ ile.
3. Rejim: değerle puan bandı tutarsızsa (net kâr ≤ 0 → M1/M5/M11 = 0; brüt kâr ≤ 0; net borç < 0; M10 "prior yok" şeması)
   eşik uzaklığı anlamsızdır → o metrik-rejim için geçmişteki geçiş oranı kullanılır.
4. Metrik başına iki lojistik model (yukarı bant geçişi / aşağı bant geçişi), geçmiş geçişlerden öğrenilir:
   P_up = σ(a + b·log(1+z_up) + c·ivme)   P_dn = σ(a' + b'·log(1+z_dn) + c'·ivme)   (hafif L2; 11 metrik × 2 model × 4 katsayı)
5. Şirket skoru: E[ΔFunnel] = Σ_metrik (P_up × kazanç − P_dn × kayıp)  →  KURULU YAY skoru.
   Aşağı risk skorun içindedir (cezalandırma ayrı ağırlıkla değil, beklenen kayıp olarak). Ayrıca gösterilir:
   beklenen kazanç, beklenen kayıp, P(Δ ≥ +8) ve P(Δ ≤ −8) (metrikler bağımsız varsayımıyla Monte Carlo).
6. Sınıf: GÜÇLÜ YAY (dengeli): E[Δ] ≥ 4 ve beklenen kayıp ≤ 2,5 · YAY — yüksek potansiyel, yüksek risk: E[Δ] ≥ 4, kayıp > 2,5 ·
   ORTA YAY: 2 ≤ E[Δ] < 4 · TERS YAY: E[Δ] ≤ −3.

# Neden bu tasarım
- Funnel'ın kendisi bant/eşik makinesi → sıçramayı eşik geçişleri üretir; doğrudan bunu modellemek, toplam skoru regresyonla tahmin etmekten şeffaf.
- Az parametre (88 katsayı, ~25.000 metrik-geçiş gözlemi) → aşırı uyum riski düşük.
- Her tahmin açıklanabilir: hangi metrik hangi banda, hangi olasılıkla (Sürükleyici / Risk sütunları).

# Backtest (walk-forward; her test dönemi yalnız kendinden önceki geçişlerle eğitildi)
Test geçişleri: 2025/09→12 (1 eğitim geçişi), 2025/12→2026/03 (2), 2026/03→06 (3). Ortalama:
| Yöntem | Spearman (tahmin vs gerçek Δ) | Üst 30'da Δ≥+8 oranı | Üst 30 ort. gerçek Δ | Alt 30 ort. gerçek Δ |
| KURULU YAY E[Δ] | 0,30 | %28 | +7,1 | −6,0 |
| Kıyas: düşük puan (ortalamaya dönüş) | 0,19 | %26 | +4,5 | −3,6 |
| Kıyas: eşik yakınlığı (öğrenmesiz) | 0,14 | %26 | +2,4 | −2,3 |
| Kıyas: son skor değişimi (ivme) | −0,11 | %11 | −4,7 | +3,0 |
Taban oran (rastgele): Δ ≥ +8 %19.  Üç testin üçünde de Spearman en yüksek KURULU YAY.
Kalibrasyon: tahmin desilleri gerçekleşenle uyumlu (en üst desil tahmin +5,0 / gerçek +6,6; en alt tahmin −4,7 / gerçek −4,9).
Büyük sıçramaların (Δ ≥ +15) %42'si modelin üst %20'sinde, %21'i alt yarıda kaldı. Üst 30'da 5+ puan düşen şirket oranı %3.

# İkinci görünüm: kategori atlama
Mutlak E[Δ] sıralaması düşük puanlı ve oynak metrikli (özellikle M10 alacak/satış) şirketleri öne çıkarıyor: istatistiksel olarak doğru
ama "kaliteye sıçrama" değil. Bu yüzden aynı modelden P(bir üst kategoriye geçiş) da üretilir: 60–69 → ANA LİSTE (≥70), <60 → İZLEME (≥60).
Backtest (en olası 20 aday, gerçekten geçenlerin oranı): 2025/09→12 %45 · 2025/12→26/03 %65 · 2026/03→06 %30; taban oran %11–14.
Kıyas "eşiğe en yakın puan": %35 · %60 · %20 → model her testte 5–10 puan önde (fark mütevazı ama tutarlı; Spearman 0,31–0,45 vs 0,30–0,41).

# Kalibrasyon kararları (aşırı uyuma karşı)
- Ortalamaya dönüş düzeltmesi (son skor değişiminin tersi) denendi → test sonuçlarını kötüleştirdi, alınmadı.
- Metrik ivmesi: sıralamaya katkısı yok (Spearman 0,300 → 0,301 ivmesiz), aşağı risk ayrımına küçük katkı (alt 30: −6,0 vs −5,6) → tutuldu.
- Eşikler/katsayılar el ile ayarlanmadı; sınıf eşikleri (4 / 2,5) yalnız raporlama içindir, sıralamayı değiştirmez.

# Başarısız olduğu durumlar
- Kaçırılan büyük sıçramaların en büyük kaynağı M1 (CFO/Net kâr): işletme sermayesi kaynaklı tek çeyreklik nakit sıçramaları eşiğe uzaklıkla öngörülemiyor.
- Zarardan kâra geçiş (M1/M5/M11 birlikte 0 → dolu) yalnız taban oranla tahmin ediliyor; çeyreklik kâr ivmesi bilgisi kullanılamadı.
- 2025/12 geçişi (yıl sonu) tüm evrende en oynak dönem; modelin isabeti dönemden döneme %13–%47 arasında değişiyor.

# Sınırlamalar
- Yalnız 4 geçiş (≈1 yıl) — mevsimsellik (yıl sonu raporu vb.) ayrıca öğrenilemedi; model büyüdükçe (her yeni çeyrek) yeniden eğitilmeli.
- Metrikler arası bağımlılık (aynı net kârın M1, M5, M11'i birlikte oynatması) P(sıçrama) hesabında bağımsız varsayıldı → kuyruk olasılıkları düşük kalabilir.
- Master'daki Funnel dönemleri farklı tarihlerde çekilmiş Evo vintage'larından geliyor (GEM'in delta uyarısı); geçiş hedefinin bir kısmı veri vintage'ı olabilir.
- Belge / operasyonel öncü göstergeler (KAP'ta yeni sözleşme, kapasite devreye alma, şirket beklentileri, aracı kurum tahminleri) geçmiş zaman damgasıyla
  elimizde olmadığından backtest edilemedi → skora girmedi. Önerilen kullanım: listenin üst sırasındaki adaylar için GEM analizinde ikinci katman olarak bakılır.
- Funnel MIN kullanıldı; NULL metrikli (BELİRSİZ) şirketlerde MAX tarafı ayrıca okunmalı.
