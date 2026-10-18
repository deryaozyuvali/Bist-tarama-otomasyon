# Hendek Filtresi

Kaynak: Serkan Ünal, *Borsa İstanbul İçin Hisse Seçim Rehberi*, s. 92–159

Tarama iki aşamalı çalışır:

1. **Rakamsal tarama** (`hendek_tarama.py`): Bilanço, gelir tablosu ve nakit akışıyla tüm şirketleri tarar ve beş gruba ayırır.
2. **Nitel kontrol** (aşağıdaki kontrol listesi): Faaliyet raporu, dipnotlar, kurumsal bilgi kartı ve KAP haberleriyle yapılır. Yalnızca 1. aşamada kısa listeye kalanlara uygulanır.

Kitabın uyarısı geçerli: Testin amacı mükemmel şirketi bulmak değil, *ne tür bir şirketle karşı karşıya olduğumuzu bilmek*. Fiyatın ne olması gerektiğini söylemez.

---

## Aşama 1 — Rakamsal tarama

**Dönem: yalnızca enflasyon muhasebeli (TMS 29) yıllar, 2022–2025.**
- TMS 29, 31.12.2023 yıl sonu tablolarından itibaren zorunlu oldu; 2022 rakamları karşılaştırma için geriye dönük düzeltildi.
- Kitabın "5–10 yıl" önerisi **bilerek uygulanmıyor**. Amaç, bütün yılların aynı muhasebe yöntemiyle hazırlanmış olması. Bu yüzden 2021 ve öncesi kullanılmıyor ve TÜFE ile ek bir düzeltme yapılmıyor.
- 2022'de parasal pozisyon kalemi olmayıp sonraki yıllarda olan 14 şirketin 2022 yılı düzeltilmemiş sayılıyor ve atılıyor.
- Hiç parasal kalemi olmayan 37 şirket uyarıyla birlikte tutuluyor. Bunlar büyük ihtimalle fonksiyonel para birimi döviz olan şirketler.

**Tutarlılık kuralı:**
- Her yılın rakamı farklı bir tarihin satın alma gücüyle ifade edilmiş olabilir. Bu yüzden **yıllar arasında TL tutar karşılaştırılmıyor**; yalnızca aynı yılın rakamlarından hesaplanan oranlar kullanılıyor: getiri, marj, borçluluk, devir hızı, sektör içi pazar payı.
- Fintables'ın bu dönemdeki USD tutarları gerçek kurlarla uyuşmuyor (2022 için ima edilen kur 68 TL). Bu yüzden dolar bazlı hiçbir hesap yapılmıyor.

**Kapsam:**
- Standart şablonlu şirketler; TMS 29 döneminde en az 3 yıl verisi olan ve 2025 yıl sonunu açıklamış olanlar.
- Hariç tutulanlar: bankalar, sigorta, holding, GYO, MKYO/GSYO, aracı kurum, faktoring, leasing, varlık yönetimi.

### Sermaye getirisi (s. 98–106)
`ROIC = Faaliyet kârı × (1 − %25 vergi) / (Ana ortaklık özkaynağı + Finansal borçlar)`

TMS 29'lu rakamlar zaten reel olduğu için bu oran doğrudan reel getiridir. Eşik reel **%5**'tir (`REEL_ESIK`).

### Gösterge 1 — Pazar payı istikrarı (s. 131–136), 3 puan
Pazar payı, şirketin satışının aynı yıl sektördeki halka açık şirketlerin toplam satışına oranıdır. Sepet, 2022–2025'in her yılında verisi olan şirketlerden oluşur.

| Kontrol | Kural |
|---|---|
| İstikrar (Greenwald–Kahn) | Yıllık mutlak pay değişimi ortalaması ≤ sektör ortalaması, **ya da** dönemin 4 yılının tamamında sektör lideri |
| En az sektör kadar hızlı büyüme | Pazar payı 2025'te 2022'deki seviyesinde veya üstünde |
| Giriş engeli | 2023 ve sonrasında borsaya gelen hiçbir şirket 2025'te sektörde ilk 3'e girememiş |

Sektörde 3'ten az oyuncu varsa bu gösterge değerlendirilmez.

### Gösterge 2 — Reel kârlılığın sürekliliği (s. 137–146), 3 puan
| Kontrol | Kural |
|---|---|
| Süreklilik | Dönemin her yılında faaliyet kârı pozitif |
| Reel | Yılların en az %70'inde ROIC > %5 (4 yılda en az 3) |
| Faaliyet kaynaklı | Dönem toplamında faaliyet kârı ≤ 1,1 × FAVÖK (kâr kur farkı vb. diğer gelirlerle şişmemiş) **ve** işletme nakit akışı / net kâr ≥ 0,7 |

Kitabın kriz yılı sorusu bu dönemde uygulanamıyor (2018 kur krizi ya da 2020 pandemisi gibi bir yıl yok), bu yüzden puanlamaya girmiyor.

### Gösterge 3 — Hendeğin gücü ve ömrü (s. 146–153)
Kitapta bu gösterge niteldir ve Aşama 2'de kontrol edilir. Tabloda gösterilen "fiyat primi" (brüt marj sektörün üstünde mi) ve "marj istikrarı" yalnızca **yardımcı bilgidir; gruplamaya etkisi yoktur**.

### Finansal güç (s. 155–157)
Piotroski F-skoru, 2025 oranlarının 2024 oranlarıyla karşılaştırılmasıyla hesaplanır.

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
| **A** | Hendek VAR + finansal güç | Portföy çekirdeği adayı; Aşama 2'den geçmeli |
| **B** | Hendek KIRILGAN + finansal güç | Daha yüksek güvenlik marjı, sınırlı pozisyon, testi düzenli tekrarla |
| **C** | Hendek YOK + finansal güç | Yalnızca ucuzsa; ortalamaya dönüş yatırımı, çıkış koşulu baştan belli |
| **D** | Hendek var/kırılgan + finansal güç YOK | En tehlikeli durum; izlenir |
| **E** | İkisi de yok | İşimiz yok |

- **Hendek VAR:** Gösterge 2'den 3/3 **ve** Gösterge 1'den ≥ 2/3 (ya da Gösterge 1 değerlendirilemiyor).
- **KIRILGAN:** Gösterge 2'den 2/3.

### Otomatik uyarılar
- Halka açıklık > %70.
- Dönemde 2 veya daha fazla yıl bedelli sermaye artırımı.
- Net kârın yarısından fazlası parasal kazanç.
- Yüksek döviz açığı (hedge dahil net YP pozisyonu < −%30 özkaynak).
- Faaliyet kârını diğer gelirler şişiriyor.
- Ortalama serbest nakit marjı negatif: büyüme dış kaynakla finanse ediliyor.
- Sektöre yeni girenler ilk 3'e yerleşebiliyor.
- Hiç parasal kalem yok: TMS 29 uygulanmamış olabilir.

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
2. `SON_YIL` ayarı güncellenir.
3. `python temel_tarama/hendek_tarama.py` çalıştırılır.

## Bilinen sınırlar
- **Dönem kısa (en fazla 4 yıl).** Kitabın "uzun süreli kârlılık" ve "lider 5–10 yıldır aynı mı" soruları tam karşılanamıyor ve kriz yılı testi yapılamıyor. Bu yüzden dönem uzun olan eski sürüme göre A grubu daha kalabalık. Kısa dönemde iyi bir konjonktür hendek gibi görünebilir; Aşama 2 bu yüzden önemli.
- Pazar payı yalnızca **halka açık rakiplere** göre ölçülüyor. Halka açık olmayan rakipler ve ithalat görünmüyor.
- Yıllar arasında TL bazında büyüme (reel ciro artışı) hesaplanmıyor; büyüme yalnızca pazar payı değişimiyle ölçülüyor.
- Gösterge 2'deki dönem toplamları (nakit/kâr, faaliyet kârı/FAVÖK) farklı yılların TL'lerini topluyor. Pay ve payda aynı yıllardan geldiği için oran kabaca tutarlı ama kesin değil.
- Faaliyet kârı, şirketin sunduğu esas faaliyet kârıdır. Diğer faaliyet gelir ve giderleri net olarak ayrıştırılamadığı için FAVÖK ile karşılaştırılarak kontrol ediliyor.
