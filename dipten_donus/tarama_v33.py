"""Dipten Dönüş Filtresi v3.3 — sayısal ön tarama (pilot).

Kural metni: docs/dipten-donus-v3.3.md

Girdiler (repoya konmaz; yerel dosya yolları argüman olarak verilir):
  --evo       Evo'dan çekilmiş geniş tablo (kod başına bir satır; st/sq/bt/bq/ot/oq/ft/fq/it/iq + YYMM,
              nb (net borç), co/no (cari/nakit oran), pd (piyasa değeri, mn TL), sek (sektör id))
  --master    FCF_MASTER.xlsx'ten çıkarılmış FCF satırları (kod, donem, fcf_ttm, statu, ...)
  --evren     BIST_EFK_FCF_Genis_Evren_Tarama CSV'si (master kapsam sınıflaması)
  --sektor    Evo sektör id → ad eşlemesi (CSV: id,baslik)
  --cikti     Çıktı klasörü

Tüm tutarlar mn TL. Marjlar oran (0.05 = %5). 1 bps = 0.0001.
"""
import argparse
import csv
import json
import os
from statistics import median

DONEMLER = [202303, 202306, 202309, 202312, 202403, 202406, 202409, 202412, 202503, 202506, 202509, 202512, 202603, 202606]

# PİLOT eşikler (v3.3). Sonuca bakılarak değiştirilmez.
P = {
    "dip_A_bps": 150, "dip_B_oran": 0.25, "dip_C_oran": 0.10, "dip_D_bps": 200,
    "sinyal_q_bps": 50, "sinyal_ttm_bps": 100,
    "seri_uyari_kat": 2.5,        # yalnızca İNCELEME UYARISI; veri kesilmez (kosu 2)
    "ceyrek_tutarlilik": 0.02,    # 4 çeyrek toplamı ile TTM farkı toleransı (tutarlılık kontrolü, kanıt değil)
    "ifna_mutabakat_esik": 0.10,  # Evo İFNA ile FCF_MASTER CFO farkı
    "on_puan_kuyruk": 35,
    "emsal_min": 5,
}
BPS = 0.0001

KAPSAM_DISI_SEKTOR = {3, 4, 6, 23, 24, 25, 26, 27, 33, 35, 36, 39, 49}

# FCF_MASTER NOTLAR ("Spor kulüpleri"): mali yıl Haziran/Mayıs, takvim TTM'i yok.
TAKVIM_DISI_MALI_YIL = {"BJKAS", "FENER", "GSRAY", "TSPOR", "KAYSE", "MERKO"}

# Karşılaştırılabilirliği doğrulanamayan çeyrekler (2023/12 öncesi; kaynak istisnası açık)
DOGRULANAMAYAN_CEYREK = {202303, 202306, 202309}

# Ön puan satırları ve azami puanları (sabit 65)
ON_PUAN_SATIRLARI = {"A1": 10, "A2": 5, "A3": 5, "A4": 5, "A5": 5, "B1": 10, "B2": 5, "B4": 5,
                     "C1": 5, "D1": 5, "D3": 5}
TUM_SATIRLAR = {"A1": 10, "A2": 5, "A3": 5, "A4": 5, "A5": 5, "B1": 10, "B2": 5, "B3": 5, "B4": 5,
                "C1": 5, "C2": 5, "C3": 5, "C4": 5, "D1": 5, "D2": 5, "D3": 5, "E1": 5, "E2": 5}


def f(x):
    if x is None:
        return None
    x = str(x).strip()
    if x in ("", "None", "nan"):
        return None
    try:
        return float(x)
    except ValueError:
        return None


def ddiv(a, b):
    if a is None or b is None or b <= 0:
        return None
    return a / b


def donem_str(p):
    return f"{p // 100}/{p % 100:02d}"


class Seri:
    """Bir şirketin 2023/12–2026/06 TTM ve çeyreklik serileri."""

    def __init__(self, row):
        self.r = row
        g = lambda k, p: f(row.get(f"{k}{p % 10000}"))
        self.st = [g("st", p) for p in DONEMLER]
        self.sq = [g("sq", p) for p in DONEMLER]
        self.bt = [g("bt", p) for p in DONEMLER]
        self.bq = [g("bq", p) for p in DONEMLER]
        self.ot = [g("ot", p) for p in DONEMLER]
        self.oq = [g("oq", p) for p in DONEMLER]
        self.ft = [g("ft", p) for p in DONEMLER]
        self.fq = [g("fq", p) for p in DONEMLER]
        self.it = [g("it", p) for p in DONEMLER]
        self.iq = [g("iq", p) for p in DONEMLER]
        self.notlar = []
        self.ilk = 0  # kırılma sonrası ilk geçerli indeks
        self._kirilma_kontrol()
        self._ceyrek_kontrol()

    def _kirilma_kontrol(self):
        """Yalnızca uyarı üretir; veri kullanım dışı bırakılmaz (karşılaştırılamazlık gösterilmedikçe)."""
        k = P["seri_uyari_kat"]
        for i in range(1, len(self.st)):
            a, b = self.st[i - 1], self.st[i]
            if a is None or b is None or a <= 0 or b <= 0:
                continue
            if b / a > k or a / b > k:
                self.notlar.append(f"İNCELEME UYARISI: TTM satış {donem_str(DONEMLER[i - 1])}→{donem_str(DONEMLER[i])} "
                                   f"{a:.0f}→{b:.0f} (ardışık çeyrekte {max(b / a, a / b):.1f} kat); veri kullanıldı")

    def _ceyrek_kontrol(self):
        """Çeyreklik seri, 4 çeyrek toplamının TTM'yi tuttuğu son noktada doğrulanmış sayılır."""
        self.ceyrek_ok = {}
        for i in range(len(DONEMLER)):
            if i - 3 < self.ilk:
                continue
            q = self.sq[i - 3:i + 1]
            if None in q or self.st[i] is None or self.st[i] <= 0:
                continue
            self.ceyrek_ok[i] = abs(sum(q) - self.st[i]) <= P["ceyrek_tutarlilik"] * abs(self.st[i])

    def gecerli(self, i):
        return i >= self.ilk and 0 <= i < len(DONEMLER)

    # TTM metrikleri
    def S(self, i):
        return self.st[i] if self.gecerli(i) else None

    def FM(self, i):
        return ddiv(self.ft[i], self.st[i]) if self.gecerli(i) else None

    def EFK(self, i):
        if not self.gecerli(i) or self.bt[i] is None or self.ot[i] is None:
            return None
        return self.bt[i] + self.ot[i]  # ot negatif gider

    def EM(self, i):
        return ddiv(self.EFK(i), self.st[i]) if self.gecerli(i) else None

    def IM(self, i):
        return ddiv(self.it[i], self.st[i]) if self.gecerli(i) else None

    # Çeyreklik metrikler (yalnızca doğrulanmış çeyreklerde)
    def q_ok(self, i):
        if not self.gecerli(i) or DONEMLER[i] in DOGRULANAMAYAN_CEYREK:
            return False
        # i çeyreği, i..i+3 aralığındaki herhangi bir doğrulanmış TTM'nin içindeyse doğrulanmış sayılır
        return any(self.ceyrek_ok.get(j) for j in range(i, min(i + 4, len(DONEMLER))))

    def fmq(self, i):
        return ddiv(self.fq[i], self.sq[i]) if self.q_ok(i) else None

    def efkq(self, i):
        if not self.q_ok(i) or self.bq[i] is None or self.oq[i] is None:
            return None
        return self.bq[i] + self.oq[i]

    def emq(self, i):
        return ddiv(self.efkq(i), self.sq[i]) if self.q_ok(i) else None

    def imq(self, i):
        return ddiv(self.iq[i], self.sq[i]) if self.q_ok(i) else None

    def sqv(self, i):
        return self.sq[i] if self.q_ok(i) else None

    def son_donem(self):
        for i in range(len(DONEMLER) - 1, -1, -1):
            if self.st[i] is not None and self.ft[i] is not None:
                return i
        return None

    def ham_ceyrek_sayisi(self, t):
        n = 0
        for i in range(self.ilk, t + 1):
            if self.st[i] is not None or self.sq[i] is not None:
                n += 1
        return n


def kanit(deger, referans, esik, tip):
    """True/False/None (None: veri eksik)."""
    if deger is None or referans is None:
        return None
    if tip == "bps":
        return deger <= referans - esik * BPS
    if tip == "oran":
        return deger <= (1 - esik) * referans
    raise ValueError(tip)


def dip_degerlendir(s, t, ifna_fark=frozenset()):
    sonuc = []
    for d in range(t - 7, t):
        if d < 0:
            continue
        kayit = {"d": d, "donem": donem_str(DONEMLER[d])}
        refs = [k for k in range(d - 7, d - 3) if s.gecerli(k) and s.S(k) is not None]
        if refs and s.S(d) is not None:
            kayit["yol"] = "R-TTM"
            kayit["ref_donemler"] = [donem_str(DONEMLER[k]) for k in refs]
            kayit["gozlem"] = len(refs)
            kayit["zayif"] = len(refs) == 1
            med = lambda fn: (lambda v: median(v) if v else None)([x for x in (fn(k) for k in refs) if x is not None])
            mFM, mEFK, mS, mIM = med(s.FM), med(s.EFK), med(s.S), med(s.IM)
            A = kanit(s.FM(d), mFM, P["dip_A_bps"], "bps")
            if mEFK is None or s.EFK(d) is None:
                B = None
            elif mEFK <= 0:
                B = "DIŞI"
            else:
                B = s.EFK(d) <= 0 or s.EFK(d) <= (1 - P["dip_B_oran"]) * mEFK
            C = None if (mS is None or mS <= 0 or s.S(d) is None) else s.S(d) <= (1 - P["dip_C_oran"]) * mS
            D = None if ({d, *refs} & ifna_fark) else kanit(s.IM(d), mIM, P["dip_D_bps"], "bps")
            kayit["fm_d"] = s.FM(d)
        elif d - 4 >= 0 and DONEMLER[d - 4] in DOGRULANAMAYAN_CEYREK and s.sq[d - 4] is not None:
            kayit["yol"] = "R-ÇEYREK (EKSİK)"
            kayit["not"] = f"referans çeyrek {donem_str(DONEMLER[d - 4])}: karşılaştırılabilirlik doğrulanamadı"
            kayit["kanit"] = {"A": None, "B": None, "C": None, "D": None}
            kayit["sonuc"] = "VERİ YETERSİZ"
            kayit["tek_kanit_AB"] = False
            sonuc.append(kayit)
            continue
        elif s.q_ok(d) and s.q_ok(d - 4) and s.sqv(d) is not None and s.sqv(d - 4) is not None:
            kayit["yol"] = "R-ÇEYREK"
            kayit["ref_donemler"] = [donem_str(DONEMLER[d - 4])]
            kayit["gozlem"] = 1
            kayit["zayif"] = False
            A = kanit(s.fmq(d), s.fmq(d - 4), P["dip_A_bps"], "bps")
            r = s.efkq(d - 4)
            if r is None or s.efkq(d) is None:
                B = None
            elif r <= 0:
                B = "DIŞI"
            else:
                B = s.efkq(d) <= 0 or s.efkq(d) <= (1 - P["dip_B_oran"]) * r
            sr = s.sqv(d - 4)
            C = None if (sr is None or sr <= 0) else s.sqv(d) <= (1 - P["dip_C_oran"]) * sr
            D = None if ({d, d - 4} & ifna_fark) else kanit(s.imq(d), s.imq(d - 4), P["dip_D_bps"], "bps")
            kayit["fm_d"] = s.fmq(d)
        else:
            kayit["yol"] = "REFERANS YOK"
            sonuc.append(kayit)
            continue
        kan = {"A": A, "B": B, "C": C, "D": D}
        kayit["kanit"] = kan
        dogru = [k for k, v in kan.items() if v is True]
        bilinmez = [k for k, v in kan.items() if v is None]
        ab_dogru = any(kan[k] is True for k in "AB")
        if len(dogru) >= 2 and ab_dogru:
            kayit["sonuc"] = "DİP"
        elif len(dogru) + len(bilinmez) >= 2 and (ab_dogru or any(kan[k] is None for k in "AB")):
            kayit["sonuc"] = "VERİ YETERSİZ"
        else:
            kayit["sonuc"] = "YOK"
        kayit["tek_kanit_AB"] = len(dogru) == 1 and dogru[0] in "AB"
        sonuc.append(kayit)
    return sonuc


def dip_sec(dipler):
    gecerli = [x for x in dipler if x.get("sonuc") == "DİP" and x.get("fm_d") is not None]
    for yol in ("R-TTM", "R-ÇEYREK"):
        aday = [x for x in gecerli if x["yol"] == yol]
        if aday:
            return sorted(aday, key=lambda x: (x["fm_d"], -x["d"]))[0]
    return None


def ge(a, b, bps):
    if a is None or b is None:
        return None
    return a >= b + bps * BPS


def erken_sinyal(s, t, dip):
    d = dip["d"]
    q = {
        "son çeyrek FAVÖK marjı ≥ dip çeyreği + 50 bps": ge(s.fmq(t), s.fmq(d), P["sinyal_q_bps"]),
        "son çeyrek FAVÖK marjı ≥ geçen yıl aynı çeyrek + 50 bps": ge(s.fmq(t), s.fmq(t - 4), P["sinyal_q_bps"]),
        "son çeyrek temiz EFK marjı ≥ geçen yıl aynı çeyrek": ge(s.emq(t), s.emq(t - 4), 0),
    }
    tt = {
        "TTM FAVÖK marjı ≥ dip TTM + 100 bps": ge(s.FM(t), s.FM(d), P["sinyal_ttm_bps"]),
        "TTM FAVÖK marjı > önceki TTM": None if s.FM(t) is None or s.FM(t - 1) is None else s.FM(t) > s.FM(t - 1),
        "TTM temiz EFK marjı > dip dönemi": None if s.EM(t) is None or s.EM(d) is None else s.EM(t) > s.EM(d),
    }
    yollar = []
    sinir = []
    for ad, kos in (("ÇEYREKLİK", q), ("TTM", tt)):
        if all(v is True for v in kos.values()):
            yollar.append(ad)
        else:
            basarisiz = [k for k, v in kos.items() if v is False]
            eksik = [k for k, v in kos.items() if v is None]
            if len(basarisiz) == 1 and not eksik:
                sinir.append(f"{ad} yolu: yalnızca '{basarisiz[0]}' sağlanmadı")
    return yollar, sinir, q, tt


def guncel_toparlanma(s, t):
    a = ge(s.fmq(t), s.fmq(t - 4), P["sinyal_q_bps"]) and ge(s.emq(t), s.emq(t - 4), 0)
    b = (s.FM(t) is not None and s.FM(t - 1) is not None and s.FM(t) > s.FM(t - 1)
         and s.EM(t) is not None and s.EM(t - 1) is not None and s.EM(t) >= s.EM(t - 1))
    return bool(a), bool(b)


def kademe(deger, esikler, puanlar):
    if deger is None:
        return None
    for e, p in zip(esikler, puanlar):
        if deger >= e:
            return p
    return 0


def puanla(s, t, dip, fcf, row, emsal_pct, ifna_fark=frozenset()):
    sat = {}

    def yaz(k, puan=None, durum="HESAPLANDI", alt=None, ust=None, not_=""):
        sat[k] = {"puan": puan, "durum": durum, "alt": alt, "ust": ust, "not": not_}

    d = dip["d"] if dip else None
    dm = lambda a, b: None if a is None or b is None else a - b

    # A1, A2, B1 — dipten artış (TTM)
    for k, fn, es, pu in (("A1", s.FM, [200, 100], [10, 5]), ("A2", s.EM, [100, 50], [5, 2.5]),
                          ("B1", s.IM, [200, 100], [10, 5])):
        v = dm(fn(t), fn(d)) if d is not None else None
        if k == "B1" and ({t, d} & ifna_fark):
            yaz(k, durum="EKSİK", not_=f"Evo–master İFNA mutabakatı bekliyor (gösterge {'' if v is None else f'{v / BPS:+.0f} bps'})")
            continue
        p = kademe(None if v is None else v / BPS, es, pu)
        if p is None:
            yaz(k, durum="EKSİK", not_="dip TTM veya son TTM hesaplanamadı (izahname kontrol edilmedi)")
        else:
            yaz(k, p, not_=f"{v / BPS:+.0f} bps")
    # A3
    a = dm(s.fmq(t), s.fmq(t - 4))
    b = dm(s.fmq(t - 1), s.fmq(t - 5))
    if a is None or b is None:
        yaz("A3", durum="EKSİK", not_="doğrulanmış çeyreklik veri yok")
    else:
        n = (a >= 50 * BPS) + (b >= 50 * BPS)
        yaz("A3", {2: 5, 1: 2.5, 0: 0}[n], not_=f"{a / BPS:+.0f} / {b / BPS:+.0f} bps")
    # A4
    v = dm(s.EM(t), s.EM(t - 1))
    if v is None:
        yaz("A4", durum="EKSİK")
    else:
        yaz("A4", 5 if v >= 50 * BPS else (2.5 if v > 0 else 0), not_=f"{v / BPS:+.0f} bps")
    # A5 — vekil: TTM reel satış YoY
    if s.S(t) is None or s.S(t - 4) is None or s.S(t - 4) <= 0:
        yaz("A5", durum="EKSİK", not_="hacim açıklanmıyor; vekil için TTM(t-4) yok")
    else:
        g = s.S(t) / s.S(t - 4) - 1
        yaz("A5", 5 if g > 0 else (2.5 if g == 0 else 0), not_=f"vekil ölçü: TTM satış {g:+.1%} (bant yok)")
    # B2
    i0, i1 = s.it[t], s.it[t - 1] if t - 1 >= s.ilk else None
    if {t, t - 1} & ifna_fark:
        yaz("B2", durum="EKSİK", not_="Evo–master İFNA mutabakatı bekliyor")
    elif i0 is None:
        yaz("B2", durum="EKSİK")
    else:
        yaz("B2", 5 if (i0 > 0 and i1 is not None and i1 > 0) else (2.5 if i0 > 0 else 0))
    # B3 — belge
    yaz("B3", durum="EKSİK", not_="belge incelemesi")
    # B4 — kullanıcının onaylı FCF standardı (FCF_MASTER, GEM v6.2 / FCF v2.2)
    if not fcf or fcf.get("t") is None or fcf["t"].get("statu") in (None, "NULL", "KOŞULLU") or fcf["t"].get("fcf") is None:
        st = fcf["t"].get("statu") if fcf and fcf.get("t") else "master'da yok"
        yaz("B4", durum="EKSİK", alt=0, ust=5, not_=f"FCF statü: {st}")
    else:
        x0 = fcf["t"]["fcf"]
        x1 = fcf.get("t1", {}).get("fcf") if fcf.get("t1") else None
        etiket = f"FCF_MASTER {fcf['t']['statu']} ({fcf['t']['kaynak']}): {x0:,.0f} mn"
        if x0 > 0:
            yaz("B4", 5, not_=etiket)
        elif x1 is not None and x0 > x1:
            yaz("B4", durum="EKSİK", alt=0, ust=2.5, not_=etiket + f"; önceki TTM {x1:,.0f} → iyileşmiş; yatırım nedeni incelemesi bekleniyor")
        elif x1 is None:
            yaz("B4", durum="EKSİK", alt=0, ust=2.5, not_=etiket + "; önceki TTM yok")
        else:
            yaz("B4", 0, not_=etiket)
    # C1
    nb = lambda yymm: f(row.get(f"nb{yymm}"))
    tt = DONEMLER[t] % 10000
    t4 = DONEMLER[t - 4] % 10000 if t - 4 >= 0 else None
    nb0, nb4 = nb(tt), (nb(t4) if t4 else None)
    if nb0 is None or nb4 is None or not s.S(t) or not s.S(t - 4):
        yaz("C1", durum="EKSİK", not_="tanımlı net borç (TFRS 16 dahil) hesaplanmadı; Evo net borç da yok")
    else:
        r0, r4 = nb0 / s.S(t), nb4 / s.S(t - 4)
        yaz("C1", durum="EKSİK", not_=f"tanımlı net borç (TFRS 16 dahil) doğrulanmadı; gösterge Evo net borç/satış {r4:.2f}→{r0:.2f}")
    for k in ("C2", "C3", "C4", "D2", "E1", "E2"):
        yaz(k, durum="EKSİK", not_="belge/model incelemesi")
    # D1
    if emsal_pct is None:
        yaz("D1", durum="EKSİK", not_="emsal sepeti tanımlanmadı (gösterge de yok: oran anlamlı değil veya geniş sektörde < 5 şirket)")
    else:
        pct, n = emsal_pct
        yaz("D1", durum="EKSİK", not_=f"emsal sepeti tanımlanmadı; gösterge geniş Evo sektöründe yüzdelik {pct:.0%} (n={n})")
    # D3 — faiz sınıflandırması doğrulanmadı
    ft = fcf.get("t") if fcf else None
    if ft and ft.get("statu") in ("KESİN", "TÜRETİLMİŞ") and ft.get("fcf") is not None and ft["fcf"] <= 0:
        yaz("D3", 0, not_=f"FCF_MASTER {ft['statu']} {ft['fcf']:,.0f} mn ≤ 0; faiz düşülmesi pozitife çeviremez → verim ≤ 0")
    else:
        yaz("D3", durum="EKSİK", not_="nakit faiz sınıflandırması doğrulanmadı" + (" (FCF > 0)" if ft and ft.get("fcf") and ft["fcf"] > 0 else ""))
    return sat


def on_puan(sat):
    alt = ust = uyg = 0.0
    for k, mx in ON_PUAN_SATIRLARI.items():
        x = sat[k]
        if x["durum"] == "HESAPLANDI":
            alt += x["puan"]
            ust += x["puan"]
        elif x["durum"] == "EKSİK":
            a = x["alt"] if x["alt"] is not None else 0
            u = x["ust"] if x["ust"] is not None else mx
            alt += a
            ust += a + (u - a)
        else:
            uyg += mx
    return alt, ust, uyg


def main():
    ap = argparse.ArgumentParser()
    for a in ("evo", "master", "evren", "sektor", "cikti"):
        ap.add_argument(f"--{a}", required=True)
    args = ap.parse_args()
    os.makedirs(args.cikti, exist_ok=True)

    evo = {r["kod"]: r for r in csv.DictReader(open(args.evo, encoding="utf-8"))}
    sektor_ad = {int(r["id"]): r["baslik"] for r in csv.DictReader(open(args.sektor, encoding="utf-8"))}
    evren = {r["Kod"]: r for r in csv.DictReader(open(args.evren, encoding="utf-8-sig"))}
    master = {}
    for r in csv.DictReader(open(args.master, encoding="utf-8")):
        y, m = r["donem"].split("/")
        master.setdefault(r["kod"], {})[int(y) * 100 + int(m)] = {
            "fcf": f(r["fcf_ttm"]), "cfo": f(r["cfo_ttm"]), "statu": r["statu"], "kaynak": r["kaynak"],
            "null": r["null_kodu"]}

    # Evren
    kayitlar = []
    for kod, row in sorted(evo.items()):
        sek = int(f(row.get("sek")) or 0)
        e = evren.get(kod)
        if e:
            ie = e["İnceleme Evreni"]
            if ie in ("İŞLETME ÖN TARAMASI", "FCF kapsamı"):
                kapsam = "ANA EVREN"
            elif ie == "MASTERDA YOK — FCF DEĞERLENDİRİLMEDİ":
                kapsam = "KAPSAM DIŞI (sektör)" if sek in KAPSAM_DISI_SEKTOR else "ANA EVREN (master'da yok)"
            else:
                kapsam = f"KAPSAM DIŞI ({ie})"
        else:
            kapsam = "KAPSAM DIŞI (sektör)" if sek in KAPSAM_DISI_SEKTOR else "ANA EVREN (master'da yok)"
        kayitlar.append({"kod": kod, "row": row, "sek": sek, "kapsam": kapsam})

    ana = [k for k in kayitlar if k["kapsam"].startswith("ANA EVREN")]

    # Emsal yüzdelikleri (D1): Evo sektörü, pozitif FAVÖK ve FD
    fd_favok = {}
    for k in ana:
        s = Seri(k["row"])
        t = s.son_donem()
        if t is None:
            continue
        pd_ = f(k["row"].get("pd"))
        nb0 = f(k["row"].get(f"nb{DONEMLER[t] % 10000}"))
        fav = s.ft[t]
        if pd_ and nb0 is not None and fav and fav > 0 and pd_ + nb0 > 0:
            fd_favok[k["kod"]] = ((pd_ + nb0) / fav, k["sek"])

    def emsal(kod):
        if kod not in fd_favok:
            return None
        oran, sek = fd_favok[kod]
        peers = [v for kk, (v, s2) in fd_favok.items() if s2 == sek and kk != kod]
        if len(peers) < P["emsal_min"]:
            return None
        dus = sum(1 for v in peers if v < oran)
        es = sum(1 for v in peers if v == oran)
        return ((dus + 0.5 * es) / len(peers), len(peers))

    sonuc = []
    for k in kayitlar:
        kod, row = k["kod"], k["row"]
        out = {"kod": kod, "sektor": sektor_ad.get(k["sek"], ""), "kapsam": k["kapsam"]}
        if not k["kapsam"].startswith("ANA EVREN"):
            out["liste"] = "KAPSAM DIŞI"
            sonuc.append(out)
            continue
        s = Seri(row)
        t = s.son_donem()
        out["notlar"] = list(s.notlar)
        if kod in TAKVIM_DISI_MALI_YIL:
            out["liste"] = "4-VERİ EKSİĞİ"
            out["neden"] = "mali yıl takvim dışı; takvim TTM'i güvenilir değil (FCF_MASTER notu)"
            sonuc.append(out)
            continue
        if t is None or s.FM(t) is None:
            out["liste"] = "4-VERİ EKSİĞİ"
            out["neden"] = "son dönem TTM satış/FAVÖK yok veya satış ≤ 0"
            sonuc.append(out)
            continue
        out["son_donem"] = donem_str(DONEMLER[t])
        if DONEMLER[t] < 202606:
            out["notlar"].append(f"BAYAT: son açıklanan dönem {donem_str(DONEMLER[t])}")
        out["n_ham_ceyrek"] = s.ham_ceyrek_sayisi(t)
        out["ttm_favok_marji"] = s.FM(t)
        out["ttm_efk_marji"] = s.EM(t)
        out["ttm_ifna_marji"] = s.IM(t)
        # Evo İFNA ile master CFO karşılaştırması (örtüşen tüm dönemler)
        m = master.get(kod, {})
        mt = m.get(DONEMLER[t])
        ifna_fark = set()
        for i, p_ in enumerate(DONEMLER):
            mm = m.get(p_)
            if mm and mm.get("cfo") is not None and s.it[i] is not None:
                fark = abs(s.it[i] - mm["cfo"]) / max(abs(mm["cfo"]), 1.0)
                if fark > P["ifna_mutabakat_esik"]:
                    ifna_fark.add(i)
                    out["notlar"].append(f"EVO–MASTER İFNA FARKI {donem_str(p_)}: Evo {s.it[i]:,.0f} / master {mm['cfo']:,.0f} mn "
                                         f"(master kaynak: {mm['kaynak']}) — mutabakat bekliyor")
        ifna_fark = frozenset(ifna_fark)
        out["ifna_mutabakat_bekliyor"] = ", ".join(donem_str(DONEMLER[i]) for i in sorted(ifna_fark))
        fcf = {"t": mt, "t1": m.get(DONEMLER[t - 1]) if t >= 1 else None} if mt else None

        dipler = dip_degerlendir(s, t, ifna_fark)
        out["dip_tarihleri"] = [{k2: v for k2, v in x.items() if k2 in ("donem", "yol", "gozlem", "zayif", "ref_donemler", "sonuc", "kanit")} for x in dipler]
        dip = dip_sec(dipler)
        fm_min = min([x for x in (s.FM(i) for i in range(max(t - 7, s.ilk), t + 1)) if x is not None], default=None)
        if fm_min is not None and s.FM(t) == fm_min:
            out["notlar"].append("dip devam ediyor olabilir (son TTM FAVÖK marjı pencerenin en düşüğü)")

        if dip:
            out["dip"] = {"donem": dip["donem"], "yol": dip["yol"], "gozlem": dip["gozlem"], "zayif": dip["zayif"],
                          "kanit": [k2 for k2, v in dip["kanit"].items() if v is True]}
            yollar, sinir, q, tt = erken_sinyal(s, t, dip)
            out["sinyal_kosullari"] = {"ÇEYREKLİK": q, "TTM": tt}
            if yollar:
                out["erken_sinyal_yolu"] = yollar
                kisa = dip["yol"] == "R-ÇEYREK" or dip["zayif"] or out["n_ham_ceyrek"] < 8
                out["liste"] = "1-ADAY HAVUZU" + (" (KISA GEÇMİŞLİ ADAY)" if kisa else "")
                sat = puanla(s, t, dip, fcf, row, emsal(kod), ifna_fark)
                alt, ust, uyg = on_puan(sat)
                out["puan_satirlari"] = sat
                out["on_puan_alt"], out["on_puan_ust"], out["uygulanamaz_kapasite"] = alt, ust, uyg
                out["kuyruk"] = 1 if alt >= P["on_puan_kuyruk"] else (2 if ust >= P["on_puan_kuyruk"] else 3)
                # operasyonel teyit (sayısal kısımlar 1–3; 4. madde belge)
                c1 = (ge(s.fmq(t), s.fmq(t - 4), 50), ge(s.fmq(t - 1), s.fmq(t - 5), 50))
                c2 = (ge(s.emq(t), s.emq(t - 4), 0), ge(s.emq(t - 1), s.emq(t - 5), 0))
                c3 = ge(s.FM(t), s.FM(dip["d"]), 100)
                out["op_teyit_sayisal"] = all(x is True for x in c1 + c2 + (c3,))
                out["nakit_teyit_sayisal"] = ("MUTABAKAT BEKLİYOR" if ({t, dip["d"]} & ifna_fark) else
                                              bool(s.it[t] and s.it[t] > 0 and s.IM(dip["d"]) is not None and s.IM(t) > s.IM(dip["d"])))
                # risk işaretleri (eleme değil)
                risk = []
                nb0 = f(row.get(f"nb{DONEMLER[t] % 10000}"))
                if nb0 is not None and s.ft[t]:
                    if s.ft[t] > 0 and nb0 / s.ft[t] > 3:
                        risk.append(f"Net borç/FAVÖK {nb0 / s.ft[t]:.1f}")
                    elif s.ft[t] <= 0 and nb0 > 0:
                        risk.append("FAVÖK ≤ 0 ve net borçlu")
                co = f(row.get(f"co{DONEMLER[t] % 10000}"))
                if co is not None and co < 1:
                    risk.append(f"cari oran {co:.2f}")
                out["risk_isaretleri"] = risk
            elif sinir:
                out["liste"] = "2-SINIRDA (erken sinyal)"
                out["neden"] = "; ".join(sinir)
            else:
                out["liste"] = "DİP VAR, SİNYAL YOK"
        else:
            sonuclar = [x.get("sonuc") for x in dipler]
            tek = [x for x in dipler if x.get("tek_kanit_AB")]
            if tek:
                x = tek[-1]
                out["liste"] = "2-SINIRDA (dip)"
                out["neden"] = (f"{x['donem']} ({x['yol']}): yalnızca {[k2 for k2, v in x['kanit'].items() if v is True][0]} kanıtı; "
                                f"diğerleri {', '.join(f'{k2}=' + ('EKSİK' if v is None else str(v)) for k2, v in x['kanit'].items() if v is not True)}")
            elif all(x.get("yol") in ("REFERANS YOK", "R-ÇEYREK (EKSİK)") for x in dipler):
                a, b = guncel_toparlanma(s, t)
                if a or b:
                    out["liste"] = "3-DİP DOĞRULANAMADI — GEÇMİŞ SINIRLI / TOPARLANMA İZLEMESİ"
                    out["neden"] = "güncel toparlanma: " + ", ".join(n for n, v in (("çeyreklik YoY", a), ("TTM", b)) if v)
                else:
                    out["liste"] = "4-VERİ EKSİĞİ"
                    out["neden"] = "hiçbir dip tarihi için referans yok; güncel toparlanma sinyali de yok"
            elif "VERİ YETERSİZ" in sonuclar:
                yetersiz = [x for x in dipler if x.get("sonuc") == "VERİ YETERSİZ"]
                if all(x.get("yol") == "R-ÇEYREK (EKSİK)" for x in yetersiz):
                    out["liste"] = "DİP KANITI YOK (KISMİ PENCERE)"
                    out["neden"] = ("değerlendirilen tarihlerde dip kanıtı yok; değerlendirilemeyen: "
                                    + ", ".join(f"{x['donem']} ({x['not']})" for x in yetersiz))
                else:
                    out["liste"] = "4-VERİ EKSİĞİ"
                    out["neden"] = "dip kanıtı için veri yetersiz: " + ", ".join(x["donem"] for x in yetersiz)
            else:
                out["liste"] = "DİP KANITI YOK"
        sonuc.append(out)

    with open(os.path.join(args.cikti, "sonuc.json"), "w", encoding="utf-8") as fo:
        json.dump({"parametreler": P, "donemler": DONEMLER, "sirketler": sonuc}, fo, ensure_ascii=False, indent=1, default=str)
    from collections import Counter
    print(Counter(x["liste"] for x in sonuc))


if __name__ == "__main__":
    main()
