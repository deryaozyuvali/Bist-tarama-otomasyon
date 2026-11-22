-- EVO (Fintables MCP, veri_sorgula) — evo_ham_<tarih>.csv girdisini üreten sorgu.
-- Tarihleri (2025-11-22 = bugünden 12 ay önce, 2022..2026 = son 5 takvim yılı) her çalıştırmada güncelle.
-- Evren: standart şablon, TTM ana ortaklık kârı > 0 ve
--   (son 5 yılın ≥3'ünde temettü)  -> A/B/C/D/E sınıflaması
--   VEYA (son 5 yılın ≥4'ünde kâr) -> temettü vermeyen/yeni başlayanlar, P sınıfı adayı
-- EVO tek sorguda en fazla 300 satır döndürür; aşılırsa ORDER BY kod ile ikiye böl (kod < 'K' / kod >= 'K').
WITH son AS (
  SELECT DISTINCT ON (f.hisse_senedi_kodu) f.hisse_senedi_kodu k, f.yil, f.ay
  FROM hisse_finansal_tablolari f WHERE f.finansal_tablo_sablonu='default' AND f.yil>=2026
  ORDER BY f.hisse_senedi_kodu, f.yil DESC, f.ay DESC),
bil AS (
  SELECT s.k, s.yil, s.ay,
   SUM(CASE WHEN b.kalem='Nakit ve Nakit Benzerleri' THEN b.try_donemsel ELSE 0 END) nakit,
   SUM(CASE WHEN b.kalem='Finansal Borçlar' THEN b.try_donemsel ELSE 0 END) fb,
   SUM(CASE WHEN b.kalem='Kullanım Hakkı Varlıkları' THEN b.try_donemsel ELSE 0 END) rou,
   SUM(CASE WHEN b.kalem='Geri Alınmış Paylar (-)' THEN b.try_donemsel ELSE 0 END) gap
  FROM son s JOIN hisse_finansal_tablolari_bilanco_kalemleri b ON b.hisse_senedi_kodu=s.k AND b.yil=s.yil AND b.ay=s.ay
  GROUP BY s.k, s.yil, s.ay),
gel AS (
  SELECT g.hisse_senedi_kodu k,
   SUM(CASE WHEN g.yil=s.yil AND g.ay=s.ay THEN g.try_ttm ELSE 0 END) np_ttm,
   SUM(CASE WHEN g.yil=2025 AND g.ay=12 THEN g.try_donemsel ELSE 0 END) np25,
   SUM(CASE WHEN g.yil=2024 AND g.ay=12 THEN g.try_donemsel ELSE 0 END) np24,
   SUM(CASE WHEN g.yil=2023 AND g.ay=12 THEN g.try_donemsel ELSE 0 END) np23,
   COUNT(CASE WHEN g.ay=12 AND g.yil BETWEEN 2021 AND 2025 AND g.try_donemsel>0 THEN 1 END) n_kar
  FROM son s JOIN hisse_finansal_tablolari_gelir_tablosu_kalemleri g ON g.hisse_senedi_kodu=s.k
  WHERE g.kalem='Ana Ortaklık Payları' AND g.yil>=2021
  GROUP BY g.hisse_senedi_kodu),
tem AS (
  SELECT t.hisse_senedi_kodu k,
   SUM(CASE WHEN t.tarih_europe_istanbul >= '2025-11-22' THEN t.nakit_temettu ELSE 0 END) d12,
   SUM(CASE WHEN EXTRACT(YEAR FROM t.tarih_europe_istanbul) IN (2024,2025,2026) THEN t.nakit_temettu ELSE 0 END) d3y,
   COUNT(DISTINCT CASE WHEN EXTRACT(YEAR FROM t.tarih_europe_istanbul) BETWEEN 2022 AND 2026 THEN EXTRACT(YEAR FROM t.tarih_europe_istanbul) END) n_tem
  FROM hisse_senedi_temettuler t WHERE t.nakit_temettu>0 AND t.tarih_europe_istanbul BETWEEN '2022-01-01' AND '2026-11-22'
  GROUP BY t.hisse_senedi_kodu)
SELECT h.hisse_senedi_kodu kod, bil.yil*100+bil.ay don, ROUND(h.piyasa_degeri/1e6) pd, ROUND(bil.nakit/1e6) nakit, ROUND(bil.fb/1e6) fb,
 ROUND(bil.rou/1e6) rou, ROUND(bil.gap/1e6) gap, ROUND(gel.np_ttm/1e6) np_ttm, ROUND(gel.np25/1e6) np25, ROUND(gel.np24/1e6) np24,
 ROUND(gel.np23/1e6) np23, gel.n_kar, ROUND(COALESCE(tem.d12,0)/1e6) d12, ROUND(COALESCE(tem.d3y,0)/1e6) d3y, COALESCE(tem.n_tem,0) n_tem
FROM hisse_senetleri h JOIN bil ON bil.k=h.hisse_senedi_kodu JOIN gel ON gel.k=h.hisse_senedi_kodu LEFT JOIN tem ON tem.k=h.hisse_senedi_kodu
WHERE gel.np_ttm>0 AND (COALESCE(tem.n_tem,0)>=3 OR gel.n_kar>=4)
ORDER BY 1 LIMIT 300
