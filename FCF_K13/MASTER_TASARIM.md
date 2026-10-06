# FCF Master Dosyası — Tasarım

Amaç: FCF rakamlarının ve bileşenlerinin tek kaynağı. Yeni bilanço dönemleri bu dosyanın üzerine eklenir; P/FCF, FCF serisinin
yönü/değişimi gibi tüm analizler buradan beslenir. Dosya, hiçbir ön bilgisi olmayan bir okuyucuya (insan ya da yapay zekâ)
verildiğinde, başka kaynağa bakmadan doğru yorumlanabilecek şekilde kurulur.

## 1. Temel ilkeler (bu çalışmada yaşanan hatalardan)

1. **Ham veri ile hesaplanan veri ayrı.** Raporlardan okunan her tutar, raporda yazdığı gibi saklanır: raporun kendi
   satın alma gücünde, kendi işaretiyle. TTM, TMS 29 çevrimi ve FCF her seferinde bu ham veriden formülle üretilir; elle
   yazılmaz. (Evo ile yaşanan sorunların çoğu, çevrilmiş ve karışık esaslı TTM'lerin kaynak gibi saklanmasından çıktı.)
2. **Her rakamın izi var.** Her tutar: hangi rapor (KAP bildirim no / site URL), hangi sayfa, hangi satır metni, hangi
   yöntemle (XBRL = PDF / yalnız PDF / OCR / elle karar) okundu.
3. **Doğrulama sonucu rakamın yanında.** A + B + C = net nakit değişimi özdeşliği, etiket kontrolü, ikinci kaynakla
   karşılaştırma — sonuçları kodla kaydedilir. "Teyitli" kelimesi, hangi testin geçtiğini söylemeden kullanılmaz.
4. **Elle kararlar ayrı bir kayıt defterinde.** Her elle müdahalenin kimliği, gerekçesi, kanıtı ve tarihi var; ham veriye
   gömülmez. Yeni dönem eklenince eski kararlar bozulmaz.
5. **Şirket kimliği koddan bağımsız.** Hisse kodu değişir (KOZAL→TRALT, MARKA→USHOL); seri şirket kimliğine bağlanır.
6. **Tanımlar tek yerde.** FCF, CAPEX, kira, CFO'nun neyi içerip neyi içermediği tek bir tanım sayfasında; şirkete özel
   istisnalar ayrı bir listede.
7. **Kalite ile kullanılabilirlik ayrı boyutlar.** "Bu rakam nereden geldi, ne kadar sağlam" ile "analizde kullanılır mı"
   iki ayrı sütun. (KESİN / TÜRETİLMİŞ / KOŞULLU karışımı bu ikisini birbirine karıştırıyordu.)

## 2. Sayfalar

Kaynak tablolar (elle/okuyucuyla doldurulur, master budur): `SIRKET`, `RAPOR`, `KALEM`, `KARAR`, `ENDEKS`, `PIYASA`.
Üretilen tablolar (script üretir, elle değiştirilmez): `TTM`, `SERI`, `GOSTERGE`, `KONTROL`.
Okuma kılavuzu: `OKUBENI`, `TANIM`, `SOZLUK`, `SIRKET_KURALLARI`.

### OKUBENI
- Dosyanın amacı, son güncellendiği dönem, **baz tarihi** (tüm çevrilmiş tutarların satın alma gücü tarihi).
- Okuma sırası: TANIM → SIRKET_KURALLARI → GOSTERGE/SERI; kaynak gerekirse TTM → KALEM → RAPOR.
- Birim: mn TL (üretilen sayfalarda), tam TL (KALEM'de). İşaret: çıkış negatif, belgedeki gibi.
- "Analizde kullanırken" kuralları (aşağıda §4).
- Bilinen sınırlar listesi.

### TANIM (tek doğru tanım)
| Kavram | Tanım | Dahil değil |
|---|---|---|
| CFO | Nakit akış tablosunun işletme bölümü **toplamı** (vergi, çalışan ödemeleri, faiz bu bölümdeyse dahil) | Ara toplamlar ("faaliyetlerden elde edilen nakit" ara satırı) |
| CAPEX | MDV + MODV **alım** satırları | Satış satırları, verilen avans değişimi, kullanım hakkı alımları, "net alım-satım" tek satırı (→ şirket kuralı), iştirak/bağlı ortaklık alımı |
| YAGM | Yatırım amaçlı gayrimenkul alım satırı | Satış |
| Kira | Kiralama yükümlülüğü **anapara** ödemeleri (finansman) | Faiz kısmı (ayrı satırsa), yeni kiralama girişleri |
| Alınan temettü | Yalnız **yatırım** bölümündekiler | İşletme bölümündeki "alınan temettü" (CFO'da zaten var) |
| FCF_STD | CFO − \|CAPEX\| − \|YAGM\| − \|Kira\| | |
| FCF_HLD | FCF_STD + alınan temettü (yatırım bölümü) | |
| Pozitif TTM çıkış kalemi | 0 sayılır, kayda geçer (eski K6) | |
| TTM | YTD_cari + FY_önceki − YTD_önceki (Aralık: FY) | |
| Esas tutarlılığı | TTM'in üç parçası aynı sunum esasında olmalı (§3.3) | |

### SIRKET
`sirket_id` (kalıcı; KAP üye kimliği), `guncel_kod`, `kod_gecmisi` (eski kod → yeni kod, tarih), `unvan`,
`ekonomik_tip` (Standart / Holding / Finansal-kapsam dışı), `hesap_yili_sonu` (12, 6, 8…), `tms29` (E/H + başlangıç dönemi),
`fonksiyonel_para`, `konsolide_mi`, `site_url`, `durum` (aktif / kodu değişti / işlem görmüyor).

### RAPOR (belge kütüğü — her finansal rapor bir satır)
`rapor_id`, `sirket_id`, `donem` (YYYY/AA), `kaynak` (KAP no / site URL / Evo), `yayin_tarihi`, `revize_mi`,
`satin_alma_gucu_tarihi` (TMS 29 baz tarihi; uygulamıyorsa boş), `birim` (TL / bin TL / mn TL), `sutun_duzeni`
(ör. "USD | TL | USD | TL"), `metin_durumu` (metin / taranmış / OCR yapıldı), `sunum_notu`.

### KALEM (ham olgular — uzun format, ana tablo)
Her satır: bir raporun bir sütunundaki bir kalem.
`rapor_id`, `kalem` (CFO, CAPEX_MDV, CAPEX_MODV, YAGM, KIRA, TEMETTU_YATIRIM, + doğrulama için B_TOPLAM, C_TOPLAM,
NET_DEGISIM), `sutun` (cari_YTD / karsilastirmali_YTD), `donem_kapsadigi` (ör. 2024/01–2024/06), `deger_tl` (belgedeki gibi),
`xbrl_deger` (farklıysa ikisi de durur), `yontem` (XBRL_PDF / PDF / OCR / ELLE), `sayfa`, `satir_metni`,
`dogrulama` (kod listesi: OZDESLIK_OK, ETIKET_OK, CAPRAZ_OK…), `sorun` (kod listesi: XBRL_ETIKET_HATASI, ISARET_ANOMALISI,
KULLANIM_HAKKI_DAHIL, AVANS_NETLENMIS, ARA_TOPLAM, TARANMIS…), `karar_id`.

Karşılaştırmalı sütunlar da saklanır. Böylece bir dönem iki kez kayıtlı olur (kendi raporunda ve bir sonraki yılın
raporunda). Bu, **yeniden düzenlemeyi otomatik yakalar** (§3.3).

### KARAR (elle karar defteri)
`karar_id`, `kapsam` (sirket / rapor / kalem / sütun), `karar` (değer, yöntem ya da "kullanma"), `gerekce`, `kanit` (sayfa,
satır, özdeşlik hesabı), `tarih`, `karar_veren`, `gecerlilik` (tek rapor / şirket geneli / kalıcı kural).

### ENDEKS
Dönem sonu TÜFE (resmî seri). Çevrim katsayısı = endeks(baz) / endeks(rapor satın alma gücü tarihi).
Şu an kullandığımız F tablosu Evo'dan ampirik çıkarıldı; master'da resmî endeks esas alınmalı, ampirik değer kontrol olarak durur.

### PIYASA
`sirket_id`, `tarih`, `piyasa_degeri`, `pay_sayisi`, `kaynak`. P/FCF hesabında hangi tarihin değeri kullanıldı, açıkça.

### TTM (üretilir)
Şirket × dönem × kalem: üç parçanın `rapor_id`'leri, parçaların ham değerleri, esas kontrolü, baz tarihine çevrilmiş TTM,
`kalite` (en zayıf parçanın kalitesi), `sorun` kodları. Sonra şirket × dönem: CFO, CAPEX, kira, temettü, FCF_STD, FCF_HLD,
`fcf_turu` (ekonomik tipe göre), `kullanilabilirlik`, `kullanilabilirlik_nedeni`, `evo_karsilastirma` (V7/Evo değeri ve fark).

### SERI (üretilir — yön ve değişim)
Şirket × dönem: aynı baz tarihinde FCF TTM; önceki çeyreğe ve önceki yıla göre değişim (reel); işaret değişimi;
**seri kırığı** işaretleri (yeniden düzenleme, sunum değişikliği, TMS 29 başlangıcı, konsolidasyon değişikliği, kod değişikliği).
Kırık varsa o noktadan önceki ve sonraki değişim hesaplanmaz ya da "kırık" diye etiketlenir.

### GOSTERGE (üretilir)
P/FCF, FCF verimi, FCF/Net kâr vb. Her satırda hangi FCF tanımı, hangi dönem, hangi piyasa tarihi kullanıldığı ve
`kullanilabilirlik` tekrar yazılır.

### KONTROL (üretilir)
Özdeşlik testleri, XBRL–PDF farkları, Evo–belge farkları, açık işler (belge bulunamayan, elle bekleyen), yeni dönemde
otomatik yakalanan yeniden düzenlemeler.

### SIRKET_KURALLARI
Şirkete özel kalıcı kurallar, gerekçe ve kanıtıyla. Örnekler: PLTUR filo alımları işletme bölümünde; GOKNR her bölümde
"enflasyon etkisi" satırı; CANTE/ODAS tabloları raporlar arası tutarsız; EREGL 4 sütunlu (USD | TL) tablo; TUREX kira yalnız
net değişim satırı; ARZUM/HUNER XBRL'de kullanım hakkı CAPEX'e dahil.

## 3. Kurallar

### 3.1 Kalite (her bileşen için)
| Kod | Anlamı |
|---|---|
| A | XBRL = PDF satırı ve tablo özdeşliği tutuyor |
| B | Tek kaynak (PDF ya da OCR) ama özdeşlik tutuyor |
| C | Elle karar (gerekçeli) |
| D | Kaynak var ama tutarsız (yorum gerektiriyor) |
| — | Belge yok |

### 3.2 Kullanılabilirlik (şirket × dönem)
| Kod | Ne zaman | Analizde |
|---|---|---|
| KULLAN | Tüm bileşenler A/B/C, seri kırığı yok | Evet |
| DIKKAT | Kullanılabilir ama not var (ör. seri kırığı, yakın fark) | Evet, notla |
| KULLANMA | D ya da belge yok | Hayır; gösterilir ama hesaba girmez |

### 3.3 Esas tutarlılığı ve yeniden düzenleme
Yeni bir rapor geldiğinde, karşılaştırmalı sütunu KALEM'deki eski kaydıyla (aynı dönemin kendi raporu) karşılaştırılır.
TMS 29 katsayısı düşüldükten sonra fark varsa → `YENIDEN_DUZENLEME` kaydı açılır. TTM kurulurken üç parça, cari raporun
karşılaştırmalı sütununun esasıyla aynı esastan seçilir; belirlenemiyorsa `kullanilabilirlik = KULLANMA`
(neden: ESAS_BELIRSIZ).

### 3.4 Yeni dönem ekleme akışı
1. RAPOR'a yeni raporları ekle (KAP bildirimi + PDF; KAP kapalıysa şirket sitesi, sonra Evo).
2. KALEM'i okuyucuyla doldur (cari ve karşılaştırmalı sütunlar; XBRL ile PDF yan yana).
3. Doğrulama: özdeşlik, etiket, XBRL–PDF farkı. Sorunlular KARAR'a.
4. ENDEKS'e yeni dönem sonu TÜFE.
5. Script: TTM → SERI → GOSTERGE → KONTROL. Baz tarihi yeni döneme kayar; tüm seri yeni satın alma gücüne çevrilir
   (ham veri değişmez).
6. KONTROL'deki yeni yeniden düzenlemeleri ve açık işleri gözden geçir.

## 4. Analizde kullanırken (OKUBENI'de)
- P/FCF yalnız `KULLAN` / `DIKKAT` satırlarda; FCF ≤ 0 ise "anlamsız".
- FCF ve piyasa değeri aynı tarihe yakın olmalı: FCF baz tarihine çevrilmiş; piyasa değeri tarihi yazılı.
- Seri yönü reel (aynı baz) tutarlarla hesaplanır; seri kırığı varsa kırığın iki tarafı karşılaştırılmaz.
- Holding: FCF türü ekonomik tipe göre (FCF_HLD); ikisi de gösterilir.
- Evo/V7 değeri yalnız karşılaştırma içindir, kaynak değildir.

## 5. Biçim
Kaynak tablolar git'te düz dosya (CSV) olarak tutulur: farkları görülebilir, script'ler okur. Excel ise bunlardan üretilen
okuma görünümüdür; elle değişiklik Excel'e değil kaynak tabloya (çoğunlukla KARAR'a) yapılır.

## 6. Bu çalışmadan taşınacaklar
Mevcut `rapor_kalemleri*.csv`, `rapor_bildirim_haritasi.json`, `elle_kararlar.json`, `ocr/` ve `site/` çıktıları
RAPOR / KALEM / KARAR tablolarının ilk doldurulmuş hâlidir. Evo köprüsü (V7) master'da yalnız karşılaştırma sütunu olur.
