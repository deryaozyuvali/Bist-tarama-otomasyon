"""
Hendek (rekabet avantajı) + finansal güç taraması
Kaynak: Serkan Ünal, "Borsa İstanbul İçin Hisse Seçim Rehberi" (s. 92-159)

Bu script AŞAMA 1'dir: sadece rakamlarla yapılabilecek kontrolleri yapar.
Faaliyet raporu / dipnot / KAP gerektiren kontroller AŞAMA 2'dir
(bkz. HENDEK_FILTRESI.md).

DÖNEM: Yalnızca enflasyon muhasebeli (TMS 29) dönem kullanılır: 2022-2025.
  - TMS 29, 31.12.2023 tablolarından itibaren zorunlu; 2022 rakamları
    karşılaştırma için geriye dönük düzeltildi.
  - Kitabın "5-10 yıl" önerisi bilerek uygulanmaz; amaç tüm yılların aynı
    muhasebe yöntemiyle hazırlanmış olması (tutarlılık).
  - 2022'de parasal pozisyon kalemi olmayıp sonraki yıllarda olan şirketlerin
    2022 yılı düzeltilmemiş kabul edilir ve atılır.

TUTARLILIK KURALI: Yıllar arasında TL tutar karşılaştırılmaz, çünkü her
yılın rakamı farklı bir tarihin satın alma gücüyle ifade edilmiş olabilir.
Sadece aynı yılın rakamlarından hesaplanan oranlar kullanılır (getiri,
marj, borçluluk, devir hızı, sektör içi pazar payı). Fintables'ın USD
tutarları bu dönemde gerçek kurlarla uyuşmadığı için kullanılmaz.
"""
from pathlib import Path
import numpy as np
import pandas as pd

KLASOR = Path(__file__).resolve().parent
CIKTI = KLASOR.parent / "results" / "temel"

# ── AYARLAR ───────────────────────────────────────────────
TMS29_BASLANGIC = 2022
SON_YIL = 2025
ONCEKI_YIL = SON_YIL - 1
MIN_YIL = 3             # TMS 29 döneminde en az bu kadar yıl verisi gerekir
VERGI = 0.25            # faaliyet kârını vergi sonrasına çevirmek için
REEL_ESIK = 0.05        # sermaye maliyeti yerine kullanılan reel getiri eşiği
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
    f = f[f.yil >= TMS29_BASLANGIC].copy()

    # TMS 29 izi: parasal pozisyon kalemi
    f["tms29_izi"] = f.parasal.fillna(0) != 0
    izli = f.groupby("kod").tms29_izi.any()
    f["tms29_hic_yok"] = f.kod.map(~izli)
    duzeltilmemis_2022 = (f.yil == TMS29_BASLANGIC) & ~f.tms29_izi & ~f.tms29_hic_yok
    f = f[~duzeltilmemis_2022]

    f = f.merge(h[["kod", "sektor", "fiili_dolasim_orani", "piyasa_degeri", "xu100"]],
                on="kod", how="left")
    f = f[~f.sektor.isin(HARIC_SEKTOR) & f.sektor.notna()].copy()
    return f


def yillik_oranlar(f):
    f = f.sort_values(["kod", "yil"]).copy()
    f["yatirilan_sermaye"] = f.ozk.fillna(0) + f.fborc.fillna(0)
    # TMS 29 döneminde rakamlar zaten reel; ek enflasyon düzeltmesi yapılmaz.
    f["roic_reel"] = bol(f.faaliyet * (1 - VERGI), f.yatirilan_sermaye)
    f.loc[f.yatirilan_sermaye <= 0, "roic_reel"] = np.nan
    f["brut_marj"] = bol(f.brut, f.satis)
    f["roa"] = bol(f.net, f.varlik)
    f["cari_oran"] = bol(f.donen, f.kv_yuk)
    f["aktif_devir"] = bol(f.satis, f.varlik)
    f["uv_borc_varlik"] = bol(f.uv_fborc.fillna(0), f.varlik)
    f["fborc_ozk"] = bol(f.fborc.fillna(0), f.ozk)
    f["serbest_nakit_marji"] = bol(f.cfo - (-f.capex.fillna(0)), f.satis)
    return f


# ── GÖSTERGE 1: Pazar payı istikrarı (borsadaki rakiplere göre) ───
def gosterge1(f):
    """Kitap s. 131-136. Pazar payı = şirketin satışı / sektördeki halka açık
    şirketlerin toplam satışı (aynı yıl içinde, birim farkı yok). Sepet,
    TMS 29 döneminin her yılında verisi olan şirketlerden kurulur."""
    yillar = list(range(TMS29_BASLANGIC, SON_YIL + 1))
    p = f[f.satis.gt(0)][["kod", "sektor", "yil", "satis"]]
    tam = p.groupby("kod").yil.nunique()
    sepet = p[p.kod.isin(tam[tam == len(yillar)].index)].copy()
    sepet["pay"] = sepet.satis / sepet.groupby(["sektor", "yil"]).satis.transform("sum")
    sepet = sepet.sort_values(["kod", "yil"])
    sepet["pay_degisim"] = sepet.groupby("kod").pay.diff().abs()
    sepet["sira"] = sepet.groupby(["sektor", "yil"]).satis.rank(ascending=False)
    oyuncu = sepet.groupby("sektor").kod.nunique()

    g = sepet.groupby("kod").agg(
        sektor=("sektor", "first"),
        pazar_payi_ilk=("pay", "first"),
        pazar_payi_son=("pay", "last"),
        pay_ort_mutlak_degisim=("pay_degisim", "mean"),
        lider_yil_sayisi=("sira", lambda s: int((s == 1).sum())),
        son_sira=("sira", "last"),
    )
    g["sektor_oyuncu_sayisi"] = g.sektor.map(oyuncu)
    g["sektor_pay_degisim_ort"] = g.sektor.map(sepet.groupby("sektor").pay_degisim.mean())

    # TMS 29 döneminde borsaya gelip 2025'te sektörde ilk 3'e giren var mı?
    giris = f.groupby("kod").yil.min()
    s = f[f.yil == SON_YIL].copy()
    s["sira"] = s.groupby("sektor").satis.rank(ascending=False)
    yeni_top3 = s[(s.sira <= 3) & s.kod.map(giris).gt(TMS29_BASLANGIC)].groupby("sektor").kod.count()
    g["sektore_yeni_giren_top3"] = g.sektor.map(yeni_top3).fillna(0).astype(int)

    kucuk = g.sektor_oyuncu_sayisi < 3
    g["g1_istikrar"] = (g.pay_ort_mutlak_degisim <= g.sektor_pay_degisim_ort) | \
                       (g.lider_yil_sayisi == len(yillar))
    # "En az sektör kadar hızlı büyüyor mu?" = pazar payı korunmuş/artmış mı
    g["g1_sektorden_hizli"] = g.pazar_payi_son >= g.pazar_payi_ilk
    g["g1_giris_engeli"] = g.sektore_yeni_giren_top3 == 0
    g["g1_puan"] = (g.g1_istikrar.astype(int) + g.g1_sektorden_hizli.astype(int)
                    + g.g1_giris_engeli.astype(int)).astype(float)
    g.loc[kucuk, "g1_puan"] = np.nan   # karşılaştıracak rakip yok → değerlendirilemez
    return g.drop(columns="sektor")


# ── GÖSTERGE 2: Reel kârlılığın sürekliliği ───────────────
def gosterge2(f):
    """Kitap s. 137-146: uzun süreli + reel + faaliyet kaynaklı.
    Kriz yılı sorusu bu dönemde uygulanamaz (2022-2025'te 2018/2020 benzeri
    bir daralma yılı yok), bu yüzden puanlamaya girmez."""
    def tek(d):
        r = d.roic_reel.dropna()
        net = d.net.sum()
        favok = d.favok.sum()
        return pd.Series({
            "veri_yili": d.yil.nunique(),
            "faal_kar_pozitif_yil": int((d.faaliyet > 0).sum()),
            "reel_roic_medyan": r.median(),
            "reel_roic_son": d.loc[d.yil == SON_YIL, "roic_reel"].squeeze() if (d.yil == SON_YIL).any() else np.nan,
            "reel_roic_esik_ustu_oran": (r > REEL_ESIK).mean() if len(r) else np.nan,
            "nakit_donusum": d.cfo.sum() / net if net > 0 else np.nan,
            "parasal_kazanc_net_kar_payi": bol(d.parasal.fillna(0).sum(), net),
            "faal_kar_favok_orani": d.faaliyet.sum() / favok if favok > 0 else np.nan,
            "brut_marj_medyan": d.brut_marj.median(),
            "brut_marj_oynaklik": d.brut_marj.std(),
            "tms29_izi_yok": bool(d.tms29_hic_yok.iloc[0]),
        })
    # Not: oranların toplamı yıllar arası TL toplamıdır; yalnızca aynı oranın
    # pay ve paydası aynı yıllardan geldiği için kabaca tutarlıdır.
    g = f.groupby("kod").apply(tek)
    g["g2_surekli"] = g.faal_kar_pozitif_yil >= g.veri_yili           # hiç zarar yok
    g["g2_reel"] = g.reel_roic_esik_ustu_oran >= 0.7
    g["g2_faaliyet_kaynakli"] = (g.faal_kar_favok_orani.fillna(9) <= 1.1) & \
                                (g.nakit_donusum.fillna(0) >= 0.7)
    g["g2_puan"] = g[["g2_surekli", "g2_reel", "g2_faaliyet_kaynakli"]].sum(axis=1)
    return g


# ── GÖSTERGE 3 (sayısal kısmı): hendeğin gücü ─────────────
def gosterge3(f, g2):
    """Kitabın Gösterge 3'ü niteldir (Aşama 2). Buradaki iki ölçü kitapta
    Gösterge 3 olarak geçmez; marka için 'ölçüt fiyat primidir' (bölüm 5)
    tespitinden türetilmiş yardımcı bilgidir ve gruplamaya etkisi yoktur."""
    son = f[f.yil == SON_YIL][["kod", "sektor"]].set_index("kod")
    d = g2[["brut_marj_medyan", "brut_marj_oynaklik"]].join(son, how="inner")
    d["sektor_brut_marj_medyan"] = d.groupby("sektor").brut_marj_medyan.transform("median")
    d["sektor_oynaklik_medyan"] = d.groupby("sektor").brut_marj_oynaklik.transform("median")
    d["bilgi_fiyat_primi"] = d.brut_marj_medyan > d.sektor_brut_marj_medyan
    d["bilgi_marj_istikrari"] = d.brut_marj_oynaklik <= d.sektor_oynaklik_medyan
    return d[["sektor_brut_marj_medyan", "bilgi_fiyat_primi", "bilgi_marj_istikrari"]]


# ── FİNANSAL GÜÇ: Piotroski F-skoru ───────────────────────
def finansal_guc(f):
    """Kitap s. 155-157. Son yıl ile önceki yıl oranları karşılaştırılır."""
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
    p["finansal_guc"] = (p.piotroski >= 6) & p.borc_ok
    return p


# ── YÖNETİM / BÜYÜME KALİTESİ (bölüm 4) ───────────────────
def yonetim(f):
    def tek(d):
        s = d[d.yil == SON_YIL]
        s = s.squeeze() if len(s) == 1 else None
        return pd.Series({
            "bedelli_artirim_yili": int((d.pay_ihrac.fillna(0) > 0).sum()),
            "temettu_yili": int((d.temettu.fillna(0) < 0).sum()),
            # yıllık serbest nakit marjı ortalaması > 0 → büyümeyi kendi nakdiyle finanse ediyor
            "kendi_kaynagiyla_buyume": bool(d.serbest_nakit_marji.mean() > 0),
            "fborc_ozk_degisim": d.fborc_ozk.iloc[-1] - d.fborc_ozk.iloc[0] if len(d) >= 2 else np.nan,
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
    hendek_tam = (r.g2_puan == 3) & (r.g1_puan.fillna(2) >= 2)
    hendek_kirilgan = ~hendek_tam & (r.g2_puan >= 2)
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
    uyari = []
    for _, x in r.iterrows():
        u = []
        if x.fiili_dolasim_orani > 70: u.append("halka açıklık >%70 (hâkim ortak zayıf)")
        if x.bedelli_artirim_yili >= 2: u.append(f"{int(x.bedelli_artirim_yili)} yıl bedelli artırım")
        if x.parasal_kazanc_net_kar_payi > 0.5: u.append("net kârın çoğu parasal kazanç")
        if x.yp_pozisyon_ozk < -0.3: u.append("yüksek döviz açığı (gelir dövizse sorun değil)")
        if x.faal_kar_favok_orani > 1.1: u.append("faaliyet kârını diğer gelirler şişiriyor")
        if x.kendi_kaynagiyla_buyume is False: u.append("büyümeyi dış kaynakla finanse ediyor")
        if x.sektore_yeni_giren_top3 > 0: u.append("sektöre yeni girenler ilk 3'e yerleşebiliyor")
        if x.tms29_izi_yok: u.append("hiç parasal kalem yok (TMS 29 uygulanmamış olabilir)")
        uyari.append("; ".join(u))
    r["uyarilar"] = uyari
    return r


def main():
    f = yillik_oranlar(yukle())
    yeterli = f.groupby("kod").yil.nunique()
    f = f[f.kod.isin(yeterli[yeterli >= MIN_YIL].index) & f.kod.isin(f[f.yil == SON_YIL].kod)]

    g2 = gosterge2(f)
    r = (f[f.yil == SON_YIL].set_index("kod")[["sektor", "fiili_dolasim_orani", "piyasa_degeri", "xu100"]]
         .join(gosterge1(f)).join(g2).join(gosterge3(f, g2))
         .join(finansal_guc(f)).join(yonetim(f)).join(degerleme(f)))
    r = sinifla(r)
    r["hendek_skoru"] = r.g1_puan.fillna(1.5) + r.g2_puan * 1.5
    r = r.sort_values(["grup", "hendek_skoru", "reel_roic_medyan"], ascending=[True, False, False])

    CIKTI.mkdir(parents=True, exist_ok=True)
    r.round(4).to_csv(CIKTI / "hendek_tarama.csv")
    kisa = r[r.grup.str[0].isin(["A", "B", "D"])]
    kisa[["sektor", "grup", "hendek_skoru", "g1_puan", "g2_puan", "reel_roic_medyan",
          "reel_roic_son", "veri_yili", "pazar_payi_ilk", "pazar_payi_son",
          "piotroski", "net_borc_favok", "pd_dd", "fk", "fd_favok", "uyarilar"]
         ].round(3).to_csv(CIKTI / "hendek_kisa_liste.csv")
    print(r.grup.value_counts().sort_index().to_string())
    print(f"\nToplam taranan: {len(r)}  → kısa liste: {len(kisa)}")


if __name__ == "__main__":
    main()
