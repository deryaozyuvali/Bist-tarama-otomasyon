"""
Temel analiz ÖN ELEME taraması.

Kaynak: Bir yatırımcının "şirket incelerken nelere dikkat ediyorum" videosu.
Burada sadece VERİDEN OTOMATİK hesaplanabilen kısmı var. Videodaki elle
bakılacak maddeler (patron tipi, genel müdür mesajı, Çin rekabeti, hendek,
ilişkili taraf dipnotları, huzur hakkı, vakıf bağışı...) bu script'in
kapsamında değil. Çıktıdaki "elle_bak" kolonu bunları hatırlatır.

ÇEKİRDEK 4 KRİTER (videoda "bu dördü tutuyorsa yatırım sinyalleri başlıyor"):
  K1  ROIC > WACC
  K2  Pozitif serbest nakit akışı, sürdürülebilir (tek yıl değil): kayan 12 aylık
      pencereler (son dönem TTM + 1 ve 2 yıl önceki aynı dönem), son >0 ve en az 2/3 >0
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


IKON = {"TUTTU": "✓", "KISMEN": "~", "TUTTURAMADI": "✗"}


def guidance_ozet():
    """Şirketlerin açıkladığı beklentiler (EVO guidance) ve gerçekleşenle karşılaştırma.
    Değerlendirme temel/guidance_degerlendirme.csv'de elle yapıldı (gerekçeli). ELEME KRİTERİ DEĞİL."""
    ham = os.path.join(HAM, "guidance_ham.csv")
    deg = os.path.join(os.path.dirname(__file__), "guidance_degerlendirme.csv")
    if not os.path.exists(ham):
        return pd.DataFrame(columns=["kod"])
    g = pd.read_csv(ham).groupby("kod")["yil"].apply(lambda x: ",".join(str(int(v)) for v in sorted(x))).rename("guidance_yillari").reset_index()
    g["guidance_var"] = True
    if os.path.exists(deg):
        e = pd.read_csv(deg).sort_values(["kod", "yil"])
        kar = e.groupby("kod").apply(lambda t: " · ".join(f"{y} {IKON[r]}" for y, r in zip(t.yil, t.sonuc))).rename("guidance_karne")
        son = e.groupby("kod")["sonuc"].apply(lambda x: "|".join(x.tail(2))).rename("guidance_son_sonuclar")
        g = g.merge(kar.reset_index(), on="kod", how="left").merge(son.reset_index(), on="kod", how="left")
    return g


def yukle():
    g = pd.read_csv(os.path.join(HAM, "gelir.csv"))
    na = pd.read_csv(os.path.join(HAM, "nakit.csv"))
    b = pd.read_csv(os.path.join(HAM, "bilanco.csv"))
    p = pd.read_csv(os.path.join(HAM, "piyasa.csv"))
    d = g.merge(na, on="kod", how="left").merge(b, on="kod", how="left").merge(p, on="kod", how="left")
    am = os.path.join(HAM, "amortisman.csv")
    if os.path.exists(am):
        d = d.merge(pd.read_csv(am), on="kod", how="left")
    d = d.merge(guidance_ozet(), on="kod", how="left")
    ic = os.path.join(HAM, "kap", "icerden_ozet.csv")
    if os.path.exists(ic):
        d = d.merge(pd.read_csv(ic), on="kod", how="left")
    # Azınlık hakları: kâr payı dağıtım tablosu (imtiyaz, bağış, YK/çalışan payı) + üst yönetim ücretleri
    kp = os.path.join(HAM, "azinlik", "karpayi_ozet.csv")
    if os.path.exists(kp):
        k = pd.read_csv(kp)[["kod", "tarih", "imtiyaz_beyan", "imtiyazli_kar_payi", "bagis", "bagis_net_kar_orani",
                              "yk_calisan_kar_payi", "yk_calisan_net_kar_orani", "grup_farkli", "tablo_tutarsiz"]]
        d = d.merge(k.rename(columns={"tarih": "karpayi_tablo_tarihi"}), on="kod", how="left")
    yu = os.path.join(HAM, "azinlik", "yonetici_ucret.csv")
    if os.path.exists(yu):
        d = d.merge(pd.read_csv(yu)[["kod", "yonetici_fayda_tl", "huzur_hakki_tl"]], on="kod", how="left")
    # İlişkili taraf değerlendirmesi (elle, kaynaklı): temel/iliskili_degerlendirme.csv
    it = os.path.join(os.path.dirname(__file__), "iliskili_degerlendirme.csv")
    if os.path.exists(it):
        e = pd.read_csv(it)
        e["satir"] = e["kategori"] + "|" + e["siddet"] + "|" + e["aciklama"]
        d = d.merge(e.groupby("kod")["satir"].apply(lambda x: "\n".join(x)).rename("iliskili_kayit").reset_index(),
                    on="kod", how="left")
    for c in d.columns:
        if c in ("iliskili_kayit",):
            continue
        if c in ("imtiyaz_beyan", "karpayi_tablo_tarihi", "grup_farkli", "tablo_tutarsiz"):
            continue
        if c in ("icerden_kimler", "guidance_var", "guidance_yillari", "guidance_karne", "guidance_son_sonuclar"):
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
    # CAPEX TTM boşsa sıfır sayma: bakım yatırımı için amortismanı kullan (ihtiyatlı) ve işaretle
    d["capex_eksik"] = d["capex"].isna() & d["cfo"].notna()
    bakim_capex = bakim_capex.where(~d["capex_eksik"], amort.clip(lower=0))
    d["sna_ham"] = d["cfo"] - capex - kira
    d["sna_bakim"] = d["cfo"] - bakim_capex - kira
    d["buyume_capex"] = capex - bakim_capex
    # Belgeyle kanıtlı SNA düzeltmeleri (imtiyaz yatırımı, gizli tedarikçi finansmanı): temel/sna_duzeltme.csv
    dz = os.path.join(os.path.dirname(__file__), "sna_duzeltme.csv")
    d["sna_duzeltme"] = ""
    if os.path.exists(dz):
        for _, k in pd.read_csv(dz).iterrows():
            m = d["kod"] == k["kod"]
            d.loc[m, "sna_bakim"] = k["sna_duzeltilmis_tl"]
            d.loc[m, "sna_ham"] = np.minimum(d.loc[m, "sna_ham"], k["sna_duzeltilmis_tl"])
            d.loc[m, "sna_duzeltme"] = k["gerekce"]

    # SNA sürdürülebilirliği: kayan 12 aylık pencereler (son dönem TTM, 1 ve 2 yıl önceki aynı dönem TTM).
    # Her pencere kendi döneminin TL'siyle (TMS 29) => yalnız işaret karşılaştırılır. Boş pencere sıfır sayılmaz.
    # Not: EVO'da 2023/9 TTM tüm şirketlerde boş; bu yüzden en fazla 3 pencere var.
    pf = os.path.join(os.path.dirname(__file__), "ham", "sna_pencere.csv")
    pen = pd.read_csv(pf)
    pen = pen[pen["cfo"].notna()].copy()
    p_capex, p_kira = -pen["capex"].fillna(0), -pen["kira"].fillna(0)
    p_am = pen["amort"].where(pen["amort"] > 0, p_capex)
    p_bakim = np.minimum(p_capex, p_am).where(pen["capex"].notna(), pen["amort"].clip(lower=0).fillna(0))
    pen["sna"] = pen["cfo"] - p_bakim - p_kira
    pen["capex_eksik"] = pen["capex"].isna()
    pen = pen.sort_values(["kod", "yil"], ascending=[True, False])
    pen["sira"] = pen.groupby("kod").cumcount()           # 0 = son pencere
    pv = pen.pivot(index="kod", columns="sira", values="sna")
    etk = pen.pivot(index="kod", columns="sira", values="yil")
    for i in range(3):
        d[f"sna_p{i}"] = d["kod"].map(pv[i]) if i in pv else np.nan
        d[f"sna_p{i}_donem"] = d["kod"].map(etk[i]) if i in etk else np.nan
    d["sna_pencere_ay"] = d["kod"].map(pen.groupby("kod")["ay"].first())
    d["sna_p0"] = d["sna_bakim"].where(d["sna_bakim"].notna(), d["sna_p0"])  # son pencere = belge düzeltmeli TTM
    pcols = ["sna_p0", "sna_p1", "sna_p2"]
    d["capex_eksik_pencere"] = d["kod"].map(pen.groupby("kod")["capex_eksik"].sum()).fillna(0).astype(int)
    d["sna_veri_yil"] = d[pcols].notna().sum(axis=1)
    d["sna_pozitif_yil"] = (d[pcols] > 0).sum(axis=1)

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
    d["K2_sna_surdurulebilir"] = (d["sna_bakim"] > 0) & (d["sna_pozitif_yil"] >= 2) & (d["sna_veri_yil"] >= 2)
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
    bayrak, arti, elle, notlar = [], [], [], []
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
        if r.get("sna_duzeltme"):
            f.append("SNA belgeyle düzeltildi: " + r["sna_duzeltme"][:120])
        if r.get("capex_eksik") or r.get("capex_eksik_pencere", 0) > 0:
            f.append("CAPEX TTM verisi eksik (bakım yatırımı = amortisman varsayıldı; elle kontrol)")
        neg = [f"{int(r[f'sna_p{i}_donem'])}/{int(r['sna_pencere_ay'])}" for i in (1, 2)
               if pd.notna(r.get(f"sna_p{i}")) and r[f"sna_p{i}"] <= 0 and pd.notna(r.get(f"sna_p{i}_donem"))]
        if neg and r["sna_bakim"] > 0:
            f.append("SNA geçmiş penceresi negatif: " + ", ".join(neg) + " (12 aylık)")
        if 0.08 <= r["roic"] <= 0.12:
            f.append(f"ROIC sınırda (%{r['roic']*100:.1f}; WACC varsayımı %{wacc*100:.0f}, tanıma duyarlı)")
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

        # Guidance (eleme değil, yorum)
        son2 = str(r.get("guidance_son_sonuclar") or "").split("|")
        if len(son2) == 2 and all(x == "TUTTURAMADI" for x in son2):
            f.append(f"beklentileri üst üste 2 yıl tutturamadı ({r.get('guidance_karne')})")

        # Azınlık hakları (KAP kâr payı tablosu + 2025/12 dipnot "üst düzey yöneticilere sağlanan faydalar")
        if r.get("imtiyazli_kar_payi", 0) > 0:
            o_imt = r["imtiyazli_kar_payi"] / r["ana_kar"] if r["ana_kar"] > 0 else np.nan
            isaret = "⚠ " if (pd.isna(o_imt) or o_imt >= 0.05) else ""
            f.append(f"{isaret}kâr payı imtiyazı: imtiyazlı paylara {r['imtiyazli_kar_payi']/1e6:,.1f} mn TL ayrıldı "
                     f"(net kârın %{o_imt*100:.1f}'i)")
        elif r.get("grup_farkli") is True:
            f.append("pay grupları arasında farklı kâr payı (imtiyaz olabilir, elle bak)")
        if r.get("bagis_net_kar_orani", 0) >= 0.05:
            f.append(f"yüksek bağış: {r['bagis']/1e6:,.1f} mn TL = net kârın %{r['bagis_net_kar_orani']*100:.0f} kadarı → alıcı patronun vakfı mı? elle bak")
        if r.get("yk_calisan_kar_payi", 0) > 0:
            f.append(f"kârdan YK/çalışanlara pay ({r['yk_calisan_kar_payi']/1e6:,.1f} mn TL)")
        yf = r.get("yonetici_fayda_tl")
        if pd.notna(yf) and yf > 0:
            o_net = yf / r["ana_kar"] if r["ana_kar"] > 0 else np.nan
            o_esas = yf / r["esas_faal_kar"] if r["esas_faal_kar"] > 0 else np.nan
            ors = [x for x in (o_net, o_esas) if pd.notna(x)]
            if ors and min(ors) >= 0.10:
                f.append(f"üst yönetim ücret/huzur hakkı kâra göre yüksek ({yf/1e6:,.0f} mn TL; "
                         f"net kâr oranı {_f(o_net, True) if pd.notna(o_net) else 'net zarar'}, esas faaliyet kârı oranı {_f(o_esas, True)})")

        # İlişkili taraf (videodaki: patronun şirketinden satın alma, ana ortağa borç/teminat, çok fazla grup içi işlem)
        iliskili_not = []
        ETIKET = {"ana_ortaga_borc": "ana ortağa/ortaklara borç", "gruba_ticari_olmayan_alacak": "gruba ticari olmayan alacak", "gruba_ticari_alacak": "gruptan yüksek ticari alacak",
                  "ana_ortak_lehine_teminat": "ana ortak/grup lehine teminat", "iliskili_taraftan_satin_alma": "ilişkili taraftan satın alma",
                  "yaygin_surekli_islem": "grup içi işlem ≥%10 (SPK m.10)"}
        for satir in str(r.get("iliskili_kayit") or "").split("\n"):
            if not satir or satir == "nan":
                continue
            kat, sid, acik = satir.split("|", 2)
            metin = f"{ETIKET.get(kat, kat)}: {acik}"
            if sid == "yuksek":
                f.append("⚠ İLİŞKİLİ TARAF – " + metin)
            elif sid == "orta" or kat == "iliskili_taraftan_satin_alma":
                f.append("ilişkili taraf – " + metin)
            else:
                iliskili_not.append(metin)
        notlar.append(" | ".join(iliskili_not))

        # artılar
        if r.get("guidance_var") is True or r.get("guidance_var") == "True":
            if len(son2) == 2 and all(x == "TUTTU" for x in son2):
                a.append(f"beklenti açıklıyor ve son 2 yıl tutturdu ({r.get('guidance_karne')})")
            else:
                karne = r.get("guidance_karne")
                a.append("beklenti (guidance) açıklıyor" + (f" ({karne})" if isinstance(karne, str) else " (henüz ölçülebilir yıl yok)"))
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
    d["yonetici_net_kar"] = oran(d.get("yonetici_fayda_tl"), d["ana_kar"]) if "yonetici_fayda_tl" in d else np.nan
    d["iliskili_notlar"] = notlar
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
    "roic", "fd_sna", "fd_sna_kira_haric", "fd_sna_ham", "sna_pozitif_yil", "sna_veri_yil", "sna_p0", "sna_p1", "sna_p2",
    "satis_usd_buyume", "brut_usd_buyume", "brut_marj", "brut_marj_sektor_yuzdelik",
    "fd_favok", "fd_favok_kira", "fk", "pd_dd", "net_borc_favok",
    "cari_oran", "asit_test", "nakit_oran", "alacak_borc",
    "piyasa_degeri", "fd", "sna_bakim", "sna_ham", "buyume_capex", "esas_faal_kar", "favok",
    "icerden_net_sermaye_yuzde", "icerden_net_tl_yaklasik", "patron_satisi",
    "guidance_var", "guidance_yillari", "guidance_karne",
    "imtiyaz_beyan", "imtiyazli_kar_payi", "bagis_net_kar_orani", "yk_calisan_kar_payi", "yonetici_fayda_tl", "yonetici_net_kar",
    "bayrak_sayisi", "kirmizi_bayraklar", "artilar", "iliskili_notlar", "sektor_notu", "eleme",
]

ELLE_BAK = (
    "Elle bak (otomatik değil): faaliyet raporu + genel müdür mesajı; patron tipi ve "
    "patron satışının gerekçesi; bağışın alıcısı (vakıf?); "
    "ilişkili taraf bayrağı olanlarda karşı taraf ve gerekçe; GYO'da ilişkili tarafa verilen kira; Çin rekabeti; giriş bariyeri/hendek; analist toplantısı; "
    "'neden ucuz?' sorusu; karar verdikten sonra 1 hafta bekle. (Otomatik eklenenler: KAP patron alım/satımı, guidance karnesi, kâr payı imtiyazı/bağış/YK payı, üst yönetim ücretleri, ilişkili taraf işlemleri.)"
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


def _guid(r):
    if not (r.get("guidance_var") is True or r.get("guidance_var") == "True"):
        return "–"
    k = r.get("guidance_karne")
    return k if isinstance(k, str) else f"var ({r.get('guidance_yillari')})"


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
          "her aday için elle bakılacaklar en altta.", "",
          "> K2 (SNA sürdürülebilirliği) kayan 12 aylık pencerelerle ölçülür: son dönem TTM ile 1 ve 2 yıl önceki "
          "aynı dönemin TTM'i; son >0 ve en az 2/3 >0. Pencereler farklı dönem TL'si (TMS 29) olduğundan yalnız işaret "
          "karşılaştırılır. 'SNA+ pencere' kolonu pozitif/mevcut pencere sayısıdır.", ""]
    for puan, baslik in [(4, "Liste A — 4/4 kriter"), (3, "Liste B — 3/4 kriter")]:
        t = aday[aday["cekirdek_puan"] == puan]
        L += [f"## {baslik} ({len(t)})", "",
              "| Kod | Sektör | Eksik kriter | ROIC | FD/SNA | SNA+ pencere | USD satış büyüme | Brüt marj | FD/FAVÖK | Patron 12 ay | Guidance | Bayrak |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for _, r in t.iterrows():
            eksik = ", ".join(k[:2] for k in ["K1_roic_wacc", "K2_sna_surdurulebilir", "K3_fd_sna", "K4_daralma_yok"] if not r[k]) or "–"
            L.append(f"| {r['kod']} | {r['sektor']} | {eksik} | {_f(r['roic'], True)} | {_f(r['fd_sna'])} | "
                     f"{int(r['sna_pozitif_yil'])}/{int(r['sna_veri_yil'])} | {_f(r['satis_usd_buyume'], True)} | "
                     f"{_f(r['brut_marj'], True)} | {_f(r['fd_favok'])} | {_patron(r)} | {_guid(r)} | {int(r['bayrak_sayisi'])} |")
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
          "## Guidance (şirketin açıkladığı beklentiler) hakkında", "",
          "Kaynak: EVO guidance tablosu. ELEME KRİTERİ DEĞİL. Beklenti açıklamak artı olarak yazılır; son iki "
          "değerlendirilebilir yılda üst üste TUTTURAMADI ise bayrak. ✓ tuttu, ~ kısmen, ✗ tutturamadı. Ana finansal "
          "hedefler (ciro/gelir, FAVÖK/marj, net kâr) belirleyici; hacim/mağaza gibi operasyonel hedefler ikincil. "
          "Yıl içinde revize edilen hedeflerde ilk açıklanan hedef esas alındı (revizyon not edildi). Gerekçeler: "
          "`temel/guidance_degerlendirme.csv`. Videoda: 'Her sene yüksek beklenti açıklıyor, her sene tutturamıyor ... "
          "bunlara bulaşılmaz.' 2026 beklentileri yıl bitmediği için değerlendirilmedi.", "",
          "## Azınlık hakları (kâr payı imtiyazı, bağış, huzur hakkı) hakkında", "",
          "ELEME KRİTERİ DEĞİL, bayrak. Kaynak 1: KAP 'Kâr Payı Dağıtım Tablosu' (her şirketin en son tablosu) → "
          "imtiyazlı pay sahiplerine ayrılan kâr payı, bağışlar, YK üyelerine/çalışanlara kârdan pay. Bağış eşiği: net "
          "dönem kârının ≥%5'i (TMS 29 nedeniyle SPK ve yasal kârdan büyüğü payda). Bağışın kime gittiği (patronun "
          "vakfı mı?) tablodan görülmez, genel kurul/faaliyet raporundan elle okunmalı. Kaynak 2: 2025/12 finansal rapor "
          "dipnotu 'üst düzey yöneticilere sağlanan faydalar' (ücret + huzur hakkı + prim; adayların 55'inde bulundu, "
          "elle okundu; 'bin TL' raporlayanlar TL'ye çevrildi). Bayrak: hem son 12 ay net kârın hem esas faaliyet "
          "kârının ≥%10'u (biri zarardaysa diğeri). Holdinglerde esas faaliyet kârı küçük görünür, ölçek için elle bak. "
          "Ham veri: `temel/ham/azinlik/`.", "",
          "## İlişkili taraflar hakkında", "",
          "ELEME KRİTERİ DEĞİL, bayrak. Videoda: 'Kendi başka şirketini satın alıyor ... ilişkili taraftan satın alım varsa "
          "iyi olma ihtimali %5-%10', 'Ana ortağa durduk yere borç veriyorsa, teminat veriyorsa uzak duruyorum', 'Çok fazla "
          "işlem varsa kaçıyorum' ve değerleme raporunu Big Four dışı biri yazdıysa sorgula. Kaynaklar (son 3 yıl, adaylar): "
          "KAP 'İlişkili Taraf İşlemleri' (SPK II-17.1 m.9/m.10), KAP 'Finansal/Maddi Duran Varlık Edinimi' (karşı taraf "
          "ilişkili = Evet), 2025/12 dipnot TRİ tablosu (ana ortak/grup lehine teminat) ve bilançodaki 'ilişkili taraflardan "
          "diğer alacaklar'. ⚠ = yüksek (ana ortağa borç ≥ özkaynağın %10'u, ana ortak lehine büyük kefalet, özkaynağın "
          "%10'undan büyük ilişkili taraftan alım). Grup içi ≥%10 işlemler sadece not (iliskili_notlar sütunu). Tamamı elle "
          "okundu, kaynak bildirim no'ları: `temel/iliskili_degerlendirme.csv`. Yüzde 100 bağlı ortaklıkla işlemler sayılmadı.", "",
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
