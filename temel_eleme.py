"""
TEMEL ELEME — Doç. Dr. Serkan Ünal "Borsa Eğitimi" playlist'inden türetilmiş
hisse eleme yöntemi. Yöntemin video-video kaynağı için bkz. TEMEL_ELEME_YONTEMI.md

Üç aşama:
  1) KESİN ELEME  — iflas / finansal darboğaz riski ve kurumsallık zafiyeti
                    (videolarda "taviz verilmemeli" denen kriterler)
  2) 8 KRİTER PUANI — "İyi hisseleri diğerlerinden ayıran 8 kriter"
                    (her biri 0-10, toplam 100'e ölçeklenir)
  3) GÜVENLİK MARJI — çarpan analiziyle içsel değer, riske göre değişen
                    gerekli iskonto (Graham / Buffett yaklaşımı)

Veri: yfinance (yıllık bilanço + gelir tablosu, son 4 yıl).
Çıktı: temel_eleme_tum.csv, temel_eleme_aday.csv
"""
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd
import yfinance as yf

from xutum_tarama_v2 import tickers

warnings.filterwarnings("ignore")

# ── PARAMETRELER ─────────────────────────────────────────
# Videolarda net sayı verilmeyen eşikler burada; istersen değiştir.
P = {
    # Kesin eleme
    "MIN_HAKIM_PAY": 0.30,        # halka açıklık > %70 ise ele ("çok dikkatli")
    "MAX_BORC_OZKAYNAK": 1.50,    # finansal borç / özkaynak
    "MAX_NETBORC_FAALIYET": 5.0,  # net borç / faaliyet kârı (borcu kaç yılda öder)
    "KOMBO_NETBORC_OZK": 0.50,    # borç + düşük marj + döngüsel kombinasyonu için
    # Puan
    "ADAY_MIN_PUAN": 60,          # 100 üzerinden
    # Güvenlik marjı
    "MAKS_FK": 15.0,              # içsel değerde kullanılacak F/K tavanı
    "TABAN_MARJ": 0.30,           # videodaki örnek: 100 TL değere %30 marj → 70 TL
    "EK_MARJ_KURUMSAL": 0.20,     # kurumsallığı zayıf şirkete +%20
    "EK_MARJ_DONGUSEL": 0.10,
    "EK_MARJ_ZARAR_YILI": 0.10,
    "IS_PARCACIGI": 6,
}

# Ekonomik krizde tüketimi ertelenemeyen (savunmacı) ve ertelenebilen
# (döngüsel) sektörler — "İflas edecek firmalar nasıl anlaşılır" videosu.
SAVUNMACI = {"Consumer Defensive", "Utilities", "Healthcare", "Communication Services"}
DONGUSEL = {"Consumer Cyclical", "Industrials", "Basic Materials"}
FINANSAL = {"Financial Services"}
# Holdingler banka/finans iştiraklerini konsolide ettiği için borç oranları yanıltıcı
HOLDING_ALT = {"Conglomerates"}


def finansal_mi(m):
    return m["Sektör"] in FINANSAL or m.get("Alt Sektör") in HOLDING_ALT


# ── YARDIMCILAR ──────────────────────────────────────────
def satir(df, *adlar):
    """Tablodaki ilk bulunan satırı yeniden eskiye sıralı döndürür."""
    for ad in adlar:
        if df is not None and ad in df.index:
            s = df.loc[ad].dropna()
            if len(s):
                return s.sort_index(ascending=False)
    return pd.Series(dtype=float)


def ilk(s):
    return float(s.iloc[0]) if len(s) else np.nan


def bol(a, b):
    if b is None or np.isnan(b) or b == 0 or a is None or np.isnan(a):
        return np.nan
    return a / b


def cagr(s):
    """Yeniden eskiye sıralı seri için yıllık bileşik büyüme."""
    s = s[s > 0]
    if len(s) < 2:
        return np.nan
    yil = len(s) - 1
    return (s.iloc[0] / s.iloc[-1]) ** (1 / yil) - 1


def yuzdelik(seri, deger, buyuk_iyi=True):
    """deger'in seri içindeki yüzdelik sırası (0-1)."""
    seri = seri.dropna()
    if np.isnan(deger) or len(seri) < 3:
        return np.nan
    oran = (seri < deger).mean() + 0.5 * (seri == deger).mean()
    return oran if buyuk_iyi else 1 - oran


# ── VERİ ÇEK ─────────────────────────────────────────────
def veri_cek(ticker, deneme=3):
    for d in range(deneme):
        try:
            t = yf.Ticker(f"{ticker}.IS")
            info = t.info or {}
            inc = t.income_stmt
            bs = t.balance_sheet
            if inc is None or inc.empty or bs is None or bs.empty:
                return {"Hisse": ticker, "_veri_yok": True}
            break
        except Exception:
            if d == deneme - 1:
                return {"Hisse": ticker, "_veri_yok": True}
            time.sleep(3 * (d + 1))

    gelir = satir(inc, "Total Revenue", "Operating Revenue")
    brut = satir(inc, "Gross Profit")
    faaliyet = satir(inc, "Operating Income", "Total Operating Income As Reported")
    netkar = satir(inc, "Net Income Common Stockholders", "Net Income")
    borc = satir(bs, "Total Debt")
    kv_borc = satir(bs, "Current Debt", "Current Debt And Capital Lease Obligation")
    nakit = satir(bs, "Cash Cash Equivalents And Short Term Investments",
                  "Cash And Cash Equivalents")
    ozk = satir(bs, "Stockholders Equity", "Common Stock Equity")
    donen = satir(bs, "Current Assets")
    kv_yuk = satir(bs, "Current Liabilities")

    return {
        "Hisse": ticker,
        "Sektör": info.get("sector") or "Bilinmiyor",
        "Alt Sektör": info.get("industry") or "",
        "Piyasa Değeri": info.get("marketCap"),
        "F/K": info.get("trailingPE"),
        "PD/DD": info.get("priceToBook"),
        "Temettü %": info.get("dividendYield"),
        "Hakim Pay": info.get("heldPercentInsiders"),
        "_gelir": gelir, "_brut": brut, "_faaliyet": faaliyet, "_netkar": netkar,
        "_borc": borc, "_kv_borc": kv_borc, "_nakit": nakit, "_ozk": ozk,
        "_donen": donen, "_kv_yuk": kv_yuk,
    }


# ── METRİKLER ────────────────────────────────────────────
def metrik(m):
    g, f, n = m["_gelir"], m["_faaliyet"], m["_netkar"]
    oz = ilk(m["_ozk"])
    borc = ilk(m["_borc"])
    borc = 0.0 if np.isnan(borc) else borc
    nakit = ilk(m["_nakit"])
    nakit = 0.0 if np.isnan(nakit) else nakit
    kv_borc = ilk(m["_kv_borc"])
    kv_borc = 0.0 if np.isnan(kv_borc) else kv_borc

    marjlar = (m["_brut"] / g).dropna() if len(g) else pd.Series(dtype=float)
    roe_seri = (n / m["_ozk"]).dropna()

    borc_s = m["_borc"].dropna()
    borc_artis = (len(borc_s) >= 3 and all(borc_s.iloc[i] > borc_s.iloc[i + 1]
                                           for i in range(min(3, len(borc_s) - 1))))
    gelir_cagr = cagr(g)
    borc_cagr = cagr(borc_s)

    m.update({
        "Özkaynak": oz,
        "Net Kâr": ilk(n),
        "Faaliyet Kârı": ilk(f),
        "Faaliyet Marjı": bol(ilk(f), ilk(g)),
        "Net Marj": bol(ilk(n), ilk(g)),
        "ROE": bol(ilk(n), oz),
        "Borç/Özkaynak": bol(borc, oz),
        "Net Borç/Özkaynak": bol(borc - nakit, oz),
        "Net Borç/Faaliyet Kârı": bol(borc - nakit, ilk(f)),
        "KV Borç": kv_borc,
        "Nakit": nakit,
        "Cari Oran": bol(ilk(m["_donen"]), ilk(m["_kv_yuk"])),
        "Kârlı Yıl": f"{int((n > 0).sum())}/{len(n)}",
        "_karli_oran": (n > 0).mean() if len(n) else np.nan,
        "_zarar_yili": bool((n <= 0).any()) if len(n) else False,
        "_kar_cv": (n.std() / abs(n.mean())) if len(n) >= 3 and n.mean() != 0 else np.nan,
        "_brut_marj_std": marjlar.std() if len(marjlar) >= 3 else np.nan,
        "_roe_ort": roe_seri.mean() if len(roe_seri) else np.nan,
        "Satış Büyümesi": gelir_cagr,
        "Özkaynak Büyümesi": cagr(m["_ozk"]),
        "_borc_artis_trendi": bool(borc_artis and (np.isnan(gelir_cagr) or
                                                   (not np.isnan(borc_cagr) and borc_cagr > gelir_cagr))),
    })
    return m


# ── 1) KESİN ELEME ───────────────────────────────────────
def kesin_eleme(m, sektor_marj_medyan):
    neden = []
    finansal = finansal_mi(m)

    # Kurumsallık — "taviz vermememiz gereken" kriter
    hp = m["Hakim Pay"]
    if hp is not None and not np.isnan(hp) and hp < P["MIN_HAKIM_PAY"]:
        neden.append(f"Hakim ortak payı %{hp*100:.0f} (<%{P['MIN_HAKIM_PAY']*100:.0f})")

    if not np.isnan(m["Özkaynak"]) and m["Özkaynak"] <= 0:
        neden.append("Negatif özkaynak")

    if (not np.isnan(m["Net Kâr"]) and m["Net Kâr"] < 0 and
            not np.isnan(m["Faaliyet Kârı"]) and m["Faaliyet Kârı"] < 0):
        neden.append("Son yıl hem faaliyet hem net zarar")

    if not finansal:
        bo = m["Borç/Özkaynak"]
        if not np.isnan(bo) and bo > P["MAX_BORC_OZKAYNAK"]:
            neden.append(f"Finansal borç/özkaynak {bo:.2f}")

        net_borc = m["Net Borç/Özkaynak"]
        nbf = m["Net Borç/Faaliyet Kârı"]
        if not np.isnan(net_borc) and net_borc > 0:
            if not np.isnan(m["Faaliyet Kârı"]) and m["Faaliyet Kârı"] <= 0:
                neden.append("Net borçlu ama faaliyet kârı yok")
            elif not np.isnan(nbf) and nbf > P["MAX_NETBORC_FAALIYET"]:
                neden.append(f"Net borç = {nbf:.1f} yıllık faaliyet kârı")

        # Meg-up örneği: nakit 1 yıllık finansal borcu karşılamıyor
        # ve dönen varlıklar da kısa vadeli yükümlülüklere yetmiyor
        cari = m["Cari Oran"]
        if (m["KV Borç"] > m["Nakit"] and not np.isnan(cari) and cari < 1):
            neden.append("Nakit KV finansal borca yetmiyor ve cari oran < 1")

        # "Yüksek borç + düşük marj + döngüsel sektör → varlığını koruyamaz"
        med = sektor_marj_medyan.get(m["Sektör"], np.nan)
        if (m["Sektör"] in DONGUSEL and not np.isnan(net_borc)
                and net_borc > P["KOMBO_NETBORC_OZK"]
                and not np.isnan(m["Faaliyet Marjı"]) and not np.isnan(med)
                and m["Faaliyet Marjı"] < med):
            neden.append("Döngüsel sektör + borçlu + marj sektörün altında")
    return neden


# ── 2) 8 KRİTER PUANI ────────────────────────────────────
def puanla(m, evren):
    finansal = finansal_mi(m)
    sektor = evren[evren["Sektör"] == m["Sektör"]]
    grup = sektor if len(sektor) >= 5 else evren
    p = {}

    # K1 Kurumsallık (hakim ortak payı)
    hp = m["Hakim Pay"]
    if hp is None or np.isnan(hp):
        p["K1 Kurumsallık"] = 3
    else:
        p["K1 Kurumsallık"] = 10 if hp >= 0.70 else 8 if hp >= 0.50 else 5 if hp >= 0.30 else 0

    # K2 Risk ve belirsizlik (sektör döngüselliği)
    p["K2 Risk"] = 10 if m["Sektör"] in SAVUNMACI else 3 if m["Sektör"] in DONGUSEL else 6

    # K3 Kâr istikrarı
    k3 = 0.0
    if not np.isnan(m["_karli_oran"]):
        k3 += 7 * m["_karli_oran"]
    if not np.isnan(m["_kar_cv"]) and m["_kar_cv"] < 0.5 and not m["_zarar_yili"]:
        k3 += 3
    p["K3 Kâr İstikrarı"] = k3

    # K4 Kâr marjı (sektöre göre)
    marj_kol = "Net Marj" if finansal else "Faaliyet Marjı"
    y = yuzdelik(grup[marj_kol], m[marj_kol])
    p["K4 Kâr Marjı"] = 0 if np.isnan(y) else 10 * y

    # K5 Finansal borç
    if finansal:
        p["K5 Borç"] = 5
    else:
        nb = m["Net Borç/Özkaynak"]
        k5 = (5 if np.isnan(nb) else 10 if nb <= 0 else 8 if nb < 0.25
              else 6 if nb < 0.5 else 3 if nb < 1 else 0)
        if m["_borc_artis_trendi"]:
            k5 = max(0, k5 - 2)
        p["K5 Borç"] = k5

    # K6 Büyüme (satış + özkaynak, evrene göre sıra — enflasyon etkisini nötrler)
    ys = [yuzdelik(evren["Satış Büyümesi"], m["Satış Büyümesi"]),
          yuzdelik(evren["Özkaynak Büyümesi"], m["Özkaynak Büyümesi"])]
    ys = [v for v in ys if not np.isnan(v)]
    p["K6 Büyüme"] = 10 * np.mean(ys) if ys else 0

    # K7 Çarpanlar (sektör içinde ucuzluk)
    fk = m["F/K"] if m["F/K"] and m["F/K"] > 0 else np.nan
    pdd = m["PD/DD"] if m["PD/DD"] and m["PD/DD"] > 0 else np.nan
    td = m["Temettü %"] if m["Temettü %"] else 0.0
    parca = [
        0 if np.isnan(fk) else yuzdelik(grup["F/K"].where(grup["F/K"] > 0), fk, buyuk_iyi=False),
        yuzdelik(grup["PD/DD"].where(grup["PD/DD"] > 0), pdd, buyuk_iyi=False),
        yuzdelik(grup["Temettü %"].fillna(0), td),
    ]
    parca = [v for v in parca if not np.isnan(v)]
    p["K7 Çarpanlar"] = 10 * np.mean(parca) if parca else 0

    # K8 Sürdürülebilir rekabet avantajı (vekil: yüksek ROE + istikrarlı brüt marj)
    y = yuzdelik(evren["_roe_ort"], m["_roe_ort"])
    k8 = 0 if np.isnan(y) else 6 * y
    if not np.isnan(m["_brut_marj_std"]) and m["_brut_marj_std"] < 0.05:
        k8 += 4
    p["K8 Rekabet Avantajı"] = k8

    toplam = sum(p.values()) / 80 * 100
    return {k: round(v, 1) for k, v in p.items()}, round(toplam, 1)


# ── 3) GÜVENLİK MARJI ────────────────────────────────────
def guvenlik_marji(m, sektor_fk_medyan, k1):
    gerekli = P["TABAN_MARJ"]
    if k1 < 5:
        gerekli += P["EK_MARJ_KURUMSAL"]
    if m["Sektör"] in DONGUSEL:
        gerekli += P["EK_MARJ_DONGUSEL"]
    if m["_zarar_yili"]:
        gerekli += P["EK_MARJ_ZARAR_YILI"]

    fk = min(sektor_fk_medyan.get(m["Sektör"], np.nan), P["MAKS_FK"])
    pd_ = m["Piyasa Değeri"]
    if np.isnan(fk) or not pd_ or np.isnan(m["Net Kâr"]) or m["Net Kâr"] <= 0:
        return np.nan, np.nan, gerekli
    icsel = fk * m["Net Kâr"]
    return icsel, 1 - pd_ / icsel, gerekli


# ── ANA AKIŞ ─────────────────────────────────────────────
def calistir(liste):
    ham, veri_yok = [], []
    with ThreadPoolExecutor(max_workers=P["IS_PARCACIGI"]) as ex:
        isler = {ex.submit(veri_cek, t): t for t in liste}
        for i, f in enumerate(as_completed(isler), 1):
            r = f.result()
            if r.get("_veri_yok"):
                veri_yok.append(r["Hisse"])
            else:
                ham.append(metrik(r))
            if i % 50 == 0:
                print(f"  {i}/{len(liste)} | veri: {len(ham)} | yok: {len(veri_yok)}")

    evren = pd.DataFrame(ham)
    for k in ["F/K", "PD/DD", "Temettü %", "Hakim Pay", "Piyasa Değeri"]:
        evren[k] = pd.to_numeric(evren[k], errors="coerce")
    sektor_marj = evren.groupby("Sektör")["Faaliyet Marjı"].median().to_dict()
    sektor_fk = evren[evren["F/K"] > 0].groupby("Sektör")["F/K"].median().to_dict()

    satirlar = []
    for _, m in evren.iterrows():
        m = m.to_dict()
        for k in ["F/K", "PD/DD", "Temettü %", "Hakim Pay", "Piyasa Değeri"]:
            m[k] = np.nan if pd.isna(m[k]) else m[k]
        neden = kesin_eleme(m, sektor_marj)
        puanlar, toplam = puanla(m, evren)
        icsel, marj, gerekli = guvenlik_marji(m, sektor_fk, puanlar["K1 Kurumsallık"])

        if neden:
            durum = "❌ ELENDİ"
        elif toplam >= P["ADAY_MIN_PUAN"]:
            durum = ("🟢 ADAY + ALIM BÖLGESİ" if not np.isnan(marj) and marj >= gerekli
                     else "🟡 ADAY (pahalı)")
        else:
            durum = "⚪ Zayıf puan"

        uyari = []
        if finansal_mi(m):
            uyari.append("Finansal şirket/holding: borç/likidite kriterleri uygulanmadı")
        if m["_borc_artis_trendi"]:
            uyari.append("Finansal borç satışlardan hızlı artıyor")
        if m["Hakim Pay"] is None or np.isnan(m["Hakim Pay"]):
            uyari.append("Hakim ortak payı verisi yok")

        satirlar.append({
            "Hisse": m["Hisse"], "Durum": durum, "Puan": toplam,
            "Sektör": m["Sektör"], **puanlar,
            "Güvenlik Marjı %": None if np.isnan(marj) else round(max(marj, -1.0) * 100, 1),  # -100 = en az 2 kat pahalı
            "Gerekli Marj %": round(gerekli * 100),
            "F/K": None if np.isnan(m["F/K"]) else round(m["F/K"], 1),
            "PD/DD": None if np.isnan(m["PD/DD"]) else round(m["PD/DD"], 2),
            "Temettü %": None if np.isnan(m["Temettü %"]) else round(m["Temettü %"], 2),
            "Hakim Pay %": None if np.isnan(m["Hakim Pay"]) else round(m["Hakim Pay"] * 100, 1),
            "Faaliyet Marjı %": None if np.isnan(m["Faaliyet Marjı"]) else round(m["Faaliyet Marjı"] * 100, 1),
            "Net Borç/Özkaynak": None if np.isnan(m["Net Borç/Özkaynak"]) else round(m["Net Borç/Özkaynak"], 2),
            "Kârlı Yıl": m["Kârlı Yıl"],
            "Eleme Nedeni": "; ".join(neden),
            "Uyarı": "; ".join(uyari),
        })

    df = pd.DataFrame(satirlar)
    sira = {"🟢 ADAY + ALIM BÖLGESİ": 0, "🟡 ADAY (pahalı)": 1, "⚪ Zayıf puan": 2, "❌ ELENDİ": 3}
    df = (df.assign(_s=df["Durum"].map(sira))
            .sort_values(["_s", "Puan"], ascending=[True, False])
            .drop(columns="_s").reset_index(drop=True))
    return df, veri_yok


if __name__ == "__main__":
    print(f"⏳ {len(tickers)} hisse temel elemeden geçiyor...\n")
    df, veri_yok = calistir(tickers)
    aday = df[df["Durum"].str.contains("ADAY")]

    print(f"\n{'='*60}")
    print(df["Durum"].value_counts().to_string())
    print(f"  Veri yok : {len(veri_yok)}")
    print(f"{'='*60}\n")
    print(aday.head(40).to_string(index=False))

    df.to_csv("temel_eleme_tum.csv", index=False)
    aday.to_csv("temel_eleme_aday.csv", index=False)
    print("\n✅ temel_eleme_tum.csv, temel_eleme_aday.csv kaydedildi")
