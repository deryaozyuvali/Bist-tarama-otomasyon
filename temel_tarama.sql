WITH p AS (
  SELECT hisse_senedi_kodu AS k, yil, ay, finansal_tablo_sablonu AS s,
         ROW_NUMBER() OVER (PARTITION BY hisse_senedi_kodu ORDER BY yil DESC, ay DESC) AS rn
  FROM hisse_finansal_tablolari WHERE yil >= 2024),
gq AS (
  SELECT p.k, p.rn, p.yil, p.ay,
    SUM(CASE WHEN g.kalem = 'Satış Gelirleri' THEN g.try_ttm END) AS satis,
    SUM(CASE WHEN g.kalem = 'Satış Gelirleri' THEN g.try_ceyreklik END) AS satis_q,
    SUM(CASE WHEN g.kalem = 'Brüt Kar (Zarar)' THEN g.try_ceyreklik END) AS brut_q,
    SUM(CASE WHEN g.kalem = 'FAVÖK' THEN g.try_ttm END) AS favok,
    SUM(CASE WHEN g.kalem = 'Ana Ortaklık Payları' THEN g.try_ttm END) AS net,
    SUM(CASE WHEN g.kalem = 'Faaliyet Karı (Zararı)' THEN g.try_ttm END) AS fk,
    SUM(CASE WHEN g.kalem IN ('Diğer Faaliyet Gelirleri', 'Diğer Faaliyet Giderleri (-)') THEN g.try_ttm END) AS diger,
    SUM(CASE WHEN g.kalem = 'Özkaynak Yöntemiyle Değerlenen Yatırımların Karlarından (Zararlarından) Paylar' THEN g.try_ttm END) AS ozk_pay,
    SUM(CASE WHEN g.kalem = 'Durdurulan Faaliyetler Dönem Karı/Zararı' THEN g.try_ttm END) AS durd
  FROM p JOIN hisse_finansal_tablolari_gelir_tablosu_kalemleri g
    ON g.hisse_senedi_kodu = p.k AND g.yil = p.yil AND g.ay = p.ay
  WHERE p.rn <= 5 AND p.s = 'default'
  GROUP BY p.k, p.rn, p.yil, p.ay),
g AS (
  SELECT k,
    MAX(CASE WHEN rn = 1 THEN yil * 100 + ay END) AS donem,
    MAX(CASE WHEN rn = 1 THEN satis END) AS satis,
    MAX(CASE WHEN rn = 5 THEN satis END) AS satis_1y,
    MAX(CASE WHEN rn = 1 THEN favok END) AS favok,
    MAX(CASE WHEN rn = 1 THEN net END) AS net,
    MAX(CASE WHEN rn = 1 THEN fk END) AS fk,
    MAX(CASE WHEN rn = 1 THEN diger END) AS diger,
    MAX(CASE WHEN rn = 1 THEN ozk_pay END) AS ozk_pay,
    MAX(CASE WHEN rn = 1 THEN durd END) AS durd,
    MAX(CASE WHEN rn <= 4 AND satis_q > 0 THEN brut_q / satis_q END)
      - MIN(CASE WHEN rn <= 4 AND satis_q > 0 THEN brut_q / satis_q END) AS bm_aralik
  FROM gq GROUP BY k),
bq AS (
  SELECT p.k, p.rn,
    SUM(CASE WHEN b.kalem = 'Ticari Alacaklar' THEN b.try_donemsel END) AS alacak,
    SUM(CASE WHEN b.kalem = 'Net Borç' THEN b.try_donemsel END) AS netborc,
    SUM(CASE WHEN b.kalem = 'Azınlık Payları' THEN b.try_donemsel END) AS azinlik,
    SUM(CASE WHEN b.kalem = 'Toplam Varlıklar' THEN b.try_donemsel END) AS aktif,
    SUM(CASE WHEN b.kalem = 'Maddi Duran Varlıklar' THEN b.try_donemsel END) AS mdv,
    SUM(CASE WHEN b.kalem = 'Kullanım Hakkı Varlıkları' THEN b.try_donemsel END) AS khv,
    SUM(CASE WHEN b.kalem = 'Maddi Olmayan Duran Varlıklar' THEN b.try_donemsel END) AS modv,
    SUM(CASE WHEN b.kalem IN ('Yatırım Amaçlı Gayrimenkuller', 'Proje Halindeki Yatırım Amaçlı Gayrimenkuller',
        'Özkaynak Yöntemiyle Değerlenen Yatırımlar', 'İştirakler, İş Ortaklıkları ve Bağlı Ortaklıklardaki Yatırımlar',
        'Satış Amacıyla Elde Tutulan Duran Varlıklar') THEN b.try_donemsel END) AS gizli
  FROM p JOIN hisse_finansal_tablolari_bilanco_kalemleri b
    ON b.hisse_senedi_kodu = p.k AND b.yil = p.yil AND b.ay = p.ay
  WHERE p.rn IN (1, 5) AND p.s = 'default'
  GROUP BY p.k, p.rn),
b AS (
  SELECT k,
    MAX(CASE WHEN rn = 1 THEN alacak END) AS alacak,
    MAX(CASE WHEN rn = 5 THEN alacak END) AS alacak_1y,
    MAX(CASE WHEN rn = 1 THEN netborc END) AS netborc,
    MAX(CASE WHEN rn = 1 THEN azinlik END) AS azinlik,
    MAX(CASE WHEN rn = 1 THEN aktif END) AS aktif,
    MAX(CASE WHEN rn = 1 THEN mdv END) AS mdv,
    MAX(CASE WHEN rn = 1 THEN khv END) AS khv,
    MAX(CASE WHEN rn = 1 THEN modv END) AS modv,
    MAX(CASE WHEN rn = 1 THEN gizli END) AS gizli
  FROM bq GROUP BY k),
t AS (
  SELECT hisse_senedi_kodu AS k, COUNT(DISTINCT yil) AS tem_yil
  FROM hisse_finansal_tablolari_nakit_akis_tablosu_kalemleri
  WHERE kalem = 'Ödenen Temettüler' AND ay = 12 AND yil >= 2021 AND try_donemsel < 0
  GROUP BY hisse_senedi_kodu),
f AS (
  {{FCF}}),
x AS (
  SELECT h.hisse_senedi_kodu AS k, sk.baslik AS sektor, h.piyasa_degeri AS pd, h.fiili_dolasim_orani AS fdo,
    g.donem, g.satis, g.favok, g.net, g.fk, g.diger, g.ozk_pay, g.durd, g.bm_aralik,
    COALESCE(b.netborc, 0) AS netborc, b.alacak, f.fcf, f.neg3, f.funnel, f.kat,
    COALESCE(t.tem_yil, 0) AS tem_yil,
    h.piyasa_degeri + COALESCE(b.netborc, 0) + COALESCE(b.azinlik, 0) AS fd,
    CASE WHEN g.favok > 0 AND h.piyasa_degeri + COALESCE(b.netborc, 0) + COALESCE(b.azinlik, 0) > 0
      THEN (h.piyasa_degeri + COALESCE(b.netborc, 0) + COALESCE(b.azinlik, 0)) / g.favok END AS fd_favok,
    g.favok / NULLIF(g.satis, 0) AS marj,
    CASE WHEN g.favok > 0 THEN COALESCE(b.netborc, 0) / g.favok END AS nb_favok,
    g.satis / NULLIF(g.satis_1y, 0) - 1 AS buyume,
    b.alacak / NULLIF(b.alacak_1y, 0) - 1 AS alacak_b,
    b.gizli / NULLIF(h.piyasa_degeri, 0) AS gizli_pd,
    b.modv / NULLIF(b.aktif, 0) AS modv_akt,
    b.mdv / NULLIF(b.aktif, 0) AS mdv_akt,
    COALESCE(b.khv, 0) / NULLIF(b.aktif, 0) AS khv_akt,
    f.fcf * 1000000 / NULLIF(h.piyasa_degeri, 0) AS fcf_verim
  FROM hisse_senetleri h
    JOIN sektorler sk ON sk.id = h.sektor_id
    JOIN g ON g.k = h.hisse_senedi_kodu
    JOIN b ON b.k = h.hisse_senedi_kodu
    LEFT JOIN t ON t.k = h.hisse_senedi_kodu
    LEFT JOIN f ON f.k = h.hisse_senedi_kodu
  WHERE h.sektor_id NOT IN (3, 4, 6, 24, 25, 26, 33, 35, 36, 39, 49)
    AND h.piyasa_degeri > 0 AND g.satis > 0),
s AS (
  SELECT x.*,
    CASE WHEN marj > 0.90 THEN 0 WHEN fd_favok <= 5 THEN 3 WHEN fd_favok <= 8 THEN 2 WHEN fd_favok <= 12 THEN 1
         WHEN fd_favok > 20 THEN -1 ELSE 0 END AS p_fd,
    CASE WHEN marj > 0.90 THEN 0 WHEN marj >= 0.25 THEN 2 WHEN marj >= 0.15 THEN 1 WHEN marj < 0.03 THEN -1 ELSE 0 END AS p_marj,
    CASE WHEN netborc < 0 THEN 2 WHEN nb_favok <= 1.5 THEN 1 WHEN nb_favok > 3 THEN -2
         WHEN favok <= 0 THEN -1 ELSE 0 END AS p_borc,
    CASE WHEN buyume >= 0.15 THEN 2 WHEN buyume >= 0 THEN 1 ELSE 0 END AS p_buyume,
    CASE WHEN gizli_pd >= 0.30 THEN 2 WHEN gizli_pd >= 0.15 THEN 1 ELSE 0 END AS p_gizli,
    CASE WHEN mdv_akt >= 0.40 AND khv_akt <= 0.02 AND marj >= 0.15 THEN 1 ELSE 0 END AS p_mulk,
    CASE WHEN pd <= 15000000000 THEN 1 ELSE 0 END AS p_kucuk,
    CASE WHEN alacak_b - buyume > 0.30 AND alacak > 0.10 * satis THEN -1 ELSE 0 END AS p_alacak,
    CASE WHEN modv_akt >= 0.25 THEN -1 ELSE 0 END AS p_tms38,
    CASE WHEN bm_aralik >= 0.20 THEN -1 ELSE 0 END AS p_oynak,
    CASE WHEN tem_yil = 0 THEN -1 ELSE 0 END AS p_temettu,
    CASE WHEN fcf_verim >= 0.10 THEN 2 WHEN fcf_verim >= 0.05 THEN 1 WHEN neg3 = 1 THEN -1 ELSE 0 END AS p_fcf,
    CASE WHEN kat = 'A' THEN 2 WHEN kat = 'I' THEN 1 WHEN kat = 'L' THEN -1 ELSE 0 END AS p_funnel
  FROM x)
SELECT k AS hisse, sektor, donem,
  p_fd + p_marj + p_borc + p_buyume + p_gizli + p_mulk + p_kucuk + p_alacak + p_tms38 + p_oynak + p_temettu AS yayinci,
  p_fcf + p_funnel AS fcf_funnel,
  p_fd + p_marj + p_borc + p_buyume + p_gizli + p_mulk + p_kucuk + p_alacak + p_tms38 + p_oynak + p_temettu
    + p_fcf + p_funnel AS puan,
  ROUND(pd / 1000000) AS pd_mn,
  ROUND(fd_favok, 1) AS fd_favok,
  ROUND(100 * marj) AS favok_marj,
  ROUND(nb_favok, 1) AS nb_favok,
  ROUND(100 * buyume) AS reel_buyume,
  ROUND(100 * gizli_pd) AS gizli_pd,
  ROUND(100 * fcf_verim, 1) AS fcf_verim,
  funnel, kat,
  p_fd, p_marj, p_borc, p_buyume, p_gizli, p_mulk, p_kucuk,
  p_alacak AS u_alacak, p_tms38 AS u_tms38, p_oynak AS u_oynak, p_temettu AS u_temettu,
  p_fcf, p_funnel,
  CASE WHEN net < 0 AND favok > 0 AND fd_favok <= 10 THEN 'X' END AS b_zarar_ama_favok,
  CASE WHEN fk <> 0 AND diger > 0.30 * ABS(fk) THEN 'X' END AS b_diger_gelir,
  CASE WHEN ozk_pay < 0 AND ABS(ozk_pay) > 0.30 * ABS(net) THEN 'X' END AS b_istirak_zarari,
  CASE WHEN marj > 0.90 THEN 'X' END AS b_finansal_gelir,
  CASE WHEN durd <> 0 AND ABS(durd) > 0.20 * ABS(net) THEN 'X' END AS b_durdurulan
FROM s
ORDER BY {{SIRA}} DESC, fd_favok ASC
LIMIT 300
