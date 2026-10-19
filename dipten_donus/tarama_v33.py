"""Dipten Dönüş Filtresi v3.3 — sayısal ön tarama (pilot).

Kural metni: docs/dipten-donus-v3.3.md

Girdiler (repoya konmaz; yerel dosya yolları argüman olarak verilir):
  --evo       Evo'dan çekilmiş geniş tablo (kod başına bir satır; st/sq/bt/bq/ot/oq/ft/fq/it/iq + YYMM,
              nb (net borç), co/no (cari/nakit oran), pd (piyasa değeri, mn TL), sek (sektör id))
  --master    FCF_MASTER.xlsx'ten çıkarılmış FCF satırları (kod, donem, fcf_ttm, statu, ...)
  --evren     BIST_EFK_FCF_Genis_Evren_Tarama CSV'si (master kapsam sınıflaması)
  --sektor    Evo sektör id → ad eşlemesi (CSV: id,baslik)
  --yayin     Evo finansal tablo yayın tarihleri (dönem eşleme şüphesi için)
  --belge     FCF_MASTER BELGE_TTM CFO kanıtları (İFNA mutabakatı için)
  --kfy       Evo dönen varlıklardaki 'Finansal Yatırımlar' (kod, kfy2503, kfy2506, kfy2603, kfy2606; mn TL) — C1 alternatif dalı
  --emsal     Emsal haritası CSV'si (kod, dar_grup, ust_grup, kanit, ...) — D1; dosya adı sürüm adıdır
  --ifna_tl   Evo İFNA TTM, TL hassasiyetinde (kod, t2412 … t2606) — mutabakat farkları yuvarlamasız hesaplanır
  (--belge artık FCF_MASTER'dan çıkarılan genişletilmiş tablo: bileşen tutarları, TMS29 katsayıları, 14g kodu, okuma durumu)
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
    "ortak_yontem_kabul": True,   # İFNA: dönem kaydı yoksa master TMS29 katsayı yöntemi baz kanıtı sayılır mı (duyarlılık için kapatılabilir)
}
BPS = 0.0001

KAPSAM_DISI_SEKTOR = {3, 4, 6, 23, 24, 25, 26, 27, 33, 35, 36, 39, 49}

# FCF_MASTER NOTLAR ("Spor kulüpleri"): mali yıl Haziran/Mayıs, takvim TTM'i yok.
TAKVIM_DISI_MALI_YIL = {"BJKAS", "FENER", "GSRAY", "TSPOR", "KAYSE", "MERKO"}

# Rapor kapak/başlık tarihi ile Evo dönem etiketi doğrudan karşılaştırılıp uyuşmazlığı belgelenen şirketler.
# (Yalnız yayın gecikmesi bu listeye alma gerekçesi değildir.)
DONEM_UYUSMAZLIGI_BELGELI = {
    "ARENA": "Evo '2025/06' satırı KAP 1512424; raporun başlığı '30 Eylül 2025 tarihi itibarıyla' (Evo 2025/06 sonrası seri kaymış)",
    "BALSU": "mali yıl 1 Temmuz–30 Haziran; Evo mali çeyreği takvim çeyreğine yazıyor, etiket rapor tarihinin 6 ay gerisinde "
             "(ör. Evo 2024/12 = '30 Haziran 2025 tarihi itibarıyla', Evo 2025/09 = '31 Mart 2026 tarihinde sona eren'); 5/5 dönem uyuşmuyor",
    "BORSK": "mali yıl 1 Nisan–31 Mart; Evo etiketi rapor tarihinin 3 ay gerisinde (ör. Evo 2024/12 = '31 Mart 2025 tarihi itibarıyla', "
             "Evo 2025/06 = '30 Eylül 2025 … altı aylık dönem'); 6/6 dönem uyuşmuyor",
    "MARTI": "mali yıl 1 Nisan–31 Mart ('özel hesap dönemine tabi'); Evo etiketi rapor tarihinin 3 ay gerisinde "
             "(ör. Evo 2024/12 = 'Cari Dönem 31.03.2025', Evo 2025/12 = '01.04.2025-31.03.2026'); 6/6 dönem uyuşmuyor",
}
# Belgeyle düzeltilen Evo değerleri: (kod, dönem, seri) -> (yeni değer mn TL, kanıt). Baz: aynı raporun diğer kalemleri 1,5414.
BELGE_DUZELTME = {
    ("SILVR", 202412, "it"): (118.105435 * 1.5414,
                              "SILVR 2024/12 FR nakit akış s.13: A toplamı 118.105.435 TL × 1,5414; rapor kendi içinde ve net nakit "
                              "değişimiyle tutarlı, Evo'nun 221,2 mn'u kendi A+B+C toplamıyla tutmuyor; master 2025/03–09'u aynı farkla düzeltmiş"),
}

# Rapor tarihi ile Evo etiketi doğrudan karşılaştırılıp UYUŞTUĞU görülenler (gecikme gerçek; dönem hatası yok).
DONEM_DOGRULANDI = {
    "ATEKS": "7/7 dönemde rapor tarihi Evo etiketiyle aynı (ör. '31 Mart 2025 tarihi itibarıyla'); 2025/03–09 raporları 06.03.2026'da birlikte yayımlanmış",
}

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


def _tr_ascii_upper(x):
    return x.translate(str.maketrans("İIıiŞşÇçĞğÖöÜü", "IIIISSCCGGOOUU")).upper()


TMS29 = {202412: 1.5414, 202503: 1.4004, 202506: 1.3211, 202509: 1.2289, 202512: 1.1776, 202603: 1.0701, 202606: 1.0}
TANIM_SIRA = ["ÇELİŞKİ", "METİN", "ONAYLI TÜRETME", "YAPISAL"]


def ifna_tanim_sinifi(b):
    """Master CFO satırının İFNA ana toplamı olduğuna dair kanıt düzeyi (metin araması tek başına yetmez).
    Bileşen (A cari YTD, B önceki yıl sonu, C önceki yıl aynı dönem) başına, kullanılan rapor okumasına bakılır:
      YAPISAL        — XBRL değeri PDF satırıyla teyitli (TEYITLI) ya da PDF satırı özdeşlikle (A+B+C = nakit değişimi) kontrol edilmiş
      ONAYLI TÜRETME — CFO, master'ın belgelenmiş özdeşlik kuralıyla türetilmiş (KAP numaralı PDF satırlarından)
      METİN          — yalnız PDF/izahname satır metni okunmuş; satırın yeri/bileşenleri doğrulanmamış
      ÇELİŞKİ        — XBRL ile PDF tutmamış, PDF yok ya da kullanılan tutar rapor okumasıyla eşleşmiyor
    Satırın sınıfı, değeri sıfır olmayan bileşenlerin en zayıfıdır."""
    sinif = []
    for k in ("A", "B", "C"):
        v = f(b.get(k))
        if not v:
            continue
        ok = _tr_ascii_upper(b.get(f"okuma_{k}", ""))
        kn = _tr_ascii_upper(b.get(f"kanit_{k.lower()}", ""))
        if "CFO =" in kn or "OZDESLIGIYLE TURETILDI" in ok or ("OZDESLIKLE" in ok and "XBRL:TEYITLI" not in ok):
            sinif.append("ONAYLI TÜRETME")
        elif "XBRL:TEYITLI" in ok or ("OZDESLIK" in kn and "✓" in kn):
            sinif.append("YAPISAL")
        elif "TUTAR_ESLESMEDI" in ok or "PDF_TUTMADI" in ok or "PDF_YOK" in ok:
            sinif.append("ÇELİŞKİ")
        else:
            sinif.append("METİN")
    return min(sinif, key=TANIM_SIRA.index) if sinif else "METİN"


def baz_sinifi(b, donem):
    """Master CFO'nun bu dönemde Evo serisiyle aynı bazda olduğuna dair kanıt (tek dönem tutar eşleşmesi kullanılmaz).
      DÖNEM KAYDI  — master FCF sayfasında bu dönemin CFO'su için Evo–belge (14g) kodu var (karşılaştırma kayıtlı)
      ORTAK YÖNTEM — bu dönemin bileşenlerine master TMS29 katsayı tablosu uygulanmış (BELGE_TTM katsayıları tabloyla aynı)
                     ya da TMS 29 uygulanmayan raporlarda katsayı 1
      YOK          — ikisi de yok"""
    k14 = b.get("kod14g", "")
    parcalar = [x.strip() for x in k14.split(";") if x.strip()]
    cfo_kodu = [x for x in parcalar if x.startswith("CFO:") or not any(x.startswith(p) for p in ("CAPEX:", "KIRA:"))]
    if any(c and "ACIKLANAMAYAN" not in c and "BELGE_YOK" not in c for c in cfo_kodu):
        return "DÖNEM KAYDI", k14
    y, m = divmod(donem, 100)
    onceki_yil_sonu = (y - 1) * 100 + 12
    beklenen = {"A": TMS29.get(donem), "B": TMS29.get(onceki_yil_sonu), "C": TMS29.get(donem)}
    tms_yok = all(b.get(f"tms29_{k}", "") in ("False", "") for k in "ABC")
    uyum = True
    for k in "ABC":
        if not f(b.get(k)):
            continue
        kat = f(b.get(f"k{k}"))
        if kat is None:
            uyum = False
        elif tms_yok and kat == 1:
            continue
        elif beklenen[k] is None or abs(kat - beklenen[k]) > 0.0002:
            uyum = False
    return ("ORTAK YÖNTEM" if uyum else "YOK"), k14


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
    # C1 — Evo Net Borç = toplam finansal borç (kira yükümlülükleri dahil) − nakit ve nakit benzerleri.
    # Eşleme MGROS ve KARSN 2026/06 bilançolarıyla birebir doğrulandı (kosu 4). KV finansal yatırımlar düşülmez;
    # düşülse puan dalı değişiyorsa satır EKSİK kalır (alt/üst = iki dalın puanı).
    nb = lambda yymm: f(row.get(f"nb{yymm}"))
    kfy = lambda yymm: f(row.get(f"kfy{yymm}"))
    tt = DONEMLER[t] % 10000
    t4 = DONEMLER[t - 4] % 10000 if t - 4 >= 0 else None
    nb0, nb4 = nb(tt), (nb(t4) if t4 else None)
    S0, S4 = s.S(t), (s.S(t - 4) if t - 4 >= 0 else None)
    if nb0 is None or nb4 is None or not S0 or not S4 or S0 <= 0 or S4 <= 0:
        yaz("C1", durum="EKSİK", not_="Evo net borç veya TTM satış (t / t−4) yok")
    else:
        def c1_puan(n0, n4):
            if n0 < 0 and n4 < 0:
                return 5, "her iki yılda net nakit"
            d = (n4 / S4 - n0 / S0) * 100  # oranın yüzde puan düşüşü
            return (5 if d >= 5 else (2.5 if d > 0 else 0)), (f"oran {d:.1f} yp düştü" if d > 0 else f"oran {-d:.1f} yp yükseldi/değişmedi")
        p, acik = c1_puan(nb0, nb4)
        k0, k4 = kfy(tt), (kfy(t4) if t4 else None)
        ek = (f"Evo net borç/TTM satış {nb4 / S4:.1%} → {nb0 / S0:.1%} ({acik}); kira yükümlülükleri dahil; "
              "blokeli nakit kontrol edilmedi; borç azalmasının kaynağı (sermaye artırımı/varlık satışı) belge incelemesinde yazılacak")
        if True:  # kfy satırı yoksa bilançoda dönen 'Finansal Yatırımlar' kalemi yoktur → 0
            p2, acik2 = c1_puan(nb0 - (k0 or 0), nb4 - (k4 or 0))
            if p2 == p:
                yaz("C1", p, not_=ek + ("; KV finansal yatırım düşülse de aynı dal" if (k0 or k4) else ""))
            else:
                yaz("C1", durum="EKSİK", alt=min(p, p2), ust=max(p, p2),
                    not_=ek + f"; KV finansal yatırım ({k4 or 0:,.0f} → {k0 or 0:,.0f} mn) düşülürse {p2:g} ({acik2}) — "
                         "yatırımların likiditesi/serbestliği belgeyle kararlaştırılacak")
    for k in ("C2", "C3", "C4", "D2", "E1", "E2"):
        yaz(k, durum="EKSİK", not_="belge/model incelemesi")
    # D1
    pd0 = f(row.get("pd"))
    nb_t = f(row.get(f"nb{DONEMLER[t] % 10000}"))
    fav = s.ft[t]
    if fav is not None and fav <= 0:
        yaz("D1", durum="UYGULANAMAZ", not_=f"FAVÖK TTM ≤ 0 ({fav:,.0f} mn); FD/FAVÖK anlamlı değil")
    elif pd0 is not None and nb_t is not None and pd0 + nb_t <= 0:
        yaz("D1", durum="EKSİK", not_=f"FD ≤ 0 (PD {pd0:,.0f} + Evo net borç {nb_t:,.0f} mn); net borç bileşenleri (blokeli nakit, "
                                      "finansal yatırımların serbestliği) doğrulanmadan uygulanamazlık kesin değil")
    elif emsal_pct is None:
        yaz("D1", durum="EKSİK", not_="FD/FAVÖK hesaplanamadı (PD, net borç veya FAVÖK yok)")
    elif emsal_pct["durum"] != "HESAPLANDI":
        yaz("D1", durum=emsal_pct["durum"], not_=emsal_pct["not"])
    else:
        pct = emsal_pct["pct"]
        yaz("D1", 5 if pct <= 0.25 else (2.5 if pct <= 0.50 else 0), not_=emsal_pct["not"])
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
    for a in ("evo", "master", "evren", "sektor", "cikti", "yayin", "belge", "kfy", "emsal", "ifna_tl"):
        ap.add_argument(f"--{a}", required=True)
    ap.add_argument("--ortak-yontem-yok", action="store_true", help="duyarlılık: ORTAK YÖNTEM baz kanıtını kabul etme")
    args = ap.parse_args()
    if args.ortak_yontem_yok:
        P["ortak_yontem_kabul"] = False
    os.makedirs(args.cikti, exist_ok=True)

    evo = {r["kod"]: r for r in csv.DictReader(open(args.evo, encoding="utf-8"))}
    # İFNA TTM, TL hassasiyetinde (2024/12–2026/06): geniş tablodaki 0,1 mn yuvarlamasının yerine geçer
    for r in csv.DictReader(open(args.ifna_tl, encoding="utf-8")):
        if r["kod"] in evo:
            for k, v in r.items():
                if k.startswith("t") and v not in ("", None):
                    evo[r["kod"]]["it" + k[1:]] = str(int(v) / 1e6)
    # KV finansal yatırımlar (dönen varlıklar içindeki 'Finansal Yatırımlar'; boş = kalem yok → 0)
    for r in csv.DictReader(open(args.kfy, encoding="utf-8")):
        if r["kod"] in evo:
            evo[r["kod"]].update({k: v for k, v in r.items() if k != "kod"})
    sektor_ad = {int(r["id"]): r["baslik"] for r in csv.DictReader(open(args.sektor, encoding="utf-8"))}
    evren = {r["Kod"]: r for r in csv.DictReader(open(args.evren, encoding="utf-8-sig"))}
    # Dönem eşleme şüphesi: 2025/03–2026/06 arasında en az 3 raporu dönem sonundan >110 gün sonra yayımlanan şirketler
    import datetime as _dt
    donem_suphe = {}
    for r in csv.DictReader(open(args.yayin, encoding="utf-8")):
        gec = []
        for k, v in r.items():
            if k.startswith("y") and v and k[1:].isdigit() and int(k[1:]) >= 2503:
                yy, mm = 2000 + int(k[1:3]), int(k[3:5])
                lag = (_dt.date.fromisoformat(v[:10]) - _dt.date(yy, mm, 28)).days
                if lag > 110:
                    gec.append(f"{yy}/{mm:02d}: {lag} gün")
        if len(gec) >= 3:
            donem_suphe[r["kod"]] = gec
    # Master CFO belge kanıtları
    belge = {}
    for r in csv.DictReader(open(args.belge, encoding="utf-8")):
        y, m = r["donem"].split("/")
        belge[(r["kod"], int(y) * 100 + int(m))] = r
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

    # Emsal haritası (sürümlü; çarpanlara bakılmadan kuruldu). Kural sırası sabit:
    # 1) şirketin iş modeli doğrulanmadıysa (kanıt D / haritada yok) → EKSİK
    # 2) dar grupta, kanıtı D olmayan ve FD/FAVÖK'ü geçerli ≥5 emsal → dar sepet
    # 3) değilse üst grupta aynı koşulla ≥5 emsal → üst sepet (geniş sepet notu)
    # 4) değilse: doğrulanmamış şirketler sınıflanınca 5'e ulaşılabilecekse EKSİK, ulaşılamıyorsa UYGULANAMAZ
    harita = {r["kod"]: r for r in csv.DictReader(open(args.emsal, encoding="utf-8"))}
    harita_surum = os.path.splitext(os.path.basename(args.emsal))[0]
    son_d = {}
    for k in ana:
        s_ = Seri(k["row"])
        t_ = s_.son_donem()
        son_d[k["kod"]] = DONEMLER[t_] if t_ is not None else None

    def emsal(kod):
        if kod not in fd_favok:
            return None
        oran, sek = fd_favok[kod]
        h = harita.get(kod)
        if not h or h["kanit"] == "D":
            return {"durum": "EKSİK", "not": f"{harita_surum}: iş modeli doğrulanmadı ({h['gerekce'] if h else 'haritada yok'}); "
                                                f"FD/FAVÖK {oran:.1f}"}
        dogrulanmamis = {kk for kk, hh in harita.items() if hh["kanit"] == "D" and kk in fd_favok}
        for seviye, alan in (("dar", "dar_grup"), ("üst", "ust_grup")):
            g = h[alan]
            if not g:
                continue
            uyeler = [kk for kk, hh in harita.items() if hh[alan] == g and hh["kanit"] != "D" and kk != kod]
            peers = [(kk, fd_favok[kk][0]) for kk in uyeler if kk in fd_favok]
            if len(peers) >= P["emsal_min"]:
                vals = [v for _, v in peers]
                dus = sum(1 for v in vals if v < oran)
                es = sum(1 for v in vals if v == oran)
                pct = (dus + 0.5 * es) / len(vals)
                farkli = [kk for kk, _ in peers if son_d.get(kk) != son_d.get(kod)]
                ad = h["dar_grup_adi"] if seviye == "dar" else h["ust_grup_adi"]
                return {"durum": "HESAPLANDI", "pct": pct, "n": len(vals), "sepet": f"{seviye}: {ad}",
                        "not": (f"{harita_surum} {seviye} sepet '{ad}' (n={len(vals)}"
                                + (", geniş sepet" if seviye == "üst" else "") + f"): FD/FAVÖK {oran:.1f}, yüzdelik {pct:.0%}, "
                                f"emsal medyanı {median(vals):.1f}"
                                + (f"; dönemi farklı emsal: {', '.join(farkli)}" if farkli else "")
                                + "; FD = PD (19.10.2026) + Evo net borç (son dönem), azınlık payları eklenmedi")}
        # yetersiz emsal
        grup_sek = {int(f(evo[kk].get("sek")) or 0) for kk, hh in harita.items()
                    if (hh["dar_grup"] and hh["dar_grup"] == h["dar_grup"]) or (hh["ust_grup"] and hh["ust_grup"] == h["ust_grup"])
                    if kk in evo}
        aday = [kk for kk in dogrulanmamis if fd_favok[kk][1] in grup_sek]
        mevcut = max(len([kk for kk, hh in harita.items() if hh[a] and hh[a] == h[a] and hh["kanit"] != "D" and kk != kod and kk in fd_favok])
                     for a in ("dar_grup", "ust_grup"))
        ad = h["dar_grup_adi"] or h["ust_grup_adi"]
        if mevcut + len(aday) >= P["emsal_min"]:
            return {"durum": "EKSİK", "not": f"{harita_surum} '{ad}': geçerli emsal {mevcut} < {P['emsal_min']}; aynı Evo sektöründe "
                                            f"iş modeli doğrulanmamış {len(aday)} şirket ({', '.join(sorted(aday))}) sınıflanınca yeniden bakılacak"}
        return {"durum": "UYGULANAMAZ", "not": f"{harita_surum} '{ad}': yeterli karşılaştırılabilir emsal yok "
                                              f"(geçerli FD/FAVÖK'lü emsal {mevcut} < {P['emsal_min']}; doğrulanmamış aday da yok)"}

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
        for (k_, p_, seri_), (v_, kanit_) in BELGE_DUZELTME.items():
            if k_ == kod:
                i_ = DONEMLER.index(p_)
                eski_ = getattr(s, seri_)[i_]
                getattr(s, seri_)[i_] = v_
                out["notlar"].append(f"BELGE DÜZELTMESİ {seri_} {donem_str(p_)}: Evo {eski_} → {v_:,.2f} mn ({kanit_})")
        if kod in DONEM_UYUSMAZLIGI_BELGELI:
            out["liste"] = "4-VERİ EKSİĞİ"
            out["neden"] = "belgeyle doğrulanmış dönem uyuşmazlığı: " + DONEM_UYUSMAZLIGI_BELGELI[kod] + "; etkilenen seri düzeltilene kadar hesaplar bekliyor"
            sonuc.append(out)
            continue
        if kod in DONEM_DOGRULANDI:
            out["notlar"].append("DÖNEM ETİKETİ DOĞRULANDI: " + DONEM_DOGRULANDI[kod] + "; geç yayın gerçek, sonuçlara etkisi yok")
        elif kod in donem_suphe:
            out["notlar"].append("DÖNEM KONTROLÜ BEKLİYOR (uyarı, karar etkisi yok): raporlar dönem sonundan >110 gün sonra yayımlanmış ("
                                 + "; ".join(donem_suphe[kod]) + "); rapor tarihi ile Evo etiketi doğrudan karşılaştırılmalı")
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
        ortak = [(i, m[p_]) for i, p_ in enumerate(DONEMLER)
                 if m.get(p_) and m[p_].get("cfo") is not None and s.it[i] is not None]
        # Seri kayması işareti (uyarı): Evo İFNA(p) = master CFO(p+1 veya p+2) en az iki dönemde ve p'de eşit değil.
        # Karar etkisi: yalnız bu şirkette master ile dönem bazlı değer değiştirme yapılmaz (karışık seri oluşmasın).
        def _esit(a, b_):
            return a is not None and b_ is not None and abs(a - b_) <= max(0.0015 * abs(b_), 0.15)
        kayma = None
        for sh in (1, 2):
            hits = [(DONEMLER[i], DONEMLER[i + sh]) for i in range(len(DONEMLER) - sh)
                    if m.get(DONEMLER[i + sh]) and _esit(s.it[i], m[DONEMLER[i + sh]].get("cfo"))
                    and not (m.get(DONEMLER[i]) and _esit(s.it[i], m[DONEMLER[i]].get("cfo")))]
            if len(hits) >= 2:
                kayma = (sh, hits)
                break
        if kayma:
            out["notlar"].append(f"SERİ KAYMASI İŞARETİ (uyarı): Evo İFNA, master CFO'nun {kayma[0]} çeyrek sonrasıyla aynı ("
                                 + ", ".join(f"Evo {donem_str(a)} = master {donem_str(b_)}" for a, b_ in kayma[1])
                                 + "); dönem etiketi rapor tarihiyle doğrudan karşılaştırılmalı")
            out["seri_kaymasi_isareti"] = kayma[0]
        mutabakat = []
        cozulmemis = {}
        for i, mm in ortak:
            # Bütün farklar kaydedilir. Evo TL hassasiyetinde; yalnız master'ın bin TL yuvarlaması (±0,0005 mn) içinde kalan eşit sayılır.
            fark_mn = s.it[i] - mm["cfo"]
            if abs(fark_mn) <= 0.0005 + 1e-9:
                continue
            payda = max(abs(mm["cfo"]), 1.0)
            b = belge.get((kod, DONEMLER[i]))
            kanit = (b or {}).get("kanit_a", "")
            tanim = ifna_tanim_sinifi(b) if b else "METİN"
            baz, k14 = baz_sinifi(b, DONEMLER[i]) if b else ("YOK", "")
            kaynak_ok = (mm["kaynak"].startswith("BELGE") and mm["statu"] in ("KESİN", "TÜRETİLMİŞ")
                         and b is not None and b.get("kullanildi") == "EVET" and "KAP" in kanit)
            baz_gecerli = baz == "DÖNEM KAYDI" or (baz == "ORTAK YÖNTEM" and P["ortak_yontem_kabul"])
            cozuldu = kaynak_ok and baz_gecerli and tanim in ("YAPISAL", "ONAYLI TÜRETME") and not kayma
            kayit = {"donem": donem_str(DONEMLER[i]), "evo": s.it[i], "master": mm["cfo"], "fark_mn": fark_mn,
                     "fark": abs(fark_mn) / payda, "isaret_farki": (s.it[i] > 0 > mm["cfo"]) or (s.it[i] < 0 < mm["cfo"]),
                     "master_kaynak": mm["kaynak"], "master_statu": mm["statu"], "baz": baz, "kod14g": k14,
                     "tanim": tanim, "kanit": kanit[:160]}
            if cozuldu:
                kayit["sonuc"] = ("KAYNAK İSTİSNASI: belgeyle düzeltilmiş master CFO kullanıldı"
                                  + (" (TÜRETİLMİŞ)" if tanim == "ONAYLI TÜRETME" else "") + f" — baz: {baz}")
                s.it[i] = mm["cfo"]
            else:
                eksik = [n for n, ok in (("seri kayması işareti", not kayma), ("belge kaynağı/statü", kaynak_ok), (f"dönem baz kanıtı ({baz})", baz_gecerli),
                                         (f"İFNA satır kanıtı ({tanim})", tanim in ("YAPISAL", "ONAYLI TÜRETME"))) if not ok]
                kayit["sonuc"] = "ÇÖZÜLEMEDİ (" + ", ".join(eksik) + ")"
                cozulmemis[i] = mm["cfo"]
            mutabakat.append(kayit)
        out["ifna_mutabakat"] = mutabakat
        # Çözülemeyen farklar: >%10 ise ilgili nakit kalemleri EKSİK; daha küçükse (büyüklükten bağımsız, %0,5 altı dahil)
        # iki kaynakla kanıt/puan dalı karşılaştırılır; dal değişiyorsa EKSİK, değişmiyorsa "puan duyarlı değil; tutar mutabakatı açık".
        ifna_fark = {i for i, v in cozulmemis.items() if abs(s.it[i] - v) / max(abs(v), 1.0) > P["ifna_mutabakat_esik"]}
        kucuk = [i for i in cozulmemis if i not in ifna_fark]
        if kucuk:
            def _imza(seri):
                dd = dip_degerlendir(seri, t)
                sec = dip_sec(dd)
                ims = [(x["donem"], x.get("kanit", {}).get("D")) for x in dd]
                b1 = None if not sec else seri.IM(t) is not None and seri.IM(sec["d"]) is not None and \
                    kademe((seri.IM(t) - seri.IM(sec["d"])) / BPS, [200, 100], [10, 5])
                b2 = (seri.it[t] or 0) > 0, (seri.it[t - 1] or 0) > 0
                b3 = None if not sec else bool(seri.it[t] and seri.it[t] > 0 and seri.IM(sec["d"]) is not None
                                               and seri.IM(t) is not None and seri.IM(t) > seri.IM(sec["d"]))
                return ims, b1, b2, b3
            temel = _imza(s)
            for i in kucuk:
                alt = Seri(row)
                alt.it = list(s.it)
                alt.it[i] = cozulmemis[i]
                if _imza(alt) != temel:
                    ifna_fark.add(i)
                else:
                    for k_ in mutabakat:
                        if k_["donem"] == donem_str(DONEMLER[i]):
                            k_["sonuc"] += " — puan bu iki değere duyarlı değil; tutar mutabakatı açık"
        for k_ in mutabakat:
            if k_["sonuc"].startswith("ÇÖZÜLEMEDİ") and k_["fark"] > P["ifna_mutabakat_esik"]:
                k_["sonuc"] += " — fark %10 üstü: ilgili nakit kalemleri EKSİK"
        for k_ in mutabakat:
            out["notlar"].append(f"İFNA {k_['donem']}: Evo {k_['evo']:,.1f} / master {k_['master']:,.3f} mn "
                                 f"(fark {k_['fark_mn']:+,.3f} mn; {k_['fark']:.2%}{'; İŞARET FARKI' if k_['isaret_farki'] else ''}) — {k_['sonuc']}")
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
                    out["liste"] = "DİP DEĞERLENDİRMESİ EKSİK — KISMİ PENCERE"
                    out["neden"] = ("Değerlendirilebilen tarihlerde dip kanıtı bulunmadı; değerlendirilemeyen: "
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
