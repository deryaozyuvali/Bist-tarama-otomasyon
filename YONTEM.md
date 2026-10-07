# Temel Tarama Yöntemi ("taşın altına bak")

Kaynak: 6 şirket incelemesi (Polisan, Gimat, Fonet, Tınaztepe, Onur Yüksek
Teknoloji, Menderes). Yayıncının yaklaşımı özetle şöyle: **özet tabloya bakıp
geçme, detaya in.** Ucuz görünen şirketin neden ucuz olduğunu, pahalı/zararlı
görünen şirketin içinde gizli bir değer olup olmadığını araştır. Hesapları
da hep **defansif** varsayımlarla yap.

`temel_tarama.py` bu yaklaşımın sayılarla ölçülebilen kısmını otomatikleştirir.
Geri kalanı aşağıdaki elle kontrol listesidir.

## 1. Otomatik puan (temel_tarama.py)

| Kural | Puan | Videodaki karşılığı |
|---|---|---|
| FD/FAVÖK ≤5 / ≤8 / ≤12 / >20 | +3 / +2 / +1 / −1 | Ana çarpan: Gimat "5'in altı", Polisan liman 6-7, akranlar 8-9 |
| FAVÖK marjı ≥%25 / ≥%15 / <%3 | +2 / +1 / −1 | Gimat ve Tınaztepe yüksek marj, Polisan kimya %1 marj |
| Net nakit / NetBorç/FAVÖK ≤1.5 / >3 | +2 / +1 / −2 | Gimat, Tınaztepe, Fonet net nakit; Menderes borç geçmişi |
| Reel ciro büyümesi ≥%15 / ≥0 | +2 / +1 | Fonet "enflasyon üzeri %36" |
| (İştirak + yatırım amaçlı gayrimenkul + satış amaçlı varlık) / PD ≥%30 / ≥%15 | +2 / +1 | Polisan Pendik arazisi, Menderes Aktur iştiraki, Tınaztepe konut/AVM |
| Mülk sahibi (MDV/aktif ≥%40, kiralama yükü yok) ve marj ≥%15 | +1 | "Kira gideri yok, o yüzden marj yüksek" |
| PD ≤15 milyar TL | +1 | "Çok konuşulmayan, gözden kaçmış" şirketler |
| Ticari alacak büyümesi, ciro büyümesini 30 puan aşıyor | −1 | Fonet: kamuya iş yapanlarda alacak riski |
| Maddi olmayan duran varlık / aktif ≥%25 | −1 | Fonet: TMS 38 aktifleştirilen Ar-Ge, FAVÖK'ü şişirir |
| Çeyreklik brüt marj aralığı ≥20 puan | −1 | Onur: 2Ç %62, 3Ç −%11 brüt marj, "yıllık bak" |
| Son 5 yılda temettü yok | −1 | Menderes: "nakit akışı yoksa iskontolu fiyatlanır" |

**Yalnızca bayrak (puana girmez, elle bak):**
- `ZARAR_AMA_FAVOK_IYI`: Net zarar var ama FAVÖK güçlü ve ucuz. Zarar iştirakten, kur farkından ya da durdurulan faaliyetten geliyor olabilir (Polisan tipi).
- `TEK_SEFERLIK_KALEM`: Olağan dışı kalemler net kârın %30'undan fazla. Değerleme kârı, bağış, teşvik geliri gibi kalemler olabilir (Tınaztepe, Menderes).
- `FAVOK_NEGATIF`: Çarpan hesaplanamıyor. Şirket elenmez; değerlendirme parça parça (SOTP) yapılmalı.
- `RAPOR_USD/EUR`: Finansallar dövizle raporlanıyor, TL'ye çevrildi.

Çıktılar: `temel_tarama.csv` (tüm liste) ve `temel_sinyal.csv` (PUAN ≥ 6).

## 2. Elle kontrol listesi (adaylar için)

1. **Segmentlere ayır:** Bölümlere göre raporlamaya bak. Şirketin adı
   (ör. "Tekstil") asıl değeri gizliyor olabilir. Kârın hangi segmentten
   geldiğini bul ve her segmenti borsadaki benzer şirketin çarpanıyla değerle
   (Menderes'in enerji tarafını Consus ile, Polisan'ın limanını GLYHO ve
   EGGUB ile karşılaştırmak gibi).
2. **Parçaların toplamı (SOTP), defansif:** Gayrimenkulü değerleme
   raporundan yaz, zarar eden yan işi sıfır yaz, iştirake iskonto uygula.
   Sonra "geriye kalan çekirdek işi kaça alıyorum?" sorusunu sor.
3. **Dipnotlar:**
   - Esas faaliyetlerden diğer gelir ve giderler: bağış, teşvik, kur farkı var mı?
   - Finansman giderleri: kur farkı nakit çıkışı gerektirmez, faiz gerektirir.
   - Borçların para birimi, vadesi ve faizi: ucuz döviz kredisi iyi borçtur.
   - İlişkili taraf işlemleri: satışın büyük kısmı grup şirketine mi gidiyor?
   - Özkaynak yöntemiyle değerlenen yatırımlar.
4. **Yönetim ve sahiplik:** Yönetim kurulunda profesyoneller var mı, yoksa
   sadece aile mi? İmtiyazlı pay ve oy hakkı yapısına, vekâlet yapısına
   (Gimat), satış süreçlerine aracılık eden danışmanların varlığına (Polisan)
   bak.
5. **Katalizör:** Satın alma veya birleşme, kısmi bölünme, gayrimenkul satışı
   ya da çağrı fiyatı ihtimali, yeni mağaza veya tesis, tarife değişikliği
   (Tınaztepe'nin 3. basamağa geçişi ve SUT artışı).
6. **Genel kurul tutanakları:** Ortakların sorduğu sorulara verilen cevaplar
   ve şirketin verdiği hedefler. Tarihlerin kaymasını bekle ve risk olarak not et.
7. **Yeni halka arzlar:** Fiyat tespit raporundaki beklentiyi gerçekleşenle
   karşılaştır. Halka arz gelirinin nerede kullanıldığına bak (Onur'da
   savunma şirketinin parayı GES'e harcaması gibi).
8. **Yeni iş ilanları:** "Cirolara oranı %50" diye açıklanan işi yıllara böl.
   Hangi yılın gelirine yazılacağına bak.
9. **Kamuya iş yapanlar:** Alacak vadeleri, yoğunlaşma riski, ihale süreleri
   ve değiştirme maliyeti.
10. **Fon ve takip:** Fon pozisyonu az ve şirket az konuşuluyorsa fırsat
    olabilir. Fon çıkışlarının satış baskısı yaratabileceğini de hesaba kat.
11. **İlk çeyrek etkisi:** Büyüme yatırımı (personel, stok) kısa vadede
    bilançoyu kötü gösterebilir. Tek çeyreğe bakıp karar verme.

## Sınırlar

- Veri Yahoo Finance'ten geliyor. Bazı hisselerde eksik veya gecikmeli.
  Kritik rakamları KAP ya da Fintables'tan teyit et.
- Polisan gibi yeniden yapılanma hikâyeleri (bölünme, satış, çağrı fiyatı)
  sayılarla yakalanamaz. FAVÖK negatif olduğu için düşük puan alırlar.
  Böyle şirketleri KAP haberlerinden takip et.
- Bu bir ön eleme aracıdır, yatırım tavsiyesi değildir.
