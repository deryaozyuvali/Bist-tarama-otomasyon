"""Eski 'Kurulu Yay / Funnel Radar' yönteminin bileşenlerini aynı veride test eder (kural tabanlı; öğrenme yok)."""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, 'kurulu_yay')
import ky
L = ky.L.copy(); D = ky.D
# bant genişliği (iyi-yön uzayında): üst eşik − alt eşik; uç bantlarda komşu bandın genişliği
def bantlar(m):
    if m == 'M11': return None
    _, yon, b, _ = ky.BANT[m]
    return sorted(yon * t for t, _, _ in b)
def genislik(m, iy, p):
    t = bantlar(m)
    if t is None or pd.isna(iy): return np.nan
    alt = [x for x in t if x <= iy]; ust = [x for x in t if x > iy]
    if alt and ust: return ust[0] - alt[-1]
    if ust and len(ust) > 1: return ust[1] - ust[0]
    if alt and len(alt) > 1: return alt[-1] - alt[-2]
    return np.nan
S = ky.SKALA
L['w'] = [genislik(m, iy, p) for m, iy, p in zip(L.m, L.iy, L.p)]
L['dup'] = L.z_up * L.m.map(S) / L.w          # üst eşiğe uzaklık / bant genişliği
L['ddn'] = L.z_dn * L.m.map(S) / L.w
L = L.sort_values(['Kod', 'm', 'D'])
L['mom2'] = L.groupby(['Kod', 'm']).mom.shift(1)   # bir önceki geçişin ivmesi
F = pd.read_excel('FCF_MASTER.xlsx', sheet_name='FCF', keep_default_na=False)
F['fcf'] = pd.to_numeric(F['FCF · TTM (mn TL)'], errors='coerce')
F = F.sort_values(['Kod', 'Dönem']); F['dfcf'] = F.groupby('Kod').fcf.diff()
FC = F.set_index(['Kod', 'Dönem'])[['fcf', 'dfcf']]

def skorla(t, esik=0.30):
    X = L[L.D == t].copy()
    yu = X.dup <= esik; yd = X.ddn <= esik
    g = pd.DataFrame({'Kod': X.Kod, 'up': np.where(yu, X.g_up, 0), 'dn': np.where(yd, X.g_dn, 0),
                      'up_y': np.where(yu & (X.mom > 0), X.g_up, 0), 'dn_y': np.where(yd & (X.mom < 0), X.g_dn, 0),
                      'up_y2': np.where(yu & (X.mom > 0) & (X.mom2 > 0), X.g_up, 0), 'n_up': yu.astype(int),
                      'p': X.p, 'ps': X.p_sonra}).groupby('Kod').sum(min_count=1)
    g['Yakın Yukarı'] = g.up; g['Net (yönsüz)'] = g.up - g.dn; g['Yön teyitli net'] = g.up_y - g.dn_y
    g['İki dönem teyitli'] = g.up_y2 - g.dn_y; g['Kümelenme (metrik sayısı)'] = g.n_up
    gercek = X.groupby('Kod').apply(lambda x: x.p_sonra.sum() - x.p.sum() if x.p_sonra.notna().all() else np.nan)
    g['Gercek'] = gercek
    fc = FC.reindex(list(zip(g.index, [t] * len(g))))
    g['FCF iyileşiyor'] = (fc.dfcf.values > 0).astype(float)
    g['Yön teyitli net × FCF teyidi'] = g['Yön teyitli net'] * np.where(g['FCF iyileşiyor'] > 0, 1, 0.5)
    return g

def olc(g, k):
    s = g.dropna(subset=['Gercek'])
    top = s.sort_values(k, ascending=False).head(30)
    return dict(spearman=s[k].rank().corr(s.Gercek.rank()), ust30=top.Gercek.mean(), ust30_isabet=(top.Gercek >= 8).mean())

P = pd.read_pickle('kurulu_yay/backtest_tahmin.pkl')
satir = []
for t in D[1:4]:
    g = skorla(t)
    g['Model E[Δ]'] = P[P.Test == t].set_index('Kod').E_delta
    for k in ['Yakın Yukarı', 'Net (yönsüz)', 'Yön teyitli net', 'İki dönem teyitli', 'Kümelenme (metrik sayısı)', 'Yön teyitli net × FCF teyidi', 'Model E[Δ]']:
        satir.append(dict(Test=t, Yontem=k, **olc(g, k)))
R = pd.DataFrame(satir)
pd.set_option('display.width', 200)
print(R.groupby('Yontem', sort=False)[['spearman', 'ust30', 'ust30_isabet']].mean().round(3))
# %30 eşik duyarlılığı
print('\nEşik duyarlılığı (Yön teyitli net):')
for e in (0.1, 0.2, 0.3, 0.4, 0.5, 1.0):
    r = pd.DataFrame([olc(skorla(t, e), 'Yön teyitli net') for t in D[1:4]]).mean()
    print(e, r.round(3).to_dict())
# kümelenme: aynı yakın yukarı puanda metrik sayısı ek bilgi taşıyor mu?
G = pd.concat([skorla(t).assign(T=t) for t in D[1:4]]).dropna(subset=['Gercek'])
G = G[G['Yakın Yukarı'] > 0]
G['puan_kova'] = pd.cut(G['Yakın Yukarı'], [0, 4, 8, 12, 40])
print('\nKümelenme: aynı Yakın Yukarı kovasında metrik sayısına göre ort. gerçek Δ')
print(G.groupby(['puan_kova', np.where(G.n_up >= 2, '2+ metrik', '1 metrik')]).Gercek.agg(['mean', 'count']).round(2))
# yön teyidi: yakın-yukarı metrik düzeyinde geçiş oranı ivme işaretine göre
X = L[L.D.isin(D[1:4]) & L.p_sonra.notna() & (L.dup <= 0.3)]
print('\nYakın üst eşikteki metriğin gerçekten geçme oranı:')
print(X.groupby(np.select([X.mom > 0, X.mom < 0], ['eşiğe yaklaşıyor', 'uzaklaşıyor'], 'veri yok/sabit')).apply(lambda x: pd.Series({'oran': (x.p_sonra > x.p).mean(), 'n': len(x)})).round(3))
X2 = X[X.mom > 0]
print(X2.groupby(np.where(X2.mom2 > 0, 'iki dönem üst üste', 'tek dönem')).apply(lambda x: pd.Series({'oran': (x.p_sonra > x.p).mean(), 'n': len(x)})).round(3))
Y = L[L.D.isin(D[1:4]) & L.p_sonra.notna() & (L.ddn <= 0.3)]
print('Yakın alt eşikteki metriğin düşme oranı:', round((Y.p_sonra < Y.p).mean(), 3), 'n', len(Y), '| yakın üstün geçme oranı:', round((X.p_sonra > X.p).mean(), 3))
# FCF teyidi: yön teyitli net >0 olanlarda FCF iyileşmesine göre
H = pd.concat([skorla(t).assign(T=t) for t in D[1:4]]).dropna(subset=['Gercek'])
H = H[H['Yön teyitli net'] > 0]
print('\nFCF teyidi (Yön teyitli net > 0):'); print(H.groupby('FCF iyileşiyor').Gercek.agg(['mean', 'count']).round(2))
