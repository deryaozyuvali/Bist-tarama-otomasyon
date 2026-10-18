"""
Hendek (rekabet avantajı) + finansal güç taraması
Kaynak: Serkan Ünal, "Borsa İstanbul İçin Hisse Seçim Rehberi" (s. 92-159)

Bu script AŞAMA 1'dir: sadece rakamlarla yapılabilecek kontrolleri yapar.
Faaliyet raporu / dipnot / KAP gerektiren kontroller AŞAMA 2'dir
(bkz. HENDEK_FILTRESI.md) ve kısa listeye kalan şirketler için elle/Claude
ile yapılır.

Girdi:  veri/finansal_2016_2025.csv  (yıl sonu, konsolide, Fintables)
        veri/hisseler.csv            (sektör, fiili dolaşım, piyasa değeri)
Çıktı:  ../results/temel/hendek_tarama.csv

Önemli muhasebe notu (kitap s. 138-144):
  - 2022 ve sonrası tablolar TMS 29 ile enflasyona göre düzeltilmiş.
    Bu yıllarda rakamlar zaten "reel"dir, üstüne enflasyon düşülmez.
  - 2021 ve öncesi nominaldir. Bu yıllarda getiri, TÜFE'den
    arındırılarak reel hale getirilir: (1+nominal)/(1+TÜFE)-1
  - Net kâr parasal pozisyon kazancı içerir, bu yüzden ana ölçüt
    faaliyet kârı ve nakit üretimidir.
"""
from pathlib import Path
import numpy as np
import pandas as pd

KLASOR = Path(__file__).resolve().parent
CIKTI = KLASOR.parent / "results" / "temel"

# ── AYARLAR ───────────────────────────────────────────────
VERGI = 0.25            # faaliyet kârını vergi sonrasına çevirmek için
REEL_ESIK = 0.05        # sermaye maliyeti yerine kullanılan reel getiri eşiği
KRIZ_YILLARI = [2018, 2020]   # kur krizi, pandemi
SON_YIL = 2025
ONCEKI_YIL = SON_YIL - 1
TMS29_BASLANGIC = 2022
MIN_YIL = 7             # en az bu kadar yıllık veri olmayan şirket değerlendirilmez
# Aralık/Aralık TÜFE (yalnızca 2021 ve öncesi için kullanılır)
TUFE = {2016: 0.0853, 2017: 0.1192, 2018: 0.2030, 2019: 0.1184,
        2020: 0.1460, 2021: 0.3608}
# İş modeli bu testle ölçülemeyen sektörler (yatırım/finans/gayrimenkul)
HARIC_SEKTOR = {"Gayrimenkul", "Holding", "Menkul Kıymet Yat. Ort.",
                "Girişim Sermayesi Yat. Ort.", "Aracı Kurum", "Varlık Yönetimi",
                "Faktoring", "Finansal Kiralama", "Tasarruf Finansman",
                "Bankacılık", "Sigorta", "Emeklilik"}


def bol(a, b):
    with np.errstate(divide="ignore", invalid="ignore"):
        r = a / b
    return r.replace([np.inf, -np.inf], np.nan) if isinstance(r, pd.Series) else r


def yukle():
    f = pd.read_csv(KLASOR / "veri" / "finansal_2016_2025.csv")
    h = pd.read_csv(KLASOR / "veri" / "hisseler.csv")
    f = f.merge(h[["kod", "sektor", "fiili_dolasim_orani", "piyasa_degeri", "xu100"]],
                on="kod", how="left")
    f = f[~f.sektor.isin(HARIC_SEKTOR) & f.sektor.notna()].copy()
    return f, h


def yillik_oranlar(f):
    f = f.sort_values(["kod", "yil"]).copy()
    f["yatirilan_sermaye"] = f.ozk.fillna(0) + f.fborc.fillna(0)
    f["roic_nom"] = bol(f.faaliyet * (1 - VERGI), f.yatirilan_sermaye)
    f.loc[f.yatirilan_sermaye <= 0, "roic_nom"] = np.nan
    tufe = f.yil.map(TUFE)
    f["roic_reel"] = np.where(f.yil >= TMS29_BASLANGIC, f.roic_nom,
                              (1 + f.roic_nom) / (1 + tufe) - 1)
    f["brut_marj"] = bol(f.brut, f.satis)
    f["faal_marj"] = bol(f.faaliyet, f.satis)
    f["roa"] = bol(f.net, f.varlik)
    f["cari_oran"] = bol(f.donen, f.kv_yuk)
    f["aktif_devir"] = bol(f.satis, f.varlik)
    f["uv_borc_varlik"] = bol(f.uv_fborc.fillna(0), f.varlik)
    f["fborc_ozk"] = bol(f.fborc.fillna(0), f.ozk)
    return f


# ── GÖSTERGE 1: Pazar payı istikrarı (borsadaki rakiplere göre) ───
def gosterge1(f):
    """Kitap s. 131-136. Sadece borsadaki rakipler görülebildiği için
    pazar payı = şirketin USD satışı / sektördeki halka açık şirketlerin
    toplam USD satışı. 2018'den beri verisi olan şirketlerle sabit bir
    sepet kurulur ki halka arzlar payları yapay olarak bozmasın."""
    p = f[(f.yil >= 2018) & f.satis_usd.gt(0)][["kod", "sektor", "yil", "satis_usd"]]
    tam = p.groupby("kod").yil.nunique()
    sepet = p[p.kod.isin(tam[tam == SON_YIL - 2018 + 1].index)].copy()
    sepet["pay"] = sepet.satis_usd / sepet.groupby(["sektor", "yil"]).satis_usd.transform("sum")
    sepet = sepet.sort_values(["kod", "yil"])
    sepet["pay_degisim"] = sepet.groupby("kod").pay.diff().abs()
    sepet["sira"] = sepet.groupby(["sektor", "yil"]).satis_usd.rank(ascending=False)
    oyuncu = sepet.groupby("sektor").kod.nunique()

    g = sepet.groupby("kod").agg(
        sektor=("sektor", "first"),
        pazar_payi_son=("pay", "last"),
        pay_ort_mutlak_degisim=("pay_degisim", "mean"),
        lider_yil_sayisi=("sira", lambda s: int((s == 1).sum())),
        son_sira=("sira", "last"),
    )
    g["sektor_oyuncu_sayisi"] = g.sektor.map(oyuncu)
    # sektörün kendi istikrarı (Greenwald-Kahn: tüm oyuncuların ortalaması)
    g["sektor_pay_degisim_ort"] = g.sektor.map(sepet.groupby("sektor").pay_degisim.mean())

    # Reel büyüme: USD satış yıllık bileşik büyüme, sektör medyanına göre
    ilk = f[f.satis_usd.gt(0)].sort_values("yil").groupby("kod").first()
    son = f[(f.yil == SON_YIL) & f.satis_usd.gt(0)].set_index("kod")
    yil_farki = (SON_YIL - ilk.yil).reindex(son.index)
    cagr = (son.satis_usd / ilk.satis_usd.reindex(son.index)) ** (1 / yil_farki) - 1
    cagr = cagr[yil_farki >= 5]
    b = pd.DataFrame({"usd_satis_cagr": cagr, "sektor": son.sektor.reindex(cagr.index)})
    b["sektor_cagr_medyan"] = b.groupby("sektor").usd_satis_cagr.transform("median")
    g = g.join(b[["usd_satis_cagr", "sektor_cagr_medyan"]], how="outer")
    g["sektor"] = g.sektor.fillna(son.sektor)

    # Son 10 yılda sektöre girip ilk 3'e yerleşen yeni oyuncu var mı?
    giris = f.groupby("kod").yil.min()
    s25 = f[f.yil == SON_YIL].copy()
    s25["sira"] = s25.groupby("sektor").satis_usd.rank(ascending=False)
    yeni_top3 = s25[(s25.sira <= 3) & s25.kod.map(giris).gt(2017)].groupby("sektor").kod.count()
    g["sektore_yeni_giren_top3"] = g.sektor.map(yeni_top3).fillna(0).astype(int)

    kucuk = g.sektor_oyuncu_sayisi.fillna(0) < 3
    g["g1_istikrar"] = (g.pay_ort_mutlak_degisim <= g.sektor_pay_degisim_ort) | (g.lider_yil_sayisi >= 5)
    g["g1_sektorden_hizli"] = g.usd_satis_cagr >= g.sektor_cagr_medyan
    g["g1_giris_engeli"] = g.sektore_yeni_giren_top3 == 0
    g["g1_puan"] = (g.g1_istikrar.astype(int) + g.g1_sektorden_hizli.astype(int)
                    + g.g1_giris_engeli.astype(int))
    g.loc[kucuk, "g1_puan"] = np.nan   # karşılaştıracak rakip yok → değerlendirilemez
    return g.drop(columns="sektor")


# ── GÖSTERGE 2: Reel kârlılığın sürekliliği ───────────────
def gosterge2(f):
    """Kitap s. 137-146: uzun süreli + reel + faaliyet kaynaklı."""
    def tek(d):
        d = d.sort_values("yil")
        r = d.roic_reel.dropna()
        son5 = d[d.yil > SON_YIL - 5]
        son3 = d[d.yil > SON_YIL - 3]
        kriz = d[d.yil.isin(KRIZ_YILLARI)]
        net5 = son5.net.sum()
        return pd.Series({
            "veri_yili": d.yil.nunique(),
            "faal_kar_pozitif_yil": int((d.faaliyet > 0).sum()),
            "reel_roic_medyan": r.median(),
            "reel_roic_son": d.loc[d.yil == SON_YIL, "roic_reel"].squeeze() if (d.yil == SON_YIL).any() else np.nan,
            "reel_roic_esik_ustu_oran": (r > REEL_ESIK).mean() if len(r) else np.nan,
            "kriz_yili_faal_kar_pozitif": bool(len(kriz) and (kriz.faaliyet > 0).all()),
            "nakit_donusum_5y": bol(son5.cfo.sum(), net5) if net5 > 0 else np.nan,
            "parasal_kazanc_net_kar_payi_3y": bol(son3.parasal.fillna(0).sum(), son3.net.sum()),
            "diger_faal_gelir_payi_3y": bol(son3.dig_fg.fillna(0).sum(), son3.faaliyet.sum()),
            # faaliyet kârı FAVÖK'ü aşıyorsa kârı kur farkı vb. diğer gelirler şişiriyor
            "faal_kar_favok_orani_3y": bol(son3.faaliyet.sum(), son3.favok.sum()) if son3.favok.sum() > 0 else np.nan,
            "brut_marj_medyan": d.brut_marj.median(),
            "brut_marj_oynaklik": d.brut_marj.std(),
        })
    g = f.groupby("kod").apply(tek)
    g["g2_surekli"] = g.faal_kar_pozitif_yil >= g.veri_yili           # hiç zarar yok
    g["g2_reel"] = g.reel_roic_esik_ustu_oran >= 0.7
    # Parasal kazanç burada eleme sebebi değil: getiri zaten faaliyet kârıyla
    # ölçülüyor (kitap s. 141, parasal kalem faaliyet kârından ayrı tutulur).
    g["g2_faaliyet_kaynakli"] = (g.faal_kar_favok_orani_3y.fillna(9) <= 1.1) & \
                                (g.nakit_donusum_5y.fillna(0) >= 0.7)
    g["g2_kriz"] = g.kriz_yili_faal_kar_pozitif.astype(bool)
    g["g2_puan"] = g[["g2_surekli", "g2_reel", "g2_faaliyet_kaynakli", "g2_kriz"]].sum(axis=1)
    return g


# ── GÖSTERGE 3 (sayısal kısmı): hendeğin gücü ─────────────
def gosterge3(f, g2):
    """Kitap s. 146-153. Avantajın kaynağı, teknoloji riski, düzenleme ve
    nesil geçişi niteldir (Aşama 2). Burada sadece izini sürebildiğimiz
    fiyat primi (brüt marj sektörün üstünde mi) ve marj istikrarına bakılır."""
    son = f[f.yil == SON_YIL][["kod", "sektor"]].set_index("kod")
    d = g2[["brut_marj_medyan", "brut_marj_oynaklik"]].join(son, how="inner")
    d["sektor_brut_marj_medyan"] = d.groupby("sektor").brut_marj_medyan.transform("median")
    d["sektor_oynaklik_medyan"] = d.groupby("sektor").brut_marj_oynaklik.transform("median")
    d["g3_fiyat_primi"] = d.brut_marj_medyan > d.sektor_brut_marj_medyan
    d["g3_marj_istikrari"] = d.brut_marj_oynaklik <= d.sektor_oynaklik_medyan
    d["g3_puan"] = d.g3_fiyat_primi.astype(int) + d.g3_marj_istikrari.astype(int)
    return d[["sektor_brut_marj_medyan", "g3_fiyat_primi", "g3_marj_istikrari", "g3_puan"]]


# ── FİNANSAL GÜÇ: Piotroski F-skoru + kitabın ek kontrolleri ──
def finansal_guc(f):
    """Kitap s. 155-157. Son yıl ile önceki yıl karşılaştırılır; ikisi de
    TMS 29'lu olduğu için aynı ölçü birimindedir (kitabın uyarısı)."""
    a = f[f.yil == SON_YIL].set_index("kod")
    b = f[f.yil == ONCEKI_YIL].set_index("kod").reindex(a.index)
    p = pd.DataFrame(index=a.index)
    p["f1_net_kar_pozitif"] = a.net > 0
    p["f2_faal_nakit_pozitif"] = a.cfo > 0
    p["f3_roa_artti"] = a.roa > b.roa
    p["f4_nakit_kardan_buyuk"] = a.cfo > a.net
    p["f5_uv_borc_azaldi"] = a.uv_borc_varlik <= b.uv_borc_varlik
    p["f6_cari_oran_artti"] = a.cari_oran > b.cari_oran
    p["f7_hisse_ihraci_yok"] = a.pay_ihrac.fillna(0) <= 0
    p["f8_brut_marj_artti"] = a.brut_marj > b.brut_marj
    p["f9_aktif_devir_artti"] = a.aktif_devir > b.aktif_devir
    p["piotroski"] = p.sum(axis=1)

    p["net_borc_favok"] = bol(a.net_borc, a.favok)
    p["fborc_ozk"] = a.fborc_ozk
    p["yp_pozisyon_ozk"] = bol(a.yp_poz, a.ozk)
    p["borc_ok"] = (a.net_borc.fillna(0) <= 0) | (p.net_borc_favok.between(0, 2.5))
    p["kur_ok"] = p.yp_pozisyon_ozk.fillna(0) > -0.3
    # Döviz açığı uyarı olarak raporlanır; ihracatçılarda gelir de dövizdir.
    p["finansal_guc"] = (p.piotroski >= 6) & p.borc_ok
    return p


# ── YÖNETİM / BÜYÜME KALİTESİ (bölüm 4) ───────────────────
def yonetim(f):
    def tek(d):
        son = d[d.yil == SON_YIL]
        tms = d[d.yil >= TMS29_BASLANGIC]
        cfo = d.cfo.sum()
        capex = -d.capex.fillna(0).sum()
        s = son.squeeze() if len(son) == 1 else None
        return pd.Series({
            "bedelli_artirim_yili": int((d.pay_ihrac.fillna(0) > 0).sum()),
            "temettu_yili": int((d.temettu.fillna(0) < 0).sum()),
            "kendi_kaynagiyla_buyume": cfo > capex,           # birikimli SNA > 0
            "fborc_ozk_degisim_2022_son": (tms.fborc_ozk.iloc[-1] - tms.fborc_ozk.iloc[0]) if len(tms) >= 2 else np.nan,
            "tedarikci_finansmani": bool(s is not None and
                                         (s.tic_borc - s.tic_alacak - s.stok) > 0),
        })
    return f.groupby("kod").apply(tek)


def degerleme(f):
    a = f[f.yil == SON_YIL].set_index("kod")
    return pd.DataFrame({"pd_dd": bol(a.piyasa_degeri, a.ozk),
                         "fk": bol(a.piyasa_degeri, a.net).where(a.net > 0),
                         "fd_favok": bol(a.piyasa_degeri + a.net_borc.fillna(0), a.favok).where(a.favok > 0)})


def sinifla(r):
    """Kitap s. 157-159: dört olasılık."""
    hendek_tam = (r.g2_puan == 4) & (r.g1_puan.fillna(2) >= 2)
    hendek_kirilgan = ~hendek_tam & (r.g2_puan >= 3)
    r["hendek"] = np.select([hendek_tam, hendek_kirilgan], ["VAR", "KIRILGAN"], "YOK")
    guc = r.finansal_guc.fillna(False).astype(bool)
    r["grup"] = np.select(
        [(r.hendek == "VAR") & guc,
         (r.hendek == "KIRILGAN") & guc,
         (r.hendek == "YOK") & guc,
         (r.hendek != "YOK") & ~guc],
        ["A - Korunaklı + güçlü (portföy çekirdeği)",
         "B - Kırılgan hendek + güçlü (güvenlik marjı iste, küçük pozisyon)",
         "C - Hendeksiz + güçlü (sadece ucuzsa, ortalamaya dönüş)",
         "D - Hendek var ama finansal güç yok (en tehlikeli, izle)"],
        "E - Hendeksiz + zayıf (işimiz yok)")
    # Bölüm 2 eleme notları (rakamla görülebilenler)
    uyari = []
    for _, x in r.iterrows():
        u = []
        if x.fiili_dolasim_orani > 70: u.append("halka açıklık >%70 (hâkim ortak zayıf)")
        if x.bedelli_artirim_yili >= 2: u.append(f"{int(x.bedelli_artirim_yili)} yıl bedelli artırım")
        if x.parasal_kazanc_net_kar_payi_3y > 0.5: u.append("net kârın çoğu parasal kazanç")
        if x.yp_pozisyon_ozk < -0.3: u.append("yüksek döviz açığı (gelir dövizse sorun değil)")
        if x.faal_kar_favok_orani_3y > 1.1: u.append("faaliyet kârını diğer gelirler şişiriyor")
        if x.kendi_kaynagiyla_buyume is False: u.append("büyümeyi dış kaynakla finanse ediyor")
        if x.sektore_yeni_giren_top3 > 0: u.append("sektöre yeni girenler ilk 3'e yerleşebiliyor")
        uyari.append("; ".join(u))
    r["uyarilar"] = uyari
    return r


def main():
    f, h = yukle()
    f = yillik_oranlar(f)
    yeterli = f.groupby("kod").yil.nunique()
    f = f[f.kod.isin(yeterli[yeterli >= MIN_YIL].index) & f.kod.isin(f[f.yil == SON_YIL].kod)]

    g2 = gosterge2(f)
    r = (f[f.yil == SON_YIL].set_index("kod")[["sektor", "fiili_dolasim_orani", "piyasa_degeri", "xu100"]]
         .join(gosterge1(f)).join(g2).join(gosterge3(f, g2))
         .join(finansal_guc(f)).join(yonetim(f)).join(degerleme(f)))
    r = sinifla(r)
    r["hendek_skoru"] = r.g1_puan.fillna(1.5) + r.g2_puan * 1.5 + r.g3_puan
    r = r.sort_values(["grup", "hendek_skoru", "reel_roic_medyan"], ascending=[True, False, False])

    CIKTI.mkdir(parents=True, exist_ok=True)
    r.round(4).to_csv(CIKTI / "hendek_tarama.csv")
    kisa = r[r.grup.str[0].isin(["A", "B", "D"])]
    kisa[["sektor", "grup", "hendek_skoru", "reel_roic_medyan", "reel_roic_son",
          "faal_kar_pozitif_yil", "veri_yili", "usd_satis_cagr", "pazar_payi_son",
          "piotroski", "net_borc_favok", "pd_dd", "fk", "fd_favok", "uyarilar"]
         ].round(3).to_csv(CIKTI / "hendek_kisa_liste.csv")
    print(r.grup.value_counts().sort_index().to_string())
    print(f"\nToplam taranan: {len(r)}  → kısa liste: {len(kisa)}")


if __name__ == "__main__":
    main()
