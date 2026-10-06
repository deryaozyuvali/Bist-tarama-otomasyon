"""GEM v6.2'nin eski toplu Funnel puanlarına etkisi.
Funnel kural/eşikleri v6.2'de değişmedi; değişebilecek tek yol veri: Kontrol 14 (Evo–belge) ile CFO değişirse M1, CFO
NULL'dan dolarsa M1 NULL→puan. Ayrıca Bölüm F 'son üç çeyreğin TTM FCF'i negatif' bayrağı nihai FCF ile yeniden hesaplanır."""
import sys, re, pandas as pd
N = pd.read_excel('FCF_TTM_nihai_belgeli.xlsx', sheet_name='FCF_TTM')
NC = N.set_index(['Kod', 'Dönem'])
Q = {'Q2': '06', 'Q3': '09', 'Q4': '12', 'Q1': '03'}
DON = ['2025/03', '2025/06', '2025/09', '2025/12', '2026/03', '2026/06']

def m1(cfo, nk):
    if cfo is None or pd.isna(cfo): return None
    if pd.isna(nk) or nk <= 0: return 0
    r = cfo / nk
    return 15 if r >= 1 else 10 if r >= 0.5 else 5 if r > 0 else 0

def tier(s):
    return 'ANA LİSTE' if s >= 70 else 'İZLEME' if s >= 60 else '50–59' if s >= 50 else 'ALT'

satir = []
for f in sys.argv[1:]:
    y, q = re.search(r'GEM_(\d{4})(Q\d)', f).groups(); don = f'{y}/{Q[q]}'
    son = pd.Timestamp(f'{y}-{Q[q]}-01') + pd.offsets.MonthEnd(0)
    fd = pd.read_excel(f, sheet_name='Funnel_Detay', header=2)
    ev = pd.read_excel(f, sheet_name='Evo_Girdileri', header=2).rename(columns={'hisse_senedi_kodu': 'Kod'})
    d = fd.merge(ev[['Kod', 'cfo_ttm', 'net_total_cur', 'yayinlanma_tarihi_utc']], on='Kod', how='left')
    d = d[d['Kapsam'] == 'STANDART']
    for _, r in d.iterrows():
        yay = pd.Timestamp(r['yayinlanma_tarihi_utc'])
        tdon = don
        if not pd.isna(yay) and (yay - son).days > 110:  # takvim dışı mali yıl → takvim dönemi
            x = yay - pd.Timedelta(days=20)
            qe = pd.Timestamp(x.year, ((x.month - 1) // 3) * 3 + 1, 1) - pd.Timedelta(days=1)
            tdon = f'{qe.year}/{qe.month:02d}'
        if (r['Kod'], tdon) not in NC.index: continue
        n = NC.loc[(r['Kod'], tdon)]
        e_cfo = r['cfo_ttm'] / 1e6 if not pd.isna(r['cfo_ttm']) else None
        n_cfo = n['CFO_TTM']
        if pd.isna(n_cfo): continue
        if e_cfo is not None and abs(e_cfo - n_cfo) <= max(0.005 * abs(n_cfo), 0.5): continue
        nk = r['net_total_cur'] / 1e6 if not pd.isna(r['net_total_cur']) else float('nan')
        eski = None if pd.isna(r['M1 Puan']) else int(r['M1 Puan'])
        yeni = m1(n_cfo, nk)
        mn, mx = r['Funnel MIN'], r['Funnel MAX']
        if pd.isna(mn): continue
        ymn = mn - (eski or 0) + yeni
        ymx = mx - (eski if eski is not None else 15) + yeni
        et = r['Tier MIN'] if r['Tier MIN'] == r['Tier MAX'] else 'BELİRSİZ'
        yt = tier(ymn) if tier(ymn) == tier(ymx) else 'BELİRSİZ'
        satir.append(dict(Dönem=tdon, Etiket=don, Kod=r['Kod'], Eski_CFO=e_cfo, Nihai_CFO=n_cfo, Net_kar=nk,
                          Kaynak=n['Kaynak'], Eski_M1=eski, Yeni_M1=yeni, Eski_MIN=mn, Eski_MAX=mx, Yeni_MIN=ymn,
                          Yeni_MAX=ymx, Eski_tier=et, Yeni_tier=yt, Eski_kategori=r['Son Kategori']))
T = pd.DataFrame(satir)
T['Puan değişti'] = (T.Eski_MIN != T.Yeni_MIN) | (T.Eski_MAX != T.Yeni_MAX)
T['Tier değişti'] = T.Eski_tier.str.replace('50–59 · BİLANÇO PUANI GEREKLİ', '50–59') != T.Yeni_tier
T['Neden'] = ['CFO NULL → belgeden' if pd.isna(a) else ('Belge düzeltmesi' if 'BELGE' in str(k) else 'Evo çekim/kural farkı')
              for a, k in zip(T.Eski_CFO, T.Kaynak)]

# Bölüm F: Funnel ≥70 ve son üç çeyreğin TTM FCF'i negatif → KOŞULLU Ana Liste
S = N.pivot(index='Kod', columns='Dönem', values='FCF · TTM (mn TL)').reindex(columns=DON)
E = {}
for f in sys.argv[1:]:
    y, q = re.search(r'GEM_(\d{4})(Q\d)', f).groups(); don = f'{y}/{Q[q]}'
    s = pd.read_excel(f, sheet_name='Sonuclar', header=2)
    E[don] = s.set_index('Kod')
F = []
for don in DON[2:]:
    if don not in E: continue
    i = DON.index(don); ucl = DON[i - 2:i + 1]
    s = E[don]
    for kod, r in s[s['Kategori'] == 'ANA LİSTE'].iterrows():
        if kod not in S.index: continue
        v = S.loc[kod, ucl]
        eski = [E[d].loc[kod, 'FCF_STD · TTM · statü satırda'] if d in E and kod in E[d].index else None for d in ucl]
        def neg(xs): return all(x is not None and not pd.isna(x) and float(x) < 0 for x in xs)
        F.append(dict(Dönem=don, Kod=kod, Eski_3neg=None if any(d not in E for d in ucl) else neg([x if x is None or pd.isna(x) else float(x) / 1e6 for x in eski]),
                      Nihai_3neg=neg(list(v)), Nihai_seri=' | '.join('' if pd.isna(x) else f'{x:,.0f}' for x in v)))
F = pd.DataFrame(F)
with pd.ExcelWriter('FUNNEL_v62_etki.xlsx') as w:
    pd.DataFrame([
        ('Soru', 'GEM v6.2 eski toplu Funnel puanlarını değiştirir mi?'),
        ('Kural', 'Funnel metrik tanımları ve eşikleri v6.2\'de DEĞİŞMEDİ. Puan yalnız veri değişirse değişir.'),
        ('M1', 'Kontrol 14 (şirket analizinde Evo–belge) ile CFO değişirse M1 (CFO/Net kâr) değişebilir. Bu sayfa nihai FCF dosyasındaki '
               'CFO\'yu eski taramanın Net kârıyla birleştirip M1, MIN/MAX ve tier\'ı yeniden hesaplar.'),
        ('Diğer metrikler', 'M2–M12 girdileri (bilanço, gelir tablosu) bu çalışmada belgeyle kontrol edilmedi → etkisi ölçülemez.'),
        ('Bölüm F', 'Funnel ≥70 ve son üç çeyreğin TTM FCF\'i negatif → KOŞULLU Ana Liste. Eski dosya bu etiketi üretmemiş; '
                    'eski ve nihai FCF ile ayrı ayrı hesaplandı.'),
        ('Toplu tarama', 'v6.2\'de Evo–belge kontrolü şirket analizi içindir; toplu Funnel taraması Evo ile aynı kalır.'),
    ], columns=['Konu', 'Açıklama']).to_excel(w, sheet_name='OKUBENI', index=False)
    T.sort_values(['Tier değişti', 'Puan değişti'], ascending=False).to_excel(w, sheet_name='M1_CFO_ETKI', index=False)
    F.to_excel(w, sheet_name='BOLUM_F', index=False)
print(len(T), 'CFO farklı satır;', T['Puan değişti'].sum(), 'puan değişir;', T['Tier değişti'].sum(), 'tier değişir')
print(T.groupby('Neden')[['Puan değişti', 'Tier değişti']].sum())
print(T[T['Tier değişti']][['Etiket', 'Kod', 'Eski_M1', 'Yeni_M1', 'Eski_MIN', 'Eski_MAX', 'Yeni_MIN', 'Yeni_MAX', 'Eski_tier', 'Yeni_tier', 'Neden']].to_string())
print(F.groupby('Dönem')[['Eski_3neg', 'Nihai_3neg']].sum()); print(F[F.Eski_3neg != F.Nihai_3neg].to_string())
