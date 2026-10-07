"""
TEMEL ANALİZ TARAMASI — "taşın altına bakan" yayıncı yöntemi
================================================================
Polisan, Gimat, Fonet, Tınaztepe, Onur Yüksek Teknoloji ve Menderes
videolarındaki yaklaşım, yfinance bilanço/gelir tablosu verisiyle
otomatik ölçülebilen kurallara çevrildi. Ayrıntılı açıklama: YONTEM.md

Mantık iki katmanlı:
  1) PUAN  : ucuzluk + kalite + bilanço gücü + gizli değer (+)
             ve yöntemin uyarı verdiği durumlar (-)
  2) BAYRAK: puana girmeyen ama mutlaka elle bakılması gereken
             noktalar (ör. net zarar ama FAVÖK güçlü → Polisan tipi)

Çıktı:
  temel_tarama.csv  → tüm hisseler, metrikler, puan, bayraklar
  temel_sinyal.csv  → PUAN >= ESIK_PUAN olan adaylar

Not: Bu bir ön elemedir. Yayıncının asıl işi (yönetim, genel kurul
tutanakları, KAP, segment/iştirak değerlemesi) YONTEM.md'deki kontrol
listesiyle elle yapılmalı.
"""
import time
import warnings

import numpy as np
import pandas as pd
import yfinance as yf

from xutum_tarama_v2 import tickers

warnings.filterwarnings("ignore")

# ── PARAMETRELER ─────────────────────────────────────────
# BIST finansalları TMS 29 ile enflasyona göre düzeltilmiş geliyor; yani
# yıllık ciro büyümesi zaten REEL. Nominal veriyle çalışırsan TÜFE'yi yaz.
ENFLASYON_YILLIK   = 0.0
KUCUK_PD_TL        = 15e9      # "az takip edilen küçük şirket" eşiği
ESIK_PUAN          = 6         # temel_sinyal.csv'ye girme eşiği
BEKLEME_SN         = 0.6       # Yahoo hız sınırına takılmamak için
# FD/FAVÖK anlamsız olan sektörler (banka, sigorta, GYO, holding/finans)
HARIC_SONEK = ("GYO",)
HARIC = {
    "AKBNK", "GARAN", "HALKB", "ISCTR", "VAKBN", "YKBNK", "SKBNK", "TSKB",
    "ALBRK", "ICBCT", "QNBTR", "KLNMA", "AKGRT", "ANHYT", "ANSGR", "AGESA",
    "TURSG", "RAYSG", "GUSGR",
}


# ── YARDIMCILAR ──────────────────────────────────────────
def satir(df, *adlar):
    """İlk bulunan satırı (sütunlar yeni→eski) döndürür, yoksa None."""
    if df is None or df.empty:
        return None
    for ad in adlar:
        if ad in df.index:
            s = pd.to_numeric(df.loc[ad], errors="coerce")
            if s.notna().any():
                return s
    return None


def ilk(s, i=0):
    if s is None or len(s) <= i:
        return np.nan
    v = s.iloc[i]
    return float(v) if pd.notna(v) else np.nan


def ttm(s, bas=0):
    """bas'tan başlayan 4 çeyreğin toplamı (eksik çeyrek varsa NaN)."""
    if s is None or len(s) < bas + 4:
        return np.nan
    p = s.iloc[bas:bas + 4]
    return float(p.sum()) if p.notna().all() else np.nan


def oran(a, b):
    if b is None or a is None or not np.isfinite(a) or not np.isfinite(b) or b == 0:
        return np.nan
    return a / b


def yahoo(fn, deneme=3):
    for k in range(deneme):
        try:
            return fn()
        except Exception:
            time.sleep(2 * (k + 1))
    return None


def finansal_kur(t):
    """Bilanço USD/EUR ise TL'ye çevirmek için kur (THYAO, PGSUS vb.)."""
    info = yahoo(lambda: t.info) or {}
    pb = info.get("financialCurrency", "TRY") or "TRY"
    if pb == "TRY":
        return 1.0, pb
    fx = yahoo(lambda: yf.Ticker(f"{pb}TRY=X").fast_info["lastPrice"])
    return (float(fx) if fx else np.nan), pb


# ── TEK HİSSE ────────────────────────────────────────────
def analiz(ticker):
    t = yf.Ticker(f"{ticker}.IS")
    q = yahoo(lambda: t.quarterly_income_stmt)
    b = yahoo(lambda: t.quarterly_balance_sheet)
    if q is None or q.empty or b is None or b.empty:
        return None

    fiyat = yahoo(lambda: t.fast_info["lastPrice"])
    pay   = ilk(satir(b, "Ordinary Shares Number", "Share Issued"))
    if not fiyat or not np.isfinite(pay):
        return None
    kur, pb = finansal_kur(t)
    pd_tl = float(fiyat) * pay

    # Gelir tablosu (çeyreklik, TTM)
    ciro_s   = satir(q, "Total Revenue", "Operating Revenue")
    brut_s   = satir(q, "Gross Profit")
    favok_s  = satir(q, "EBITDA", "Normalized EBITDA")
    netkar_s = satir(q, "Net Income Common Stockholders", "Net Income")
    ozel_s   = satir(q, "Total Unusual Items")

    ciro, favok, netkar = ttm(ciro_s), ttm(favok_s), ttm(netkar_s)
    if not np.isfinite(ciro) or ciro <= 0 or not np.isfinite(favok):
        return None

    # Bilanço (son çeyrek, bir yıl önce)
    borc   = ilk(satir(b, "Total Debt"))
    nakit  = ilk(satir(b, "Cash Cash Equivalents And Short Term Investments",
                       "Cash And Cash Equivalents"))
    netborc = ilk(satir(b, "Net Debt"))
    if np.isfinite(borc) and np.isfinite(nakit):
        netborc = borc - nakit
    netborc = 0.0 if not np.isfinite(netborc) else netborc
    aktif  = ilk(satir(b, "Total Assets"))
    alacak_s = satir(b, "Accounts Receivable", "Receivables")
    mod    = ilk(satir(b, "Other Intangible Assets",
                       "Goodwill And Other Intangible Assets"))
    gizli  = np.nansum([
        ilk(satir(b, "Investment Properties")),
        ilk(satir(b, "Long Term Equity Investment",
                  "Investmentsin Associatesat Cost")),
        ilk(satir(b, "Assets Held For Sale Current",
                  "Non Current Assets Held For Sale")),
    ]) * kur
    kiralama = ilk(satir(b, "Capital Lease Obligations"))
    mdv      = ilk(satir(b, "Net PPE"))

    fd = pd_tl + netborc * kur
    fd_favok   = oran(fd, favok * kur) if favok > 0 else np.nan
    favok_marj = oran(favok, ciro)
    nb_favok   = oran(netborc, favok) if favok > 0 else np.nan

    # Büyüme: son çeyrek vs bir yıl önceki aynı çeyrek
    ciro_buyume = oran(ilk(ciro_s, 0), ilk(ciro_s, 4)) - 1 \
        if ciro_s is not None and len(ciro_s) > 4 else np.nan
    reel_buyume = (1 + ciro_buyume) / (1 + ENFLASYON_YILLIK) - 1 \
        if np.isfinite(ciro_buyume) else np.nan
    alacak_buyume = oran(ilk(alacak_s, 0), ilk(alacak_s, 4)) - 1 \
        if alacak_s is not None and len(alacak_s) > 4 else np.nan

    # Çeyreklik brüt marj oynaklığı (Onur tipi dengesiz bilanço)
    marj_oynak = np.nan
    if brut_s is not None and ciro_s is not None:
        m = (brut_s / ciro_s).iloc[:5].replace([np.inf, -np.inf], np.nan).dropna()
        if len(m) >= 3:
            marj_oynak = float(m.max() - m.min())

    # Temettü geçmişi (son 5 yıl)
    div = yahoo(lambda: t.dividends)
    temettu_var = None
    if div is not None:
        son5 = div[div.index >= pd.Timestamp.now(tz=div.index.tz) - pd.DateOffset(years=5)] \
            if len(div) else div
        temettu_var = len(son5) > 0

    # ── PUANLAMA ─────────────────────────────────────────
    puan, bayrak = 0, []

    # 1) Ucuzluk: FD/FAVÖK (yayıncının ana çarpanı; 5 altı "çok ucuz")
    if np.isfinite(fd_favok):
        if fd_favok <= 5:    puan += 3
        elif fd_favok <= 8:  puan += 2
        elif fd_favok <= 12: puan += 1
        elif fd_favok > 20:  puan -= 1
    else:
        bayrak.append("FAVOK_NEGATIF")

    # 2) Kalite: FAVÖK marjı (mülk sahibi → kira yok → yüksek marj)
    if np.isfinite(favok_marj):
        if favok_marj >= 0.25:   puan += 2
        elif favok_marj >= 0.15: puan += 1
        elif favok_marj < 0.03:  puan -= 1

    # 3) Bilanço: net nakit iyi, ağır borç kötü
    if netborc < 0:
        puan += 2; bayrak.append("NET_NAKIT")
    elif np.isfinite(nb_favok):
        if nb_favok <= 1.5: puan += 1
        elif nb_favok > 3:  puan -= 2; bayrak.append("YUKSEK_BORC")

    # 4) Enflasyon üstü (reel) büyüme
    if np.isfinite(reel_buyume):
        if reel_buyume >= 0.15:  puan += 2
        elif reel_buyume >= 0:   puan += 1
        else:                    bayrak.append("REEL_KUCULME")

    # 5) Gizli değer: iştirak + yatırım amaçlı gayrimenkul + satış amaçlı
    #    varlıklar piyasa değerine göre büyükse (Polisan, Menderes, Tınaztepe)
    gizli_oran = oran(gizli, pd_tl)
    if np.isfinite(gizli_oran) and gizli_oran >= 0.30:
        puan += 2; bayrak.append("GIZLI_DEGER")
    elif np.isfinite(gizli_oran) and gizli_oran >= 0.15:
        puan += 1

    # 6) Mülk sahibi (kira yükü yok) + yüksek marj (Gimat, Tınaztepe)
    if (np.isfinite(aktif) and np.isfinite(mdv) and mdv / aktif >= 0.40
            and (not np.isfinite(kiralama) or kiralama / aktif <= 0.02)
            and np.isfinite(favok_marj) and favok_marj >= 0.15):
        puan += 1; bayrak.append("MULK_SAHIBI")

    # 7) Az takip edilen küçük şirket
    if pd_tl <= KUCUK_PD_TL:
        puan += 1; bayrak.append("KUCUK")

    # ── UYARILAR (eksi) ──────────────────────────────────
    # Kamu/alacak riski: alacaklar cirodan çok daha hızlı büyüyor (Fonet)
    if (np.isfinite(alacak_buyume) and np.isfinite(ciro_buyume)
            and alacak_buyume - ciro_buyume > 0.30):
        puan -= 1; bayrak.append("ALACAK_SISMESI")

    # TMS 38: aktifleştirilmiş Ar-Ge şişkin → FAVÖK olduğundan iyi görünür
    if np.isfinite(mod) and np.isfinite(aktif) and mod / aktif >= 0.25:
        puan -= 1; bayrak.append("AKTIF_ARGE_TMS38")

    # Dengesiz çeyrekler → yıllık bak (Onur)
    if np.isfinite(marj_oynak) and marj_oynak >= 0.20:
        puan -= 1; bayrak.append("MARJ_OYNAK")

    # Temettü dağıtmayan şirket iskontolu fiyatlanır (Menderes)
    if temettu_var is False:
        puan -= 1; bayrak.append("TEMETTU_YOK")

    # ── SADECE BAYRAK (elle bak) ─────────────────────────
    # Polisan tipi: net zarar var ama FAVÖK güçlü ve ucuz → zarar
    # iştirak/kur farkı/durdurulan faaliyetten mi geliyor?
    if (np.isfinite(netkar) and netkar < 0 and favok > 0
            and np.isfinite(fd_favok) and fd_favok <= 10):
        bayrak.append("ZARAR_AMA_FAVOK_IYI")
    # Tek seferlik/olağan dışı kalemler kârı belirgin etkiliyor
    ozel = ttm(ozel_s)
    if np.isfinite(ozel) and np.isfinite(netkar) and netkar != 0 \
            and abs(ozel) >= 0.30 * abs(netkar):
        bayrak.append("TEK_SEFERLIK_KALEM")
    if pb != "TRY":
        bayrak.append(f"RAPOR_{pb}")

    yuzde = lambda x: round(x * 100, 1) if np.isfinite(x) else np.nan
    return {
        "HISSE": ticker,
        "PUAN": puan,
        "PD_mn": round(pd_tl / 1e6),
        "FD_mn": round(fd / 1e6) if np.isfinite(fd) else np.nan,
        "FD/FAVOK": round(fd_favok, 1) if np.isfinite(fd_favok) else np.nan,
        "FAVOK_MARJ%": yuzde(favok_marj),
        "NETBORC/FAVOK": round(nb_favok, 2) if np.isfinite(nb_favok) else np.nan,
        "CIRO_BUYUME%": yuzde(ciro_buyume),
        "REEL_BUYUME%": yuzde(reel_buyume),
        "ALACAK_BUYUME%": yuzde(alacak_buyume),
        "GIZLI_DEGER/PD%": yuzde(gizli_oran),
        "MOD/AKTIF%": yuzde(oran(mod, aktif)),
        "BRUT_MARJ_OYNAKLIK%": yuzde(marj_oynak),
        "TTM_NET_KAR_mn": round(netkar * kur / 1e6) if np.isfinite(netkar) else np.nan,
        "BAYRAKLAR": " ".join(bayrak),
    }


if __name__ == "__main__":
    import sys

    liste = sys.argv[1:] or [
        x for x in tickers if x not in HARIC and not x.endswith(HARIC_SONEK)
    ]
    print(f"⏳ {len(liste)} hisse temel tarama...\n")

    sonuclar, hatalar = [], []
    for i, tk in enumerate(liste):
        try:
            r = analiz(tk)
        except Exception as e:
            print(f"  {tk}: hata {e}")
            r = None
        (sonuclar.append(r) if r else hatalar.append(tk))
        time.sleep(BEKLEME_SN)
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(liste)} | Veri: {len(sonuclar)}")

    if not sonuclar:
        raise SystemExit("Hiç veri alınamadı (Yahoo hız sınırı?).")

    df = pd.DataFrame(sonuclar).sort_values(
        ["PUAN", "FD/FAVOK"], ascending=[False, True], na_position="last"
    ).reset_index(drop=True)
    aday = df[df["PUAN"] >= ESIK_PUAN].reset_index(drop=True)

    print(f"\n{'='*55}")
    print(f"  Taranan  : {len(df)}   Veri yok: {len(hatalar)}")
    print(f"  Aday     : {len(aday)} (PUAN >= {ESIK_PUAN})")
    print(f"{'='*55}\n")
    print(aday.to_string(index=False) if len(aday) else "Aday yok.")

    df.to_csv("temel_tarama.csv", index=False)
    aday.to_csv("temel_sinyal.csv", index=False)
    print("\n✅ temel_tarama.csv / temel_sinyal.csv kaydedildi")
