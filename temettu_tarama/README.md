# FD / Temettü ("kira çarpanı") taraması

Yayıncının yöntemi şu: hisseyi kiralık bir ev gibi düşün. Şirketin borcunu üstlenip kasasındaki
nakdi alarak ödediğin gerçek bedel (düzeltilmiş Firma Değeri), şirketin cebine koyacağı
**temettülerle** kaç yılda geri döner?
Hedef 10 yıl veya altı. 3–5 yıl çok iyi. 15 yıla kadar sadece istisna olarak kabul edilir.

## Çalıştırma
```
python3 fd_temettu_tarama.py evo_ham_<tarih>.csv FCF_MASTER.xlsx FD_Temettu_Tarama_<tarih>.xlsx
# Yalnız yayıncının kuralları (FCF master kullanılmaz):
python3 fd_temettu_tarama.py evo_ham_<tarih>.csv - FD_Temettu_Tarama_Yayinci_<tarih>.xlsx
```
`evo_ham_*.csv` dosyası EVO (Fintables) SQL çıktısıdır; sorgu `evo_sorgu.sql` içinde: PD, nakit, finansal borç, kullanım hakkı,
geri alınmış paylar, ana ortaklık net kârı (TTM ve yıllık) ve temettü geçmişi. Sorgu kodun içinde
değil, EVO tarafında çalıştırılıyor. Yöntem ayrıntıları Excel'in `YONTEM` sayfasında.

## Sınıflar
- **A**: 5/5 yıl kâr, 5/5 yıl temettü, holding değil. FD/Temettü hem son 12 ayda hem tahminde 10 veya altı. FCF (GEM v6.2 master) temettünün en az 1 katı.
- **B**: A ile aynı, ancak FCF teyidi zayıf.
- **C**: 10–15 yıl arası, yani istisna bandı.
- **P**: Hiç temettü vermemiş ya da yeni başlamış (son 5 yılın en fazla 2'si). Nakit %10 sayılır, temettü tahmini yapılmaz. Kârın ve FCF'in küçüğü tamamen dağıtılsa FD 10 yılda dönüyorsa, ve 5 yılın en az 4'ünde kâr varsa, bu sınıfa girer. P bir alım listesi değil; dağıtım kanıtı aranacak listedir.
- **D**: Tahmine göre ucuz, ama geçmişi kesintili, holding ya da veri sorunu var. Elle incelenmeli.
- **E**: 15 yıldan fazla.

## Geri alınan paylar (`geri_alim_adet.csv`)
Bu kural video altındaki yorumlarda netleşti ve yayıncı onayladı:
- Geri alınan pay temettü ve oy hakkı almaz, bu yüzden yok sayılır. Piyasa değerinden düşülecek tutar **adet × güncel fiyat** olmalı. Bilançodaki "Geri Alınmış Paylar" tutarı TMS29 ile endekslenmiş maliyet bedelidir, pay adedi değildir.
- Paylar itfa edilip sermayeden düşülmüşse ödenmiş sermaye zaten azalmıştır. Ek düzeltme gerekmez.
- Geri alınan paylar sonradan satılabilir (PCILT 05/2026, GRSEL 07/2025). Adet son KAP bildirimlerinden toplanmalı.
- Adeti dosyada olmayan şirketlerde maliyet bedeli kullanılır ve bayrak düşülür. Önce aday listesindekilerin adedini doldur.
