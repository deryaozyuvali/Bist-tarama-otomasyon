# HASAT kural seti — "Sıkıcı ama nakit üreten şirket" (son 3 yıla uyarlanmış, v1)

Amaç: büyük yatırım dönemini geride bırakmış, artık bakım düzeyinde yatırım yapan ve kazandığı nakdin giderek büyük
kısmını hissedara bırakabilen şirketleri bulmak. Büyüme aranmaz; çöküş elenir.

## Veri ve baz
- Noktalar: **Y23** = FY2023 (ilk TMS 29 yıl sonu), **Y24** = FY2024, **Y25** = FY2025, **T** = TTM 2026/06.
  Daha eskisi kullanılmaz (pandemi, enflasyon muhasebesi öncesi).
- Baz Funnel ile aynı: Evo TTM/yıllık rakamlar; TMS 29 uygulayan şirketlerde geçmiş yıllar son raporun satın alma gücünde
  (reel, harici deflatör yok). TMS 29 uygulamayan (işlevsel para birimi USD) şirketlerde büyüme ve borç trendi **USD** ile ölçülür.
- FCF bileşenleri (CFO, CAPEX, kira) Y25 ve T için **FCF_MASTER**'dan (belgeyle düzeltilmiş), Y23/Y24 için Evo'dan.
- GYO'lar ayrı kol (master FCF kapsamı dışında; veri Evo'dan).

## Eleme (biri tutarsa aday olmaz)
| Kural | Madde | Tanım |
|---|---|---|
| E1 Nakit üretimi | 9 | 4 noktanın en az 3'ünde CFO > 0 **ve** T'de CFO > 0 |
| E2 Tuzak | 2, 7 | CAPEX düşmüş (döngü HASAT/GEÇİŞTE) **ve** reel satış −%30 / reel brüt kâr −%35 altında ya da brüt zarar → **TUZAK ŞÜPHESİ** |
| E3 Veri | — | FCF 2026/06 master'da KOŞULLU/NULL ise elenir (GEM: KOŞULLU rakama dayalı yorum yapılmaz) |

Not: 2023 birçok şirket için reel zirve yılı (medyan şirkette 2023→T reel satış −%10, brüt kâr −%17). Bu yüzden eşikler
"çöküş" düzeyinde; CAPEX'i düşmemiş şirketteki çöküş eleme değil, puan kaybı + "Çöküş uyarısı".

## Ölçütler
| Ölçüt | Madde | Tanım |
|---|---|---|
| **Yatırım döngüsü** | 2, 3 | CAPEX/Amortisman (GYO: CAPEX/CFO) Y23–Y25 zirvesi ile T karşılaştırılır. **HASAT**: zirve ≥ 1,5 (GYO 0,7), T ≤ 1,2 (GYO 0,3) ve CAPEX/Satış zirvenin %70'i veya altı · **SÜREKLİ DÜŞÜK CAPEX**: tüm yıllar ≤ 1,2 (GYO 0,3) · **GEÇİŞTE**: T zirvenin %85'inin altında · aksi **YATIRIM DÖNEMİNDE** |
| Bakım CAPEX (vekil) | 3 | min(CAPEX_T, Amortisman_T) |
| **Hasat nakdi** | 5 | CFO_T − bakım CAPEX − kira_T; **hasat getirisi** = hasat nakdi / piyasa değeri |
| Amortisman kalkanı | 4 | Amortisman/CAPEX_T ≥ 1 ve FCF/Net kâr_T > 1 (muhasebe kârı nakdi küçük gösteriyor) |
| **Borç** | 6, 10 | Net borç Y23 → T: NET NAKDE GEÇTİ · SÜREKLİ NET NAKİT · BORÇ AZALIYOR (−%20 veya Net borç/FAVÖK −%30) · AZALMIYOR · NET BORCA GEÇTİ. Ek: ödenen faiz/CFO ve **borç sonrası hasat getirisi** = (hasat nakdi + ödenen faiz)/PD |
| Brüt kâr reel | 8 | Reel brüt kâr değişimi Y23 → T (USD bazlılarda USD) |
| Temettü | 11 | Ödenen temettü olan yıl sayısı (4 nokta) ve temettü verimi T |
| Ucuzluk | 12 | Hasat getirisi, P/FCF, FD/FAVÖK, PD/DD; GYO'da PD/DD ve PD/Satış (kira çarpanı vekili) |

## Puan (100)
**Şirket:** Döngü 25 (HASAT 25 · SÜREKLİ DÜŞÜK 20 · GEÇİŞTE 10) · Nakit 15 (4/4 CFO>0 ve FCF_T>0: 15; 3/4: 8) ·
Amortisman kalkanı 10 · Borç 15 (net nakde geçti 15 · sürekli net nakit 12 · azalıyor 8) · Brüt kâr reel 10 (≥+%10: 10 · ≥0: 6 · ≥−%15: 2) ·
Temettü 10 (yıl/4 × 5 + verim ≥%4: 5, ≥%2: 3) · Ucuzluk 15 (hasat getirisi ≥%15: 15 · ≥%10: 10 · ≥%6: 5).

**GYO:** Döngü 20 · Nakit 15 · Borç 20 · Gelir reel 10 · Temettü 10 · Ucuzluk PD/DD 25 (≤0,5: 25 · ≤0,65: 20 · ≤0,8: 12 · ≤1: 5).

**Kategori:** ≥70 GÜÇLÜ ADAY · 55–69 ADAY · 40–54 İZLE · <40 UYMUYOR · eleme → ELENDİ / TUZAK ŞÜPHESİ.

## Kalibrasyon
Yayıncının örnekleri: Panora (PAGYO), Torunlar (TRGYO), Akiş (AKSGY) → üçü de **GÜÇLÜ ADAY**
(PAGYO, TRGYO: HASAT + net nakde geçti; AKSGY: sürekli düşük CAPEX + net nakde geçti; PD/DD 0,44–0,60).

## Otomatik taramanın cevaplayamadığı (belge katmanı — GEM analizinde)
1. CAPEX **neden** düştü: faaliyet raporunda "yatırım tamamlandı / kapasite devreye alındı", kapasite kullanım oranı.
2. Bakım / büyüme CAPEX ayrımı dipnotta var mı (vekil yerine gerçek rakam).
3. Kredi vade tablosu: borç ne zaman biter, faiz yükü ne zaman kalkar.
4. Temettü politikası; GYO'da gerçek kira geliri (PD/Satış yalnızca vekil, konut satışı karışabilir).
