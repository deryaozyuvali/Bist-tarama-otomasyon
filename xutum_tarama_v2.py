import yfinance as yf
import pandas as pd
import numpy as np
import gc
import warnings
warnings.filterwarnings("ignore")

# ── İNDİKATÖR FONKSİYONLARI ──────────────────────────────
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

# ── BAR SEÇİM MANTIĞI ─────────────────────────────────────
# Kural (Derya'nın tanımı): Tarama hangi an yapılıyorsa, o an
# içinde bulunduğumuz hafta/ay'ın GÜNCEL (o ana kadarki) değeri
# "bu haftanın/ayın kapanışı" gibi kabul edilir. Örnek: geçen
# haftanın (tamamlanmış) kapanışı Cuma 60 idi; bu hafta Çarşamba
# tarama yapılıyorsa, Çarşamba'ya kadarki fiyat hareketi "bu
# haftanın kapanışı" sayılır ve geçen haftanın 60'ı ile kıyaslanır.
# Bu yüzden artık hiçbir bar 'kapanmamış' diye atılmıyor — yfinance
# zaten devam eden hafta/ay için o ana kadarki OHLC'yi tek bar
# olarak döndürüyor; biz de onu doğrudan son bar (-1) olarak
# kullanıyoruz. Önceki 'kapanmamış bar' tespiti (son_bar_kapanmamis_mi)
# gereksizdi ve üstelik haftalık tarafta yanlış bir bar kaymasına
# (off-by-one) yol açıyordu.


# ── TEK HİSSE TARA ───────────────────────────────────────
def tara(ticker, debug=False):
    try:
        # ── AYLIK VERİ ───────────────────────────────────
        df_m = yf.download(f"{ticker}.IS", period="7y",
                           interval="1mo", progress=False,
                           auto_adjust=True)
        if df_m.empty or len(df_m) < 32:
            return None

        c_m = df_m["Close"].squeeze().dropna()
        v_m = df_m["Volume"].squeeze().reindex(c_m.index).fillna(0)

        son_ay_idx = -1  # tarama anı = bu ayın güncel kapanışı

        if debug:
            print(f"  [{ticker}] AYLIK son 3 index: {list(c_m.index[-3:])} | "
                  f"kullanılan son bar konumu: {son_ay_idx}")

        rsi_m  = hesapla_rsi(c_m)
        macd_cizgi_m = hesapla_macd_cizgisi(c_m)
        macd_m = hesapla_macd_hist(c_m)
        obv_m  = hesapla_obv(c_m, v_m)

        i0, i1 = son_ay_idx, son_ay_idx - 1
        rsi_m_up  = float(rsi_m.iloc[i0])  > float(rsi_m.iloc[i1])
        macd_m_up = float(macd_cizgi_m.iloc[i0]) > float(macd_cizgi_m.iloc[i1])
        obv_m_up  = float(obv_m.iloc[i0])  > float(obv_m.iloc[i1])
        obv_m_ath = float(obv_m.iloc[i0])  >= float(obv_m.max()) * 0.95
        rsi_m_val = round(float(rsi_m.iloc[i0]), 1)

        del df_m, c_m, v_m, rsi_m, macd_m, obv_m
        gc.collect()

        # ── HAFTALIK VERİ ────────────────────────────────
        df_w = yf.download(f"{ticker}.IS", period="3y",
                           interval="1wk", progress=False,
                           auto_adjust=True)
        if df_w.empty or len(df_w) < 32:
            return None

        c_w = df_w["Close"].squeeze().dropna()

        son_hf_idx = -1  # tarama anı = bu haftanın güncel kapanışı

        if debug:
            print(f"  [{ticker}] HAFTALIK son 3 index: {list(c_w.index[-3:])} | "
                  f"kullanılan son bar konumu: {son_hf_idx}")

        rsi_w  = hesapla_rsi(c_w)
        macd_cizgi_w = hesapla_macd_cizgisi(c_w)
        macd_w = hesapla_macd_hist(c_w)

        j0, j1 = son_hf_idx, son_hf_idx - 1
        rsi_w_up  = float(rsi_w.iloc[j0])  > float(rsi_w.iloc[j1])
        macd_w_up = float(macd_cizgi_w.iloc[j0]) > float(macd_cizgi_w.iloc[j1])
        rsi_w_val = round(float(rsi_w.iloc[j0]), 1)

        del df_w, c_w, rsi_w, macd_w
        gc.collect()

        # ── SİNYAL ───────────────────────────────────────
        aylik_ok    = rsi_m_up and macd_m_up and obv_m_up and obv_m_ath
        haftalik_ok = rsi_w_up and macd_w_up
        sinyal      = aylik_ok and haftalik_ok

        return {
            "Hisse"    : ticker,
            "RSI(A)"   : rsi_m_val,
            "RSI(A)↑"  : "✅" if rsi_m_up  else "❌",
            "MACD(A)↑" : "✅" if macd_m_up else "❌",
            "OBV(A)↑"  : "✅" if obv_m_up  else "❌",
            "OBV ATH~" : "✅" if obv_m_ath else "❌",
            "RSI(H)"   : rsi_w_val,
            "RSI(H)↑"  : "✅" if rsi_w_up  else "❌",
            "MACD(H)↑" : "✅" if macd_w_up else "❌",
            "SINYAL"   : "🟢" if sinyal else "—"
        }

    except Exception as e:
        if debug:
            print(f"  [{ticker}] HATA: {e}")
        return None


# ── XUTUM 566 HİSSE ──────────────────────────────────────
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

    # ── ADIM 1: DOĞRULAMA — AKCNS'i debug modda tek başına çalıştır ──
    print("── DOĞRULAMA: AKCNS (debug) ──")
    sonuc_akcns = tara("AKCNS", debug=True)
    print(sonuc_akcns)
    print()

    # ── ADIM 2: TAM TARAMA ────────────────────────────────
    print(f"⏳ {len(tickers)} hisse taranıyor...\n")

    sonuclar = []
    hatalar  = []

    for i, ticker in enumerate(tickers):
        r = tara(ticker)
        if r:
            sonuclar.append(r)
        else:
            hatalar.append(ticker)
        if (i + 1) % 50 == 0:
            gecen = sum(1 for s in sonuclar if s["SINYAL"] == "🟢")
            print(f"  {i+1}/{len(tickers)} | Taranan: {len(sonuclar)} | Sinyal: {gecen}")
            pd.DataFrame(sonuclar).to_csv("ara_kayit.csv", index=False)

    # ── SONUÇLAR ─────────────────────────────────────────────

        df_tm    = pd.DataFrame(sonuclar)
    df_tm    = df_tm.sort_values("RSI(H)", ascending=True, na_position="last").reset_index(drop=True)
    df_gecen = df_tm[df_tm["SINYAL"] == "🟢"].reset_index(drop=True)

    print(f"\n{'='*55}")
    print(f"  Taranan   : {len(df_tm)}")
    print(f"  Hata/Yok  : {len(hatalar)}")
    print(f"  Sinyal    : {len(df_gecen)} hisse")
    print(f"{'='*55}\n")

    if len(df_gecen) > 0:
        print(df_gecen.to_string(index=False))
    else:
        print("Sinyal yok.")

    df_tm.to_csv("xutum_tarama.csv",    index=False)
    df_gecen.to_csv("xutum_sinyal.csv", index=False)
    print("\n✅ Dosyalar kaydedildi → sol panelden indir")
