#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MUM TARAMA v1.4 — BIST Haftalık + Aylık Mum Formasyonu Tarayıcısı
=============================================================
- Kaggle üzerinde çalışmak için tasarlanmıştır.
- Günlük HAM (auto_adjust=False) OHLC verisini Yahoo Finance / yfinance üzerinden çeker.
- Mum geometrisi için temettü/split geriye-düzeltmesi KULLANILMAZ; TradingView ham mumlarıyla uyum hedeflenir.
- BIST sembol evreni kod içine gömülüdür (Evo/Fintables, 647 sembol).
- RSI / MACD / OBV / funnel / bilanço YOKTUR.
- Yalnızca fiyat, trend ve mum formasyonları kullanılır.
- Açık hafta/ay ASLA taranmaz; XIST işlem takvimiyle son tamamlanmış
  hafta ve ay belirlenir.
- B sınıfı formasyonlarda "TEYİT BEKLİYOR" ve sayısal teyit şartı verilir.
- Önceki dönemin B formasyonu son kapanışta teyit olduysa
  "BOĞA TEYİDİ" / "AYI TEYİDİ" olarak raporlanır.

Çıktılar:
    mum_tarama_sonuc.csv
    mum_tarama_haftalik.csv
    mum_tarama_aylik.csv
    mum_tarama_hatalar.csv

Kaggle:
    Notebook hücresine:
        !python mum_tarama.py

Not:
    İlk çalıştırmada eksikse yfinance ve exchange_calendars paketlerini kurar.
"""

import sys
import os
import subprocess
import warnings
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

warnings.filterwarnings("ignore")

def _ensure(pkg, import_name=None):
    import_name = import_name or pkg
    try:
        __import__(import_name)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", pkg])

_ensure("yfinance")
_ensure("exchange_calendars")

import numpy as np
import pandas as pd
import yfinance as yf
import exchange_calendars as xcals

# ---------------------------------------------------------------------------
# 0) AYARLAR
# ---------------------------------------------------------------------------

BIST_KODLARI = ['A1CAP', 'A1YEN', 'AAGYO', 'ACSEL', 'ADEL', 'ADESE', 'ADGYO', 'AEFES', 'AFYON', 'AGESA', 'AGHOL', 'AGROT', 'AGYO', 'AHGAZ', 'AHSGY', 'AKBNK', 'AKCNS', 'AKENR', 'AKFGY', 'AKFIS', 'AKFYE', 'AKGRT', 'AKHAN', 'AKMGY', 'AKSA', 'AKSEN', 'AKSGY', 'AKSUE', 'AKYHO', 'ALARK', 'ALBRK', 'ALBTN', 'ALCAR', 'ALCTL', 'ALFAS', 'ALGYO', 'ALKA', 'ALKIM', 'ALKLC', 'ALMAD', 'ALTNY', 'ALVES', 'ANELE', 'ANGEN', 'ANHYT', 'ANSGR', 'ARASE', 'ARCLK', 'ARDYZ', 'ARENA', 'ARFYE', 'ARMGD', 'ARSAN', 'ARTMS', 'ARZUM', 'ASELS', 'ASGYO', 'ASTOR', 'ASUZU', 'ATAGY', 'ATAKP', 'ATATP', 'ATATR', 'ATEKS', 'ATLAS', 'ATSYH', 'AVGYO', 'AVHOL', 'AVOD', 'AVPGY', 'AVTUR', 'AYCES', 'AYDEM', 'AYEN', 'AYES', 'AYGAZ', 'AZTEK', 'BAGFS', 'BAHKM', 'BAKAB', 'BALAT', 'BALSU', 'BANVT', 'BARMA', 'BASCM', 'BASGZ', 'BAYRK', 'BEGYO', 'BERA', 'BESLR', 'BESTE', 'BETAE', 'BEYAZ', 'BFREN', 'BIENY', 'BIGCH', 'BIGEN', 'BIGTK', 'BIMAS', 'BINBN', 'BINHO', 'BIOEN', 'BIZIM', 'BJKAS', 'BLCYT', 'BLUME', 'BMSCH', 'BMSTL', 'BNTAS', 'BOBET', 'BORLS', 'BORSK', 'BOSSA', 'BRISA', 'BRKO', 'BRKSN', 'BRKVY', 'BRLSM', 'BRMEN', 'BRSAN', 'BRYAT', 'BSOKE', 'BTCIM', 'BUCIM', 'BULGS', 'BURCE', 'BURVA', 'BVSAN', 'BYDNR', 'CANTE', 'CASA', 'CATES', 'CCOLA', 'CELHA', 'CEMAS', 'CEMTS', 'CEMZY', 'CEOEM', 'CGCAM', 'CIMSA', 'CLEBI', 'CMBTN', 'CMENT', 'CONSE', 'COSMO', 'CRDFA', 'CRFSA', 'CUSAN', 'CVKMD', 'CWENE', 'DAGHL', 'DAGI', 'DAPGM', 'DARDL', 'DCTTR', 'DENGE', 'DERHL', 'DERIM', 'DESA', 'DESPC', 'DEVA', 'DGATE', 'DGGYO', 'DGNMO', 'DIRIT', 'DITAS', 'DMRGD', 'DMSAS', 'DNISI', 'DOAS', 'DOBUR', 'DOCO', 'DOFER', 'DOFRB', 'DOGUB', 'DOHOL', 'DOKTA', 'DSTKF', 'DUNYH', 'DURDO', 'DURKN', 'DYOBY', 'DZGYO', 'EBEBK', 'ECILC', 'ECOGR', 'ECZYT', 'EDATA', 'EDIP', 'EFOR', 'EFORC', 'EGEEN', 'EGEGY', 'EGEPO', 'EGGUB', 'EGPRO', 'EGSER', 'EKDMR', 'EKGYO', 'EKIM', 'EKIZ', 'EKOS', 'EKSUN', 'ELITE', 'EMKEL', 'EMNIS', 'EMPAE', 'ENDAE', 'ENERY', 'ENJSA', 'ENKAI', 'ENPRA', 'ENSRI', 'ENTRA', 'EPLAS', 'ERBOS', 'ERCB', 'EREGL', 'ERSU', 'ESCAR', 'ESCOM', 'ESEN', 'ETILR', 'ETYAT', 'EUHOL', 'EUKYO', 'EUPWR', 'EUREN', 'EUYO', 'EYGYO', 'FADE', 'FENER', 'FLAP', 'FMIZP', 'FONET', 'FORMT', 'FORTE', 'FRIGO', 'FRMPL', 'FROTO', 'FZLGY', 'GARAN', 'GARFA', 'GATEG', 'GEDIK', 'GEDZA', 'GENIL', 'GENKM', 'GENTS', 'GEREL', 'GESAN', 'GIPTA', 'GLBMD', 'GLCVY', 'GLRMK', 'GLRYH', 'GLYHO', 'GMTAS', 'GOKNR', 'GOLDA', 'GOLTS', 'GOODY', 'GOZDE', 'GRNYO', 'GRSEL', 'GRTHO', 'GRTRK', 'GSDDE', 'GSDHO', 'GSRAY', 'GUBRF', 'GUNDG', 'GWIND', 'GZNMI', 'HALKB', 'HATEK', 'HATSN', 'HDFGS', 'HEDEF', 'HEKTS', 'HKTM', 'HLGYO', 'HOROZ', 'HRKET', 'HTTBT', 'HUBVC', 'HUNER', 'HURGZ', 'ICBCT', 'ICUGS', 'IDEAS', 'IDGYO', 'IEYHO', 'IHAAS', 'IHEVA', 'IHGZT', 'IHLAS', 'IHLGM', 'IHYAY', 'IMASM', 'INDES', 'INFO', 'INGRM', 'INTEK', 'INTEM', 'INVEO', 'INVES', 'IPEKE', 'ISATR', 'ISBIR', 'ISBTR', 'ISCTR', 'ISDMR', 'ISFIN', 'ISGSY', 'ISGYO', 'ISKPL', 'ISKUR', 'ISMEN', 'ISSEN', 'ISVEA', 'ISYAT', 'ITTFH', 'IZENR', 'IZFAS', 'IZINV', 'IZMDC', 'JANTS', 'KAPLM', 'KARCL', 'KAREL', 'KARSN', 'KARTN', 'KARYE', 'KATMR', 'KAYSE', 'KBORU', 'KCAER', 'KCHOL', 'KENT', 'KERVN', 'KERVT', 'KFEIN', 'KGYO', 'KIMMR', 'KLGYO', 'KLKIM', 'KLMSN', 'KLNMA', 'KLRHO', 'KLSER', 'KLSYN', 'KLYPV', 'KMPUR', 'KNFRT', 'KOCMT', 'KONKA', 'KONTR', 'KONYA', 'KOPOL', 'KORDS', 'KOTON', 'KOZAA', 'KOZAL', 'KRDMA', 'KRDMB', 'KRDMD', 'KRGYO', 'KRONT', 'KRPLS', 'KRSTL', 'KRTEK', 'KRVGD', 'KSTUR', 'KTLEV', 'KTSKR', 'KUTPO', 'KUVVA', 'KUYAS', 'KZBGY', 'KZGYO', 'LIDER', 'LIDFA', 'LILAK', 'LINK', 'LKMNH', 'LMKDC', 'LOGO', 'LRSHO', 'LUKSK', 'LXGYO', 'LYDHO', 'LYDYE', 'MAALT', 'MACKO', 'MAGEN', 'MAKIM', 'MAKTK', 'MANAS', 'MARBL', 'MARKA', 'MARMR', 'MARTI', 'MASFN', 'MAVI', 'MCARD', 'MEDTR', 'MEGAP', 'MEGMT', 'MEKAG', 'MEPET', 'MERCN', 'MERIT', 'MERKO', 'METEN', 'METRO', 'METUR', 'MEYSU', 'MGROS', 'MHRGY', 'MIATK', 'MIPAZ', 'MMCAS', 'MNDRS', 'MNDTR', 'MOBTL', 'MOGAN', 'MOPAS', 'MPARK', 'MRGYO', 'MRSHL', 'MSGYO', 'MTRKS', 'MTRYO', 'MZHLD', 'NATEN', 'NETAS', 'NETCD', 'NIBAS', 'NTGAZ', 'NTHOL', 'NUGYO', 'NUHCM', 'OBAMS', 'OBASE', 'ODAS', 'ODINE', 'OFSYM', 'ONCSM', 'ONRYT', 'ORCAY', 'ORGE', 'ORMA', 'ORZAX', 'OSMEN', 'OSTIM', 'OTKAR', 'OTTO', 'OYAKC', 'OYAYO', 'OYLUM', 'OYYAT', 'OZATD', 'OZGYO', 'OZKGY', 'OZRDN', 'OZSUB', 'OZYSR', 'PAGYO', 'PAHOL', 'PAMEL', 'PAPIL', 'PARSN', 'PASEU', 'PATEK', 'PCILT', 'PEHOL', 'PEKGY', 'PENGD', 'PENTA', 'PETKM', 'PETUN', 'PGSUS', 'PINSU', 'PKART', 'PKENT', 'PLTUR', 'PNLSN', 'PNSUT', 'POLHO', 'POLTK', 'PRDGS', 'PRKAB', 'PRKME', 'PRZMA', 'PSDTC', 'PSGYO', 'QNBFB', 'QNBFK', 'QNBFL', 'QNBTR', 'QUAGR', 'QUICK', 'RALYH', 'RAYSG', 'REEDR', 'RGYAS', 'RNPOL', 'RODRG', 'ROYAL', 'RTALB', 'RUBNS', 'RUZYE', 'RYGYO', 'RYSAS', 'SAFKR', 'SAHOL', 'SAMAT', 'SANEL', 'SANFM', 'SANKO', 'SARAE', 'SARKY', 'SASA', 'SAYAS', 'SDTTR', 'SEGMN', 'SEGYO', 'SEKFK', 'SEKUR', 'SELEC', 'SELGD', 'SELVA', 'SERNT', 'SEYKM', 'SILVR', 'SISE', 'SKBNK', 'SKTAS', 'SKYLP', 'SKYMD', 'SMART', 'SMRTG', 'SMRVA', 'SNGYO', 'SNICA', 'SNKRN', 'SNPAM', 'SODSN', 'SOHOE', 'SOKE', 'SOKM', 'SONME', 'SRVGY', 'SSAAT', 'SUMAS', 'SUNTK', 'SURGY', 'SUWEN', 'SVGYO', 'TABGD', 'TARKM', 'TATEN', 'TATGD', 'TAVHL', 'TBORG', 'TCELL', 'TCKRC', 'TDGYO', 'TEHOL', 'TEKTU', 'TERA', 'TETMT', 'TEZOL', 'TGSAS', 'THYAO', 'TKFEN', 'TKNSA', 'TLMAN', 'TMPOL', 'TMSN', 'TNZTP', 'TOASO', 'TRALT', 'TRCAS', 'TRENJ', 'TRGYO', 'TRHOL', 'TRILC', 'TRMET', 'TSGYO', 'TSKB', 'TSPOR', 'TTKOM', 'TTRAK', 'TUCLK', 'TUKAS', 'TUPRS', 'TUREX', 'TURGG', 'TURSG', 'UCAYM', 'UFUK', 'ULAS', 'ULKER', 'ULUFA', 'ULUSE', 'ULUUN', 'UMPAS', 'UNLU', 'USAK', 'UZERB', 'VAKBN', 'VAKFA', 'VAKFN', 'VAKKO', 'VANGD', 'VBTYZ', 'VERTU', 'VERUS', 'VESBE', 'VESTL', 'VKFYO', 'VKGYO', 'VKING', 'VRGYO', 'VSNMD', 'YAPRK', 'YATAS', 'YAYLA', 'YBTAS', 'YEOTK', 'YESIL', 'YGGYO', 'YGYO', 'YIGIT', 'YKBNK', 'YKSLN', 'YONGA', 'YUNSA', 'YYAPI', 'YYLGD', 'ZEDUR', 'ZERGY', 'ZGYO', 'ZOREN', 'ZRGYO']
YAHOO_KODLARI = [f"{k}.IS" for k in BIST_KODLARI]

VERI_PERIYODU = "5y"
BATCH_SIZE = 60
MIN_GUNLUK_SATIR = 25

# Trend yalnızca fiyattan ölçülür; indikatör değildir.
TREND_LOOKBACK = 5
MIN_TREND_NET_MOVE = 0.03      # 5 mumda en az yaklaşık %3 net hareket
MIN_SLOPE_PER_BAR = 0.003      # regresyon eğimi: mum başına yaklaşık %0.3
MIN_DIRECTIONAL_RATIO = 0.50   # fiyat değişimlerinin en az yarısı trend yönünde

# Mum toleransları
DOJI_BODY_RATIO = 0.10
SMALL_BODY_FACTOR = 0.40
LONG_BODY_FACTOR = 1.00

IST = ZoneInfo("Europe/Istanbul")
BUILD_ID = "MUM_TARAMA_2026-08-11_v1.7_STRICT_RAW_OHLC"

SINIF = {
    "Yutan Boğa": "A",
    "Morning Star": "A",
    "Three Inside Up": "A",
    "Hammer": "B",
    "Ters Hammer": "B",
    "Piercing": "B",
    "Boğa Harami": "B",
    "Dragonfly Doji": "C",

    "Yutan Ayı": "A",
    "Evening Star": "A",
    "Three Inside Down": "A",
    "Shooting Star": "B",
    "Hanging Man": "B",
    "Dark Cloud": "B",
    "Ayı Harami": "B",
    "Gravestone Doji": "C",
}

YON = {
    "Yutan Boğa": "BOĞA",
    "Morning Star": "BOĞA",
    "Three Inside Up": "BOĞA",
    "Hammer": "BOĞA",
    "Ters Hammer": "BOĞA",
    "Piercing": "BOĞA",
    "Boğa Harami": "BOĞA",
    "Dragonfly Doji": "BOĞA",

    "Yutan Ayı": "AYI",
    "Evening Star": "AYI",
    "Three Inside Down": "AYI",
    "Shooting Star": "AYI",
    "Hanging Man": "AYI",
    "Dark Cloud": "AYI",
    "Ayı Harami": "AYI",
    "Gravestone Doji": "AYI",
}

FORM_UZUNLUK = {
    "Yutan Boğa": 2,
    "Morning Star": 3,
    "Three Inside Up": 3,
    "Hammer": 1,
    "Ters Hammer": 1,
    "Piercing": 2,
    "Boğa Harami": 2,
    "Dragonfly Doji": 1,

    "Yutan Ayı": 2,
    "Evening Star": 3,
    "Three Inside Down": 3,
    "Shooting Star": 1,
    "Hanging Man": 1,
    "Dark Cloud": 2,
    "Ayı Harami": 2,
    "Gravestone Doji": 1,
}

# ---------------------------------------------------------------------------
# 1) BIST İŞLEM TAKVİMİ
# ---------------------------------------------------------------------------

def xist_takvim():
    """
    exchange_calendars içindeki XIST takvimini kullanır.
    Böylece cuma/ayın 31'i varsayımı yapılmaz; resmi tatiller hesaba katılır.
    """
    bugun = datetime.now(IST).date()
    basla = bugun - timedelta(days=365 * 7)
    bitir = bugun + timedelta(days=45)
    return xcals.get_calendar("XIST", start=str(basla), end=str(bitir))


def son_tamamlanmis_seans(cal):
    """
    Şu an itibarıyla kapanışı gerçekleşmiş son XIST seansını döndürür.
    Gün içinde çalıştırılırsa bugünkü açık seansı tamamlanmış saymaz.
    """
    now_utc = pd.Timestamp.now(tz="UTC")
    sch = cal.schedule
    closed = sch[sch["close"] <= now_utc]
    if closed.empty:
        raise RuntimeError("Tamamlanmış XIST seansı bulunamadı.")
    return pd.Timestamp(closed.index[-1]).tz_localize(None).normalize()


def donem_son_seans_haritasi(cal, frekans):
    sessions = pd.DatetimeIndex(cal.sessions).tz_localize(None)
    s = pd.Series(sessions, index=sessions)
    if frekans == "W":
        keys = sessions.to_period("W-FRI")
    else:
        keys = sessions.to_period("M")
    return s.groupby(keys).max().to_dict()


def son_tamamlanmis_donem_tarihi(cal, frekans, son_seans):
    """
    Piyasa geneli için son tamamlanmış haftanın/ayın gerçek son XIST seansını verir.
    Tek bir hissenin Yahoo verisinin geride kalması bu tarihi değiştiremez.
    """
    m = donem_son_seans_haritasi(cal, frekans)
    adaylar = [
        pd.Timestamp(v).tz_localize(None).normalize() if getattr(pd.Timestamp(v), "tzinfo", None) else pd.Timestamp(v).normalize()
        for v in m.values()
        if pd.notna(v)
    ]
    adaylar = [v for v in adaylar if v <= son_seans]
    if not adaylar:
        raise RuntimeError(f"Son tamamlanmış {frekans} dönemi bulunamadı.")
    return max(adaylar)


# ---------------------------------------------------------------------------
# 2) YAHOO FINANCE — BATCH + RETRY
# ---------------------------------------------------------------------------

def _tek_ticker_df(raw, ticker):
    if raw is None or len(raw) == 0:
        return pd.DataFrame()

    if isinstance(raw.columns, pd.MultiIndex):
        lvl0 = set(raw.columns.get_level_values(0))
        lvl1 = set(raw.columns.get_level_values(1))

        if ticker in lvl0:
            d = raw[ticker].copy()
        elif ticker in lvl1:
            d = raw.xs(ticker, axis=1, level=1).copy()
        else:
            return pd.DataFrame()
    else:
        d = raw.copy()

    cols = {str(c).lower(): c for c in d.columns}
    gerekli = ["open", "high", "low", "close"]
    if not all(x in cols for x in gerekli):
        return pd.DataFrame()

    out = pd.DataFrame({
        "acilis": pd.to_numeric(d[cols["open"]], errors="coerce"),
        "yuksek": pd.to_numeric(d[cols["high"]], errors="coerce"),
        "dusuk": pd.to_numeric(d[cols["low"]], errors="coerce"),
        "kapanis": pd.to_numeric(d[cols["close"]], errors="coerce"),
    })
    out.index = pd.to_datetime(out.index).tz_localize(None).normalize()
    out = out[~out.index.duplicated(keep="last")]
    out = out.dropna(subset=["acilis", "yuksek", "dusuk", "kapanis"])
    return out.sort_index()


def yahoo_veri_indir():
    """
    647 hisseyi batch halinde indirir.
    Batch içinde gelmeyen ticker'ları tek tek retry eder.
    """
    veriler = {}
    hatalar = []

    print(f"Yahoo Finance: {len(YAHOO_KODLARI)} BIST sembolü indiriliyor...")

    for start in range(0, len(YAHOO_KODLARI), BATCH_SIZE):
        batch = YAHOO_KODLARI[start:start + BATCH_SIZE]
        print(f"  Batch {start//BATCH_SIZE + 1} / {(len(YAHOO_KODLARI)-1)//BATCH_SIZE + 1}")

        try:
            raw = yf.download(
                tickers=batch,
                period=VERI_PERIYODU,
                interval="1d",
                group_by="ticker",
                auto_adjust=False,
                actions=False,
                threads=True,
                progress=False,
                timeout=25,
            )
        except Exception:
            raw = pd.DataFrame()

        eksikler = []
        for ticker in batch:
            d = _tek_ticker_df(raw, ticker)
            if len(d) >= MIN_GUNLUK_SATIR:
                veriler[ticker[:-3]] = d
            else:
                eksikler.append(ticker)

        # Sorunlu sembol tüm batch'i bozmasın: tekil retry.
        for ticker in eksikler:
            try:
                one = yf.download(
                    tickers=ticker,
                    period=VERI_PERIYODU,
                    interval="1d",
                    auto_adjust=False,
                    actions=False,
                    threads=False,
                    progress=False,
                    timeout=20,
                    multi_level_index=False,
                )
                d = _tek_ticker_df(one, ticker)
                if len(d) >= MIN_GUNLUK_SATIR:
                    veriler[ticker[:-3]] = d
                else:
                    hatalar.append((ticker[:-3], "Yahoo verisi yok / yetersiz"))
            except Exception as e:
                hatalar.append((ticker[:-3], f"Yahoo hata: {str(e)[:120]}"))

    return veriler, hatalar


# ---------------------------------------------------------------------------
# 3) GÜNLÜKTEN TAMAMLANMIŞ HAFTALIK / AYLIK MUM
# ---------------------------------------------------------------------------

def periyoda_cevir(gunluk, frekans, cal, son_seans):
    """
    Günlük Yahoo verisini W/M OHLC'ye çevirir.
    Sadece XIST takvimine göre tamamen kapanmış dönemleri bırakır.
    """
    d = gunluk.copy()
    d = d[d.index <= son_seans]
    if d.empty:
        return pd.DataFrame()

    if frekans == "W":
        key = d.index.to_period("W-FRI")
    else:
        key = d.index.to_period("M")

    z = d.copy()
    z["_period"] = key

    out = z.groupby("_period").agg(
        ilk_islem_gunu=("acilis", lambda x: x.index.min()),
        son_veri_gunu=("acilis", lambda x: x.index.max()),
        acilis=("acilis", "first"),
        yuksek=("yuksek", "max"),
        dusuk=("dusuk", "min"),
        kapanis=("kapanis", "last"),
    )

    last_session_map = donem_son_seans_haritasi(cal, frekans)
    out["resmi_son_seans"] = [last_session_map.get(p, pd.NaT) for p in out.index]

    # v1.5 FIX — Bir hissenin haftalık/aylık mumu, ilgili dönemde işlem gördüğü
    # halde dönemin RESMİ son XIST seansında veri yok diye düşürülmemeli.
    # Eski koşul `son_veri_gunu >= resmi_son_seans` bazı haftaları tamamen
    # siliyor; böylece formasyon motoru i-1 yerine fiilen i-2 mumu ile
    # karşılaştırma yapıyordu (örn. 31 Temmuz haftasını atlayıp 24 Temmuz).
    #
    # Tamamlanmış dönem kontrolü yalnızca XIST takviminden yapılır. Groupby'ya
    # girmiş olması zaten o dönemde hisseye ait en az bir günlük OHLC bulunduğu
    # anlamına gelir. Trend tanımları ve formasyon geometrisi DEĞİŞTİRİLMEDİ.
    out = out[
        out["resmi_son_seans"].notna()
        & (out["resmi_son_seans"] <= son_seans)
    ].copy()

    # Etiket resmi dönem sonu olarak kalır; OHLC ise o dönem içindeki gerçek
    # ilk/son işlem verilerinden üretilir. Böylece ardışık periyotlar korunur.
    out["tarih"] = out["resmi_son_seans"]
    return out.reset_index(drop=True)


# ---------------------------------------------------------------------------
# 4) MUM ANATOMİSİ + SAF FİYAT TRENDİ
# ---------------------------------------------------------------------------

def anatomi(d):
    x = d.copy()
    x["govde"] = (x["kapanis"] - x["acilis"]).abs()
    x["aralik"] = (x["yuksek"] - x["dusuk"]).replace(0, np.nan)
    x["ust_golge"] = x["yuksek"] - x[["acilis", "kapanis"]].max(axis=1)
    x["alt_golge"] = x[["acilis", "kapanis"]].min(axis=1) - x["dusuk"]
    x["yesil"] = x["kapanis"] > x["acilis"]
    x["kirmizi"] = x["kapanis"] < x["acilis"]
    x["govde_orani"] = x["govde"] / x["aralik"]
    x["ort_govde10"] = x["govde"].shift(1).rolling(10, min_periods=5).mean()
    return x


def trend_var(d, formasyon_baslangic_i, yon):
    """
    Trend yalnızca FORMASYONDAN ÖNCEKİ mumlarla ölçülür.
    Look-ahead yoktur.

    3 fiyat şartından en az 2'si aranır:
      1) net hareket >= MIN_TREND_NET_MOVE
      2) regresyon eğimi doğru yönde ve yeterli
      3) mumlar arası değişimlerin çoğunluğu doğru yönde
    """
    end = formasyon_baslangic_i - 1
    start = end - TREND_LOOKBACK + 1
    if start < 0 or end < start:
        return False

    c = d["kapanis"].iloc[start:end + 1].astype(float)
    if len(c) < TREND_LOOKBACK or c.iloc[0] <= 0:
        return False

    net = c.iloc[-1] / c.iloc[0] - 1
    xx = np.arange(len(c), dtype=float)
    slope = np.polyfit(xx, c.values, 1)[0] / max(c.mean(), 1e-12)
    diffs = c.diff().dropna()

    # Aynı geçmişin hem yükseliş hem düşüş sayılmasını engelle:
    # net hareket + regresyon eğimi + yönlü mum oranı birlikte aynı yönde olmalı.
    if yon == "dusus":
        return bool(
            net <= -MIN_TREND_NET_MOVE
            and slope <= -MIN_SLOPE_PER_BAR
            and (diffs < 0).mean() >= MIN_DIRECTIONAL_RATIO
        )
    else:
        return bool(
            net >= MIN_TREND_NET_MOVE
            and slope >= MIN_SLOPE_PER_BAR
            and (diffs > 0).mean() >= MIN_DIRECTIONAL_RATIO
        )


# ---------------------------------------------------------------------------
# 5) FORMASYON TESPİTİ
# ---------------------------------------------------------------------------

def _bar(d, i):
    r = d.iloc[i]
    return {
        "o": float(r.acilis),
        "h": float(r.yuksek),
        "l": float(r.dusuk),
        "c": float(r.kapanis),
        "body": float(r.govde),
        "range": float(r.aralik) if pd.notna(r.aralik) else 0.0,
        "up": float(r.ust_golge),
        "down": float(r.alt_golge),
        "body_ratio": float(r.govde_orani) if pd.notna(r.govde_orani) else np.nan,
        "green": bool(r.yesil),
        "red": bool(r.kirmizi),
        "avgbody": float(r.ort_govde10) if pd.notna(r.ort_govde10) else np.nan,
    }


def formasyonlari_bul(d, i):
    """
    i indeksinde tamamlanan bütün geçerli formasyonları döndürür.

    ÖNEMLİ:
    - Trend mantığına DOKUNULMADI. Her formasyonun ilk mumundan önce
      mevcut trend_var() fonksiyonu aynen kullanılır.
    - Formasyon geometrileri v1.6'da baştan denetlendi ve simetrik hale getirildi.
    - BIST için gap zorunluluğu kullanılmaz; fakat Morning/Evening Star'da
      ortadaki mumun gerçekten "star bölgesinde" kalması şarttır.
    """
    bulunan = []
    if i < 0 or i >= len(d):
        return bulunan

    b0 = _bar(d, i)
    b1 = _bar(d, i - 1) if i >= 1 else None
    b2 = _bar(d, i - 2) if i >= 2 else None

    def _long(b):
        # Ortalama gövde mevcutsa en az ortalama kadar; yoksa yalnızca yön/range
        # şartlarına dayan. Bu, mevcut LONG_BODY_FACTOR ayarını korur.
        return pd.isna(b["avgbody"]) or b["body"] >= LONG_BODY_FACTOR * b["avgbody"]

    def _non_doji(b):
        return pd.notna(b["body_ratio"]) and b["body_ratio"] > DOJI_BODY_RATIO

    def _body_top(b):
        return max(b["o"], b["c"])

    def _body_bottom(b):
        return min(b["o"], b["c"])

    def _body_inside(inner, outer):
        return _body_bottom(inner) >= _body_bottom(outer) and _body_top(inner) <= _body_top(outer)

    # ------------------------------------------------------------------
    # 1 MUMLU BOĞA
    # ------------------------------------------------------------------
    if trend_var(d, i, "dusus"):
        eps = max(b0["body"], b0["range"] * 0.03, 1e-12)

        # Hammer: küçük gerçek gövde üst bölgede, uzun alt gölge, çok küçük üst gölge.
        # Doji'ler ayrı sınıfta tutulur.
        hammer = (
            _non_doji(b0)
            and b0["down"] >= 2.0 * eps
            and b0["up"] <= 0.35 * eps
            and b0["body_ratio"] <= 0.40
            and _body_top(b0) >= b0["l"] + 0.60 * b0["range"]
        )
        if hammer:
            bulunan.append("Hammer")

        # Inverted Hammer: küçük gövde alt bölgede, uzun üst gölge.
        inv_hammer = (
            _non_doji(b0)
            and b0["up"] >= 2.0 * eps
            and b0["down"] <= 0.35 * eps
            and b0["body_ratio"] <= 0.40
            and _body_bottom(b0) <= b0["l"] + 0.40 * b0["range"]
        )
        if inv_hammer:
            bulunan.append("Ters Hammer")

        dragonfly = (
            b0["body_ratio"] <= DOJI_BODY_RATIO
            and b0["down"] >= 2.5 * max(b0["up"], b0["range"] * 0.02)
            and b0["down"] >= 0.60 * b0["range"]
            and _body_top(b0) >= b0["l"] + 0.75 * b0["range"]
        )
        if dragonfly:
            bulunan.append("Dragonfly Doji")

    # ------------------------------------------------------------------
    # 1 MUMLU AYI
    # ------------------------------------------------------------------
    if trend_var(d, i, "yukselis"):
        eps = max(b0["body"], b0["range"] * 0.03, 1e-12)

        shooting = (
            _non_doji(b0)
            and b0["up"] >= 2.0 * eps
            and b0["down"] <= 0.35 * eps
            and b0["body_ratio"] <= 0.40
            and _body_bottom(b0) <= b0["l"] + 0.40 * b0["range"]
        )
        if shooting:
            bulunan.append("Shooting Star")

        hanging = (
            _non_doji(b0)
            and b0["down"] >= 2.0 * eps
            and b0["up"] <= 0.35 * eps
            and b0["body_ratio"] <= 0.40
            and _body_top(b0) >= b0["l"] + 0.60 * b0["range"]
        )
        if hanging:
            bulunan.append("Hanging Man")

        gravestone = (
            b0["body_ratio"] <= DOJI_BODY_RATIO
            and b0["up"] >= 2.5 * max(b0["down"], b0["range"] * 0.02)
            and b0["up"] >= 0.60 * b0["range"]
            and _body_bottom(b0) <= b0["l"] + 0.25 * b0["range"]
        )
        if gravestone:
            bulunan.append("Gravestone Doji")

    if i >= 1:
        # ------------------------------------------------------------------
        # 2 MUMLU BOĞA
        # ------------------------------------------------------------------
        if trend_var(d, i - 1, "dusus"):
            first_long = _long(b1)

            # Bullish Engulfing: kırmızı gövdeyi yeşil gövde tamamen yutar.
            if (
                b1["red"] and b0["green"]
                and _non_doji(b1) and _non_doji(b0)
                and b0["o"] <= b1["c"]
                and b0["c"] >= b1["o"]
                and b0["body"] > b1["body"]
            ):
                bulunan.append("Yutan Boğa")

            # Piercing: uzun kırmızı ilk mum; ikinci yeşil mum ilk gövdenin
            # orta noktasının üstünde fakat ilk açılışın altında kapanır.
            # Gap zorunlu değil; açılış ilk kapanış civarında/altında olmalı.
            if (
                b1["red"] and first_long and b0["green"]
                and _non_doji(b1) and _non_doji(b0)
                and b0["o"] <= b1["c"]
                and b0["c"] > (b1["o"] + b1["c"]) / 2
                and b0["c"] < b1["o"]
            ):
                bulunan.append("Piercing")

            # Bullish Harami: küçük yeşil gövde, uzun kırmızı gövdenin içinde.
            if (
                b1["red"] and first_long and b0["green"]
                and _non_doji(b1)
                and _body_inside(b0, b1)
                and b0["body"] <= SMALL_BODY_FACTOR * max(b1["body"], 1e-12)
            ):
                bulunan.append("Boğa Harami")

        # ------------------------------------------------------------------
        # 2 MUMLU AYI
        # ------------------------------------------------------------------
        if trend_var(d, i - 1, "yukselis"):
            first_long = _long(b1)

            if (
                b1["green"] and b0["red"]
                and _non_doji(b1) and _non_doji(b0)
                and b0["o"] >= b1["c"]
                and b0["c"] <= b1["o"]
                and b0["body"] > b1["body"]
            ):
                bulunan.append("Yutan Ayı")

            # Dark Cloud Cover: Piercing'in tam simetriği.
            if (
                b1["green"] and first_long and b0["red"]
                and _non_doji(b1) and _non_doji(b0)
                and b0["o"] >= b1["c"]
                and b0["c"] < (b1["o"] + b1["c"]) / 2
                and b0["c"] > b1["o"]
            ):
                bulunan.append("Dark Cloud")

            if (
                b1["green"] and first_long and b0["red"]
                and _non_doji(b1)
                and _body_inside(b0, b1)
                and b0["body"] <= SMALL_BODY_FACTOR * max(b1["body"], 1e-12)
            ):
                bulunan.append("Ayı Harami")

    if i >= 2:
        # ------------------------------------------------------------------
        # 3 MUMLU BOĞA
        # ------------------------------------------------------------------
        if trend_var(d, i - 2, "dusus"):
            first_long = _long(b2)
            third_long = _long(b0)
            middle_small = b1["body"] <= SMALL_BODY_FACTOR * max(b2["body"], 1e-12)
            first_mid = (b2["o"] + b2["c"]) / 2

            # Morning Star — sıkı BIST/no-gap tanımı:
            # 1) İlk mum uzun ve kırmızı olmalı.
            # 2) Orta mum gerçekten "star" olmalı: küçük gövde ve ilk kırmızı
            #    gövdenin EN ALT %25'lik bölümünde / altında kalmalı. Sadece alt
            #    yarıda olmak yeterli değildir; bu gevşeklik ANSGR/BANVT tipi
            #    yalancı pozitif üretiyordu.
            # 3) Üçüncü mum uzun ve yeşil olmalı, ilk mumun orta noktasını aşmalı.
            first_body_bottom = _body_bottom(b2)
            star_ceiling = first_body_bottom + 0.25 * b2["body"]
            middle_in_star_zone = _body_top(b1) <= star_ceiling
            if (
                b2["red"] and first_long and _non_doji(b2)
                and middle_small and middle_in_star_zone
                and b0["green"] and third_long and _non_doji(b0)
                and b0["c"] > first_mid
                and b0["c"] > _body_top(b1)
            ):
                bulunan.append("Morning Star")

            # Three Inside Up = sıkı Bullish Harami + üçüncü mum teyidi.
            # Orta mum yalnızca ilk gövdenin içinde olmakla kalmaz, belirgin
            # biçimde küçük olmalıdır; aksi halde sıradan iki mumluk toparlanma
            # yanlışlıkla Three Inside Up sayılabilir.
            if (
                b2["red"] and first_long and _non_doji(b2)
                and b1["green"] and _non_doji(b1)
                and _body_inside(b1, b2)
                and b1["body"] <= SMALL_BODY_FACTOR * max(b2["body"], 1e-12)
                and b0["green"] and _non_doji(b0)
                and b0["c"] > b2["o"]
            ):
                bulunan.append("Three Inside Up")

        # ------------------------------------------------------------------
        # 3 MUMLU AYI
        # ------------------------------------------------------------------
        if trend_var(d, i - 2, "yukselis"):
            first_long = _long(b2)
            third_long = _long(b0)
            middle_small = b1["body"] <= SMALL_BODY_FACTOR * max(b2["body"], 1e-12)
            first_mid = (b2["o"] + b2["c"]) / 2

            # Evening Star — Morning Star'ın tam simetriği.
            first_body_top = _body_top(b2)
            star_floor = first_body_top - 0.25 * b2["body"]
            middle_in_star_zone = _body_bottom(b1) >= star_floor
            if (
                b2["green"] and first_long and _non_doji(b2)
                and middle_small and middle_in_star_zone
                and b0["red"] and third_long and _non_doji(b0)
                and b0["c"] < first_mid
                and b0["c"] < _body_bottom(b1)
            ):
                bulunan.append("Evening Star")

            # Three Inside Down = sıkı Bearish Harami + üçüncü mum teyidi.
            if (
                b2["green"] and first_long and _non_doji(b2)
                and b1["red"] and _non_doji(b1)
                and _body_inside(b1, b2)
                and b1["body"] <= SMALL_BODY_FACTOR * max(b2["body"], 1e-12)
                and b0["red"] and _non_doji(b0)
                and b0["c"] < b2["o"]
            ):
                bulunan.append("Three Inside Down")

    # Aynı isim birden fazla yoldan gelirse tekilleştir.
    return list(dict.fromkeys(bulunan))


# ---------------------------------------------------------------------------
# 6) TEYİT / GEÇERSİZLİK SEVİYELERİ
# ---------------------------------------------------------------------------

def formasyon_araligi(d, i, formasyon):
    n = FORM_UZUNLUK[formasyon]
    start = i - n + 1
    parca = d.iloc[start:i + 1]
    return float(parca["yuksek"].max()), float(parca["dusuk"].min())


def seviyeler(d, i, formasyon):
    tepe, dip = formasyon_araligi(d, i, formasyon)
    yon = YON[formasyon]

    if yon == "BOĞA":
        teyit = tepe
        teyit_notu = f"Sonraki {'haftalık' if False else ''} kapanış > {teyit:.2f}"
        gecersiz = dip
        gecersiz_notu = f"{gecersiz:.2f} altı formasyonu bozar"
    else:
        teyit = dip
        teyit_notu = f"Sonraki kapanış < {teyit:.2f}"
        gecersiz = tepe
        gecersiz_notu = f"{gecersiz:.2f} üstü formasyonu bozar"

    return tepe, dip, teyit, teyit_notu, gecersiz, gecersiz_notu


def teyit_edildi_mi(d, form_i, confirm_i, formasyon):
    _, _, teyit, _, gecersiz, _ = seviyeler(d, form_i, formasyon)
    close = float(d["kapanis"].iloc[confirm_i])

    if YON[formasyon] == "BOĞA":
        return close > teyit, close < gecersiz
    return close < teyit, close > gecersiz


# ---------------------------------------------------------------------------
# 7) SON TAMAMLANMIŞ DÖNEMİ TARA
# ---------------------------------------------------------------------------

def hisse_tara(kod, d, periyot_adi):
    """
    İki şey arar:
    A) Son tamamlanmış mumda yeni formasyon
    B) Bir önceki mumdaki B formasyonu son mumda teyit edilmiş mi?
    """
    if len(d) < max(15, TREND_LOOKBACK + 5):
        return []

    d = anatomi(d)
    son_i = len(d) - 1
    onceki_i = son_i - 1
    kayitlar = []

    def ekle(form_i, formasyon, durum, sinyal_tarihi, teyit_tarihi=None):
        sinif = SINIF[formasyon]
        yon = YON[formasyon]
        tepe, dip, teyit, teyit_notu, gecersiz, gecersiz_notu = seviyeler(d, form_i, formasyon)

        # Teyit notu yalnızca gerektiği yerde aksiyon üretir.
        donem_kelime = "haftalık" if periyot_adi == "HAFTALIK" else "aylık"
        if sinif == "A":
            teyit_notu = "Formasyon kendi içinde teyitli"
        elif sinif == "C":
            teyit_notu = "Tek başına sinyal değil; izleme"
        elif "TEYİDİ" in durum:
            if yon == "BOĞA":
                teyit_notu = f"Teyit geldi: {donem_kelime} kapanış > {teyit:.2f}"
            else:
                teyit_notu = f"Teyit geldi: {donem_kelime} kapanış < {teyit:.2f}"
        else:
            if yon == "BOĞA":
                teyit_notu = f"Sonraki {donem_kelime} kapanış > {teyit:.2f}"
            else:
                teyit_notu = f"Sonraki {donem_kelime} kapanış < {teyit:.2f}"

        kayitlar.append({
            "build": BUILD_ID,
            "kod": kod,
            "periyot": periyot_adi,
            "formasyon": formasyon,
            "sinif": sinif,
            "yon": yon,
            "durum": durum,
            "formasyon_tarihi": pd.Timestamp(sinyal_tarihi).date(),
            "teyit_tarihi": pd.Timestamp(teyit_tarihi).date() if teyit_tarihi is not None else "",
            "kapanis": round(float(d["kapanis"].iloc[-1]), 2),
            "formasyon_tepe": round(tepe, 2),
            "formasyon_dip": round(dip, 2),
            "teyit_seviyesi": round(teyit, 2),
            "teyit_sarti": teyit_notu,
            "gecersizlik_seviyesi": round(gecersiz, 2),
            "gecersizlik_notu": gecersiz_notu,
        })

    # A) Son mumda yeni formasyon
    for formasyon in formasyonlari_bul(d, son_i):
        sinif = SINIF[formasyon]
        yon = YON[formasyon]

        if sinif == "A":
            durum = f"{yon} TEYİDİ"
        elif sinif == "B":
            durum = "TEYİT BEKLİYOR"
        else:
            durum = "İZLE"

        ekle(
            son_i,
            formasyon,
            durum,
            d["tarih"].iloc[son_i],
        )

    # B) Önceki dönemde B çıktıysa, son dönemde teyit gerçekleşmiş olabilir.
    if onceki_i >= 0:
        for formasyon in formasyonlari_bul(d, onceki_i):
            if SINIF[formasyon] != "B":
                continue

            confirmed, invalidated = teyit_edildi_mi(d, onceki_i, son_i, formasyon)
            if confirmed:
                yon = YON[formasyon]
                ekle(
                    onceki_i,
                    formasyon,
                    f"{yon} TEYİDİ",
                    d["tarih"].iloc[onceki_i],
                    teyit_tarihi=d["tarih"].iloc[son_i],
                )
            # Teyit olmadı / bozulduysa tarama sonucuna eklemiyoruz.

    return kayitlar


# ---------------------------------------------------------------------------
# 8) ANA PROGRAM
# ---------------------------------------------------------------------------

def main():
    # Eski bir çalışmadan kalan CSV asla yeni sonuç sanılmasın.
    output_files = [
        "mum_tarama_sonuc.csv",
        "mum_tarama_haftalik.csv",
        "mum_tarama_aylik.csv",
        "mum_tarama_hatalar.csv",
    ]
    for f in output_files:
        if os.path.exists(f):
            os.remove(f)

    print("=" * 78)
    print("MUM TARAMA — BIST | Yahoo Finance | Haftalık + Aylık")
    print(f"BUILD: {BUILD_ID}")
    print(f"RUN TIME (Europe/Istanbul): {datetime.now(IST).isoformat(timespec='seconds')}")
    print("=" * 78)

    cal = xist_takvim()
    son_seans = son_tamamlanmis_seans(cal)
    son_hafta = son_tamamlanmis_donem_tarihi(cal, "W", son_seans)
    son_ay = son_tamamlanmis_donem_tarihi(cal, "M", son_seans)

    print(f"Şu ana kadar tamamlanmış son XIST seansı: {son_seans.date()}")
    print(f"Taranacak son tamamlanmış hafta: {son_hafta.date()}")
    print(f"Taranacak son tamamlanmış ay   : {son_ay.date()}")

    veriler, hatalar = yahoo_veri_indir()
    print(f"\nKullanılabilir Yahoo verisi: {len(veriler)} / {len(BIST_KODLARI)} sembol")

    tum = []

    for n, (kod, gunluk) in enumerate(veriler.items(), 1):
        try:
            h = periyoda_cevir(gunluk, "W", cal, son_seans)
            a = periyoda_cevir(gunluk, "M", cal, son_seans)

            # Yahoo verisi eski kalan bir hisse için önceki hafta/ayı
            # "son dönem" sanıp sinyal üretme.
            if not h.empty and pd.Timestamp(h["tarih"].iloc[-1]).normalize() == son_hafta:
                tum.extend(hisse_tara(kod, h, "HAFTALIK"))
            else:
                got = "yok" if h.empty else str(pd.Timestamp(h["tarih"].iloc[-1]).date())
                hatalar.append((
                    kod,
                    f"Haftalık veri güncel değil; beklenen {son_hafta.date()}, gelen {got}"
                ))

            if not a.empty and pd.Timestamp(a["tarih"].iloc[-1]).normalize() == son_ay:
                tum.extend(hisse_tara(kod, a, "AYLIK"))
            else:
                got = "yok" if a.empty else str(pd.Timestamp(a["tarih"].iloc[-1]).date())
                hatalar.append((
                    kod,
                    f"Aylık veri güncel değil; beklenen {son_ay.date()}, gelen {got}"
                ))
        except Exception as e:
            hatalar.append((kod, f"Tarama hata: {str(e)[:150]}"))

    kolonlar = [
        "build", "kod", "periyot", "formasyon", "sinif", "yon", "durum",
        "formasyon_tarihi", "teyit_tarihi", "kapanis",
        "formasyon_tepe", "formasyon_dip",
        "teyit_seviyesi", "teyit_sarti",
        "gecersizlik_seviyesi", "gecersizlik_notu",
    ]

    if tum:
        r = pd.DataFrame(tum)[kolonlar]

        # ---------------------------------------------------------------
        # HARD SELF-CHECKS
        # Bu kurallar bozulursa CSV yazmak yerine açık hata verir.
        # ---------------------------------------------------------------
        new_mask = r["teyit_tarihi"].astype(str).str.strip().eq("")
        weekly_new = r[new_mask & (r["periyot"] == "HAFTALIK")]
        monthly_new = r[new_mask & (r["periyot"] == "AYLIK")]

        bad_week = weekly_new[
            pd.to_datetime(weekly_new["formasyon_tarihi"]).dt.normalize()
            != pd.Timestamp(son_hafta).normalize()
        ]
        bad_month = monthly_new[
            pd.to_datetime(monthly_new["formasyon_tarihi"]).dt.normalize()
            != pd.Timestamp(son_ay).normalize()
        ]

        if not bad_week.empty or not bad_month.empty:
            raise RuntimeError(
                "SELF-CHECK FAILED: Yeni sinyal son tamamlanmış dönem dışında üretildi. "
                "Eski/kopya kod çalışıyor olabilir."
            )

        # Aynı tek-mum geometrisi aynı tarihte hem bullish hem bearish olamaz.
        one_bar_conflicts = [
            ("Hammer", "Hanging Man"),
            ("Ters Hammer", "Shooting Star"),
            ("Dragonfly Doji", "Gravestone Doji"),
        ]
        for bull_name, bear_name in one_bar_conflicts:
            b = r[r["formasyon"] == bull_name][["kod", "periyot", "formasyon_tarihi"]]
            a = r[r["formasyon"] == bear_name][["kod", "periyot", "formasyon_tarihi"]]
            if not b.empty and not a.empty:
                z = b.merge(a, on=["kod", "periyot", "formasyon_tarihi"], how="inner")
                if not z.empty:
                    raise RuntimeError(
                        f"SELF-CHECK FAILED: {bull_name}/{bear_name} aynı tarihte birlikte çıktı. "
                        "Trend yönü çelişkili."
                    )

        durum_sira = {
            "BOĞA TEYİDİ": 0,
            "AYI TEYİDİ": 0,
            "TEYİT BEKLİYOR": 1,
            "İZLE": 2,
        }
        sinif_sira = {"A": 0, "B": 1, "C": 2}
        r["_d"] = r["durum"].map(durum_sira).fillna(9)
        r["_s"] = r["sinif"].map(sinif_sira).fillna(9)
        r = r.sort_values(
            ["periyot", "_d", "_s", "yon", "kod", "formasyon"],
            ascending=True,
        ).drop(columns=["_d", "_s"])

        r.to_csv("mum_tarama_sonuc.csv", index=False, encoding="utf-8-sig")
        r[r["periyot"] == "HAFTALIK"].to_csv(
            "mum_tarama_haftalik.csv", index=False, encoding="utf-8-sig"
        )
        r[r["periyot"] == "AYLIK"].to_csv(
            "mum_tarama_aylik.csv", index=False, encoding="utf-8-sig"
        )

        # Yazılan ana CSV'yi tekrar okuyup gerçekten bu build ve bu dönemlere ait olduğunu doğrula.
        verify = pd.read_csv("mum_tarama_sonuc.csv", encoding="utf-8-sig")
        if verify.empty:
            raise RuntimeError("SELF-CHECK FAILED: Yazılan sonuç CSV boş.")
        if "build" not in verify.columns or not verify["build"].astype(str).eq(BUILD_ID).all():
            raise RuntimeError("SELF-CHECK FAILED: CSV build kimliği bu çalışmayla eşleşmiyor.")
        vm = verify[verify["teyit_tarihi"].fillna("").astype(str).str.strip().eq("")]
        vw = vm[vm["periyot"] == "HAFTALIK"]
        va = vm[vm["periyot"] == "AYLIK"]
        if (not vw.empty and not pd.to_datetime(vw["formasyon_tarihi"]).dt.normalize().eq(pd.Timestamp(son_hafta).normalize()).all()):
            raise RuntimeError("SELF-CHECK FAILED: Yazılan CSV'de eski haftalık yeni sinyal var.")
        if (not va.empty and not pd.to_datetime(va["formasyon_tarihi"]).dt.normalize().eq(pd.Timestamp(son_ay).normalize()).all()):
            raise RuntimeError("SELF-CHECK FAILED: Yazılan CSV'de eski aylık yeni sinyal var.")

        print(f"OUTPUT VERIFIED: {BUILD_ID}")
        print(f"OUTPUT PERIODS: weekly={son_hafta.date()} monthly={son_ay.date()}")

        for per in ["HAFTALIK", "AYLIK"]:
            x = r[r["periyot"] == per]
            print("\n" + "=" * 78)
            print(f"{per} — {len(x)} sonuç")
            print("=" * 78)
            if x.empty:
                print("Sinyal yok.")
            else:
                goster = [
                    "kod", "formasyon", "sinif", "yon", "durum",
                    "formasyon_tarihi", "teyit_tarihi",
                    "kapanis", "teyit_sarti", "gecersizlik_notu",
                ]
                print(x[goster].to_string(index=False))
    else:
        pd.DataFrame(columns=kolonlar).to_csv(
            "mum_tarama_sonuc.csv", index=False, encoding="utf-8-sig"
        )
        print("\nSon tamamlanmış haftada/ayda formasyon bulunamadı.")

    if hatalar:
        err = pd.DataFrame(hatalar, columns=["kod", "hata"]).drop_duplicates()
    else:
        err = pd.DataFrame(columns=["kod", "hata"])
    err.to_csv("mum_tarama_hatalar.csv", index=False, encoding="utf-8-sig")

    print("\n" + "-" * 78)
    print(f"Tamamlandı — BUILD: {BUILD_ID}")
    print("Dosyalar:")
    print("  mum_tarama_sonuc.csv")
    print("  mum_tarama_haftalik.csv")
    print("  mum_tarama_aylik.csv")
    print("  mum_tarama_hatalar.csv")
    print("-" * 78)


if __name__ == "__main__":
    main()
