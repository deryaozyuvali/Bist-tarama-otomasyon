-- Temel ön eleme için EVO (Fintables MCP) `veri_sorgula` sorguları.
-- Her sorgu en fazla 300 satır döndürür: her birini önce "LIMIT 300", sonra
-- "LIMIT 300 OFFSET 300" ile iki sayfa çalıştır, sonuçları birleştirip
-- temel/ham/<dosya>.csv olarak kaydet (temel/evo_to_csv.py).
-- Kapsam: 'default' şablonlu (banka/sigorta/leasing/faktoring hariç), 2026+ dönemi olan şirketler.
-- NOT: Yıl sabitleri (2026, 2022-2025, 2021-11-25) her çeyrekte güncellenmeli.

-- ===================== ham/gelir.csv =====================
WITH son AS (SELECT DISTINCT ON (hisse_senedi_kodu) hisse_senedi_kodu, yil, ay FROM hisse_finansal_tablolari WHERE finansal_tablo_sablonu='default' AND yil>=2026 ORDER BY hisse_senedi_kodu, yil DESC, ay DESC)
SELECT g.hisse_senedi_kodu kod, s.yil, s.ay,
SUM(CASE WHEN g.yil=s.yil AND (g.kalem LIKE 'Satış Gelirleri%' OR g.kalem='Toplam Hasılat') THEN g.try_ttm END) satis,
SUM(CASE WHEN g.yil=s.yil AND g.kalem='Brüt Kar (Zarar)' THEN g.try_ttm END) brut,
SUM(CASE WHEN g.yil=s.yil AND g.kalem IN ('Genel Yönetim Giderleri (-)','Pazarlama, Satış ve Dağıtım Giderleri (-)','Araştırma ve Geliştirme Giderleri (-)') THEN g.try_ttm END) opex,
SUM(CASE WHEN g.yil=s.yil AND g.kalem='Faaliyet Karı (Zararı)' THEN g.try_ttm END) faal_kar,
SUM(CASE WHEN g.yil=s.yil AND g.kalem='FAVÖK' THEN g.try_ttm END) favok,
SUM(CASE WHEN g.yil=s.yil AND g.kalem='Amortisman' THEN g.try_ttm END) amort,
SUM(CASE WHEN g.yil=s.yil AND g.kalem='(Esas Faaliyet Dışı) Finansal Giderler (-)' THEN g.try_ttm END) fin_gider,
SUM(CASE WHEN g.yil=s.yil AND g.kalem='Sürdürülen Faaliyetler Vergi Öncesi Karı (Zararı)' THEN g.try_ttm END) vok,
SUM(CASE WHEN g.yil=s.yil AND g.kalem='Sürdürülen Faaliyetler Vergi Geliri (Gideri)' THEN g.try_ttm END) vergi,
SUM(CASE WHEN g.yil=s.yil AND g.kalem='Dönem Karı (Zararı)' THEN g.try_ttm END) donem_kar,
SUM(CASE WHEN g.yil=s.yil AND g.kalem='Azınlık Payları' THEN g.try_ttm END) azinlik_kar,
SUM(CASE WHEN g.yil=s.yil AND g.kalem='Ana Ortaklık Payları' THEN g.try_ttm END) ana_kar,
SUM(CASE WHEN g.yil=s.yil AND (g.kalem LIKE 'Satış Gelirleri%' OR g.kalem='Toplam Hasılat') THEN g.usd_ttm END) satis_usd0,
SUM(CASE WHEN g.yil=s.yil-1 AND (g.kalem LIKE 'Satış Gelirleri%' OR g.kalem='Toplam Hasılat') THEN g.usd_ttm END) satis_usd1,
SUM(CASE WHEN g.yil=s.yil-1 AND g.kalem='Brüt Kar (Zarar)' THEN g.usd_ttm END) brut_usd1,
SUM(CASE WHEN g.yil=s.yil AND g.kalem='Brüt Kar (Zarar)' THEN g.usd_ttm END) brut_usd0,
SUM(CASE WHEN g.yil=s.yil AND g.kalem='Faaliyet Karı (Zararı)' THEN g.usd_ttm END) faal_usd0,
SUM(CASE WHEN g.yil=s.yil-1 AND g.kalem='Faaliyet Karı (Zararı)' THEN g.usd_ttm END) faal_usd1,
SUM(CASE WHEN g.yil=s.yil AND g.kalem='Ana Ortaklık Payları' THEN g.usd_ttm END) ana_usd0,
SUM(CASE WHEN g.yil=s.yil-1 AND g.kalem='Ana Ortaklık Payları' THEN g.usd_ttm END) ana_usd1,
SUM(CASE WHEN g.yil=s.yil-2 AND g.kalem='Ana Ortaklık Payları' THEN g.usd_ttm END) ana_usd2,
SUM(CASE WHEN g.yil=s.yil-3 AND g.kalem='Ana Ortaklık Payları' THEN g.usd_ttm END) ana_usd3
FROM hisse_finansal_tablolari_gelir_tablosu_kalemleri g JOIN son s ON g.hisse_senedi_kodu=s.hisse_senedi_kodu AND g.ay=s.ay AND g.yil BETWEEN s.yil-3 AND s.yil
GROUP BY 1,2,3 ORDER BY 1 LIMIT 300;

-- ===================== ham/nakit.csv =====================
WITH son AS (SELECT DISTINCT ON (hisse_senedi_kodu) hisse_senedi_kodu, yil, ay FROM hisse_finansal_tablolari WHERE finansal_tablo_sablonu='default' AND yil>=2026 ORDER BY hisse_senedi_kodu, yil DESC, ay DESC)
SELECT n.hisse_senedi_kodu kod,
SUM(CASE WHEN n.yil=s.yil AND n.ay=s.ay AND n.kalem='İşletme Faaliyetlerinden Nakit Akışları' THEN n.try_ttm END) cfo,
SUM(CASE WHEN n.yil=s.yil AND n.ay=s.ay AND n.kalem='Maddi ve Maddi Olmayan Duran Varlıkların Alımından Kaynaklanan Nakit Çıkışları' THEN n.try_ttm END) capex,
SUM(CASE WHEN n.yil=s.yil AND n.ay=s.ay AND n.kalem IN ('Kira Ödemeleri','Kira Sözleşmelerinden Kaynaklanan Borç Ödemelerine İlişkin Nakit Çıkışları') THEN n.try_ttm END) kira,
SUM(CASE WHEN n.yil=s.yil AND n.ay=s.ay AND n.kalem='Ödenen Temettüler' THEN n.try_ttm END) temettu_odenen,
SUM(CASE WHEN n.yil=s.yil AND n.ay=s.ay AND n.kalem='İşletmenin Kendi Paylarını ve Diğer Özkaynağa Dayalı Araçlarını Almasıyla İlgili Nakit Çıkışları' THEN n.try_ttm END) geri_alim,
SUM(CASE WHEN n.yil=s.yil AND n.ay=s.ay AND n.kalem IN ('Bağlı Ortaklıkların Kontrolünün Elde Edilmesine Yönelik Alışlara İlişkin Nakit Çıkışları','Bağlı Ortaklıklarda İlave Pay Alımlarına ilişkin Nakit Çıkışları','İştiraklar ve/veya İş Ortaklıkları Pay Alımı veya Sermaye Artırımı Sebebiyle Oluşan Nakit Çıkışları','Bağlı Ortaklıklardaki Kontrolün Kaybına Yol Açmayan Şekilde Ortaklık Payları Değişmelerinden Kaynaklanan Nakit Çıkışları') THEN n.try_ttm END) edinim,
SUM(CASE WHEN n.yil=s.yil AND n.ay=s.ay AND n.kalem='Ödenen Faiz' THEN n.try_ttm END) odenen_faiz,
SUM(CASE WHEN n.yil=s.yil AND n.ay=s.ay AND n.kalem='Pay ve Diğer Özkaynağa Dayalı Araçların İhracından Kaynaklanan Nakit Girişleri' THEN n.try_ttm END) pay_ihrac,
SUM(CASE WHEN n.ay=12 AND n.yil=2025 AND n.kalem='İşletme Faaliyetlerinden Nakit Akışları' THEN n.try_donemsel END) cfo_2025,
SUM(CASE WHEN n.ay=12 AND n.yil=2024 AND n.kalem='İşletme Faaliyetlerinden Nakit Akışları' THEN n.try_donemsel END) cfo_2024,
SUM(CASE WHEN n.ay=12 AND n.yil=2023 AND n.kalem='İşletme Faaliyetlerinden Nakit Akışları' THEN n.try_donemsel END) cfo_2023,
SUM(CASE WHEN n.ay=12 AND n.yil=2022 AND n.kalem='İşletme Faaliyetlerinden Nakit Akışları' THEN n.try_donemsel END) cfo_2022,
SUM(CASE WHEN n.ay=12 AND n.yil=2025 AND n.kalem='Maddi ve Maddi Olmayan Duran Varlıkların Alımından Kaynaklanan Nakit Çıkışları' THEN n.try_donemsel END) capex_2025,
SUM(CASE WHEN n.ay=12 AND n.yil=2024 AND n.kalem='Maddi ve Maddi Olmayan Duran Varlıkların Alımından Kaynaklanan Nakit Çıkışları' THEN n.try_donemsel END) capex_2024,
SUM(CASE WHEN n.ay=12 AND n.yil=2023 AND n.kalem='Maddi ve Maddi Olmayan Duran Varlıkların Alımından Kaynaklanan Nakit Çıkışları' THEN n.try_donemsel END) capex_2023,
SUM(CASE WHEN n.ay=12 AND n.yil=2022 AND n.kalem='Maddi ve Maddi Olmayan Duran Varlıkların Alımından Kaynaklanan Nakit Çıkışları' THEN n.try_donemsel END) capex_2022,
SUM(CASE WHEN n.ay=12 AND n.yil=2025 AND n.kalem IN ('Kira Ödemeleri','Kira Sözleşmelerinden Kaynaklanan Borç Ödemelerine İlişkin Nakit Çıkışları') THEN n.try_donemsel END) kira_2025,
SUM(CASE WHEN n.ay=12 AND n.yil=2024 AND n.kalem IN ('Kira Ödemeleri','Kira Sözleşmelerinden Kaynaklanan Borç Ödemelerine İlişkin Nakit Çıkışları') THEN n.try_donemsel END) kira_2024,
SUM(CASE WHEN n.ay=12 AND n.yil=2023 AND n.kalem IN ('Kira Ödemeleri','Kira Sözleşmelerinden Kaynaklanan Borç Ödemelerine İlişkin Nakit Çıkışları') THEN n.try_donemsel END) kira_2023,
SUM(CASE WHEN n.ay=12 AND n.yil=2022 AND n.kalem IN ('Kira Ödemeleri','Kira Sözleşmelerinden Kaynaklanan Borç Ödemelerine İlişkin Nakit Çıkışları') THEN n.try_donemsel END) kira_2022
FROM hisse_finansal_tablolari_nakit_akis_tablosu_kalemleri n JOIN son s ON n.hisse_senedi_kodu=s.hisse_senedi_kodu AND ((n.yil=s.yil AND n.ay=s.ay) OR (n.ay=12 AND n.yil BETWEEN 2022 AND 2025))
GROUP BY 1 ORDER BY 1 LIMIT 300;

-- ===================== ham/amortisman.csv =====================
SELECT n.hisse_senedi_kodu kod,
SUM(CASE WHEN n.yil=2025 THEN n.try_donemsel END) amort_2025,
SUM(CASE WHEN n.yil=2024 THEN n.try_donemsel END) amort_2024,
SUM(CASE WHEN n.yil=2023 THEN n.try_donemsel END) amort_2023,
SUM(CASE WHEN n.yil=2022 THEN n.try_donemsel END) amort_2022
FROM hisse_finansal_tablolari_nakit_akis_tablosu_kalemleri n
WHERE n.ay=12 AND n.yil BETWEEN 2022 AND 2025 AND n.kalem='Amortisman ve İtfa Gideri İle İlgili Düzeltmeler'
AND n.hisse_senedi_kodu IN (SELECT hisse_senedi_kodu FROM hisse_finansal_tablolari WHERE finansal_tablo_sablonu='default' AND yil>=2026)
GROUP BY 1 ORDER BY 1 LIMIT 300;

-- ===================== ham/bilanco.csv =====================
WITH son AS (SELECT DISTINCT ON (hisse_senedi_kodu) hisse_senedi_kodu, yil, ay FROM hisse_finansal_tablolari WHERE finansal_tablo_sablonu='default' AND yil>=2026 ORDER BY hisse_senedi_kodu, yil DESC, ay DESC)
SELECT b.hisse_senedi_kodu kod,
SUM(CASE WHEN b.yil=s.yil AND b.kalem='Nakit ve Nakit Benzerleri' THEN b.try_donemsel END) nakit,
SUM(CASE WHEN b.yil=s.yil AND b.kalem='Ticari Alacaklar' THEN b.try_donemsel END) tic_alacak,
SUM(CASE WHEN b.yil=s.yil AND b.kalem='Ticari Borçlar' THEN b.try_donemsel END) tic_borc,
SUM(CASE WHEN b.yil=s.yil AND b.kalem='Stoklar' THEN b.try_donemsel END) stok,
SUM(CASE WHEN b.yil=s.yil AND b.kalem='Toplam Dönen Varlıklar' THEN b.try_donemsel END) donen,
SUM(CASE WHEN b.yil=s.yil AND b.kalem='Toplam Kısa Vadeli Yükümlülükler' THEN b.try_donemsel END) kvy,
SUM(CASE WHEN b.yil=s.yil AND b.kalem='Toplam Varlıklar' THEN b.try_donemsel END) aktif,
SUM(CASE WHEN b.yil=s.yil AND b.kalem='Net Borç' THEN b.try_donemsel END) net_borc,
SUM(CASE WHEN b.yil=s.yil AND b.kalem='Toplam Finansal Borçlar' THEN b.try_donemsel END) fin_borc,
SUM(CASE WHEN b.yil=s.yil AND b.kalem='Toplam Kısa Vadeli Finansal Borçlar' THEN b.try_donemsel END) kv_fin_borc,
SUM(CASE WHEN b.yil=s.yil AND b.kalem='Ana Ortaklığa Ait Özkaynaklar' THEN b.try_donemsel END) ana_ozk,
SUM(CASE WHEN b.yil=s.yil AND b.kalem='Azınlık Payları' THEN b.try_donemsel END) azinlik_ozk,
SUM(CASE WHEN b.yil=s.yil AND b.kalem='Toplam Özkaynaklar' THEN b.try_donemsel END) ozk,
SUM(CASE WHEN b.yil=s.yil AND b.kalem='Maddi Olmayan Duran Varlıklar' THEN b.try_donemsel END) modv,
SUM(CASE WHEN b.yil=s.yil AND b.kalem='Kullanım Hakkı Varlıkları' THEN b.try_donemsel END) kullanim_hakki,
SUM(CASE WHEN b.yil=s.yil AND b.kalem='Müşteri Sözleşmelerinden Doğan Varlıklar' THEN b.try_donemsel END) mus_soz_varlik,
SUM(CASE WHEN b.yil=s.yil AND b.kalem='Ticari Alacaklar' THEN b.usd_donemsel END) tic_alacak_usd0,
SUM(CASE WHEN b.yil=s.yil-1 AND b.kalem='Ticari Alacaklar' THEN b.usd_donemsel END) tic_alacak_usd1,
SUM(CASE WHEN b.yil=s.yil AND b.kalem='Net Borç' THEN b.usd_donemsel END) net_borc_usd0,
SUM(CASE WHEN b.yil=s.yil-1 AND b.kalem='Net Borç' THEN b.usd_donemsel END) net_borc_usd1,
SUM(CASE WHEN b.yil=s.yil AND b.kalem='Maddi Olmayan Duran Varlıklar' THEN b.usd_donemsel END) modv_usd0,
SUM(CASE WHEN b.yil=s.yil-1 AND b.kalem='Maddi Olmayan Duran Varlıklar' THEN b.usd_donemsel END) modv_usd1
FROM hisse_finansal_tablolari_bilanco_kalemleri b JOIN son s ON b.hisse_senedi_kodu=s.hisse_senedi_kodu AND b.ay=s.ay AND b.yil BETWEEN s.yil-1 AND s.yil
GROUP BY 1 ORDER BY 1 LIMIT 300;

-- ===================== ham/piyasa.csv =====================
SELECT h.hisse_senedi_kodu kod, h.piyasa_degeri, h.son_fiyat, h.fiili_dolasim_orani, se.baslik sektor,
(SELECT MAX(ha.ilk_islem_tarihi_europe_istanbul) FROM halka_arzlar ha WHERE ha.hisse_senedi_kodu=h.hisse_senedi_kodu) halka_arz_tarihi,
(SELECT COUNT(*) FROM hisse_senedi_sermaye_artirimlari sa WHERE sa.hisse_senedi_kodu=h.hisse_senedi_kodu AND sa.ihrac_orani>0 AND sa.tarih_europe_istanbul>=DATE '2021-11-25') bedelli_5y,
(SELECT MAX(sa.tarih_europe_istanbul) FROM hisse_senedi_sermaye_artirimlari sa WHERE sa.hisse_senedi_kodu=h.hisse_senedi_kodu AND sa.ihrac_orani>0) son_bedelli,
(SELECT COUNT(DISTINCT EXTRACT(YEAR FROM t.tarih_europe_istanbul)) FROM hisse_senedi_temettuler t WHERE t.hisse_senedi_kodu=h.hisse_senedi_kodu AND t.tarih_europe_istanbul>=DATE '2021-11-25' AND t.nakit_temettu>0) temettu_yil_5y,
(SELECT MAX(t.tarih_europe_istanbul) FROM hisse_senedi_temettuler t WHERE t.hisse_senedi_kodu=h.hisse_senedi_kodu AND t.nakit_temettu>0) son_temettu
FROM hisse_senetleri h LEFT JOIN sektorler se ON se.id=h.sektor_id
WHERE h.hisse_senedi_kodu IN (SELECT hisse_senedi_kodu FROM hisse_finansal_tablolari WHERE finansal_tablo_sablonu='default' AND yil>=2026)
ORDER BY 1 LIMIT 300;
