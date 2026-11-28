# Sabri Çakar Tez Defteri (Bölüm 4-5-6) – BIST Taraması

**Veri:** Fintables / EVO MCP · 2023, 2024, 2025 yıl sonu + 2026/9 (TTM gelir/nakit, 30.09.2026 bilanço)
**Evren:** Standart (`default`) şablonlu 600 şirket → 3 yıllık verisi tam olan **579** şirket tarandı.
Banka, sigorta, faktoring ve leasing şablonları videoya uygun olarak kapsam dışı.

## Kullanılan kurallar

### "İdeal" şartlar (videoda verilen hedef eşikler) – 12 şart
| # | Şart | Kaynak |
|---|---|---|
| 1 | 3 yıl üst üste net kâr > 0 | Genel (en az 3 yıl) |
| 2 | İNA / Net kâr ≥ 1, **her yıl** | Bölüm 6 ("her zaman net kârın üzerinde") |
| 3 | SNA (İNA − maddi/maddi olmayan duran varlık alımı − kira ödemeleri) 2025 > 0 | Bölüm 6 (kira işletme nakdi sayılmalı) |
| 4 | SNA son 2 yıl üst üste negatif değil | Bölüm 6 (1–1,5 yıl normal) |
| 5 | Ödenen temettü ≤ SNA (her yıl) | Bölüm 6 |
| 6 | Faaliyet giderleri / Brüt kâr < %80 | Bölüm 4 (Buffett) |
| 7 | Faiz (esas faaliyet dışı finansal gider) / Net esas faaliyet kârı ≤ %15 | Bölüm 4 |
| 8 | Düzeltilmiş net kâr > 0 (net parasal pozisyon + ertelenmiş vergi geliri + yatırım faaliyeti gelirleri çıkarılınca) | Bölüm 4 (5 kalem) |
| 9 | Faiz karşılama (esas faal. kârı / faiz) ≥ 2 | Bölüm 5 |
| 10 | Net borç / FAVÖK < 2 | Bölüm 5 |
| 11 | Cari oran ≥ 1,2 | Bölüm 5 (1,2–1,3 kabul) |
| 12 | Alacak + stok günü bozulmuyor | Bölüm 5 |

### Kırmızı bayraklar (videoda "kırmızı bayrak / alarm" denilenler)
Faiz karşılama < 2 · Faal.gid/Brüt ≥ %80 · Net borç/FAVÖK > 3 · Cari oran 3 yıl < 1 · SNA 3 yıl negatif ·
SNA 2 yıl negatif + net borç artıyor · Temettü SNA'yı aşıyor · 2025 kârı tek seferlik kalemlerden ·
İNA 3 yıl kârın çok altında · Nakit 3 yıl KV finansal borcun çok altında · Alacak+stok günü hızla artıyor.

### Videoda sayı verilmediği için benim yorumum olan eşikler
- "Kârın çok altında" → 3 yıl üst üste İNA/NK < 0,5
- "Nakit borcun çok altında, uzun süre" → 3 yıl üst üste nakit < KV finansal borcun %50'si
- "Alacak/stok günleri satıştan hızlı artıyor" → (alacak günü + stok günü) 2023→2025 %20'den ve 10 günden fazla arttı
- Net esas faaliyet kârı = Brüt kâr − (GYG + PSD + Ar-Ge); "diğer faaliyet gelir/giderleri" hariç (Bölüm 4'teki öneri)
- Faiz gideri olarak "(Esas Faaliyet Dışı) Finansal Giderler" kullanıldı; kur farkı giderlerini de içerir (videoda da birlikte anılıyor)
- Stres testi (satış −%20, faiz ×2) eleme yapmaz, sadece not olarak raporlanır

## Katmanlar
| Katman | Tanım | Adet |
|---|---|---|
| **A** | 12 şartın tamamı + sıfır kırmızı bayrak | **1** |
| **B** | Kırmızı bayrak yok, 3 yıl kârlı, 1–2 ideal şart eksik | 15 |
| **C** | Kırmızı bayrak yok, 3 yıl kârlı, 3+ şart eksik | 3 |
| **D** | 3 yıl kârlı, tek kırmızı bayrak | 65 |
| Elendi | | 495 |

Ayrıntılar: `sonuc_adaylar.csv` (A–D), `sonuc_tum.csv` (579 şirket, tüm metrikler).

## A – Tüm şartları geçen
| Kod | Şirket | İNA/NK 23-24-25 | TTM | Faal.gid/Brüt | Faiz/EFK | Faiz karş. | NB/FAVÖK | Cari |
|---|---|---|---|---|---|---|---|---|
| NETCD | Netcad Yazılım | 1,06 · 1,03 · 1,15 | 1,25 | %30 | %2 | 58,9x | net nakit | 6,13 |

## B – Kırmızı bayraksız, 1-2 şart eksik (finansal yapılılar hariç)
| Kod | Şirket | Sektör | İNA/NK 23-24-25 | Eksik şart | 2026/9 uyarı |
|---|---|---|---|---|---|
| CMENT | Çimentaş | Çimento | 1,41 · 1,45 · 1,48 | Faiz/EFK %18 (>%15) | TTM İNA/NK 0,63, TTM SNA<0 |
| LMKDC | Limak Doğu Anadolu Çimento | Çimento | 0,96 · 1,35 · 1,25 | İNA/NK 2023'te 0,96 | – |
| ISDMR | İskenderun Demir Çelik | Ana metal | 3,00 · 1,16 · 6,05 | Faiz/EFK %47 | stres: karşılama <2 |
| LILAK | Lila Kağıt | Kağıt | 14,5 · 3,20 · 1,72 | Faiz/EFK %40 | stres: karşılama <2 |
| CITAS | Çitlekçi Mağazacılık | Gıda perakende | 1,64 · 2,68 · 0,92 | İNA/NK 2025'te 0,92 | TTM İNA/NK 0,52 |
| MASFN | Masfen Enerji | Enerji tekn. | 1,99 · 0,78 · 0,74 | İNA/NK | TTM İNA/NK 0,78 |
| DERIM | Derimod | Tekstil | 0,58 · 0,77 · 3,67 | İNA/NK | TTM İNA/NK 0,56 |
| MPARK | MLP Sağlık | Sağlık | 0,99 · 1,32 · 1,82 | İNA/NK 2023 + Faiz/EFK %43 | – |
| TNZTP | Tapdi Oksijen | Sağlık | 0,44 · −0,58 · 0,83 | İNA/NK + Faiz/EFK | TTM İNA negatif |
| VKGYO / AKSGY / KRGYO | GYO'lar | Gayrimenkul | – | İNA/NK | değerleme kazancına dikkat |

B'deki finansal yapılılar (BULGS, GLRYH, TERA) videoya göre bu yöntemle okunması uygun olmadığından ayrıca işaretlendi.

## D – Tek kırmızı bayrağı olan dikkat çekici şirketler
| Tek bayrak | Şirketler |
|---|---|
| Temettü bir yıl SNA'yı aşmış | EGGUB, KPEKS, NTGAZ, ASELS, TUPRS, ENKAI, TABGD, NUHCM, OYAKC, CLEBI, LOGO, KLKIM, TRALT, … |
| Faiz karşılama < 2 | MAVI, TCELL, TTKOM, CCOLA, RYSAS, PENTA, … |
| Alacak+stok günü artıyor | FONET, MTRKS, AFYON, AHGAZ, … |

Özellikle **EGGUB** (İNA/NK 1,96 · 2,18 · 2,73, faiz/EFK %6, net borç ≈ 0, cari 2,33) ve **NTGAZ** (İNA/NK 7,28 · 2,24 · 1,72, faiz/EFK %6) ideal şartlardan yalnızca temettü şartında takılıyor.

## Videodaki 5 örnek şirket
| Kod | Sonuç | Neden |
|---|---|---|
| BIMAS | Elendi | 2025 net kârının ≈ tamamı net parasal pozisyon kazancı; faal.gid/brüt %88 (perakende); 2024 temettüsü SNA'yı aşıyor |
| ASELS | D | 2023-2024 temettüsü SNA'yı aşıyor (yatırım dönemi); faiz/EFK %32 |
| TUPRS | D | 2024-2025 temettüsü SNA'yı aşıyor; faiz/EFK %45 |
| CCOLA | D | Faiz karşılama 1,7 |
| FROTO | Elendi | Temettü SNA'yı aşıyor + faiz karşılama < 2 |

## Sınırlar
- Tek yıllık oranlar yıl içi oranlardır, bu yüzden TMS 29 yeniden ifade farkı oranları bozmaz. Ancak net borcun yıllar arası nominal kıyası enflasyondan etkilenir.
- Kur riski, değişken faiz, borç vadesi, ilişkili taraf ve kefaletler dipnot gerektirir. Bu taramada kontrol **edilmedi**.
- DuPont (ROE'nin kaldıraçtan gelip gelmediği) videoda henüz anlatılmadığı için uygulanmadı.
- Perakendede cari oran < 1 olağan kabul edilir. Bu kural bayrak metninde not edildi.
- Bu bir eleme listesidir, yatırım tavsiyesi değildir. Videoda değerleme (fiyat) kriteri yok.
