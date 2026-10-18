# Hendek Filtresi

Kaynak: Serkan Ünal, *Borsa İstanbul İçin Hisse Seçim Rehberi*, s. 92–159

Tarama iki aşamalı çalışır:

1. **Rakamsal tarama** (`hendek_tarama.py`): Bilanço, gelir tablosu ve nakit akışıyla tüm şirketleri tarar ve beş gruba ayırır.
2. **Nitel kontrol** (aşağıdaki kontrol listesi): Faaliyet raporu, dipnotlar, kurumsal bilgi kartı ve KAP haberleriyle yapılır. Yalnızca 1. aşamada kısa listeye kalanlara uygulanır.

Kitabın uyarısı geçerli: Testin amacı mükemmel şirketi bulmak değil, *ne tür bir şirketle karşı karşıya olduğumuzu bilmek*. Fiyatın ne olması gerektiğini söylemez.

---

## Aşama 1 — Rakamsal tarama

**Kapsam:**
- Standart şablonlu şirketler; 2016–2025 yıl sonu konsolide tablolar.
- En az 7 yıl verisi olan ve 2025 yıl sonunu açıklamış şirketler.
- Hariç tutulanlar: bankalar, sigorta, holding, GYO, MKYO/GSYO, aracı kurum, faktoring, leasing, varlık yönetimi.

### Enflasyon kuralı (s. 138–144)
- **2022 ve sonrası** TMS 29 ile düzeltilmiş rakamlardır. Bunlar zaten reeldir; üstüne enflasyon düşülmez.
- **2021 ve öncesi** nominaldir. Getiri şöyle reelleştirilir: `(1 + nominal) / (1 + TÜFE) − 1`
- Büyüme USD satışlarla ölçülür, çünkü kitap TL'nin yanında döviz bazında da bakmayı önerir.
- Ana ölçüt net kâr değil; **faaliyet kârı** ve **işletme nakit akışı**dır. Parasal pozisyon kazancı faaliyet kârından ayrı tutulur.

### Sermaye getirisi (s. 98–106)
`Reel ROIC = Faaliyet kârı × (1 − %25 vergi) / (Ana ortaklık özkaynağı + Finansal borçlar)`

Eşik reel **%5**'tir ve sermaye maliyeti yerine kullanılır. Değiştirmek için `REEL_ESIK` ayarı kullanılır.

### Gösterge 1 — Pazar payı istikrarı (s. 131–136), 3 puan
Pazar payı, şirketin USD satışının sektördeki halka açık şirketlerin toplam satışına oranıdır. Sepet, 2018'den beri verisi olan şirketlerden oluşur.

| Kontrol | Kural |
|---|---|
| İstikrar (Greenwald–Kahn) | Yıllık mutlak pay değişimi ortalaması ≤ sektör ortalaması, **ya da** son 8 yılın en az 5'inde sektör lideri |
| Sektörden hızlı büyüme | USD satış bileşik büyümesi ≥ sektör medyanı |
| Giriş engeli | 2018 sonrası borsaya gelen hiçbir şirket sektörde ilk 3'e girememiş |

Sektörde 3'ten az halka açık oyuncu varsa bu gösterge değerlendirilmez. Sonuç tablosunda boş görünür.

### Gösterge 2 — Reel kârlılığın sürekliliği (s. 137–146), 4 puan
| Kontrol | Kural |
|---|---|
| Uzun süreli | Verisi olan her yıl faaliyet kârı pozitif |
| Reel | Yılların en az %70'inde reel ROIC > %5 |
| Faaliyet kaynaklı | Son 3 yılda faaliyet kârı ≤ 1,1 × FAVÖK (kâr kur farkı vb. diğer gelirlerle şişmemiş) **ve** son 5 yılda işletme nakit akışı / net kâr ≥ 0,7 |
| Kriz yılları | 2018 ve 2020'de faaliyet kârı pozitif |

### Gösterge 3 — Hendeğin gücü, sayısal iz (s. 146–153), 2 puan
| Kontrol | Kural |
|---|---|
| Fiyat primi (marka ölçütü tanınırlık değil, primdir) | Brüt marj medyanı > sektör medyanı |
| Marj istikrarı | Brüt marj oynaklığı ≤ sektör medyanı |

Avantajın kaynağı, teknoloji riski, düzenleme bağımlılığı ve nesil geçişi niteldir; bunlar Aşama 2'de kontrol edilir.

### Finansal güç (s. 155–157)
Piotroski F-skoru, 2025'in 2024 ile karşılaştırılmasıyla hesaplanır. İki yıl da TMS 29'lu olduğu için aynı ölçü birimindedir.

| Başlık | Sinyaller |
|---|---|
| Kârlılık | net kâr > 0 · işletme nakit akışı > 0 · aktif kârlılığı arttı · nakit akışı > net kâr |
| Borç ve likidite | uzun vadeli borç / varlık azaldı · cari oran arttı · hisse ihracı yok |
| Verimlilik | brüt marj arttı · aktif devir hızı arttı |

**Finansal güç VAR** sayılması için iki koşul gerekir:
- F-skoru ≥ 6
- Net nakit **ya da** net borç/FAVÖK ≤ 2,5

### Gruplar (kitaptaki dört olasılık, s. 157–159)
| Grup | Tanım | Ne yapılır |
|---|---|---|
| **A** | Hendek VAR + finansal güç | Portföy çekirdeği; uzun süre tutulur |
| **B** | Hendek KIRILGAN + finansal güç | Daha yüksek güvenlik marjı istenir, pozisyon sınırlı tutulur, test düzenli tekrarlanır |
| **C** | Hendek YOK + finansal güç | Yalnızca ucuzsa alınır. Bu bir ortalamaya dönüş yatırımıdır: büyümeye prim ödenmez, çıkış koşulu baştan belirlenir |
| **D** | Hendek var/kırılgan + finansal güç YOK | En tehlikeli durum. Hendek içeriden çöküyor olabilir; izlenir |
| **E** | İkisi de yok | İşimiz yok. Ucuzluk tek başına gerekçe değildir |

- **Hendek VAR:** Gösterge 2'den 4/4 **ve** Gösterge 1'den ≥ 2/3 (ya da Gösterge 1 değerlendirilemiyor).
- **KIRILGAN:** Gösterge 2'den 3/4.

### Otomatik uyarılar (bölüm 2 ve 4'ten)
- Halka açıklık > %70: hâkim ortak zayıf.
- 10 yılda 2 veya daha fazla yıl bedelli sermaye artırımı.
- Net kârın yarısından fazlası parasal kazanç: kâr kalitesine bakılmalı.
- Yüksek döviz açığı (hedge dahil net YP pozisyonu < −%30 özkaynak). Gelir de dövizse sorun değildir.
- Birikimli işletme nakit akışı yatırım harcamasını karşılamıyor: büyüme dış kaynakla finanse ediliyor.
- Faaliyet kârını diğer gelirler şişiriyor.
- Sektöre yeni girenler ilk 3'e yerleşebiliyor: giriş engeli zayıf.

### Çıktılar
- `results/temel/hendek_tarama.csv`: Tüm şirketler, tüm kolonlar.
- `results/temel/hendek_kisa_liste.csv`: A, B ve D grupları; özet kolonlar ve değerleme (PD/DD, F/K, FD/FAVÖK).

---

## Aşama 2 — Nitel kontrol listesi

Kısa listedeki her şirket için. Kaynaklar Fintables doküman havuzundadır (`dokumanlarda_ara` → `dokuman_chunk_yukle`). Tek bir net **olumsuz** cevap şirketi eler (s. 95).

### 2.1 Hâkim ortak (s. 92–95)
| Soru | Nereye bakılır | Arama |
|---|---|---|
| Hâkim ortağın payı yeterli mi? (%30 altı halka açıklık olumlu) | Kurumsal bilgi kartı → Ortaklık yapısı | `dokuman_tipi="kurumsal_bilgi_karti"` |
| Kâr payında bizi zarara uğratan imtiyaz var mı? | Pay grupları (A/B/C) + KAP esas sözleşme | KAP: `"imtiyaz" "esas sözleşme"` |
| Şirketten ilişkili taraflara düzenli kaynak akıyor mu? (yön ve büyüklük) | Dipnot: ilişkili taraflardan alacaklar, ilişkili taraflara borçlar, peşin ödemeler | `finansal_rapor`: `"ilişkili taraflardan alacaklar"` |
| Hâkim ortağın geçmişi kötü mü? | KAP haberleri, SPK kararları | `kap_haberi`: `"SPK" "idari para cezası"` |

### 2.2 Yönetim ve büyüme kalitesi (s. 98–106)
- Vaat edilen hedefler gerçekleşti mi? Kaynak: Fintables `guidance` becerisi ve eski faaliyet raporları.
- Büyüme fiziki mi?
  - Perakendede mağaza sayısı ve m²
  - Sanayide kapasite ve üretim tonu
  - Telekomda abone sayısı
  - Kaynak: faaliyet raporu.
- Satın almayla gelen pay hendek büyütmez (Arçelik örneği). Pazar payı artışı organik mi, satın almayla mı?

### 2.3 Dış dünya (s. 107–111)
- Gelir ve borç hangi para biriminde? Kaynak: dipnot, kur riski tablosu.
- Satışlar kredi koşullarına mı bağlı?
- Fiyatı kim belirliyor: şirket mi, düzenleyici mi, emtia piyasası mı?
- Kamuya bağımlılık, tarife ve lisans süresi.

### 2.4 Rakipler, tedarikçiler, müşteriler (s. 112–116)
- Pazar parçalı mı, yoğun mu? Rakipler rasyonel mi?
- Pazar payı beyanı: *önce pazarın nasıl tanımlandığına* bak. Çimentoda pazar bölgeseldir.
- Bağımsız veri kaynakları:
  - BDDK, BTK, EPDK
  - ODD (otomotiv)
  - TÜİK; ithalatın yerli üreticilerden pay alıp almadığı da buradan izlenir
- Girdi kaç kaynaktan sağlanıyor?
- Müşteri yoğunlaşması: ilk 1–5 müşterinin payı. Dolaylı işaretler:
  - alacak devir hızı yavaşlıyor
  - alacakların varlıklar içindeki payı artıyor
  - brüt marj oynak
- Lisans veya telif ödemesi var mı? Yabancı ortak yatırım ve ihracat coğrafyasını kısıtlıyor mu (Ford Otosan, Tofaş örneği)?

### 2.5 Hendeğin kaynağı ve ömrü (s. 117–125, 146–153)
- **Kaynak hangisi?**
  - Devlet: lisans, ruhsat
  - Operasyon: maliyet, ölçek, dağıtım ağı
  - Müşteri: geçiş maliyeti, patent, coğrafya, marka
- **Dayanıklılık sırası:** Saf maliyet üstünlüğü en kırılgandır. Ölçek ve dağıtım ağı dayanıklıdır. Müşteriden gelen avantaj en uzun ömürlüdür. Güçlü bilanço tek başına hendek değildir.
- **Taklit edilebilir mi?** Şirketin nasıl başardığını tek cümleyle açıklayabiliyorsak, rakip de açıklayabilir (Southwest ve BİM örnekleri).
- **Teknolojik kırılma:** Sektör dönüşüm eğrisinin neresinde? Düşük penetrasyon, sıranın henüz gelmediği anlamına da gelebilir.
- **Düzenleme:** Avantaj tek bir mevzuata mı bağlı (numara taşıma örneği)?
- **Nesil geçişi:**
  - Şirketi hangi nesil yönetiyor?
  - Kurucuya ne kadar bağımlı?
  - Profesyonel kadro var mı?
  - Aile içi anlaşmazlık var mı?
  - Kaynak: kurumsal bilgi kartı (yönetim kurulu, ilk seçilme tarihleri) ve faaliyet raporu.

### 2.6 Hendeksiz şirket için 4 soru (C grubu, s. 158)
1. Finansal olarak güçlü mü ve bu güç artıyor mu?
2. Yönetim, aynı işi yapan rakiplerinden daha iyi sonuç üretiyor mu?
3. Fiyat hata payına yer bırakacak kadar düşük mü?
4. Hangi koşulda çıkacağımızı biliyor muyuz?

İlk ikisi "hayır" ise fiyat ne kadar düşük olursa olsun uzak durulur.

---

## Verinin güncellenmesi
Fintables verisi yalnızca Claude'un bağlı EVO aracıyla çekilebiliyor; GitHub Actions bu kaynağa erişemiyor. Güncelleme adımları:
1. Yeni yıl sonu tabloları açıklanınca (Mart–Nisan) Claude'dan `sql/finansal_veri.sql` ile veriyi yeniden çekmesi istenir.
2. `SON_YIL` ve `TUFE` ayarları güncellenir.
3. `python temel_tarama/hendek_tarama.py` çalıştırılır.

## Bilinen sınırlar
- Pazar payı yalnızca **halka açık rakiplere** göre ölçülür. Halka açık olmayan büyük rakipler (A101 gibi) ve ithalat görünmez. Bu yüzden Gösterge 1 bir yaklaşıktır ve Aşama 2'de bağımsız veriyle doğrulanmalıdır.
- 2021 öncesi reel ROIC kaba bir düzeltmedir. Kitap da enflasyon düzeltmesinin tam bir çözüm değil, önemli bir iyileştirme olduğunu söylüyor (s. 142).
- Yatırılan sermaye yıl sonu bakiyesidir; ortalama kullanılmaz.
- Faaliyet kârı, şirketin kendi sunduğu "esas faaliyet kârı"dır. Diğer faaliyet gelir ve giderleri net olarak ayrıştırılamadığı için FAVÖK ile karşılaştırılarak kontrol edilir.
