"""
GEÇMİŞ TARAMA — Backtest
────────────────────────
xutum_tarama_v2.py'deki AYNI indikatör/sinyal mantığını (hiç değiştirmeden)
kullanarak, GEÇEN YIL belirli bir 15 günlük pencerede (varsayılan: 14-26
Ağustos 2025) hangi hisselerin "aylık + haftalık" birleşik 🟢 sinyali
vermiş olduğunu bulur, sonra bu hisselerin sinyal tarihinden bugüne kadar
1 ay / 3 ay / 6 ay / 12 ay / bugüne-kadar getirilerini hesaplar ve
XU100 endeksiyle karşılaştırır.

Önemli metodolojik not: Geçmişe dönük olarak, tamamlanmış bir haftanın
barı zaten sabittir (Yahoo Finance geçmiş haftalar için "o hafta neydi"
diye tek bir kesin değer verir — günlük yeniden-çalıştırmalarda değişen
şey sadece "bu an içinde bulunulan, henüz kapanmamış hafta/ay" barıdır).
Bu yüzden 15 günlük pencere içinde HER GÜN için ayrı ayrı kontrol yerine,
o pencereye denk gelen HAFTALIK kapanış barlarının her biri + o ay için
TEK BİR aylık bar üzerinden kontrol yapılır. Bu, canlı taramanın günlük
tekrarlarını geçmişe dönük olarak birebir simüle etmenin matematiksel
olarak doğru karşılığıdır (bkz. script içi açıklamalar).

Bakım: bu script sadece bir ANALİZ/BACKTEST aracıdır; xutum_tarama_v2.py
ve diğer canlı tarama scriptlerine hiç dokunulmamıştır.
"""

import yfinance as yf
import pandas as pd
import numpy as np
import gc
import warnings
import json
warnings.filterwarnings("ignore")

# ── PENCERE TANIMI ───────────────────────────────────────
GECMIS_BASLANGIC = "2025-08-14"
GECMIS_BITIS      = "2025-08-26"
# Haftalık barları biraz daha geniş bir aralıkta arıyoruz ki pencereye
# denk gelen tüm haftalık kapanışları kaçırmayalım.
HAFTA_ARA_BASLANGIC = "2025-08-10"
HAFTA_ARA_BITIS     = "2025-08-30"
AY_YIL, AY_AY = 2025, 8  # Ağustos 2025

# ── İNDİKATÖR FONKSİYONLARI (xutum_tarama_v2.py ile BİREBİR AYNI) ──
def hesapla_rsi(close, period=14):
    delta = close.diff()
    gain  = delta.clip(lower=0)
    loss  = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period-1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period-1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def hesapla_macd_cizgisi(close, fast=12, slow=26):
    return close.ewm(span=fast, adjust=False).mean() - close.ewm(span=slow, adjust=False).mean()

def hesapla_macd_hist(close, fast=12, slow=26, signal=9):
    macd = hesapla_macd_cizgisi(close, fast, slow)
    return macd - macd.ewm(span=signal, adjust=False).mean()

def hesapla_obv(close, volume):
    return (np.sign(close.diff()).fillna(0) * volume).cumsum()


def ileri_getiri(seri, pos, hafta_sayisi):
    """seri: haftalık kapanış serisi, pos: referans (sinyal) index'i.
    hafta_sayisi kadar ileri git, bulunan en yakın (<=) index'i kullan."""
    hedef = pos + hafta_sayisi
    if hedef >= len(seri):
        hedef = len(seri) - 1
    if hedef <= pos:
        return None
    p0 = float(seri.iloc[pos])
    p1 = float(seri.iloc[hedef])
    if p0 == 0:
        return None
    return round((p1 / p0 - 1) * 100, 2)


def tara_gecmis(ticker, xu100_w, debug=False):
    try:
        df_m = yf.download(f"{ticker}.IS", period="10y", interval="1mo",
                            progress=False, auto_adjust=True)
        if df_m.empty or len(df_m) < 32:
            return []

        c_m = df_m["Close"].squeeze().dropna()
        v_m = df_m["Volume"].squeeze().reindex(c_m.index).fillna(0)

        rsi_m  = hesapla_rsi(c_m)
        macd_cizgi_m = hesapla_macd_cizgisi(c_m)
        obv_m  = hesapla_obv(c_m, v_m)

        # Ağustos 2025 ayına denk gelen bar pozisyonunu bul
        ay_pos = None
        for i, ts in enumerate(c_m.index):
            if ts.year == AY_YIL and ts.month == AY_AY:
                ay_pos = i
                break
        if ay_pos is None or ay_pos < 1:
            return []

        rsi_m_up  = float(rsi_m.iloc[ay_pos])  > float(rsi_m.iloc[ay_pos-1])
        macd_m_up = float(macd_cizgi_m.iloc[ay_pos]) > float(macd_cizgi_m.iloc[ay_pos-1])
        obv_m_up  = float(obv_m.iloc[ay_pos])  > float(obv_m.iloc[ay_pos-1])
        # ATH kontrolü: SADECE o ana kadarki (ay_pos'a kadar) OBV verisiyle — geleceğe bakmadan
        obv_m_ath = float(obv_m.iloc[ay_pos]) >= float(obv_m.iloc[:ay_pos+1].max()) * 0.95
        rsi_m_val = round(float(rsi_m.iloc[ay_pos]), 1)

        aylik_ok = rsi_m_up and macd_m_up and obv_m_up and obv_m_ath

        del df_m, c_m, v_m, rsi_m, macd_cizgi_m, obv_m
        gc.collect()

        if not aylik_ok:
            return []  # aylık şart sağlanmadıysa hiçbir hafta sinyal veremez, erken çık

        df_w = yf.download(f"{ticker}.IS", period="6y", interval="1wk",
                            progress=False, auto_adjust=True)
        if df_w.empty or len(df_w) < 32:
            return []

        c_w = df_w["Close"].squeeze().dropna()
        rsi_w  = hesapla_rsi(c_w)
        macd_cizgi_w = hesapla_macd_cizgisi(c_w)

        sonuclar = []
        for i, ts in enumerate(c_w.index):
            if i < 1:
                continue
            ts_str = ts.strftime("%Y-%m-%d")
            if not (HAFTA_ARA_BASLANGIC <= ts_str <= HAFTA_ARA_BITIS):
                continue

            rsi_w_up  = float(rsi_w.iloc[i]) > float(rsi_w.iloc[i-1])
            macd_w_up = float(macd_cizgi_w.iloc[i]) > float(macd_cizgi_w.iloc[i-1])
            rsi_w_val = round(float(rsi_w.iloc[i]), 1)
            haftalik_ok = rsi_w_up and macd_w_up
            sinyal = aylik_ok and haftalik_ok

            if not sinyal:
                continue

            kapanis_0 = float(c_w.iloc[i])
            xu_ret = {}
            if xu100_w is not None:
                xpos = None
                for xi, xts in enumerate(xu100_w.index):
                    if xts.strftime("%Y-%m-%d") == ts_str:
                        xpos = xi
                        break
                if xpos is not None:
                    for etiket, hf in [("1ay",4), ("3ay",13), ("6ay",26), ("12ay",52)]:
                        xu_ret[etiket] = ileri_getiri(xu100_w, xpos, hf)
                    xu_ret["bugune_kadar"] = ileri_getiri(xu100_w, xpos, len(xu100_w))

            sonuclar.append({
                "hafta_tarihi": ts_str,
                "Hisse": ticker,
                "RSI(A)_2025": rsi_m_val,
                "RSI(H)_2025": rsi_w_val,
                "kapanis_sinyal_haftasi": round(kapanis_0, 4),
                "getiri_1ay(%)":  ileri_getiri(c_w, i, 4),
                "getiri_3ay(%)":  ileri_getiri(c_w, i, 13),
                "getiri_6ay(%)":  ileri_getiri(c_w, i, 26),
                "getiri_12ay(%)": ileri_getiri(c_w, i, 52),
                "getiri_bugune_kadar(%)": ileri_getiri(c_w, i, len(c_w)),
                "xu100_1ay(%)": xu_ret.get("1ay"),
                "xu100_3ay(%)": xu_ret.get("3ay"),
                "xu100_6ay(%)": xu_ret.get("6ay"),
                "xu100_12ay(%)": xu_ret.get("12ay"),
                "xu100_bugune_kadar(%)": xu_ret.get("bugune_kadar"),
            })

        del df_w, c_w, rsi_w, macd_cizgi_w
        gc.collect()
        return sonuclar

    except Exception as e:
        if debug:
            print(f"  [{ticker}] HATA: {e}")
        return []


# ── XUTUM 566 HİSSE (xutum_tarama_v2.py ile BİREBİR AYNI LİSTE) ──
tickers = [
    "A1CAP","A1YEN","AAGYO","ACSEL","ADEL","ADESE","ADGYO","AEFES","AFYON","AGESA",
    "AGHOL","AGROT","AGYO","AHGAZ","AHSGY","AKBNK","AKCNS","AKENR","AKFGY","AKFIS",
    "AKFYE","AKGRT","AKHAN","AKMGY","AKSA","AKSEN","AKSGY","AKSUE","AKYHO","ALARK",
    "ALBRK","ALCAR","ALCTL","ALFAS","ALGYO","ALKA","ALKIM","ALKLC","ALMAD","ALTNY",
    "ALVES","ANELE","ANGEN","ANHYT","ANSGR","ARASE","ARCLK","ARDYZ","ARENA","ARFYE",
    "ARMGD","ARSAN","ARTMS","ARZUM","ASELS","ASGYO","ASTOR","ASUZU","ATAGY","ATAKP",
    "ATATP","ATATR","ATEKS","ATLAS","ATSYH","AVGYO","AVHOL","AVOD","AVPGY","AVTUR",
    "AYCES","AYDEM","AYEN","AYES","AYGAZ","AZTEK","BAGFS","BAHKM","BAKAB","BALAT",
    "BALSU","BANVT","BARMA","BASCM","BASGZ","BAYRK","BEGYO","BERA","BESLR","BESTE",
    "BETAE","BEYAZ","BFREN","BIENY","BIGCH","BIGEN","BIGTK","BIMAS","BINBN","BINHO",
    "BIOEN","BIZIM","BJKAS","BLCYT","BLUME","BMSCH","BMSTL","BNTAS","BOBET","BORLS",
    "BORSK","BOSSA","BRISA","BRKO","BRKSN","BRKVY","BRLSM","BRMEN","BRSAN","BRYAT",
    "BSOKE","BTCIM","BUCIM","BULGS","BURCE","BURVA","BVSAN","BYDNR","CANTE","CASA",
    "CATES","CCOLA","CELHA","CEMAS","CEMTS","CEMZY","CEOEM","CGCAM","CIMSA","CLEBI",
    "CMBTN","CMENT","CONSE","COSMO","CRDFA","CRFSA","CUSAN","CVKMD","CWENE","DAGHL",
    "DAGI","DAPGM","DARDL","DCTTR","DENGE","DERHL","DERIM","DESA","DESPC","DEVA",
    "DGATE","DGGYO","DGNMO","DIRIT","DITAS","DMRGD","DMSAS","DNISI","DOAS","DOBUR",
    "DOCO","DOFER","DOFRB","DOGUB","DOHOL","DOKTA","DSTKF","DUNYH","DURDO","DURKN",
    "DYOBY","DZGYO","EBEBK","ECILC","ECOGR","ECZYT","EDATA","EDIP","EFOR","EFORC",
    "EGEEN","EGEGY","EGEPO","EGGUB","EGPRO","EGSER","EKDMR","EKGYO","EKIM","EKIZ",
    "EKOS","EKSUN","ELITE","EMKEL","EMNIS","EMPAE","ENDAE","ENERY","ENJSA","ENKAI",
    "ENPRA","ENSRI","ENTRA","EPLAS","ERBOS","ERCB","EREGL","ERSU","ESCAR","ESCOM",
    "ESEN","ETILR","ETYAT","EUHOL","EUKYO","EUPWR","EUREN","EUYO","EYGYO","FADE",
    "FENER","FLAP","FMIZP","FONET","FORMT","FORTE","FRIGO","FRMPL","FROTO","FZLGY",
    "GARAN","GARFA","GATEG","GEDIK","GEDZA","GENIL","GENKM","GENTS","GEREL","GESAN",
    "GIPTA","GLBMD","GLCVY","GLRMK","GLRYH","GLYHO","GMTAS","GOKNR","GOLDA","GOLTS",
    "GOODY","GOZDE","GRNYO","GRSEL","GRTHO","GRTRK","GSDDE","GSDHO","GSRAY","GUBRF",
    "GUNDG","GWIND","GZNMI","HALKB","HATEK","HATSN","HDFGS","HEDEF","HEKTS","HKTM",
    "HLGYO","HOROZ","HRKET","HTTBT","HUBVC","HUNER","HURGZ","ICBCT","ICUGS","IDEAS",
    "IDGYO","IEYHO","IHAAS","IHEVA","IHGZT","IHLAS","IHLGM","IHYAY","IMASM","INDES",
    "INFO","INGRM","INTEK","INTEM","INVEO","INVES","IPEKE","ISATR","ISBIR","ISBTR",
    "ISCTR","ISDMR","ISFIN","ISGSY","ISGYO","ISKPL","ISKUR","ISMEN","ISSEN","ISVEA",
    "ISYAT","ITTFH","IZENR","IZFAS","IZINV","IZMDC","JANTS","KAPLM","KAREL","KARSN",
    "KARTN","KARYE","KATMR","KAYSE","KBORU","KCAER","KCHOL","KENT","KERVN","KERVT",
    "KFEIN","KGYO","KIMMR","KLGYO","KLKIM","KLMSN","KLNMA","KLRHO","KLSER","KLSYN",
    "KLYPV","KMPUR","KNFRT","KOCMT","KONKA","KONTR","KONYA","KOPOL","KORDS","KOTON",
    "KOZAA","KOZAL","KRDMA","KRDMB","KRDMD","KRGYO","KRONT","KRPLS","KRSTL","KRTEK",
    "KRVGD","KSTUR","KTLEV","KTSKR","KUTPO","KUVVA","KUYAS","KZBGY","KZGYO","LIDER",
    "LIDFA","LILAK","LINK","LKMNH","LMKDC","LOGO","LRSHO","LUKSK","LXGYO","LYDHO",
    "LYDYE","MAALT","MACKO","MAGEN","MAKIM","MAKTK","MANAS","MARBL","MARKA","MARMR",
    "MARTI","MAVI","MCARD","MEDTR","MEGAP","MEGMT","MEKAG","MEPET","MERCN","MERIT",
    "MERKO","METRO","METUR","MEYSU","MGROS","MHRGY","MIATK","MIPAZ","MMCAS","MNDRS",
    "MNDTR","MOBTL","MOGAN","MOPAS","MPARK","MRGYO","MRSHL","MSGYO","MTRKS","MTRYO",
    "MZHLD","NATEN","NETAS","NETCD","NIBAS","NTGAZ","NTHOL","NUGYO","NUHCM","OBAMS",
    "OBASE","ODAS","ODINE","OFSYM","ONCSM","ONRYT","ORCAY","ORGE","ORMA","ORZAX",
    "OSMEN","OSTIM","OTKAR","OTTO","OYAKC","OYAYO","OYLUM","OYYAT","OZATD","OZGYO",
    "OZKGY","OZRDN","OZSUB","OZYSR","PAGYO","PAHOL","PAMEL","PAPIL","PARSN","PASEU",
    "PATEK","PCILT","PEHOL","PEKGY","PENGD","PENTA","PETKM","PETUN","PGSUS","PINSU",
    "PKART","PKENT","PLTUR","PNLSN","PNSUT","POLHO","POLTK","PRDGS","PRKAB","PRKME",
    "PRZMA","PSDTC","PSGYO","QNBFB","QNBFK","QNBFL","QNBTR","QUAGR","RALYH","RAYSG",
    "REEDR","RGYAS","RNPOL","RODRG","ROYAL","RTALB","RUBNS","RUZYE","RYGYO","RYSAS",
    "SAFKR","SAHOL","SAMAT","SANEL","SANFM","SANKO","SARAE","SARKY","SASA","SAYAS",
    "SDTTR","SEGMN","SEGYO","SEKFK","SEKUR","SELEC","SELGD","SELVA","SERNT","SEYKM",
    "SILVR","SISE","SKBNK","SKTAS","SKYLP","SKYMD","SMART","SMRTG","SMRVA","SNGYO",
    "SNICA","SNKRN","SNPAM","SODSN","SOHOE","SOKE","SOKM","SONME","SRVGY","SSAAT",
    "SUMAS","SUNTK","SURGY","SUWEN","SVGYO","TABGD","TARKM","TATEN","TATGD","TAVHL",
    "TBORG","TCELL","TCKRC","TDGYO","TEHOL","TEKTU","TERA","TETMT","TEZOL","TGSAS",
    "THYAO","TKFEN","TKNSA","TLMAN","TMPOL","TMSN","TNZTP","TOASO","TRALT","TRCAS",
    "TRENJ","TRGYO","TRHOL","TRILC","TRMET","TSGYO","TSKB","TSPOR","TTKOM","TTRAK",
    "TUCLK","TUKAS","TUPRS","TUREX","TURGG","TURSG","UCAYM","UFUK","ULAS","ULKER",
    "ULUFA","ULUSE","ULUUN","UMPAS","UNLU","USAK","UZERB","VAKBN","VAKFA","VAKFN",
    "VAKKO","VANGD","VBTYZ","VERTU","VERUS","VESBE","VESTL","VKFYO","VKGYO","VKING",
    "VRGYO","VSNMD","YAPRK","YATAS","YAYLA","YBTAS","YEOTK","YESIL","YGGYO","YGYO",
    "YIGIT","YKBNK","YKSLN","YONGA","YUNSA","YYAPI","YYLGD","ZEDUR","ZERGY","ZGYO",
    "ZOREN","ZRGYO",
]

if __name__ == "__main__":
    print("── XU100 endeks verisi indiriliyor (benchmark) ──")
    try:
        df_xu = yf.download("XU100.IS", period="6y", interval="1wk",
                             progress=False, auto_adjust=True)
        xu100_w = df_xu["Close"].squeeze().dropna()
        print(f"XU100 haftalık bar sayısı: {len(xu100_w)}")
    except Exception as e:
        print(f"XU100 indirilemedi: {e}")
        xu100_w = None

    print(f"\n⏳ {len(tickers)} hisse için geçmiş ({GECMIS_BASLANGIC} – {GECMIS_BITIS}) taraması yapılıyor...\n")

    tum_sonuclar = []
    hatalar = []

    for i, ticker in enumerate(tickers):
        r = tara_gecmis(ticker, xu100_w)
        if r:
            tum_sonuclar.extend(r)
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(tickers)} | Şu ana kadar bulunan sinyal olayı: {len(tum_sonuclar)}")
            if tum_sonuclar:
                pd.DataFrame(tum_sonuclar).to_csv("gecmis_tarama_ara_kayit.csv", index=False)

    df = pd.DataFrame(tum_sonuclar)
    if not df.empty:
        df = df.sort_values(["hafta_tarihi", "Hisse"]).reset_index(drop=True)

    print(f"\n{'='*60}")
    print(f"  Pencere        : {GECMIS_BASLANGIC} – {GECMIS_BITIS}")
    print(f"  Bulunan sinyal : {len(df)} olay ({df['Hisse'].nunique() if not df.empty else 0} benzersiz hisse)")
    print(f"{'='*60}\n")

    df.to_csv("gecmis_tarama_sonuc.csv", index=False)
    print("✅ gecmis_tarama_sonuc.csv kaydedildi")
