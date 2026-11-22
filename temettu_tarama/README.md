# FD / Temettü ("kira çarpanı") taraması

Yayıncının yöntemi şu: hisseyi kiralık bir ev gibi düşün. Şirketin borcunu üstlenip kasasındaki
nakdi alarak ödediğin gerçek bedel (düzeltilmiş Firma Değeri), şirketin cebine koyacağı
**temettülerle** kaç yılda geri döner?
Hedef 10 yıl veya altı. 3–5 yıl çok iyi. 15 yıla kadar sadece istisna olarak kabul edilir.

## Çalıştırma
```
python3 fd_temettu_tarama.py evo_ham_<tarih>.csv FCF_MASTER.xlsx FD_Temettu_Tarama_<tarih>.xlsx
```
`evo_ham_*.csv` dosyası EVO (Fintables) SQL çıktısıdır: PD, nakit, finansal borç, kullanım hakkı,
geri alınmış paylar, ana ortaklık net kârı (TTM ve yıllık) ve temettü geçmişi. Sorgu kodun içinde
değil, EVO tarafında çalıştırılıyor. Yöntem ayrıntıları Excel'in `YONTEM` sayfasında.

## Sınıflar
- **A**: 5/5 yıl kâr, 5/5 yıl temettü, holding değil. FD/Temettü hem son 12 ayda hem tahminde 10 veya altı. FCF (GEM v6.2 master) temettünün en az 1 katı.
- **B**: A ile aynı, ancak FCF teyidi zayıf.
- **C**: 10–15 yıl arası, yani istisna bandı.
- **D**: Tahmine göre ucuz, ama geçmişi kesintili, holding ya da veri sorunu var. Elle incelenmeli.
- **E**: 15 yıldan fazla.
