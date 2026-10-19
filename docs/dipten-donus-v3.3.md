# DİPTEN DÖNÜŞ FİLTRESİ v3.3 — CLAUDE CODE UYGULAMA TALİMATI

Tarih: 19 Ekim 2026
Önceki sürüm: v3.2. Bu sürüm v3.2'nin yerini alır. Değişen yerler 16. bölümde listelenmiştir.

## 0. Amaç ve kapsam (bu bölüm diğer bütün hükümlere üstündür)

Bu filtrenin amacı, operasyonel dipten toparlanmaya başlayan şirketleri ERKEN yakalamaktır. Bütün sorunları çözülmüş şirketleri seçmek değildir.

1. Ön tarama ile teyit ayrıdır. Anlamlı geçmiş bozulma (5. bölüm) ve sayısal erken sinyal (6. bölüm) bulunan şirket ADAY HAVUZUNA girer. İki çeyrek teyit, pozitif FCF, tamamlanmış belge incelemesi, yüksek toplam puan veya bütün borç sorunlarının çözülmüş olması aday havuzuna giriş şartı değildir; bunlar teyit, risk değerlendirmesi ve inceleme önceliği içindir.
2. Puanlar önceliklendirir; aday silmez. 35/65 ve 70/100 eşikleri yalnızca inceleme sırası ve teyit düzeyi içindir. Puanı düşük adaylar, sınırdaki şirketler ve kısa geçmiş nedeniyle teyidi eksik olanlar kayıtta kalır. Kısa finansal geçmiş otomatik eleme nedeni değildir (5. bölüm).
3. Eksik veri olumsuz sonuç değildir. EKSİK ve UYGULANAMAZ kalemler ayrı gösterilir; otomatik eleme veya kesin sıfır puan üretmez.
4. Sınırdaki adaylar görünür tutulur (8.5). Bu liste otomatik olumlu kabul edilmez; pilotta yanlış eleme olup olmadığını incelemek için kullanılır.
5. Dönüş, risk ve değerleme ayrı eksenlerdir. Borç riski veya pahalı fiyat açıkça işaretlenir; tespit edilmiş operasyonel toparlanma bulgusu silinmez.
6. Yeni kriter eklenmez. Önce puanlama/veri tutarlılığı sabitlenir, ardından pilot çalıştırılır. Pilot hem geçenleri hem sınırdakileri değerlendirir. Eşikler sonuçları güzelleştirmek için değiştirilmez; kaçırılan gerçek dönüşler ve sahte sinyaller gerekçeleriyle raporlanır.

Bu belge bir tarama metodolojisidir. Sayısal eşikler geçmişte doğrulanmış başarı ölçütleri değildir. "PİLOT" parametreler başlangıç varsayımlarıdır. Sonuçları gördükten sonra eşiklerle oynanmaz; değişiklik gerekiyorsa yeni sürüm ve gerekçe kaydı oluşturulur. GEM v4/v5 metinlerindeki çelişen filtre hükümleri bu taramada kullanılmaz. Başka çalışmaların evrenleri bu talimat gerekçesiyle değiştirilmez.

## 1. Kapsam ve iş akışı

- Ana evren: BIST'teki finans dışı faaliyet şirketleri. Banka, sigorta, finansal kiralama, faktoring, finansman, aracı kurum, GYO/GSYO/MKYO ve holdingler bu modelin dışındadır; ayrı metodoloji gerektiren evrende tutulur. Kapsam dışı olmak "kötü şirket" anlamına gelmez.
- Şirket bazında sabit olumlu/olumsuz liste tutulmaz. Önceki analizlerin şirket sonuçları taşınmaz.
- Geçmiş: Ana tarama mevcut son 8 çeyreği esas alır. Daha uzun karşılaştırılabilir geçmiş varsa yardımcı bilgi olarak (örneğin referans hesabında) kullanılır; aday havuzuna giriş şartı değildir. Halka arz tarihi ile finansal geçmiş uzunluğu ayrıdır; halka arz öncesi karşılaştırılabilir finansallar varsa kullanılabilir, yoksa mevcut veriyle devam edilir. İki yıldır borsada olan şirket otomatik elenmez.
- Eksik geçmiş/veri, temel başarısızlıktan ayrı "VERİ EKSİĞİ" sınıfıdır.
- İşlem likiditesi ayrı raporlanır (mümkünse son 60 işlem gününün medyan günlük TL hacmi). Kullanıcı eşik belirlemedikçe düşük hacim temel toparlanmayı iptal etmez; uygulanabilirlik uyarısı üretir.
- İki aşama: (1) sayısal tarama, aday havuzu ve ön puan; (2) adaylarda belge incelemesi, nakit/bilanço teyidi ve değerleme.
- Aday havuzundaki bütün şirketler kaydedilir. Evren ilk 10–15 ile kesilmez. Belge incelemesi 8. bölümdeki kuyruk sırasıyla partiler halinde yürütülür.

## 2. EVO / TMS 29 veri protokolü (sabit karar)

Kullanıcının Evo ile daha önce doğruladığı çalışma kararı esas alınır:

1. Evo geçmiş dönemleri güncel raporlama döneminin satın alma gücüne yeniden bazlar.
2. Cari/önceki dönem karşılaştırmaları aynı veri çekim oturumundaki verilerle yapılır.
3. TTM akışları doğrudan Evo'dan, ilgili kalemin `try_ttm` alanından alınır. Alanın o kalem için mevcut olduğu şemadan doğrulanır; alan adı veya tablo adı uydurulmaz.
4. Ek TÜFE veya TMS 29 düzeltmesi YAPILMAZ. İkinci enflasyon düzeltmesi yasaktır.
5. Farklı tarihlerde çekilmiş finansal seriler birleştirilmez. Yenilemede şirketin karşılaştırmalı serisi bir arada yeniden çekilir.
6. Her koşuya run_id, başlangıç/bitiş zamanı, finansal dönem, rapor yayımlanma tarihi, kaynak ve birim bilgisi yazılır. Aynı koşuda revizyon farkı görülürse ilgili şirketin serisi tutarlı biçimde yeniden çekilir. Aynı oturum, şirketlerin aynı mali dönemi açıkladığı anlamına gelmez; dönemler açık gösterilir. Aralık 2023 öncesi gözlemler "TMS 29 öncesi kaynak, Evo tarafından yeniden bazlanmış" olarak etiketlenir.
7. Bilanço kalemleri dönem sonu bakiyeleridir; bunlarda TTM kullanılmaz (nakit, stok, borç, özkaynak, cari oran).
8. TTM marj = TTM ilgili kâr / TTM satış. Çeyreklik marjların basit ortalaması kullanılmaz.
9. Çeyreklik veri gerekiyorsa Evo'nun belgelenmiş karşılaştırılabilir çeyreklik serisi kullanılır. Kümülatiften fark alınacaksa girdilerin aynı satın alma gücü ve konsolidasyon bazında olduğu doğrulanır; doğrulanamıyorsa çeyreklik metrik NULL olur. Eski raporlarla fark alınmaz; yeni TÜFE düzeltmesi eklenmez.
10. Doğrudan TTM'i bulunmayan zorunlu kalem sessizce ham çeyreklerden türetilmez. Onaylı veri motorunda belgelenmiş yöntem varsa kullanılır ve "TÜRETİLMİŞ" etiketi konur; yoksa VERİ EKSİĞİ.
11. Aralık döneminde TTM = aynı kapsam ve bazdaki tam yıl; iki ayrı veri gibi puanlanmaz.
12. Şirketin gerçekte tabi olduğu raporlama rejimi/para birimi kaydedilir. Evo'nun alan tanımıyla çelişen bir durumda varsayımla düzeltme yapılmaz; veri istisnası açılır.

## 3. Ortak tanımlar ve korumalar

- İFNA: İşletme faaliyetlerinden nakit akışları. "İşletme sermayesi değişimi öncesi faaliyet nakdi" ile karıştırılmaz.
- Temiz EFK: Brüt kâr − pazarlama/satış/dağıtım giderleri − genel yönetim giderleri − gelir tablosunda giderleşmiş Ar-Ge. Giderler pozitif büyüklük olarak işlenir; satışların maliyetinde veya toplu faaliyet giderlerinde zaten bulunan gider ikinci kez düşülmez. Tanım bütün dönemlerde sabittir; varlık satışı, yatırım geliri, parasal kazanç ve finansman geliri eklenmez.
- FAVÖK: Evo'da tanımı doğrulanan seri. Şirketin "düzeltilmiş FAVÖK"ü ayrı gösterilir; iki seri birbirine eklenmez.
- Payda korumaları:
  - Satış ≤ 0 ise marj hesaplanmaz.
  - Negatif/sıfıra yakın kâr veya FAVÖK üzerinden yüzdesel büyüme ya da çarpan üretilmez; mutlak değişim ve marj değişimi kullanılır.
  - FAVÖK ≤ 0 ise FD/FAVÖK ve Net Borç/FAVÖK "ANLAMLI DEĞİL"dir; negatif oran ucuzluk veya düşük borçluluk sayılmaz.
  - Net kâr ≤ 0 veya sıfıra yakınsa FCF/Net Kâr hesaplanmaz; bu oran hiçbir durumda geçiş şartı değildir.
  - Yüzdesel kâr büyümesi yalnızca pozitif bazda hesaplanır; kârdan zarara ve zarardan kâra geçiş ayrıca etiketlenir.
- Net borç (TFRS 16 dahil) = faiz taşıyan finansal borçlar + bunlara dahil olmayan kira yükümlülükleri − serbest nakit ve nakit benzerleri − gerçekten likit ve serbest kısa vadeli finansal yatırımlar. Blokeli nakit düşülmez; aynı kira veya yatırım iki kez sayılmaz.
- Karşılaştırmalarda yuvarlanmamış veri kullanılır. 100 baz puan (bps) = 1 yüzde puan.
- Cari oran = dönen varlıklar / kısa vadeli yükümlülükler.
- Asit-test = (dönen varlıklar − stoklar − kısa vadeli peşin ödenmiş giderler) / kısa vadeli yükümlülükler. Kısa vadeli yükümlülükler ≤ 0 ise bu oranlarla puan verilmez. Eksik peşin gider kalemi sıfır varsayılmaz. Oranların yükselmesi tek başına tahsil edilebilirliği kanıtlamaz.

## 4. FCF standardı

Durum (19 Ekim 2026): `deryaozyuvali/Bist-tarama-otomasyon` reposunda (kullanıcının erişilebilir tek reposu) FCF veya Evo kodu bulunmadı. Kullanıcı mevcut bir FCF standardı olduğunu belirtti; konumu/formülü henüz paylaşılmadı. Kod bulunamaması, onaylı yöntem bulunmadığı anlamına gelmez.

- Kullanıcının standardı paylaşıldığında o kullanılır ve aşağıdaki taslağın yerini alır.
- O zamana kadar FCF_STD v1 (TASLAK) kullanılabilir. Bütün FCF çıktıları ve FCF'ye dayanan B4/D3 puanları "TASLAK PUAN" olarak gösterilir.
- Her satırda `fcf_yontem` ve `fcf_yontem_surumu` alanı tutulur. Onaylı yöntem gelince ilgili bütün şirketler aynı yöntemle yeniden hesaplanır; eski ve yeni yöntem sonuçları aynı sıralamada karıştırılmaz.
- Evo'nun hazır FCF alanı FCF_STD yerine konmaz.

FCF_STD v1 (TASLAK) = İFNA TTM − CAPEX TTM − İFNA dışında raporlanmış kira anapara ödemeleri TTM

- CAPEX: maddi ve maddi olmayan duran varlık alımlarının brüt nakit çıkışı. Yatırım amaçlı gayrimenkul alımı ayrı raporlanmışsa eklenir; diğer CAPEX içinde zaten sayılmışsa tekrar eklenmez. Varlık satış gelirleri mahsup edilmez. Nakit dışı kullanım hakkı varlığı eklenmesi CAPEX değildir.
- Kira: ödeme İFNA içinde zaten düşülmüşse tekrar düşülmez.
- İşaretler kaynak şemasına göre standartlaştırılır; net yatırım nakit akışının mutlak değeri CAPEX sayılmaz.

Faiz sınıflandırması: FCF_STD içinde henüz düşülmemiş nakit faiz varsa (örneğin finansman faaliyetlerinde raporlanan ödenen faiz) yardımcı seri FCF_FAIZ_SONRASI = FCF_STD − henüz düşülmemiş nakit faiz üretilir. İFNA veya CAPEX içinde zaten düşülmüş faiz yeniden düşülmez. Ana FCF_STD değişmez; yardımcı seri ve mutabakatı ayrı saklanır. Değerlemedeki nakit verimi faiz ve kira sonrası olmalıdır; sınıflandırma çözülemezse verim NULL olur.

Bakım/büyüme CAPEX ayrımı yalnızca belgeye dayanır; açıklanmıyorsa tahminle yaratılmaz. FCF negatifliği ancak belgeyle "yatırım kaynaklı" etiketlenir. CAPEX düşüşü tek başına iyi veya kötü sayılmaz.

Eksik kayıt sıfır değildir. Her TTM bileşeninin dönem kapsamı ve kaynağı kaydedilir. Doğrudan TTM tutarının varlığı, dört ham çeyreğin ayrı ayrı doğrulandığı anlamına gelmez; kapsam güvencesinin kaynağı yazılır.

## 5. Gerçek dip tespiti (puansız giriş koşulu)

İFNA'nın daha önce negatif olması zorunlu değildir. Hisse fiyatındaki düşüş operasyonel dip kanıtı değildir.

PİLOT arama yöntemi:

- t: şirketin son açıklanmış mali çeyreği.
- Aday dip tarihleri: d ∈ {t−7 … t−1}. Son dönem (t) minimumsa "dip devam ediyor olabilir" denir; bu tek başına dönüş teyidi değildir.
- Ana pencere: son 8 çeyrek. Daha eski karşılaştırılabilir veri varsa yalnızca referans hesabında yardımcı olarak kullanılır.
- Referans seçimi: Her d için aşağıdaki yollardan ilk uygulanabilen kullanılır. Yol, sonuca bakılmadan yalnızca veri varlığına göre belirlenir; aynı veri durumundaki her şirkete aynı yol uygulanır.
  - R-TTM: TTM(d), d−7 … d−4 dönemlerinde biten TTM gözlemlerinin medyanıyla karşılaştırılır. Bu gözlemler TTM(d) ile ortak çeyrek içermez (TTM(d−4) d−7…d−4'ü, TTM(d) d−3…d'yi kapsar). Mevcut gözlemlerin hepsi kullanılır, seçme yapılmaz. Tek gözlemle hesaplanan referans "ZAYIF REFERANS" etiketi alır.
  - R-ÇEYREK: R-TTM için hiç gözlem yoksa, d çeyreğinin çeyreklik değeri geçen yılın aynı çeyreğiyle (d−4) karşılaştırılır. Ortak çeyrek yoktur ve mevsimsellik kontrol edilir. Çeyreklik girdiler 2. bölüm madde 9'a göre doğrulanmış olmalıdır; doğrulanamıyorsa bu yol EKSİK olur.
  - İkisi de uygulanamıyorsa o d için "referans yok".
- Dip hiçbir zaman kendi referansına katılmaz. Referans, en yüksek marjlı dönem seçilerek oluşturulmaz. TTM gözlemleri arasındaki ortak çeyrekler bağımsız kanıt sayılmaz.
- Hangi yolun mümkün olduğu (n = Evo'daki karşılaştırılabilir ham çeyrek sayısı, son çeyrek t dahil):
  - R-TTM mümkün ⇔ d ≥ t − n + 8. Dört gözlemin tamamı ⇔ d ≥ t − n + 11.
  - R-ÇEYREK mümkün ⇔ d ≥ t − n + 5.
  - Örnekler: n = 18 veya fazlası → bütün d'ler R-TTM, 4 gözlem. n = 12 → d ≥ t−4 için R-TTM (1–3 gözlem), d ∈ {t−7 … t−5} için R-ÇEYREK. n = 8 → R-TTM yok; d ∈ {t−3 … t−1} için R-ÇEYREK. n ≤ 5 → referans yok.
- Kayıt: Her d için kullanılan yol, referans dönemleri, gözlem sayısı ve ZAYIF REFERANS etiketi çıktıya yazılır.

Bozulma kanıtları (en az ikisi; en az biri A veya B):

- A: TTM FAVÖK marjı referans medyandan en az 150 bps düşük.
- B: TTM temiz EFK pozitif referans medyandan en az %25 düşük. Pozitif referanstan sıfıra/zarara geçiş de B'yi sağlar. Referans pozitif değilse B değerlendirme dışıdır.
- C: TTM reel satışlar pozitif referans medyandan en az %10 düşük.
- D: TTM İFNA/satış marjı referans medyandan en az 200 bps düşük.

R-ÇEYREK yolunda aynı eşikler d çeyreğinin çeyreklik değerlerine, geçen yılın aynı çeyreğine göre uygulanır (çeyreklik FAVÖK marjı, çeyreklik temiz EFK, çeyreklik reel satış, çeyreklik İFNA/satış). Doğrulanmamış çeyreklik kalem EKSİK'tir.

Seçim ve sınıflar:

- En az iki kanıtı sağlayan tarihler arasından dip tarihi şöyle seçilir: R-TTM ile sağlayan tarih varsa bunlar arasından TTM FAVÖK marjı en düşük olan; yoksa R-ÇEYREK ile sağlayanlar arasından çeyreklik FAVÖK marjı en düşük olan. Eşitlikte en güncel alınır.
- A ve B'nin ilişkili ölçüler olduğu kayda geçer. Dip bulmak ayrıca puan kazandırmaz.
- Eksik gözlem yüzünden iki kanıtın varlığı kararlaştırılamıyorsa "dip kanıtı için veri yetersiz" yazılır, "dip yok" yazılmaz. Eldeki iki geçerli kanıt koşulu sağlıyorsa diğer kanıtların eksikliği girişi engellemez.
- Tam veriyle koşulu sağlamayan şirket "BU MODELDE DİP KANITI YOK" sınıfındadır; bundan kötü şirket sonucu çıkarılmaz.
- Büyük satın alma, satış veya faaliyet kapsamı değişikliği varsa organik/karşılaştırılabilir seri olmadan dip teyit edilmez.
- Sektörel eşik farklılaştırması gerekirse sonuçlara bakmadan önce ayrıca sürümlenmiş parametre seti hazırlanır. Bir şirketi geçirmek için eşik değiştirilmez.

Kısa geçmiş:

- Sekiz çeyrekten kısa geçmiş otomatik eleme nedeni değildir.
- KISA GEÇMİŞLİ ADAY: Dip kanıtı ve erken sinyal mevcut veriyle gösterilebiliyor; ancak seçilen dip R-ÇEYREK ile veya ZAYIF REFERANS ile bulunmuş ya da n < 8. Aday havuzuna girer; etiket görünür kalır.
- DİP DOĞRULANAMADI — GEÇMİŞ SINIRLI / TOPARLANMA İZLEMESİ: Hiçbir d için referans yok veya referans yolları EKSİK, fakat güncel toparlanma sinyali var. Güncel toparlanma sinyali, 6. bölümdeki erken sinyal koşullarının dipten bağımsız kısmıdır: (a) son çeyrek FAVÖK marjı geçen yılın aynı çeyreğinden en az 50 bps yüksek ve temiz EFK marjı geçen yılın aynı çeyreğinden düşük değil; veya (b) son TTM FAVÖK marjı önceki TTM'den yüksek ve temiz EFK marjı önceki TTM'den düşük değil. Bu şirketler aday havuzuna girmez ve puanlanmaz; ayrı listede gösterilir.
- Hesaplanamayan YoY, TTM veya referans karşılaştırmaları tahminle doldurulmaz; EKSİK işaretlenir.
- Sınırlı geçmişten "dip yok", "şirket kötü" veya "dönüş kesin" sonucu çıkarılmaz.

## 6. Erken sinyal ve teyit koşulları

ADAY HAVUZUNA GİRİŞ = dip kanıtı (5. bölüm) + sayısal erken sinyal (aşağıda). Başka şart yoktur.

Sayısal ERKEN SİNYAL (iki yoldan biri yeterli; kullanılan yol yazılır):

- Çeyreklik yol: Son çeyrek FAVÖK marjı hem dip çeyreğinden hem geçen yılın aynı çeyreğinden en az 50 bps yüksek; temiz EFK marjı geçen yılın aynı çeyreğinden düşük değil. Bütün çeyreklik girdiler doğrulanmış olmalı.
- TTM yolu: Son TTM FAVÖK marjı dip TTM'den en az 100 bps yüksek ve bir önceki TTM'den yüksek; temiz EFK marjı dip dönemindekinden yüksek.
- TTM geriden geldiği için çeyreklik yol korunur. Dip R-ÇEYREK ile bulunduysa ve TTM(d) hesaplanamıyorsa TTM yolu EKSİK'tir; çeyreklik yol kullanılır. Mevsimsellik veya tek seferlik etkiyle açıklanabilecek ham sinyal, belge incelemesi tamamlanana kadar "sayısal erken sinyal"dir.

OPERASYONEL TEYİT (tümü gerekir; aday havuzuna giriş şartı DEĞİLDİR):

1. Son iki çeyreğin FAVÖK marjı, her biri kendi geçen yıl aynı çeyreğinden en az 50 bps yüksek.
2. Son iki çeyrekte temiz EFK marjı geçen yılın aynı çeyreklerinden düşük değil.
3. Son TTM FAVÖK marjı dipten en az 100 bps yüksek.
4. Belge incelemesi, iyileşmenin yalnızca tek seferlik kalem, konsolidasyon değişimi veya karşılık iptalinden gelmediğini destekliyor.

Çeyreklik veri doğrulanamıyorsa TTM sinyali raporlanır ama teyit tamamlanmış sayılmaz. İki ardışık TTM bağımsız iki kanıt değildir; üç çeyrekleri ortaktır.

NAKİT TEYİDİ (aday havuzuna giriş şartı DEĞİLDİR): Son TTM İFNA > 0; İFNA marjı dipten iyileşmiş; nakit kaynağı incelemesi tamamlanmış ve kalıcılığı destekliyor. Sadece işaret değişimi yetmez.

Nakit kaynağı incelemesi: Değişim işletme sermayesi öncesi nakit üretimi, alacaklar, stoklar, ticari borçlar, avanslar, vergi/faiz ve diğer önemli unsurlarla açıklanır. Nakit akış tablosundaki etkiler kullanılır; TMS 29 altındaki bilanço bakiye farkı doğrudan nakit etkisi sayılmaz. Tedarikçi ödemelerinin geciktirilmesi, alacak satışı/faktoring, geçici müşteri avansı, daralmaya bağlı stok boşaltma ve ilişkili taraf hareketleri incelenir. Bunlar otomatik kötü sayılmaz; ekonomik neden ve tekrar edebilirlik belgeyle ayrılır. Ticari borç artışının aynı faydası birden fazla başlıkta puanlanmaz.

## 7. Puanlama (tek tablo, toplam 100, eşikler PİLOT)

Puanlar sıralama ve teyit düzeyi içindir; aday havuzuna giriş ve teyit koşullarının yerine geçmez.

Satır türleri:
- [OTO]: Evo verisinden otomatik hesaplanır.
- [BELGE]: Analist/belge incelemesi gerekir.
- [OTO*]: Yalnızca gerekli bütün girdiler ve kapsamları doğrulanmışsa otomatik; aksi halde BELGE/NULL.

Her satırın durumu şu değerlerden biridir: HESAPLANDI / EKSİK (veri veya inceleme bekleniyor) / UYGULANAMAZ (gerekçesi doğrulanmış; örneğin yeterli emsal yok). EKSİK ve UYGULANAMAZ satırlara puan verilmez ve sıfır yazılmaz.

Kısa geçmiş durumu: Dip R-ÇEYREK ile bulunmuş ve TTM(d) hesaplanamıyorsa "dipten" ölçülen A1, A2 ve B1 için: gerekli eski çeyrekler Evo'da yoksa ve izahnamede de bulunmadığı doğrulandıysa UYGULANAMAZ; izahname henüz kontrol edilmediyse EKSİK.

### A. Operasyonel toparlanma (30)

- A1 [OTO]: TTM FAVÖK marjının dipten artışı. ≥200 bps: 10 · 100–<200: 5 · <100: 0
- A2 [OTO]: TTM temiz EFK marjının dipten artışı. ≥100 bps: 5 · 50–<100: 2,5 · <50: 0
- A3 [OTO]: Son iki çeyreğin FAVÖK marjı YoY artışı. İkisinde ≥50 bps: 5 · birinde: 2,5 · hiçbirinde: 0
- A4 [OTO]: Son TTM temiz EFK marjının önceki TTM'ye göre değişimi. ≥50 bps: 5 · >0–<50: 2,5 · ≤0: 0
- A5 [OTO/BELGE]: Karşılaştırılabilir ana faaliyet satış hacminin son çeyrek YoY değişimi. Artmış: 5 · değişmemiş: 2,5 · azalmış: 0. Hacim açıklanmıyorsa aynı puanlama son TTM reel satışların bir yıl önceki TTM'ye değişimine uygulanır ("vekil ölçü" etiketi). İkisi de yoksa EKSİK. Önceden tanımlanmış ana faaliyet kullanılır; iyileşen segment seçilmez. Konsolidasyon etkisi ayrıştırılamıyorsa EKSİK.

### B. Nakit toparlanması (25)

- B1 [OTO]: TTM İFNA marjının dipten artışı. ≥200 bps: 10 · 100–<200: 5 · <100: 0
- B2 [OTO]: Pozitif İFNA'nın devamı. Son ve önceki TTM pozitif: 5 · yalnızca son TTM pozitif: 2,5 · son TTM ≤0: 0
- B3 [BELGE]: Nakdin kaynağı. Süregelen faaliyet ve/veya sürdürülebilir işletme sermayesi normalleşmesi: 5 · kalıcı ve geçici karışık, ayrım belgelenmiş ama devamı belirsiz: 2,5 · geçici kaynak veya ödeme baskısı: 0 · inceleme yoksa EKSİK. Otomatik tahminle doldurulmaz; kaynak belge, dönem, gerekçe ve karşı açıklama yazılır. Nakit teyidi için B3 = 5 gerekir.
- B4 [OTO + BELGE] (TASLAK YÖNTEM, bkz. 4. bölüm): FCF_STD. Hesaplama kesinliği ile yöntem onayı ayrıdır. Yöntem TASLAK olduğu sürece "kesin puan" ifadesi kullanılmaz.
  - Son TTM > 0: "Taslak yönteme göre B4 = 5 hesaplandı; bu dal için ek belge beklenmiyor. Yöntem onayı bekleniyor."
  - Son TTM ≤ 0 ve önceki TTM'ye göre iyileşmemiş: "Taslak yönteme göre B4 = 0 hesaplandı; bu dal için ek belge beklenmiyor. Yöntem onayı bekleniyor."
  - Son TTM ≤ 0 ama önceki TTM'ye göre iyileşmiş ve yatırım nedeni henüz incelenmemiş: B4_puan = NULL, B4_alt_sinir = 0, B4_ust_sinir = 2,5, durum = "yatırım nedeni incelemesi bekleniyor".
  - İnceleme tamamlandı ve negatifliğin büyüme yatırımı kaynaklı olduğu belgelendi: 2,5. İnceleme tamamlandı ve belgeler bu nedeni desteklemiyor: 0.
  - Belgeye erişilemedi veya şirket nedeni açıklamamış: EKSİK olarak kalır (alt 0, üst 2,5), durum "belge erişilemedi / açıklama yok". Bu, "inceleme tamamlandı ve kriter sağlanmadı" ile karıştırılmaz.
  - Formül veya veri eksikse EKSİK (alt 0, üst 5).

### C. Bilanço dayanıklılığı (20)

- C1 [OTO]: TFRS 16 dahil net borç / TTM satış oranının bir yıl öncesine göre değişimi. ≥5 yüzde puan düşüş: 5 · >0–<5 düşüş: 2,5 · düşüş yok: 0. Hem cari hem önceki yılda net nakit varsa 5.
- C2 [OTO*]: (Serbest nakit + ayrıca sayılmamış likit yatırımlar + taahhütlü, kullanılmamış ve vadesi uygun kredi limiti) / önümüzdeki 12 ayın finansal borç ve kira anaparası. ≥1,2: 5 · 1–<1,2: 2,5 · <1: 0. Gerçekten anapara ödemesi yoksa 5. Toplam banka limiti yeterli değildir; limitin taahhütlü, kullanılmamış ve vadesinin uygun olduğu doğrulanmalıdır.
- C3 [OTO*]: TTM temiz EFK / TTM nakden ödenen toplam faiz. ≥3: 5 · 1,5–<3: 2,5 · <1,5: 0. Faiz pozitifken EFK ≤0 ise 0. Muhasebeleşmiş finansman gideri değil, nakden ödenen faiz kullanılır ve ilgili bütün sınıflandırmalar (İFNA, yatırım, finansman) kapsanır. Belgeli sıfır faiz: 5. Kalemin bulunamaması sıfır sayılmaz.
- C4 [BELGE]: Cari oran ve asit-test bir yıl öncesine göre ikisi de yükselmiş ve önemli tahsilat/stok kalitesi sorunu yok: 5 · yalnızca biri yükselmiş ve kalite sorunu yok: 2,5 · ikisi de yükselmemiş veya doğrulanmış önemli kalite sorunu: 0 · inceleme yoksa EKSİK.

Notlar: C1'de borç azalmasının kaynağı sermaye artırımı veya varlık satışıysa kaynak açıkça yazılır; aynı olay operasyonel nakit başarısı sayılmaz. C2'de 0 puan otomatik temerrüt/eleme değildir; faiz, ticari ödemeler ve işletme ihtiyacı ayrıca 12 aylık likidite incelemesine girer. Cari oran < 1 veya Net Borç/FAVÖK > 3 tek başına eleme sebebi değildir; Net Borç/FAVÖK raporlanır ama negatif FAVÖK ile yorumlanmaz.

### D. Değerleme (15)

- D1 [OTO]: Geçerli TTM FD/FAVÖK'ün emsaller içindeki yeri. Alt %25: 5 · %25–%50: 2,5 · %50 üstü: 0. Oran anlamlı değilse veya yeterli emsal yoksa UYGULANAMAZ (gerekçesiyle).
- D2 [BELGE/MODEL]: Temkinli normalleşmiş özsermaye değeri / mevcut piyasa değeri − 1. ≥%25: 5 · >0–<%25: 2,5 · ≤0: 0. Varsayım/kaynak eksikse EKSİK.
- D3 [OTO*] (TASLAK YÖNTEM; yöntem TASLAK iken "kesin puan" denmez): Faiz ve kira sonrası FCF getirisi. Pozitif ve emsal medyanına eşit/üstünde: 5 · pozitif ama medyan altı: 2,5 · ≤0: 0. Faiz sınıflandırması çözülmediyse EKSİK; yeterli emsal yoksa UYGULANAMAZ.

Emsal sepeti: Sonuçlar görülmeden iş modeli/alt sektöre göre belirlenir; en az 5 karşılaştırılabilir şirket gerekir. D1'de pozitif FAVÖK ve pozitif FD içeren oranlar kullanılır. Yüzdelik sıra = (daha düşük oranlı emsal + 0,5 × eşit oranlı emsal) / emsal sayısı. D3 medyanına geçerli negatif getiriler dahildir. Fiyatlar aynı değerleme gününden, mali veriler son açıklanmış dönemden; dönem farkları gösterilir.

Normalleşmiş değer: Geçmişin en iyi marjı seçilerek yaratılmaz. 3–5 yıllık karşılaştırılabilir marj/hacim, bugünkü kapasite ve güncel sektör koşullarıyla temkinli/baz/iyimser senaryolar kurulur; D2 temkinli senaryodan puan alır. Varsayımlar ve çarpan gerekçesi yazılır. FD'den özsermayeye geçişte net borç, azınlık payları ve diğer düzeltmeler tutarlı işlenir; TFRS 16 pay ve paydada uyumludur.

Yardımcı göstergeler (puansız): Tarihsel PD/DD yalnızca yardımcıdır; muhasebe rejimi ve seri sunumu kontrol edilmeden 5 yıllık ortalama kullanılmaz. 52 haftalık dipten uzaklık, XU100'e göre performans ve varsa altın bazlı fiyat ayrı sütunlardır. Konsensüs destekleyicidir; hedef fiyat adil değer kabul edilmez.

### E. Yönetim ve katalizör (10)

- E1 [BELGE]: Son 12 ayda gerçekleşmiş ve ölçülebilir etkisi görülen olay: 5 · resmen açıklanmış, takvimi/ölçeği belli ama etkisi teyit edilmemiş: 2,5 · belgeli katalizör yok: 0 · arama yapılmadıysa EKSİK.
- E2 [BELGE]: En az iki ölçülebilir hedef zamanında ve kapsamında gerçekleşmiş: 5 · biri: 2,5 · değerlendirme tamamlanmış, gerçekleşme yok: 0 · inceleme yoksa EKSİK. Şirketin hiç ölçülebilir hedef açıklamadığı doğrulanmışsa UYGULANAMAZ.

Guidance zorunlu değildir; hedefler yatırım devreye alma, kapasite kullanımı, maliyet azaltma, zarar eden birimin kapatılması gibi kilometre taşları olabilir. E1'deki olay E2'de tekrar sayılmaz. Geri alım programı ile fiili alım ayrılır; otomatik puan verilmez.

## 8. Ön puan, inceleme kuyrukları ve sonuç sınıfları

### 8.1 Sayısal ön puan

- Kapsam bütün şirketlerde SABİTTİR: A1 + A2 + A3 + A4 + A5 + B1 + B2 + B4 + C1 + D1 + D3. Azami 65.
- C2 ve C3 erken hesaplanabilse bile ön puana EKLENMEZ. Sonuçları ayrı sütunda gösterilir ve nihai puana işlenir. Böylece her şirket aynı 65 üzerinden sıralanır ve 35/65 eşiği aynı anlamı korur.
- Her şirket için hesaplanır:
  - ON_PUAN_ALT = HESAPLANDI satırların puanı + EKSİK satırların alt sınırı. Alt sınır satır için özel tanımlanmışsa o değerdir (B4'te 0); tanımlı değilse 0'dır. Alt sınırdaki 0 "doğrulanmış 0" diye gösterilmez.
  - ON_PUAN_UST = ON_PUAN_ALT + her EKSİK satırın KALAN olası puanı (satırın üst sınırı − alt sınırı). Örnek: negatif ama iyileşen FCF'de B4'ün kalan puanı 2,5 − 0 = 2,5'tir, satır azamisi olan 5 değil. Aynı puan iki kez eklenmez.
  - UYGULANAMAZ satırlar ne alt ne üst sınıra katılır. UYGULANAMAZ_KAPASITE ayrı sütunda, gerekçesiyle gösterilir.
- Ön puan "ALT–ÜST / 65 (ön)" olarak yazılır, örneğin "32–34,5/65 (ön)". Nihai puan gibi sunulmaz; eksik veya uygulanamaz kalemler nedeniyle yeniden ölçeklenmez.
- FCF yöntemi TASLAK iken ön puanda B4 veya D3 katkısı varsa "taslak FCF katkısı içerir (B4 = x, D3 = y)" notu yazılır.
- 35/65 yalnızca inceleme önceliğidir, eleme eşiği değildir.

### 8.2 İnceleme kuyrukları (eleme değil, sıra)

- Kuyruk 1: ON_PUAN_ALT ≥ 35.
- Kuyruk 2 (eksik inceleme): ON_PUAN_ALT < 35 ≤ ON_PUAN_UST. Eksik kalemin tamamlanması şirketi Kuyruk 1'e taşıyabilir; bu yüzden ayrı görünür. UYGULANAMAZ kalemler üst sınırı artırmadığı için, yalnızca uygulanamaz bir kalem yüzünden hiçbir şirket Kuyruk 2'ye girmez.
- Kuyruk 3: ON_PUAN_UST < 35. Kayıtta kalır, "düşük puanlı erken sinyal" olarak izlenir.
- Kuyruk içi sıra: ON_PUAN_ALT büyükten küçüğe; eşitlikte ON_PUAN_UST.
- KISA GEÇMİŞLİ ADAY'lar aynı kuyruklara girer; etiketleri görünür kalır. DİP DOĞRULANAMADI listesi ve sınırdaki adaylar listesi kuyrukların dışındadır.

### 8.3 Eksik ve uygulanamaz kalemler

- EKSİK: Veri veya inceleme bekleniyor. Puanı NULL; olası aralığa katılır.
- UYGULANAMAZ: Gerekçesi doğrulanmış (örneğin beş uygun emsal yok, şirket ölçülebilir hedef açıklamamış). Puan verilmez, toplam yeniden ölçeklenmez; gerekçe yazılır.
- Nihai gösterim: bilinen_puan, bilinen_azami_puan, eksik_puan_kapasitesi, uygulanamaz_puan_kapasitesi ve [bilinen_puan, bilinen_puan + eksik_puan_kapasitesi] aralığı. Bu aralık istatistiksel güven aralığı değildir.
- Örnek: Bilinen 55, değerlendirilen azami 75, eksik kapasite 20, uygulanamaz kapasite 5 → "55/75 değerlendirildi; olası aralık 55–75/100; 5 puan uygulanamaz (D1: yeterli emsal yok)". Yanlış: "55/100 başarısız" veya "73/100".

### 8.4 Üç sonuç ekseni

1. Dönüş durumu: kapsam dışı / veri yetersiz / dip doğrulanamadı — geçmiş sınırlı / toparlanma izlemesi / dip kanıtı yok / dip var, dönüş sinyali yok / sayısal erken sinyal / belgeyle teyit edilmiş erken sinyal / operasyonel ve nakit teyitli dönüş.
2. Finansal risk: inceleme eksik / yüksek risk / incelendi, önemli açıklanamayan açık saptanmadı (risksiz demek değildir).
3. Değerleme: incelenmedi / uygulanamaz / temkinli senaryoda ≥%25 yükseliş alanı / %0–<%25 / pozitif yükseliş alanı yok.

Borç riski veya pahalı fiyat ilgili eksende açıkça işaretlenir; dönüş eksenindeki bulguyu silmez.

Puan tamamlanma durumu, dönüş durumundan ayrı bir alandır: TAM / KISMİ — EKSİK / KISMİ — UYGULANAMAZ / KISMİ — TASLAK FCF (birden fazlası birlikte olabilir). Dönüş durumu bu alandan etkilenmez.

### 8.5 Sınırdaki adaylar listesi

Dip veya erken sinyal şartlarından YALNIZCA BİRİNİ kaçıran şirketler bu listede gösterilir:

- Dip: Değerlendirilebilen bir d için tam olarak bir kanıt sağlanmış (A veya B) ve ikinci kanıt eksik veya sağlanmamış.
- Erken sinyal: Dip kanıtı var; kullanılabilir yollardan birinde tam olarak bir alt koşul sağlanmamış.
- Kaçırılan koşul ve gerçekleşen değer ile eşik arasındaki fark yazılır.

Bu liste otomatik olumlu kabul edilmez, puan almaz ve aday havuzuna dahil değildir. Amacı pilotta yanlış eleme olup olmadığını incelemektir.

### 8.6 Etiketler (teyit düzeyi)

- ÖNCELİKLİ DERİN ANALİZ/TAKİP: Puan tamamlanma durumu TAM (bütün satırlar HESAPLANDI, FCF yöntemi onaylı); bilinen toplam ≥70; A ≥15; B ≥15; operasyonel ve nakit teyidi sağlanmış; 12 aylık likidite incelemesi tamamlanmış; açıklanamayan kritik finansal risk yok.
- DÖNÜŞ TEYİTLİ, TOPLAM PUAN KISMİ: Operasyonel ve nakit teyidi sağlanmış; puan tamamlanma durumu TAM değil (EKSİK, UYGULANAMAZ veya TASLAK FCF). Örneğin yeterli emsali olmadığı için D1'i uygulanamaz olan şirket dönüş teyidini kaybetmez. Uygulanamaz kaleme puan verilmez, toplam 100'e ölçeklenmez. Tam öncelik etiketinin olmaması dönüşün teyit edilmediği anlamına gelmez.
- İZLEME: Bilinen toplam 55–<70 ve en az sayısal erken sinyal.
- DÜŞÜK PUANLI ERKEN SİNYAL: Erken sinyal var, puan daha düşük. Kayıtta kalır.
- Bilinen toplamı ≥70 olup teyit koşulları eksik olan şirket teyitli listeye geçirilmez; mevcut dönüş durumunda eksik gerekçesiyle tutulur.

### 8.7 Yüksek risk işaretleri

Belgeli temerrüt veya ödeme aksaması; giderilememiş faaliyet sürekliliği finansman açığı; borç sözleşmesi ihlali; maddi denetim sorunu; ciddi varlık/tahsilat kalitesi belirsizliği. Her şartlı görüş aynı ağırlıkta değildir; bulgunun niteliği değerlendirilir. Kritik risk çözülmedikçe yüksek puan öncelik etiketi sağlamaz; riskli dönüşler ayrı listede görünür kalır, dönüş bulgusu silinmez.

## 9. Belge incelemesi (adaylar için GEM bağlantısı)

Evo üzerinden doküman haritası: finansal rapor/dipnot, faaliyet raporu, yatırımcı sunumu/bülten, analist toplantısı notu, ilgili araştırma yazısı, son 12 ayın KAP bildirimleri. Kodla sonuç çıkmazsa tam şirket adı ve konuyla aranır; yalnızca sembol eşleşmesine güvenilmez. "Bulunamadı" ile "okunmadı" ayrılır.

Zorunlu incelemeler:
- Hacim, fiyatlama, ürün karması, kapasite kullanımı, yatırım takvimi, segmentler.
- Karşılık hareketleri, stok değer düşüklüğü, diğer faaliyet gelir/giderleri, finansman ve yatırım gelir/giderleri, ertelenmiş vergi.
- İlişkili taraf isimleri ve işlem büyüklükleri, diğer alacaklar, yönetim menfaatleri.
- Kira yükümlülükleri/ödemeleri, faiz sınıflandırması, borç vadeleri, taahhütlü finansman, kur riski.
- Hedge sonrası döviz pozisyonu ve kur hassasiyeti. Kâr küçük/negatifse "kaç kat kâr" yerine mutlak etki ve özkaynağa oranı da gösterilir.
- Net kâr > temiz EFK ise fark parasal sonuç, finansman, yatırım, iştirak, vergi ve diğer kalemlerle açıklanır. Bu bir araştırma alarmıdır, hüküm değildir. Parasal sonuç ikinci kez eklenmez.
- Nakit üretmeyen muhasebe kârının işletme sermayesi açıklaması araştırılır; otomatik "makyaj" denmez.
- Yönetim hedefleri açıklandığı tarihteki haliyle gerçekleşmeyle karşılaştırılır; revizyonlar gizlenmez.
- Her önemli bulguda alternatif operasyonel açıklama değerlendirilir. Düzeltme yapılırsa raporlanan tutar ve düzeltme köprüsü birlikte saklanır.

Sektör medyanı hem marj seviyesi hem değişimi için gösterilir. Sektörün tamamının toparlanması geçerli bir döngüsel dönüş olabilir; sektör üstü performans zorunlu değildir. Doğrulanmamış genellemeler (örneğin "dezenflasyonda herkesin marjı artar") uygulanmaz.

## 10. Zorunlu çıktı ve takip

Her şirket için en az: kod, sektör, son mali dönem, rapor yayımlanma tarihi, çekim zamanı/run_id; ham çeyrek sayısı (n); değerlendirilen dip tarihleri ve her biri için referans yolu (R-TTM / R-ÇEYREK), referans dönemleri, gözlem sayısı ve ZAYIF REFERANS etiketi; seçilen dip tarihi ve kanıtları; erken sinyal yolu; son iki çeyreğin YoY marj değişimleri; TTM FAVÖK/temiz EFK/İFNA marjları; FCF_STD, fcf_yontem, fcf_yontem_surumu ve TASLAK/ONAYLI durumu; varsa faiz sonrası FCF; nakit kaynağı; net borç; cari ve asit-test; faiz ve vade analizi; ön puan (alt–üst); nihai puan alt kırılımı ve her satırın durumu (HESAPLANDI/EKSİK/UYGULANAMAZ); kuyruk numarası veya liste adı (aday havuzu / kısa geçmişli aday / dip doğrulanamadı / sınırdaki); puan tamamlanma durumu; üç sonuç ekseni; sınırdaki aday ise kaçırılan koşul; kaynak belgeler; değerleme tarihi/varsayımları; sonraki bilanço kontrol listesi.

Sonraki bilanço kontrol listesi şirkete özel sayısal beklentiler içerir (marjın korunması, İFNA'nın tedarikçi borcuna bağımlılığının azalması, yatırımın devreye alınması, yaklaşan borç ödemesinin finansmanı vb.); genel kopya metinle doldurulmaz.

Takip: Bilançolar geldikçe ilgili şirket serisi bir arada güncellenir. Son tarihler KAP'ın şirket bazlı takviminden alınır; sabit 40/70 gün kuralı kodlanmaz. Dönem sonunda kapsam, açıklamayanlar, eksik veriler, ertelenmiş incelemeler ve revizyonlar topluca kontrol edilir. Yeni rapor gelmediği için şirket listeden sessizce silinmez.

## 11. Uygulama sırası ve kabul kontrolleri

1. Repodaki teknik tarama scriptleri bu çalışmadan bağımsızdır, değiştirilmez. Bu çalışma ayrı klasörde yürür.
2. Kural dosyası ve parametre kaydı: sabit veri protokolü PİLOT eşiklerden ayrı; FCF yöntemi sürüm numarasıyla kaydedilir.
3. Evo şemasından gerçek alan eşlemesi çıkarılır; alanlar bulunmadan SQL üretilmez. Şunların varlığı ve KAPSAMI ayrıca raporlanır: nakden ödenen faiz ve sınıfı; kira anapara ödemeleri; borç vade dağılımı; taahhütlü kullanılmamış kredi limitleri.
4. Puanlama ayrı fonksiyonlar ve açıklama kodlarıyla uygulanır. [BELGE] satırları inceleme olmadan EKSİK kalır. Ön puan sabit 65 kapsamla, alt–üst olarak hesaplanır.
5. Pilot: önce küçük, farklı durumları kapsayan bir örnekle veri/işaret/dönem eşlemeleri doğrulanır; sonra tanımlı evrene uygulanır. Pilot şirketler sonuçları güzelleştirmek için seçilmez. Pilot raporu aday havuzunu, sınırdaki adayları ve DİP DOĞRULANAMADI / toparlanma izlemesi listesini birlikte kapsar.
6. Kabul senaryoları:
   - Hiç negatif İFNA yaşamadan toparlanan şirket
   - Mevsimsel sahte dönüş
   - Negatif FAVÖK
   - Negatif FCF ve negatif net kâr
   - Kiranın zaten İFNA'da olduğu durum
   - Eksik CAPEX
   - Net nakit
   - Sermaye artırımıyla borç düşüşü
   - Geçici tedarikçi nakdi
   - Yeni halka arz ama yeterli eski finansal veri
   - Son dönem dibi (dip devam ediyor)
   - Kapsam değişikliği
   - Aynı seride veri revizyonu
   - İki yıl yavaş marj erimesi + ikinci bozulma kanıtı + sonrasında iyileşme: dip tespit edilmeli ve aday havuzuna girmeli. Aynı erime sürüp iyileşme yoksa: dip olabilir ama dönüş adayı OLMAMALI.
   - Negatif ama iyileşen FCF: B4 NULL, alt 0, üst 2,5; Kuyruk 2'ye düşebilmeli.
   - Beş uygun emsali olmayan şirket: D1 UYGULANAMAZ; dönüş teyitliyse "dönüş teyitli, toplam puan kısmi" etiketi alabilmeli.
   - Dip kanıtında tek kanıtı olan şirket: sınırdaki adaylar listesinde görünmeli, aday havuzunda görünmemeli.
   - 8 çeyrek geçmişli şirket: R-ÇEYREK ile dip aranabilmeli; dip ve sinyal varsa KISA GEÇMİŞLİ ADAY olmalı, otomatik elenmemeli.
   - 5 çeyrek geçmişli ve güncel toparlanma sinyali olan şirket: DİP DOĞRULANAMADI listesinde görünmeli; "dip yok" yazılmamalı.
   - Yalnızca UYGULANAMAZ kalemi olan şirket: Kuyruk 2'ye girmemeli; UYGULANAMAZ_KAPASITE ayrı görünmeli.
   - Pozitif FCF (taslak yöntem): "Taslak yönteme göre B4 = 5" ifadesi kullanılmalı; "kesin puan" denmemeli.
   - Aynı veri uzunluğundaki iki şirkete aynı referans yolu uygulanmalı; yol sonuca göre değişmemeli.
7. Tutarlılık: Puan toplamı 100, alt aralıklar çakışmasız. Ön puan kapsamı her şirkette 65. Bilinmeyen puan kesin sıfır yazılmaz. Üst sınıra yalnızca EKSİK satırların kalan puanı eklenir; UYGULANAMAZ satır üst sınırı artırmaz. Eksik veride yeniden ölçekleme yok. Negatif paydada "ucuz/geçer" sonucu yok. Çifte kira düşümü ve ikinci enflasyon düzeltmesi yok. TASLAK ve ONAYLI FCF sonuçları aynı sıralamada karışmaz.
8. Geçmiş test: Her tarihte o gün kamuya açık veri ve o tarihteki evren kullanılır. Bugün yeniden bazlanmış/revize edilmiş Evo verisi o tarihte biliniyormuş gibi sunulamaz. Arşiv yoksa "bugünkü veriyle retrospektif inceleme" etiketi konur.
9. Başarı yalnızca fiyatla ölçülmez: sonraki 2–4 çeyrekte faaliyet/nakit iyileşmesinin sürmesi, risklerin gerçekleşmesi, toplam getiri ve XU100'e göre performans ayrı ölçülür. Temettü, sermaye hareketleri, işlem maliyeti ve rapor sonrası erişilebilir fiyat dikkate alınır.
10. Pilot raporu şu soruları cevaplar: Gerçek toparlanmaları yakalıyor muyuz? Hangilerini hangi koşul nedeniyle kaçırıyoruz? Mevsimsellik veya geçici etkiler hangi sahte sinyalleri üretiyor? Veri eksikliği yanlışlıkla olumsuz sonuç gibi işleniyor mu? Kaçırılan gerçek dönüşler ve sahte sinyaller gerekçeleriyle yazılır. Eşik değişikliği önerisi varsa yeni sürüm olarak, sonuçlardan bağımsız gerekçeyle sunulur; pilot sonucuna uygulanmaz.

## 12. v2.0 → v3.0 değişiklikleri (özet)

| v2.0 | v3.0 |
|---|---|
| Katmanlar 105, puan tablosu 100, değerleme puana girmiyor | Tek tablo: 30+25+20+15+10 = 100 |
| Negatif İFNA zorunlu | Operasyonel bozulma kanıtı yeterli |
| Dip yaşamak 20 puan | Dip puansız giriş koşulu |
| 8 çeyreğin minimumu = dip | Referansa göre en az iki bozulma kanıtı |
| 2 ardışık çeyrek marj artışı = yapısal | YoY çeyreklik kontrol + TTM dipten iyileşme + belge |
| Sadece TTM ile arama | Çeyreklik erken sinyal yolu da var |
| Cari oran < 1 otomatik eleme | Vade, faiz, nakit ve varlık kalitesi birlikte |
| FCF/Net Kâr ≥ 1 şartı | Yardımcı oran; payda kontrolü |
| TTM'e geçmek TMS 29'u çözer | Evo yeniden bazlama + aynı çekim + try_ttm + ek düzeltme yok |
| Kiralar her durumda düşülür | Sadece henüz düşülmemiş nakit ödeme |
| Guidance şartı / geri alım otomatik olumlu | Ölçülebilir katalizör ve gerçekleşme |
| Fiyat dibe yakınsa fırsat | Normalleşmiş değer ile fiyat ayrı |
| 65+/70+ kesin aday | Puan + teyit + risk + ayrı değerleme ekseni |
| Eksik veri 0 veya 100'e ölçekleme | NULL + olası puan aralığı |
| İlk 10–15 aday | Tüm adaylar kayıtta |
| v4 ve v5 birlikte | Bu tarama için tek sürüm |

## 13. v3.0 → v3.1 değişiklikleri (özet)

- Dip referans penceresi d−4…d−1'den d−8…d−5'e taşındı.
- FCF_STD v1 taslağı tanımlandı.
- Sayısal ön puan (azami 65) ve inceleme sırası tanımlandı.
- C2/C3 için veri erişim kontrolü eklendi.

## 14. Dayanak ve sınırlar

Evo'nun yeniden bazlama ve try_ttm kararı, kullanıcının 19 Ekim 2026'da aktardığı önceki doğrulamaya dayanır; bu belge hazırlanırken Evo'ya yeniden sorgu atılmamıştır.

Kaynaklar:
- IAS 29: https://www.ifrs.org/issued-standards/list-of-standards/ias-29-financial-reporting-in-hyperinflationary-economies/
- IFRS 16 nakit sınıflandırması: https://www.ifrs.org/content/dam/ifrs/project/pir-ifrs-16/rfi-iasb-2025-1-pir-ifrs-16.pdf
- ACCA, cari oran ve işletme sermayesi: https://www.accaglobal.com/gb/en/student/exam-support-resources/fundamentals-exams-study-resources/f9/technical-articles/wcm.html
- SEC, FCF tanımı ve sınırları: https://www.sec.gov/rules-regulations/staff-guidance/corporation-finance-interpretations/non-gaap-financial-measures
- KAP 2026 finansal rapor takvimi: https://kap.org.tr/tr/api/about/content-file/8a019492945fbe080194acf109622904

Bu kaynaklar muhasebe ilkelerini destekler. PİLOT puan ağırlıklarını, bps eşiklerini, %25 değerleme eşiğini, 55/70 puan sınırlarını, 35/65 ön puan eşiğini veya referans yollarını (R-TTM: d−7…d−4, R-ÇEYREK: d−4) doğrulamazlar; bunlar sınanacak model tasarımı tercihleridir.

## 15. v3.1 → v3.2 değişiklikleri

| v3.1 | v3.2 | Gerekçe |
|---|---|---|
| Amaç bölümü yoktu | 0. bölüm eklendi; diğer hükümlere üstün | Filtre erken yakalama içindir; teyit giriş şartı değildir |
| C2/C3 hesaplanabiliyorsa ön puana eklenir | Ön puan kapsamı her şirkette sabit 65; C2/C3 ayrı sütun, nihai puana | Farklı paydalar sıralamayı bozuyordu |
| B4 negatif FCF'de "geçici 0" | B4 NULL, alt 0, üst 2,5; ön puan alt–üst olarak gösterilir; Kuyruk 2 eklendi | Bilinmeyen puan kesin sıfır sayılmamalı |
| Dip penceresi gerekçesi: "3 çeyrek ortak" | Ortaklık 0/1/2/3; bedel (≈19 çeyrek geçmiş) ve referans gözlem sayısı kaydı eklendi | Gerekçe abartılıydı; şeffaflık |
| Yavaş erime testi koşulsuz | İkinci kanıt + sonrasında iyileşme şartıyla | Sadece düşmeye devam eden şirket aday olmamalı |
| "Repoda motor yok" | "Repoda kod yok; kullanıcı standardı var, henüz paylaşılmadı"; TASLAK puan etiketi; yöntem değişince toplu yeniden hesap | Kod yokluğu ≠ standart yokluğu |
| C2/C3: "alan varsa OTO" | Bütün girdiler ve kapsamları doğrulanmışsa OTO; aksi halde BELGE/NULL | Toplam limit ≠ taahhütlü kullanılmamış limit; finansman gideri ≠ nakit faiz |
| Öncelik için "bütün satırlar tamamlanmış" | EKSİK ile UYGULANAMAZ ayrıldı; "dönüş teyitli, toplam puan kısmi" etiketi | Emsali olmayan şirkette kilitlenme |
| Sınırdaki adaylar yoktu | 8.5: tek koşulu kaçıranlar ayrı listede, puansız | Pilotta yanlış elemeyi görmek için |

## 16. v3.2 → v3.3 değişiklikleri

| v3.2 | v3.3 | Gerekçe |
|---|---|---|
| Tam dip penceresi için yaklaşık 19 çeyrek | Ana tarama son 8 çeyrek; daha uzun geçmiş yalnızca yardımcı | Kısa geçmişli şirketler otomatik elenmesin |
| Referans d−8…d−5, en az 3 gözlem zorunlu | R-TTM (d−7…d−4, mevcut gözlemlerin hepsi, tek gözlem ZAYIF) → yoksa R-ÇEYREK (d çeyreği vs d−4) | Ortak çeyrek yok; kısa geçmişte de çalışır; yol yalnızca veri varlığına göre önceden belli |
| Kısa geçmiş için sınıf yoktu | KISA GEÇMİŞLİ ADAY ve DİP DOĞRULANAMADI — TOPARLANMA İZLEMESİ listesi | Görünür kalsınlar; sınırlı veriden olumsuz sonuç çıkmasın |
| Üst sınıra "NULL satırların azamisi" ekleniyordu | Yalnızca EKSİK satırların kalan puanı; UYGULANAMAZ hariç | Kuyruk 2 şişmesin, çift sayım olmasın |
| B4 için "kesin" ifadesi | Taslak yöntemde "dal kapandı, yöntem onayı bekleniyor"; erişilemeyen belge EKSİK | Hesap kesinliği ≠ yöntem onayı |
| ÖNCELİKLİ UYGULANAMAZ'a izin veriyor, "kısmi" etiketi UYGULANAMAZ'ı kapsamıyordu | Tamamlanma durumu ayrı alan; ÖNCELİKLİ = TAM; "dönüş teyitli, puan kısmi" UYGULANAMAZ'ı da kapsar | Çelişki giderildi |
| Pilot soruları dolaylı | Dört pilot sorusu açıkça yazıldı | Pilotun neyi ölçtüğü net olsun |
