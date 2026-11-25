"""
Temel analiz ÖN ELEME taraması.

Kaynak: Bir yatırımcının "şirket incelerken nelere dikkat ediyorum" videosu.
Burada sadece VERİDEN OTOMATİK hesaplanabilen kısmı var. Videodaki elle
bakılacak maddeler (patron tipi, genel müdür mesajı, Çin rekabeti, hendek,
ilişkili taraf dipnotları, huzur hakkı, vakıf bağışı...) bu script'in
kapsamında değil. Çıktıdaki "elle_bak" kolonu bunları hatırlatır.

ÇEKİRDEK 4 KRİTER (videoda "bu dördü tutuyorsa yatırım sinyalleri başlıyor"):
  K1  ROIC > WACC
  K2  Pozitif serbest nakit akışı, sürdürülebilir (tek yıl değil)
  K3  FD / SNA < 10  (büyüme yatırımı ayıklanmış, kira düşülmüş)
  K4  İşlerde ciddi daralma yok  (VEKİL gösterge, gelecek tahmini değil)

Veri: EVO / Fintables MCP'den çekilen ham CSV'ler (temel/ham/*.csv).
Tutarlar TRY; TMS 29 enflasyon muhasebesi uygulanmış tablolar.
Büyüme karşılaştırmaları USD üzerinden yapılır (TL'de dönemler arası
satın alma gücü farklı olduğu için).

[Bizim varsayımlarımız — videoda geçmeyen, hesap için gereken seçimler]
  * WACC: Videoda nasıl hesaplandığı söylenmiyor. TMS 29 tablolarında
    esas faaliyet kârı / yatırılan sermaye REEL bir getiriye yakındır;
    bu yüzden eşik reel bir oran olarak parametrik (varsayılan %10).
  * Bakım yatırımı ≈ min(yatırım harcaması, amortisman). Amortismanın
    üzerindeki yatırım harcaması "büyüme yatırımı" sayılır.
  * Kira (TFRS 16): Videodaki gibi kira ödemeleri SNA'dan düşülür. FD ise
    raporlandığı gibi bırakılır (net borç kira yükümlülüğünü içerir). Bu, kirayı
    hem borçta hem giderde saymak demektir → bilerek İHTİYATLI seçim.
    Bilgi amaçlı "fd_sna_kira_haric" kolonunda FD'den kira yükümlülüğü vekili
    (min(kullanım hakkı, finansal borç)) çıkarılmış hali de var. Kullanım hakkı
    TMS 29'da enflasyonla şiştiği için tek başına vekil olarak kullanılmadı.
  * Ödenen faiz CFO içinde raporlandıysa SNA'yı düşürür (muhafazakâr).
"""
import argparse
import os
import warnings
import numpy as np
import pandas as pd

warnings.simplefilter("ignore", pd.errors.PerformanceWarning)

HAM = os.path.join(os.path.dirname(__file__), "ham")

# Kapsam dışı: FD/SNA ve ROIC mantığının uymadığı finansal yapılar
# (banka/sigorta/leasing/faktoring zaten 'default' şablonda değil)
KAPSAM_DISI_SEKTOR = {"Aracı Kurum", "Menkul Kıymet Yat. Ort.", "Girişim Sermayesi Yat. Ort."}
# Videoda "her sektörde farklı bakmaya çalışıyorum" — bu sektörler taranır ama uyarı alır
SEKTOR_NOTU = {
    "Holding": "Holding: parçaların değerine tek tek bakılmalı",
    "Gayrimenkul": "GYO: kira çarpanına bakılmalı (stokçu ayrı); ilişkili tarafa verilen kira",
    "Bilişim ve Yazılım": "Yazılım: aktifleştirme oranı + tekrarlayan gelir payı",
    "Gıda Perakendeciliği": "Perakende: nakit dönüşüm döngüsü, kira",
    "Giyim, Tekstil ve Deri Ürünleri Perakendeciliği": "Giyim perakende: m² başı satış, aynı mağaza büyümesi, kira",
    "İlaç ve Sağlık": "İlaç: fiyat kararnamesi/avro değeri; Hastane: SGK/sigorta, kira",
    "Enerji Üretim ve Dağıtım": "Enerji: üretim verisi (EPİAŞ), regülasyon, PTF",
    "Otomotiv": "Otomotiv: OSD üretim/ihracat, araç başı FAVÖK, Çinli rakipler",
    "Madencilik ve Taş Ocakçılığı": "Madencilik: kaynak/rezerv ayrımı, projeksiyon gecikmesi",
    "İnşaat": "Taahhüt: bakiye sipariş / PD, müşteri sözleşmelerinden doğan varlıklar",
    "Haberleşme": "Telekom: yüksek yatırım ihtiyacı, kârlılık göründüğü kadar değil",
}


def n(x):
    return pd.to_numeric(x, errors="coerce")


def yukle():
    g = pd.read_csv(os.path.join(HAM, "gelir.csv"))
    na = pd.read_csv(os.path.join(HAM, "nakit.csv"))
    b = pd.read_csv(os.path.join(HAM, "bilanco.csv"))
    p = pd.read_csv(os.path.join(HAM, "piyasa.csv"))
    d = g.merge(na, on="kod", how="left").merge(b, on="kod", how="left").merge(p, on="kod", how="left")
    am = os.path.join(HAM, "amortisman.csv")
    if os.path.exists(am):
        d = d.merge(pd.read_csv(am), on="kod", how="left")
    ic = os.path.join(HAM, "kap", "icerden_ozet.csv")
    if os.path.exists(ic):
        d = d.merge(pd.read_csv(ic), on="kod", how="left")
    for c in d.columns:
        if c in ("icerden_kimler",):
            continue
        if c not in ("kod", "sektor", "halka_arz_tarihi", "son_bedelli", "son_temettu"):
            d[c] = n(d[c])
    return d


def oran(a, b):
    a, b = n(a), n(b)
    return np.where((b > 0) & np.isfinite(a), a / b, np.nan)


def hesapla(d, wacc, fd_sna_esik, bugun):
    z = lambda c: d[c].fillna(0) if c in d else 0  # eksik kalem = 0

    # --- Kârlılık / ROIC (videodaki tanım: esas faaliyet kârı, vergi düşülmüş, / yatırılan sermaye)
    d["esas_faal_kar"] = z("brut") + z("opex")
    vergi_orani = (-z("vergi") / d["vok"]).where(d["vok"] > 0)
    d["vergi_orani"] = vergi_orani.clip(0, 0.35).fillna(0.25)
    d["nopat"] = d["esas_faal_kar"] * (1 - d["vergi_orani"])
    d["yatirilan_sermaye"] = d["ozk"] + d["net_borc"]
    d["roic"] = oran(d["nopat"], d["yatirilan_sermaye"])
    d.loc[d["esas_faal_kar"] <= 0, "roic"] = np.minimum(d["roic"], 0)  # zarardaysa pozitif görünmesin

    # --- Serbest nakit akışı
    capex = -z("capex")                      # pozitif tutar
    kira = -z("kira")
    amort = z("amort")
    bakim_capex = np.minimum(capex, amort.where(amort > 0, capex))
    d["sna_ham"] = d["cfo"] - capex - kira
    d["sna_bakim"] = d["cfo"] - bakim_capex - kira
    d["buyume_capex"] = capex - bakim_capex

    # Yıllık SNA sürdürülebilirliği (2022-2025)
    yil_pozitif = 0
    yil_var = 0
    for y in (2022, 2023, 2024, 2025):
        cfo_y, capex_y, kira_y = z(f"cfo_{y}"), -z(f"capex_{y}"), -z(f"kira_{y}")
        am_y = z(f"amort_{y}") if f"amort_{y}" in d else capex_y
        am_y = am_y.where(am_y > 0, capex_y)
        sna_y = cfo_y - np.minimum(capex_y, am_y) - kira_y
        d[f"sna_{y}"] = sna_y.where(d[f"cfo_{y}"].notna())
        yil_var += d[f"cfo_{y}"].notna().astype(int)
        yil_pozitif += (d[f"sna_{y}"] > 0).astype(int)
    d["sna_pozitif_yil"] = yil_pozitif
    d["sna_veri_yil"] = yil_var

    # --- Değerleme
    kira_yuk_vekil = np.minimum(z("kullanim_hakki"), z("fin_borc")).where(z("kira") < 0, 0)
    d["fd"] = d["piyasa_degeri"] + d["net_borc"] + z("azinlik_ozk")
    d["fd_kira_haric"] = d["fd"] - kira_yuk_vekil
    d["fd_sna"] = oran(d["fd"], d["sna_bakim"])                 # ana kriter (ihtiyatlı)
    d["fd_sna_kira_haric"] = oran(d["fd_kira_haric"], d["sna_bakim"])  # bilgi
    d["fd_sna_ham"] = oran(d["fd"], d["sna_ham"])
    d["fd_favok"] = oran(d["fd"], d["favok"])
    d["favok_kira_sonrasi"] = d["favok"] - kira
    d["fd_favok_kira"] = oran(d["fd_kira_haric"], d["favok_kira_sonrasi"])
    d["fk"] = oran(d["piyasa_degeri"], d["ana_kar"])
    d["pd_dd"] = oran(d["piyasa_degeri"], d["ana_ozk"])

    # --- Büyüme (USD, yıllık)
    d["satis_usd_buyume"] = oran(d["satis_usd0"], d["satis_usd1"]) - 1
    d["brut_usd_buyume"] = oran(d["brut_usd0"], d["brut_usd1"]) - 1
    d["brut_marj"] = oran(d["brut"], d["satis"])
    d["brut_marj_onceki"] = oran(d["brut_usd1"], d["satis_usd1"])

    # --- Bilanço
    d["cari_oran"] = oran(d["donen"], d["kvy"])
    d["asit_test"] = oran(d["donen"] - z("stok"), d["kvy"])
    d["nakit_oran"] = oran(d["nakit"], d["kvy"])
    d["alacak_borc"] = oran(d["tic_alacak"], d["tic_borc"])
    d["alacak_satis"] = oran(d["tic_alacak"], d["satis"])
    d["alacak_usd_buyume"] = oran(d["tic_alacak_usd0"], d["tic_alacak_usd1"]) - 1
    d["net_borc_favok"] = np.where(d["favok"] > 0, d["net_borc"] / d["favok"], np.nan)
    d["fin_gider_esas"] = oran(-z("fin_gider"), d["esas_faal_kar"])
    d["azinlik_kar_payi"] = oran(z("azinlik_kar"), d["donem_kar"])
    d["modv_aktif"] = oran(z("modv"), d["aktif"])
    d["capex_satis"] = oran(capex, d["satis"])
    d["kira_favok"] = oran(kira, d["favok"])

    # ===================== ÇEKİRDEK 4 KRİTER =====================
    d["K1_roic_wacc"] = d["roic"] > wacc
    d["K2_sna_surdurulebilir"] = (d["sna_bakim"] > 0) & (d["sna_pozitif_yil"] >= np.minimum(3, d["sna_veri_yil"])) & (d["sna_veri_yil"] >= 2)
    d["K3_fd_sna"] = (d["fd_sna"] > 0) & (d["fd_sna"] < fd_sna_esik)
    d["K4_daralma_yok"] = (d["satis_usd_buyume"] > -0.10) & (d["brut_usd_buyume"].fillna(0) > -0.15) & (d["esas_faal_kar"] > 0)
    kcols = ["K1_roic_wacc", "K2_sna_surdurulebilir", "K3_fd_sna", "K4_daralma_yok"]
    d["cekirdek_puan"] = d[kcols].fillna(False).astype(int).sum(axis=1)

    # ===================== ELEME (kesin) =====================
    elen = []
    ha = pd.to_datetime(d["halka_arz_tarihi"], errors="coerce", utc=True)
    bir_yil_once = pd.Timestamp(bugun, tz="UTC") - pd.DateOffset(years=1)
    for i, r in d.iterrows():
        e = []
        if r["sektor"] in KAPSAM_DISI_SEKTOR:
            e.append("kapsam dışı (finansal yapı)")
        if pd.notna(ha[i]) and ha[i] > bir_yil_once:
            e.append("halka arzı 1 yıldan yeni")
        if not (r["piyasa_degeri"] > 0):
            e.append("piyasa değeri yok")
        elen.append("; ".join(e))
    d["eleme"] = elen

    # ===================== KIRMIZI BAYRAKLAR / ARTILAR =====================
    bugun_ts = pd.Timestamp(bugun, tz="UTC")
    son_bed = pd.to_datetime(d["son_bedelli"], errors="coerce", utc=True)
    son_tem = pd.to_datetime(d["son_temettu"], errors="coerce", utc=True)
    bayrak, arti, elle = [], [], []
    for i, r in d.iterrows():
        f, a, m = [], [], []
        if r["ay"] < 6 or r["yil"] < 2026:
            f.append(f"veri eski ({int(r['yil'])}/{int(r['ay'])})")
        if r["bedelli_5y"] >= 2:
            f.append(f"sürekli bedelli ({int(r['bedelli_5y'])} kez/5 yıl)")
        elif pd.notna(son_bed[i]) and son_bed[i] > bugun_ts - pd.DateOffset(years=2):
            f.append("son 2 yılda bedelli")
        if r["alacak_borc"] > 2 and r["alacak_satis"] > 0.25:
            f.append(f"ticari alacak yüksek, borçla dengesiz (alacak/borç {r['alacak_borc']:.1f})")
        if pd.notna(r["alacak_usd_buyume"]) and pd.notna(r["satis_usd_buyume"]) and r["alacak_usd_buyume"] - r["satis_usd_buyume"] > 0.25 and r["alacak_satis"] > 0.15:
            f.append("alacaklar satıştan hızlı büyüyor")
        if r["pd_dd"] < 1 and not (r["roic"] > wacc):
            f.append("PD/DD<1 ama ROIC<WACC (değer tuzağı olabilir)")
        if not (r["roic"] > wacc) and r["buyume_capex"] > 0 and r["capex_satis"] > 0.10:
            f.append("ROIC düşükken büyüme yatırımı")
        if r["net_borc_favok"] > 2.5 and (r.get("temettu_odenen", 0) < 0 or r.get("geri_alim", 0) < 0):
            f.append("borçluyken temettü/geri alım")
        if r["net_borc_favok"] > 3.5 or (r["favok"] <= 0 and r["net_borc"] > 0):
            f.append("borç yükü ağır")
        if r["cari_oran"] < 1:
            f.append(f"cari oran < 1 ({r['cari_oran']:.2f})")
        if r["azinlik_kar_payi"] > 0.20:
            f.append(f"kârın %{r['azinlik_kar_payi']*100:.0f}'i azınlığın (konsolidasyon düzeltmesi)")
        if r["modv_aktif"] > 0.25:
            f.append("maddi olmayan varlık yüksek (TMS 38 aktifleştirme/şerefiye kontrol)")
        ana = [r.get("ana_usd1"), r.get("ana_usd2")]
        ana = [x for x in ana if pd.notna(x) and x > 0]
        if r["ana_usd0"] > 0 and ana and r["ana_usd0"] > 2 * np.mean(ana):
            f.append("kâr geçmişin 2 katı üstünde (tek seferlik/zirve olabilir → düşük çarpan)")
        if r["capex_satis"] > 0.15:
            f.append(f"yatırım harcaması yüksek (satışın %{r['capex_satis']*100:.0f}'i)")
        if r["kira_favok"] > 0.20:
            f.append(f"kira ağır (FAVÖK'ün %{r['kira_favok']*100:.0f}'i → FD/FAVÖK yanıltır)")
        if r["ana_ozk"] <= 0:
            f.append("özkaynak negatif")
        if r["ana_kar"] <= 0:
            f.append("son 12 ay net zarar (nakit/esas kâr var ama net kâr yok → nedenini anla)")
        elif r["fk"] > 50:
            f.append(f"net kâr çok zayıf (F/K {r['fk']:.0f})")

        # Patron / yönetici / ana ortak işlemleri (KAP pay alım-satım bildirimleri, son 12 ay)
        icy, ictl = r.get("icerden_net_sermaye_yuzde"), r.get("icerden_net_tl_yaklasik")
        kim = r.get("icerden_kimler") if isinstance(r.get("icerden_kimler"), str) else ""
        if pd.notna(icy) and icy < 0 and (icy <= -0.25 or ictl <= -25e6):
            f.append(f"⛔ PATRON/YÖNETİCİ NET SATIŞ (12 ay): sermayenin %{abs(icy):.2f}'i, ~{abs(ictl)/1e6:,.0f} mn TL ({kim[:80]})")
        if pd.notna(r.get("devir_bildirim")) and r.get("devir_bildirim") > 0:
            f.append("içeriden pay devri/virman bildirimi var (elle bak)")

        # artılar
        if pd.notna(icy) and icy > 0 and (icy >= 0.1 or ictl >= 10e6):
            a.append(f"patron/yönetici net alım (12 ay): %{icy:.2f}, ~{ictl/1e6:,.0f} mn TL")
        if pd.notna(son_tem[i]) and son_tem[i] > bugun_ts - pd.DateOffset(years=1):
            a.append("son 1 yılda nakit temettü")
        if r["temettu_yil_5y"] >= 4:
            a.append(f"düzenli temettü ({int(r['temettu_yil_5y'])}/5 yıl)")
        if r["brut_marj"] > 0.30:
            a.append(f"brüt marj yüksek (%{r['brut_marj']*100:.0f})")
        if pd.notna(r["brut_marj_onceki"]) and r["brut_marj"] - r["brut_marj_onceki"] > 0.03:
            a.append("brüt marj genişliyor (makas açılıyor)")
        if (r["esas_faal_kar"] > 0 and r["fin_gider_esas"] > 0.5 and pd.notna(r["net_borc_usd1"])
                and r["net_borc_usd0"] < 0.85 * r["net_borc_usd1"] and r["net_borc_usd1"] > 0):
            a.append("borç azalıyor + finansman gideri kârı yiyor (borç kapanınca kâr ortaya çıkabilir)")
        if r["cari_oran"] >= 1.5 and r["asit_test"] >= 1 and r["nakit_oran"] >= 0.20:
            a.append("likidite oranları sağlam (1,5 / 1 / 0,20)")

        m.append(SEKTOR_NOTU.get(r["sektor"], ""))
        bayrak.append(" | ".join(f))
        arti.append(" | ".join(a))
        elle.append(m[0])
    d["kirmizi_bayraklar"] = bayrak
    d["patron_satisi"] = ["⛔ PATRON" in x for x in bayrak]
    d["bayrak_sayisi"] = [len(x.split(" | ")) if x else 0 for x in bayrak]
    d["artilar"] = arti
    d["sektor_notu"] = elle

    # Sektör içi brüt marj yüzdeliği (elma ile elma)
    d["brut_marj_sektor_yuzdelik"] = d.groupby("sektor")["brut_marj"].rank(pct=True)
    d["fd_sna_sektor_medyan"] = d.groupby("sektor")["fd_sna"].transform(lambda s: s[(s > 0)].median())
    return d


KOLONLAR = [
    "kod", "sektor", "yil", "ay", "cekirdek_puan",
    "K1_roic_wacc", "K2_sna_surdurulebilir", "K3_fd_sna", "K4_daralma_yok",
    "roic", "fd_sna", "fd_sna_kira_haric", "fd_sna_ham", "sna_pozitif_yil", "sna_veri_yil",
    "satis_usd_buyume", "brut_usd_buyume", "brut_marj", "brut_marj_sektor_yuzdelik",
    "fd_favok", "fd_favok_kira", "fk", "pd_dd", "net_borc_favok",
    "cari_oran", "asit_test", "nakit_oran", "alacak_borc",
    "piyasa_degeri", "fd", "sna_bakim", "sna_ham", "buyume_capex", "esas_faal_kar", "favok",
    "icerden_net_sermaye_yuzde", "icerden_net_tl_yaklasik", "patron_satisi",
    "bayrak_sayisi", "kirmizi_bayraklar", "artilar", "sektor_notu", "eleme",
]

ELLE_BAK = (
    "Elle bak (otomatik değil): faaliyet raporu + genel müdür mesajı; patron tipi ve "
    "geçmiş beklentileri tutturma; patron satışının gerekçesi; huzur hakkı ve "
    "vakıf bağışı (genel kurul); ilişkili taraf işlemleri ve satın almalar (dipnot); "
    "kâr payı imtiyazı; Çin rekabeti; giriş bariyeri/hendek; analist toplantısı; "
    "'neden ucuz?' sorusu; karar verdikten sonra 1 hafta bekle. (Patron alım/satımı KAP'tan otomatik eklendi.)"
)


def _f(x, yuzde=False, ondalik=1):
    if pd.isna(x):
        return "–"
    if yuzde:
        return f"-%{abs(x)*100:.0f}" if x < 0 else f"%{x*100:.0f}"
    return f"{x:.{ondalik}f}"


def _patron(r):
    y = r.get("icerden_net_sermaye_yuzde")
    if pd.isna(y):
        return "–"
    if r.get("patron_satisi"):
        return f"⛔ satış %{abs(y):.2f}"
    return f"alım %{y:.2f}" if y > 0 else f"satış %{abs(y):.2f}"


def ozet_yaz(aday, d, a, yol):
    gecerli = d[d["eleme"] == ""]
    L = [f"# Temel ön eleme — {a.tarih}", "",
         f"Varsayımlar: reel WACC eşiği **%{a.wacc*100:.0f}**, FD/SNA < **{a.fd_sna:g}**. "
         f"Taranan {len(d)} şirket, kesin elenen {len(d)-len(gecerli)} "
         "(finansal yapı / halka arzı 1 yıldan yeni / veri yok).", "",
         "| Kriter | Geçen |", "|---|---|"]
    for k, ad in [("K1_roic_wacc", "K1 ROIC > WACC"), ("K2_sna_surdurulebilir", "K2 SNA sürdürülebilir pozitif"),
                  ("K3_fd_sna", "K3 FD/SNA < eşik"), ("K4_daralma_yok", "K4 daralma yok (vekil)")]:
        L.append(f"| {ad} | {int(gecerli[k].fillna(False).sum())} |")
    L += ["", "> Bu bir **ön eleme**: yalnızca veriden hesaplanabilen kısım. Listeye girmek 'al' demek değildir; "
          "her aday için elle bakılacaklar en altta.", ""]
    for puan, baslik in [(4, "Liste A — 4/4 kriter"), (3, "Liste B — 3/4 kriter")]:
        t = aday[aday["cekirdek_puan"] == puan]
        L += [f"## {baslik} ({len(t)})", "",
              "| Kod | Sektör | Eksik kriter | ROIC | FD/SNA | SNA+ yıl | USD satış büyüme | Brüt marj | FD/FAVÖK | Patron 12 ay | Bayrak |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
        for _, r in t.iterrows():
            eksik = ", ".join(k[:2] for k in ["K1_roic_wacc", "K2_sna_surdurulebilir", "K3_fd_sna", "K4_daralma_yok"] if not r[k]) or "–"
            L.append(f"| {r['kod']} | {r['sektor']} | {eksik} | {_f(r['roic'], True)} | {_f(r['fd_sna'])} | "
                     f"{int(r['sna_pozitif_yil'])}/{int(r['sna_veri_yil'])} | {_f(r['satis_usd_buyume'], True)} | "
                     f"{_f(r['brut_marj'], True)} | {_f(r['fd_favok'])} | {_patron(r)} | {int(r['bayrak_sayisi'])} |")
        L.append("")
    L += ["## Bayraklar ve artılar (adaylar)", ""]
    for _, r in aday.iterrows():
        satir = f"- **{r['kod']}**"
        if isinstance(r["kirmizi_bayraklar"], str) and r["kirmizi_bayraklar"]:
            satir += f" — 🚩 {r['kirmizi_bayraklar']}"
        if isinstance(r["artilar"], str) and r["artilar"]:
            satir += f" — ✅ {r['artilar']}"
        if isinstance(r["sektor_notu"], str) and r["sektor_notu"]:
            satir += f" — 🔎 {r['sektor_notu']}"
        L.append(satir)
    L += ["", "## Patron / yönetici işlemleri hakkında", "",
          "Kaynak: KAP 'Pay Alım Satım Bildirimi'leri, son 12 ay, sadece aday şirketler. Bank of America, FMR, Goldman, "
          "yatırım/emeklilik fonları gibi kurumlar SAYILMADI; kişiler, ana ortak/holding ve grup şirketleri sayıldı. "
          "Aile içi devir, virman ve teminat amaçlı devirler satış sayılmadı (ayrı bayrak). Şirket parasıyla yapılan geri "
          "alım bu kapsamda değil (videoda da önemsenmiyor). '⛔' eşiği: net satış sermayenin ≥%0,25'i veya ≥25 mn TL. "
          "Videoda: 'Patron hisse satıyorsa genellikle uzak duruyorum ... çok temel gerekçeleri olması lazım.' "
          "Satışın gerekçesi (ör. halka açıklık artırma, borç ödeme) bildirim metninden elle okunmalı.", "",
          "## Her aday için elle bakılacaklar", "", ELLE_BAK, ""]
    open(yol, "w", encoding="utf-8").write("\n".join(L))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wacc", type=float, default=0.10, help="Reel WACC eşiği (varsayılan 0.10)")
    ap.add_argument("--fd-sna", type=float, default=10.0, help="FD/SNA üst sınırı (videoda 10)")
    ap.add_argument("--tarih", default=pd.Timestamp.today().strftime("%Y-%m-%d"))
    ap.add_argument("--cikti", default=os.path.join(os.path.dirname(__file__), "..", "results", "temel"))
    a = ap.parse_args()

    d = hesapla(yukle(), a.wacc, a.fd_sna, a.tarih)
    os.makedirs(os.path.join(a.cikti, a.tarih), exist_ok=True)

    tum = d[KOLONLAR].sort_values(["cekirdek_puan", "fd_sna"], ascending=[False, True])
    tum.to_csv(os.path.join(a.cikti, a.tarih, "tum_sirketler.csv"), index=False)

    aday = tum[(tum["eleme"] == "") & (tum["cekirdek_puan"] >= 3)].copy()
    aday["liste"] = np.where(aday["cekirdek_puan"] == 4, "A (4/4)", "B (3/4)")
    aday["elle_bak"] = ELLE_BAK
    aday = aday.sort_values(["cekirdek_puan", "patron_satisi", "bayrak_sayisi", "fd_sna"], ascending=[False, True, True, True])
    aday.to_csv(os.path.join(a.cikti, a.tarih, "on_eleme.csv"), index=False)
    aday.to_csv(os.path.join(a.cikti, "latest_on_eleme.csv"), index=False)

    ozet_yaz(aday, d, a, os.path.join(a.cikti, a.tarih, "ozet.md"))

    print(f"Taranan: {len(d)} | Elenen: {(d['eleme']!='').sum()} | "
          f"4/4: {(aday['cekirdek_puan']==4).sum()} | 3/4: {(aday['cekirdek_puan']==3).sum()}")
    for k in ["K1_roic_wacc", "K2_sna_surdurulebilir", "K3_fd_sna", "K4_daralma_yok"]:
        print(f"  {k}: {int(d.loc[d['eleme']=='', k].fillna(False).sum())} geçti")


if __name__ == "__main__":
    main()
