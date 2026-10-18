-- Hendek taraması için yıl sonu finansal veri (Fintables / EVO MCP, veri_sorgula)
-- Sorgu başına 300 satır sınırı var: __O__ yerine 0, 300, 600 ... 4800 yazılarak
-- sayfa sayfa çekilir. OFFSET en fazla 5000 olabildiği için son satırlar
-- ORDER BY 1 DESC,2 DESC LIMIT n ile alınır. Çıktılar veri/finansal_2016_2025.csv'de birleşir.
-- Sektör/halka açıklık: SELECT h.hisse_senedi_kodu kod, h.sektor_id, s.baslik sektor,
--   h.fiili_dolasim_orani, h.piyasa_degeri, h.son_fiyat,
--   CASE WHEN 'XU100' = ANY(h.endeksler) THEN 1 ELSE 0 END xu100
--   FROM hisse_senetleri h LEFT JOIN sektorler s ON s.id=h.sektor_id ORDER BY 1 LIMIT 300 OFFSET __O__
SELECT f.hisse_senedi_kodu kod, f.yil, b.nakit, b.tic_alacak, b.stok, b.donen, b.varlik, b.kv_yuk, b.uv_fborc, b.tic_borc, b.ozk, b.fborc, b.net_borc, b.yp_poz, b.sermaye, g.satis, g.brut, g.faaliyet, g.parasal, g.net, g.favok, g.satis_usd, g.faaliyet_usd, g.dig_fg, n.cfo, n.capex, n.pay_ihrac, n.temettu
FROM hisse_finansal_tablolari f
LEFT JOIN (SELECT hisse_senedi_kodu, yil, 
  SUM(CASE WHEN kalem='Nakit ve Nakit Benzerleri' THEN try_donemsel END) nakit, 
  SUM(CASE WHEN kalem='Ticari Alacaklar' THEN try_donemsel END) tic_alacak, 
  SUM(CASE WHEN kalem='Stoklar' THEN try_donemsel END) stok, 
  SUM(CASE WHEN kalem='Toplam Dönen Varlıklar' THEN try_donemsel END) donen, 
  SUM(CASE WHEN kalem='Toplam Varlıklar' THEN try_donemsel END) varlik, 
  SUM(CASE WHEN kalem='Toplam Kısa Vadeli Yükümlülükler' THEN try_donemsel END) kv_yuk, 
  SUM(CASE WHEN kalem='Toplam Uzun Vadeli Finansal Borçlar' THEN try_donemsel END) uv_fborc, 
  SUM(CASE WHEN kalem='Ticari Borçlar' THEN try_donemsel END) tic_borc, 
  SUM(CASE WHEN kalem='Ana Ortaklığa Ait Özkaynaklar' THEN try_donemsel END) ozk, 
  SUM(CASE WHEN kalem='Toplam Finansal Borçlar' THEN try_donemsel END) fborc, 
  SUM(CASE WHEN kalem='Net Borç' THEN try_donemsel END) net_borc, 
  SUM(CASE WHEN kalem='Hedge Dahil Net Yabancı Para Pozisyonu' THEN try_donemsel END) yp_poz, 
  SUM(CASE WHEN kalem='Ödenmiş Sermaye' THEN try_donemsel END) sermaye
FROM hisse_finansal_tablolari_bilanco_kalemleri WHERE ay=12 AND yil>=2016 GROUP BY hisse_senedi_kodu, yil) b ON b.hisse_senedi_kodu=f.hisse_senedi_kodu AND b.yil=f.yil
LEFT JOIN (SELECT hisse_senedi_kodu, yil, 
  SUM(CASE WHEN kalem IN ('Satış Gelirleri','Toplam Hasılat') THEN try_donemsel END) satis, 
  SUM(CASE WHEN kalem='Brüt Kar (Zarar)' THEN try_donemsel END) brut, 
  SUM(CASE WHEN kalem='Faaliyet Karı (Zararı)' THEN try_donemsel END) faaliyet, 
  SUM(CASE WHEN kalem='Net Parasal Pozisyon Kazançları (Kayıpları)' THEN try_donemsel END) parasal, 
  SUM(CASE WHEN kalem='Ana Ortaklık Payları' THEN try_donemsel END) net, 
  SUM(CASE WHEN kalem='FAVÖK' THEN try_donemsel END) favok, 
  SUM(CASE WHEN kalem IN ('Satış Gelirleri','Toplam Hasılat') THEN usd_donemsel END) satis_usd, 
  SUM(CASE WHEN kalem='Faaliyet Karı (Zararı)' THEN usd_donemsel END) faaliyet_usd, 
  SUM(CASE WHEN kalem='Diğer Faaliyet Gelirleri' THEN try_donemsel END) dig_fg
FROM hisse_finansal_tablolari_gelir_tablosu_kalemleri WHERE ay=12 AND yil>=2016 GROUP BY hisse_senedi_kodu, yil) g ON g.hisse_senedi_kodu=f.hisse_senedi_kodu AND g.yil=f.yil
LEFT JOIN (SELECT hisse_senedi_kodu, yil, 
  SUM(CASE WHEN kalem='İşletme Faaliyetlerinden Nakit Akışları' THEN try_donemsel END) cfo, 
  SUM(CASE WHEN kalem='Maddi ve Maddi Olmayan Duran Varlıkların Alımından Kaynaklanan Nakit Çıkışları' THEN try_donemsel END) capex, 
  SUM(CASE WHEN kalem='Pay ve Diğer Özkaynağa Dayalı Araçların İhracından Kaynaklanan Nakit Girişleri' THEN try_donemsel END) pay_ihrac, 
  SUM(CASE WHEN kalem='Ödenen Temettüler' AND satir_no>35 THEN try_donemsel END) temettu
FROM hisse_finansal_tablolari_nakit_akis_tablosu_kalemleri WHERE ay=12 AND yil>=2016 GROUP BY hisse_senedi_kodu, yil) n ON n.hisse_senedi_kodu=f.hisse_senedi_kodu AND n.yil=f.yil
WHERE f.ay=12 AND f.yil>=2016 AND f.finansal_tablo_sablonu='default' ORDER BY 1,2 LIMIT 300 OFFSET __O__ 
