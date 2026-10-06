"""HASAT taraması — "Sıkıcı ama nakit üreten şirket" kural seti, son 3 yıla uyarlanmış (KURAL_SETI.md).
Baz: Funnel ile aynı — Evo TTM / yıllık rakamlar, TMS 29 uygulayan şirketlerde son raporun satın alma gücünde (harici deflatör yok).
TMS 29 uygulamayan (işlevsel para birimi USD vb.) şirketlerde TL seri nominal → büyüme/borç trendi USD bazında ölçülür.
Noktalar: Y23 = FY2023 (ilk TMS 29 yıl sonu), Y24 = FY2024, Y25 = FY2025, T = TTM 2026/06.
FCF bileşenleri Y25 ve T için FCF_MASTER'dan (belgeyle düzeltilmiş), Y23/Y24 için Evo'dan.
Girdi: hasat/evo_3yil.csv (evo_topla.py), FCF_MASTER.xlsx, PFCF_GETIRI.xlsx  →  Çıktı: HASAT_TARAMA.xlsx"""
import os, sys, collections, json
import pandas as pd, numpy as np

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.join(KOK, 'belge'))
_s = open('ttm.py').read()
exec(_s[:_s.index('idx = collections.defaultdict')])  # TMS29_YOK (Evo/V7 CFO'su nominal belgeyle örtüşen şirketler)
os.chdir(KOK)
USD = set(TMS29_YOK)

E = pd.read_csv('hasat/evo_3yil.csv', index_col='Kod')
M = pd.read_excel('FCF_MASTER.xlsx', sheet_name='FCF', keep_default_na=False)
for c in ['CFO_TTM', '|MDV+MODV alımı|', '|YAGM alımı|', 'CAPEX_STD', '|Kira anapara|', 'FCF · TTM (mn TL)']:
    M[c] = pd.to_numeric(M[c], errors='coerce')
MI = M.set_index(['Kod', 'Dönem'])
A = pd.read_excel('FCF_MASTER.xlsx', sheet_name='ANA', header=None).iloc[4:, :5]
A.columns = ['Kod', 'Ünvan', 'Kapsam', 'Tip', 'Sektör']; A = A[A.Kod.notna()].set_index('Kod')
G = pd.read_excel('FCF_MASTER.xlsx', sheet_name='FUNNEL_GIRDI'); G = G[G['Dönem'] == '2026/06'].set_index('Kod')
P = pd.read_excel('PFCF_GETIRI.xlsx', sheet_name='P_FCF', header=None)
h = next(i for i in range(10) if 'Kod' in [str(x) for x in P.iloc[i]])
P.columns = P.iloc[h]; P = P.iloc[h + 1:]; P = P[P.Kod.notna()].set_index('Kod')
GET = [c for c in P.columns if isinstance(c, str) and c.startswith('Getiri')]

mn = lambda x: None if pd.isna(x) else float(x) / 1e6
def ab(x): return None if x is None else abs(x)
def oran(a, b): return None if a is None or b is None or b == 0 else a / b

satirlar = []
for kod in A.index:
    kap = A.loc[kod, 'Kapsam']
    if kod not in E.index or kap not in ('STANDART', 'TIER 0'): continue
    e = E.loc[kod]
    gyo = kap == 'TIER 0' and ('GYO' in str(kod)[-3:] or 'Gayrimenkul Yatırım' in str(A.loc[kod, 'Ünvan']))
    if kap == 'TIER 0' and not gyo: continue
    usd = kod in USD
    r = dict(Kod=kod, Ünvan=A.loc[kod, 'Ünvan'], Tip=A.loc[kod, 'Tip'], Sektör=A.loc[kod, 'Sektör'], Grup='GYO' if gyo else 'Şirket',
             Baz='USD (TMS 29 yok)' if usd else 'TL reel (TMS 29)')
    Y = ['23', '24', '25', '26']
    for y in Y:
        r['Satış ' + y] = mn(e.get('s' + y)); r['Brüt ' + y] = mn(e.get('b' + y)); r['FAVÖK ' + y] = mn(e.get('f' + y))
        r['Net kâr ' + y] = mn(e.get('n' + y)); r['Amort ' + y] = ab(mn(e.get('am' + y))); r['Net borç ' + y] = mn(e.get('nb' + y))
        r['Ödenen tem ' + y] = ab(mn(e.get('tem' + y)))
    for y in ('23', '24'):
        cfo, mdv, yg, ki = mn(e.get('cfo' + y)), mn(e.get('mdv' + y)), mn(e.get('yagm' + y)), mn(e.get('kira' + y))
        r['CFO ' + y] = cfo
        r['CAPEX ' + y] = None if mdv is None and yg is None else ab(mdv or 0) + ab(yg or 0)
        r['Kira ' + y] = ab(ki or 0)
    for y, d in (('25', '2025/12'), ('26', '2026/06')):
        if (kod, d) in MI.index and pd.notna(MI.loc[(kod, d), 'CFO_TTM']):
            m = MI.loc[(kod, d)]
            r['CFO ' + y], r['CAPEX ' + y], r['Kira ' + y] = m['CFO_TTM'], m['CAPEX_STD'], m['|Kira anapara|'] if pd.notna(m['|Kira anapara|']) else 0.0
            r['FCF statü ' + y] = m['Statü']
        else:  # master kapsamı dışı (GYO) → Evo
            cfo, mdv, yg, ki = (mn(e.get(k + y)) for k in ('gcfo', 'gmdv', 'gyagm', 'gkira'))
            r['CFO ' + y] = cfo
            r['CAPEX ' + y] = None if cfo is None else ab(mdv or 0) + ab(yg or 0)
            r['Kira ' + y] = ab(ki or 0); r['FCF statü ' + y] = 'Evo (master dışı)'
    for y in Y:
        c, k, ki = r.get('CFO ' + y), r.get('CAPEX ' + y), r.get('Kira ' + y)
        r['FCF ' + y] = None if c is None or k is None else c - k - (ki or 0)
    # USD bazı (TMS 29 yok): büyüme ve borç trendi
    r['Satış 23 USD'], r['Satış 26 USD'] = mn(e.get('us23')), mn(e.get('us26'))
    r['Brüt 23 USD'], r['Brüt 26 USD'] = mn(e.get('ub23')), mn(e.get('ub26'))
    r['Net borç 23 USD'], r['Net borç 26 USD'] = mn(e.get('unb23')), mn(e.get('unb26'))
    r['Ödenen faiz 26'] = ab(mn(e.get('faiz26')))
    r['PD'] = pd.to_numeric(P.loc[kod, 'Piyasa değeri (mn TL)'], errors='coerce') if kod in P.index else None
    for g in GET: r[g] = P.loc[kod, g] if kod in P.index else None
    oz = G.loc[kod, 'ozkaynak_parent_cur'] if kod in G.index else None
    r['Özkaynak (ana ort.)'] = mn(oz) if oz is not None and not pd.isna(oz) else mn(e.get('goz26'))
    satirlar.append(r)
D = pd.DataFrame(satirlar)

def deg(a, b):  # b / a − 1
    return None if a is None or b is None or pd.isna(a) or pd.isna(b) or a <= 0 else b / a - 1

def hesap(r):
    o = {}
    Y = ['23', '24', '25', '26']
    usd = r['Baz'].startswith('USD')
    # --- K1 nakit üretimi
    cfo = [r.get('CFO ' + y) for y in Y]
    o['CFO>0 yıl'] = sum(1 for c in cfo if c is not None and c > 0)
    o['CFO veri'] = sum(1 for c in cfo if c is not None)
    # --- K2 tuzak testi (reel satış / brüt kâr 23 → T)
    if usd:
        o['Satış değişimi 23→T'] = deg(r['Satış 23 USD'], r['Satış 26 USD']); o['Brüt kâr değişimi 23→T'] = deg(r['Brüt 23 USD'], r['Brüt 26 USD'])
    else:
        o['Satış değişimi 23→T'] = deg(r['Satış 23'], r['Satış 26']); o['Brüt kâr değişimi 23→T'] = deg(r['Brüt 23'], r['Brüt 26'])
    # --- K3 yatırım döngüsü
    gyo = r['Grup'] == 'GYO'
    # GYO: yatırım amaçlı gayrimenkul gerçeğe uygun değerde → amortisman anlamsız; yoğunluk CAPEX/CFO ile ölçülür
    ca = {y: (oran(r.get('CAPEX ' + y), r.get('CFO ' + y)) if (r.get('CFO ' + y) or 0) > 0 else (9.99 if (r.get('CAPEX ' + y) or 0) > 0 else None))
          if gyo else oran(r.get('CAPEX ' + y), r.get('Amort ' + y)) for y in Y}
    yo = {y: oran(r.get('CAPEX ' + y), r.get('Satış ' + y)) for y in Y}
    for y in Y: o[('CAPEX/CFO ' if gyo else 'CAPEX/Amort ') + y] = ca[y]; o['CAPEX/Satış ' + y] = yo[y]
    gecmis = [y for y in ('23', '24', '25') if ca[y] is not None]
    zirve = max(gecmis, key=lambda y: ca[y]) if gecmis else None
    cT, yT = ca['26'], yo['26']
    if cT is None or zirve is None:
        dongu = 'VERİ YOK'
    elif gyo and ca[zirve] >= 0.7 and cT <= 0.3:
        dongu = 'HASAT (yatırım bitti)'
    elif gyo and all(ca[y] is not None and ca[y] <= 0.3 for y in gecmis + ['26']):
        dongu = 'SÜREKLİ DÜŞÜK CAPEX'
    elif gyo and cT < ca[zirve] * 0.85:
        dongu = 'GEÇİŞTE (CAPEX düşüyor)'
    elif gyo:
        dongu = 'YATIRIM DÖNEMİNDE'
    elif ca[zirve] >= 1.5 and cT <= 1.2 and (yo[zirve] is None or yT is None or yT <= 0.7 * yo[zirve]):
        dongu = 'HASAT (yatırım bitti)'
    elif all(ca[y] is not None and ca[y] <= 1.2 for y in gecmis + ['26']):
        dongu = 'SÜREKLİ DÜŞÜK CAPEX'
    elif cT < ca[zirve] * 0.85 and (yo[zirve] is None or yT is None or yT < yo[zirve] * 0.85):
        dongu = 'GEÇİŞTE (CAPEX düşüyor)'
    else:
        dongu = 'YATIRIM DÖNEMİNDE'
    o['Yatırım döngüsü'] = dongu; o['CAPEX zirve yılı'] = ('20' + zirve) if zirve else None
    # --- K4 amortisman kalkanı
    o['Amort/CAPEX T'] = oran(r.get('Amort 26'), r.get('CAPEX 26'))
    o['FCF/Net kâr T'] = oran(r.get('FCF 26'), r.get('Net kâr 26')) if (r.get('Net kâr 26') or 0) > 0 else None
    # --- K5 hasat nakdi
    am, cp = r.get('Amort 26'), r.get('CAPEX 26')
    bakim = None if am is None or cp is None else min(am, cp)
    o['Bakım CAPEX (vekil)'] = bakim
    o['Hasat nakdi T'] = None if r.get('CFO 26') is None or bakim is None else r['CFO 26'] - bakim - (r.get('Kira 26') or 0)
    pdv = r.get('PD')
    o['Hasat getirisi'] = oran(o['Hasat nakdi T'], pdv) if pdv else None
    o['FCF getirisi'] = oran(r.get('FCF 26'), pdv) if pdv else None
    o['P/FCF'] = oran(pdv, r.get('FCF 26')) if r.get('FCF 26') and r['FCF 26'] > 0 and pdv else None
    # --- K6 borç
    nb23, nbT = (r['Net borç 23 USD'], r['Net borç 26 USD']) if usd else (r['Net borç 23'], r['Net borç 26'])
    o['Net borç/FAVÖK 23'] = oran(r['Net borç 23'], r['FAVÖK 23']) if (r['FAVÖK 23'] or 0) > 0 else None
    o['Net borç/FAVÖK T'] = oran(r['Net borç 26'], r['FAVÖK 26']) if (r['FAVÖK 26'] or 0) > 0 else None
    if nb23 is None or nbT is None: borc = 'VERİ YOK'
    elif nb23 > 0 and nbT <= 0: borc = 'NET NAKDE GEÇTİ'
    elif nb23 <= 0 and nbT <= 0: borc = 'SÜREKLİ NET NAKİT'
    elif nbT < nb23 * 0.8 or (o['Net borç/FAVÖK 23'] is not None and o['Net borç/FAVÖK T'] is not None
                             and o['Net borç/FAVÖK T'] < o['Net borç/FAVÖK 23'] * 0.7): borc = 'BORÇ AZALIYOR'
    elif nbT > 0 and nb23 <= 0: borc = 'NET BORCA GEÇTİ'
    else: borc = 'BORÇ AZALMIYOR'
    o['Borç durumu'] = borc
    o['Ödenen faiz/CFO T'] = oran(r.get('Ödenen faiz 26'), r.get('CFO 26')) if (r.get('CFO 26') or 0) > 0 else None
    # Madde 6: borç ödendiğinde → faiz yükü kalkınca hissedara kalacak nakit (ödenen faiz CFO içindeyse de dışındaysa da eklenir: üst sınır)
    o['Borç sonrası hasat getirisi'] = (oran((o['Hasat nakdi T'] or 0) + (r.get('Ödenen faiz 26') or 0), pdv)
                                        if pdv and o.get('Hasat nakdi T') is not None and borc in ('BORÇ AZALIYOR', 'BORÇ AZALMIYOR') else None)
    # --- K8 temettü
    o['Temettü ödenen yıl'] = sum(1 for y in Y if (r.get('Ödenen tem ' + y) or 0) > 0)
    o['Temettü verimi T'] = oran(r.get('Ödenen tem 26'), pdv) if pdv else None
    # --- K9 ucuzluk
    o['PD/DD'] = oran(pdv, r.get('Özkaynak (ana ort.)')) if (r.get('Özkaynak (ana ort.)') or 0) > 0 else None
    o['FD/FAVÖK'] = oran((pdv or 0) + (r['Net borç 26'] or 0), r['FAVÖK 26']) if pdv and (r['FAVÖK 26'] or 0) > 0 else None
    if r['Grup'] == 'GYO':
        o['PD/Satış (kira çarpanı vekili)'] = oran(pdv, r['Satış 26']) if pdv and (r['Satış 26'] or 0) > 0 else None
    # --- ELEME
    neden = []
    if o['CFO veri'] >= 3 and (o['CFO>0 yıl'] < 3 or (r.get('CFO 26') or 0) <= 0): neden.append('CFO düzenli pozitif değil')
    if o['CFO veri'] < 3: neden.append('CFO verisi eksik')
    sd, bd = o['Satış değişimi 23→T'], o['Brüt kâr değişimi 23→T']
    # 2023 birçok şirket için reel zirve; medyan şirkette reel satış −%10, brüt kâr −%17 (2023→T). Tuzak = çöküş düzeyi.
    cokus = (sd is not None and sd < -0.30) or (bd is not None and bd < -0.35) or (r['Brüt 26'] is not None and r['Brüt 26'] <= 0)
    o['Çöküş uyarısı'] = 'EVET (reel satış −%30 / brüt kâr −%35 altında veya brüt zarar)' if cokus else ''
    # Yayıncı: "CAPEX düştü" ancak iş çöktüğü için düştüyse aranan durum değil → tuzak yalnız CAPEX düşüşüyle birlikte
    tuzak = cokus and dongu in ('HASAT (yatırım bitti)', 'GEÇİŞTE (CAPEX düşüyor)')
    if tuzak: neden.append('TUZAK: CAPEX düştü ama satış/brüt kâr da çöktü')
    if r.get('FCF statü 26') in ('KOŞULLU', 'NULL'): neden.append(f"FCF 2026/06 {r.get('FCF statü 26')}")
    o['Eleme'] = '; '.join(neden)
    # --- PUAN (100)
    p = collections.OrderedDict()
    p['Döngü (25)'] = {'HASAT (yatırım bitti)': 25, 'SÜREKLİ DÜŞÜK CAPEX': 20, 'GEÇİŞTE (CAPEX düşüyor)': 10}.get(dongu, 0)
    p['Nakit (15)'] = (15 if o['CFO>0 yıl'] == 4 else 8 if o['CFO>0 yıl'] == 3 else 0) if (r.get('FCF 26') or 0) > 0 else (5 if o['CFO>0 yıl'] == 4 else 0)
    p['Amortisman kalkanı (10)'] = (5 if (o['Amort/CAPEX T'] or 0) >= 1 else 0) + (5 if (o['FCF/Net kâr T'] or 0) > 1 else 0)
    p['Borç (15)'] = {'NET NAKDE GEÇTİ': 15, 'SÜREKLİ NET NAKİT': 12, 'BORÇ AZALIYOR': 8}.get(borc, 0)
    p['Brüt kâr reel (10)'] = 0 if bd is None else 10 if bd >= 0.10 else 6 if bd >= 0 else 2 if bd >= -0.15 else 0
    tv = o['Temettü verimi T'] or 0
    p['Temettü (10)'] = round(o['Temettü ödenen yıl'] / 4 * 5) + (5 if tv >= 0.04 else 3 if tv >= 0.02 else 0)
    hg = o['Hasat getirisi'] or 0
    p['Ucuzluk (15)'] = 15 if hg >= 0.15 else 10 if hg >= 0.10 else 5 if hg >= 0.06 else 0
    if gyo:  # GYO: amortisman kalkanı yok; ağırlık borç ve PD/DD'de
        pdd = o['PD/DD']
        p = collections.OrderedDict()
        p['Döngü (20)'] = {'HASAT (yatırım bitti)': 20, 'SÜREKLİ DÜŞÜK CAPEX': 16, 'GEÇİŞTE (CAPEX düşüyor)': 8}.get(dongu, 0)
        p['Nakit (15)'] = 15 if o['CFO>0 yıl'] == 4 else 8 if o['CFO>0 yıl'] == 3 else 0
        p['Borç (20)'] = {'NET NAKDE GEÇTİ': 20, 'SÜREKLİ NET NAKİT': 16, 'BORÇ AZALIYOR': 10}.get(borc, 0)
        p['Gelir reel (10)'] = 0 if sd is None else 10 if sd >= 0.10 else 6 if sd >= 0 else 2 if sd >= -0.15 else 0
        p['Temettü (10)'] = round(o['Temettü ödenen yıl'] / 4 * 5) + (5 if tv >= 0.04 else 3 if tv >= 0.02 else 0)
        p['Ucuzluk PD/DD (25)'] = 0 if pdd is None else 25 if pdd <= 0.5 else 20 if pdd <= 0.65 else 12 if pdd <= 0.8 else 5 if pdd <= 1 else 0
    o.update(p); o['HASAT PUANI'] = sum(p.values())
    if tuzak: o['Kategori'] = 'TUZAK ŞÜPHESİ'
    elif neden: o['Kategori'] = 'ELENDİ'
    else:
        s = o['HASAT PUANI']
        o['Kategori'] = 'GÜÇLÜ ADAY' if s >= 70 else 'ADAY' if s >= 55 else 'İZLE' if s >= 40 else 'UYMUYOR'
    return pd.Series(o)

S = pd.concat([D, D.apply(hesap, axis=1)], axis=1)
S.to_pickle('hasat/hasat.pkl')
print(S.groupby(['Grup', 'Kategori']).size())
