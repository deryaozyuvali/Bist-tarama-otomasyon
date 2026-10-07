# Temel Tarama Yöntemi ("taşın altına bak")

Kaynak: 6 şirket incelemesi (Polisan, Gimat, Fonet, Tınaztepe, Onur Yüksek
Teknoloji, Menderes). Yayıncının yaklaşımı özetle şöyle: **özet tabloya bakıp
geçme, detaya in.** Ucuz görünen şirketin neden ucuz olduğunu, pahalı/zararlı
görünen şirketin içinde gizli bir değer olup olmadığını araştır. Hesapları
da hep **defansif** varsayımlarla yap.

## Veri ve çalıştırma

| Kaynak | Ne geliyor |
|---|---|
| **EVO** (Fintables MCP) | Çeyreklik bilanço, gelir tablosu (TTM), nakit akış, piyasa değeri, sektör. Geçmiş dönemler TMS 29 ile son döneme düzeltilmiş olarak geliyor, yani yıllık büyüme **reel**. |
| **FCF_MASTER.xlsx** (Dropbox) | FCF TTM ve statüsü (yalnızca KESİN ve TÜRETİLMİŞ kullanılır), Funnel V8.2 MIN puanı ve kategorisi. |

EVO'ya sadece Claude'un MCP aracıyla erişilebiliyor (GitHub Actions'tan
erişilemiyor). Bu yüzden tarama şöyle çalışıyor:

1. `python temel_tarama.py FCF_MASTER.xlsx > sorgu.sql`
   FCF ve Funnel verisi `temel_tarama.sql` şablonuna gömülür.
2. Üretilen sorgu EVO `veri_sorgula` ile çalıştırılır. Puanlamanın tamamı SQL
   içindedir ve sonuç PUAN'a göre sıralı ilk 300 hissedir.
3. `python evo_sonuc_csv.py <evo_sonuc.txt> results/temel/temel_tarama_<TARİH>.csv`

Kapsam dışı sektörler: banka, sigorta, gayrimenkul/GYO, aracı kurum, finansal
kiralama, faktoring, MKYO, GSYO, varlık yönetimi, emeklilik, tasarruf
finansman. Bu sektörlerde FD/FAVÖK anlamsız. Holdingler kapsamda (Polisan).

## 1. Yayıncı puanı (`yayinci`)

| Kural | Puan | Videodaki karşılığı |
|---|---|---|
| FD/FAVÖK ≤5 / ≤8 / ≤12 / >20 | +3 / +2 / +1 / −1 | Ana çarpan: Gimat "5'in altı", Polisan liman 6-7, akranlar 8-9. FD = PD + net borç + azınlık payları. |
| FAVÖK marjı ≥%25 / ≥%15 / <%3 | +2 / +1 / −1 | Gimat ve Tınaztepe yüksek marj, Polisan kimya %1 marj |
| Net nakit / NetBorç/FAVÖK ≤1,5 / >3 / FAVÖK ≤0 | +2 / +1 / −2 / −1 | Gimat, Tınaztepe, Fonet net nakit; Menderes borç geçmişi |
| Reel ciro büyümesi (TTM, yıllık) ≥%15 / ≥0 | +2 / +1 | Fonet "enflasyon üzeri %36" |
| (YAGM + iştirakler + özkaynak yöntemiyle değerlenenler + satış amaçlı varlıklar) / PD ≥%30 / ≥%15 | +2 / +1 | Polisan Pendik arazisi, Menderes Aktur iştiraki, Tınaztepe konut/AVM |
| Mülk sahibi: MDV/aktif ≥%40, kullanım hakkı ≤%2, marj ≥%15 | +1 | "Kira gideri yok, o yüzden marj yüksek" |
| PD ≤15 milyar TL | +1 | "Çok konuşulmayan, gözden kaçmış" şirketler |
| Ticari alacak büyümesi, ciro büyümesini 30 puan aşıyor (alacak > ciro×%10) | −1 | Fonet: kamuya iş yapanlarda alacak riski |
| Maddi olmayan duran varlık / aktif ≥%25 | −1 | Fonet: TMS 38 aktifleştirilen Ar-Ge, FAVÖK'ü şişirir |
| Son 4 çeyrekte brüt marj aralığı ≥20 puan | −1 | Onur: 2Ç %62, 3Ç −%11 brüt marj, "yıllık bak" |
| 2021–2025 yıl sonlarında hiç ödenen temettü yok | −1 | Menderes: "nakit akışı yoksa iskontolu fiyatlanır" |

## 2. FCF ve Funnel puanı (`fcf_funnel`, FCF_MASTER'dan)

| Kural | Puan |
|---|---|
| FCF verimi (FCF TTM / PD) ≥%10 / ≥%5 | +2 / +1 |
| Son üç dönemin TTM FCF'i negatif (ve verim <%5) | −1 |
| Funnel kategorisi ANA LİSTE / İZLEME / ALT | +2 / +1 / −1 |

`puan = yayinci + fcf_funnel`

## 3. Bayraklar (puana girmez, elle bak)

- `ZARAR_AMA_FAVOK`: Net zarar var ama FAVÖK pozitif ve FD/FAVÖK ≤10. Zarar
  iştirakten, kur farkından ya da durdurulan faaliyetten geliyor olabilir
  (Polisan tipi).
- `DIGER_GELIR`: Net diğer faaliyet geliri, faaliyet kârının %30'undan fazla.
  Teşvik, kur farkı, vade farkı gibi kalemler kârı taşıyor olabilir (Menderes).
- `ISTIRAK_ZARARI`: Özkaynak yöntemiyle değerlenen yatırımlardan gelen zarar,
  net kârın %30'undan fazla (Polisan'ın Kansai iştiraki).
- `DURDURULAN`: Durdurulan faaliyetlerin etkisi, net kârın %20'sinden fazla.
  Elden çıkarılan iş olabilir (Polisan Hellas).

Puanı etkileyen uyarılar `uyari` sütununda listelenir: `ALACAK`, `TMS38`,
`MARJ_OYNAK`, `TEMETTU_YOK`.

## 4. Elle kontrol listesi (adaylar için)

1. **Segmentlere ayır:** Bölümlere göre raporlamaya bak. Şirketin adı
   (ör. "Tekstil") asıl değeri gizliyor olabilir. Her segmenti borsadaki
   benzer şirketin çarpanıyla değerle (Menderes'in enerji tarafını Consus ile,
   Polisan'ın limanını GLYHO ve EGGUB ile karşılaştırmak gibi).
2. **Parçaların toplamı (SOTP), defansif:** Gayrimenkulü değerleme raporundan
   yaz, zarar eden yan işi sıfır yaz, iştirake iskonto uygula. Sonra "geriye
   kalan çekirdek işi kaça alıyorum?" sorusunu sor.
3. **Dipnotlar:** Diğer faaliyet gelir ve giderleri (bağış, teşvik, kur farkı),
   finansman giderleri (kur farkı nakit değil, faiz nakit), borçların para
   birimi, vadesi ve faizi, ilişkili taraf işlemleri, özkaynak yöntemiyle
   değerlenen yatırımlar.
4. **Yönetim ve sahiplik:** Yönetim kurulunda profesyoneller var mı? İmtiyazlı
   pay ve oy hakkı, vekâlet yapısı (Gimat), satış süreçlerine aracılık eden
   danışmanlar (Polisan).
5. **Katalizör:** Satın alma veya birleşme, kısmi bölünme, gayrimenkul satışı
   ya da çağrı fiyatı ihtimali, yeni mağaza veya tesis, tarife değişikliği
   (Tınaztepe'nin 3. basamağa geçişi).
6. **Genel kurul tutanakları:** Ortakların sorduğu sorular ve şirketin verdiği
   hedefler. Tarihlerin kaymasını bekle.
7. **Yeni halka arzlar:** Fiyat tespit raporundaki beklentiyi gerçekleşenle
   karşılaştır. Halka arz gelirinin nerede kullanıldığına bak (Onur'da
   savunma şirketinin parayı GES'e harcaması gibi).
8. **Yeni iş ilanları:** "Cirolara oranı %50" diye açıklanan işi yıllara böl.
9. **Kamuya iş yapanlar:** Alacak vadeleri, yoğunlaşma riski, ihale süreleri
   ve değiştirme maliyeti.
10. **Fon ve takip:** Fon pozisyonu az ve şirket az konuşuluyorsa fırsat
    olabilir. Fon çıkışlarının satış baskısı yaratabileceğini de hesaba kat.
11. **İlk çeyrek etkisi:** Büyüme yatırımı (personel, stok) kısa vadede
    bilançoyu kötü gösterebilir. Tek çeyreğe bakıp karar verme.

## Sınırlar

- Polisan gibi yeniden yapılanma hikâyeleri (bölünme, satış, çağrı fiyatı)
  sayılarla yakalanamaz. FAVÖK negatif olduğu için düşük puan alırlar. Böyle
  şirketleri KAP haberlerinden takip et.
- EVO'da "Ödenen Temettüler" kalemi bazı şirketlerde boş geliyor. Bu yüzden
  `TEMETTU_YOK` uyarısını KAP'tan teyit et.
- Bu bir ön eleme aracıdır, yatırım tavsiyesi değildir.
