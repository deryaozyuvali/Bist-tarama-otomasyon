"""KURULU YAY — bir sonraki bilançoda Funnel V8.2 puan sıçraması olasılığı (öncü radar; Funnel'ın yerine geçmez).
Veri: yalnız FCF_MASTER.xlsx (FUNNEL: M1–M12 değer + puan, 5 dönem; FCF: TTM FCF serisi). Funnel kuralları değiştirilmez.

Yöntem (metrik bazında geçiş modeli):
  Her metrik için mevcut değerin bir üst / bir alt puan bandının eşiğine uzaklığı, metriğin evrendeki tipik çeyreklik
  oynaklığıyla ölçeklenir (z_up, z_dn). Son çeyrekteki hareket aynı ölçekle "iyileşme yönünde ivme" (mom) olur.
  Metrik başına iki lojistik model (yukarı bant geçişi / aşağı bant geçişi) geçmiş geçişlerden öğrenilir:
      P_up = σ(a + b·z_up + c·mom)   P_dn = σ(a' + b'·z_dn + c'·mom)
  Beklenen puan değişimi  E[Δ] = Σ_metrik ( P_up·kazanç − P_dn·kayıp ); sıçrama olasılığı P(Δ ≥ 8) Monte Carlo ile.
  Kurulu Yay skoru = E[Δ] (aşağı risk zaten içinde); ayrıca yukarı potansiyel, aşağı risk ve P(sıçrama) ayrı gösterilir.
Test: ileriye dönük (walk-forward) — her test geçişi yalnız ondan önceki geçişlerle eğitilen modelle tahmin edilir."""
import os, json
import numpy as np, pandas as pd

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(KOK)
D = ['2025/06', '2025/09', '2025/12', '2026/03', '2026/06']
F = pd.read_excel('FCF_MASTER.xlsx', sheet_name='FUNNEL')
F = F[(F.Kapsam == 'STANDART') & (F['Puan Durumu'] == 'PUANLANIR')]

# Funnel V8.2 bantları (GEM Bölüm D) — iyi yön: +1 büyük iyi, −1 küçük iyi. (eşik, puan, karşılaştırma)
BANT = {
    'M1': ('M1 CFO/NK', +1, [(1.0, 15, '>='), (0.5, 10, '>='), (0.0, 5, '>')], 0),
    'M2': ('M2 Net Borç/FAVÖK', -1, [(0.5, 10, '<='), (1.5, 7, '<='), (3.0, 4, '<='), (5.0, 2, '<=')], 0),
    'M3': ('M3 Cari Oran', +1, [(1.5, 5, '>'), (1.0, 3, '>'), (0.5, 1, '>')], 0),
    'M5': ('M5 ROE', +1, [(0.20, 12, '>'), (0.10, 8, '>'), (0.05, 5, '>'), (0.0, 2, '>')], 0),
    'M6': ('M6 Brüt Marj', +1, [(0.40, 11, '>'), (0.25, 8, '>'), (0.15, 5, '>'), (0.0, 2, '>')], 0),
    'M7': ('M7 Satış Büyümesi', +1, [(0.10, 10, '>='), (0.0, 7, '>='), (-0.05, 4, '>=')], 0),
    'M8': ('M8 Özkaynak Büyümesi', +1, [(0.05, 10, '>='), (-0.05, 7, '>='), (-0.15, 4, '>=')], 0),
    'M9': ('M9 OPEX/Brüt Kâr', -1, [(0.40, 8, '<='), (0.50, 5, '<='), (1.00, 2, '<=')], 0),
    'M10': ('M10 R', -1, [(1.00, 7, '<='), (1.10, 4, '<=')], 0),
    'M11': ('M11 FAVÖK/NK', 0, None, None),   # tepe bandı [1,3] — özel
    'M12': ('M12 Marj Trendi', +1, [(0.05, 5, '>'), (-0.05, 3, '>'), (-0.15, 1, '>')], 0),
}
MAXP = {'M1': 15, 'M2': 10, 'M3': 5, 'M5': 12, 'M6': 11, 'M7': 10, 'M8': 10, 'M9': 8, 'M10': 7, 'M11': 7, 'M12': 5}

def esikler(m, v, p):
    """→ (üst eşik, üst puan, alt eşik, alt puan) iyi-yön değer uzayında; yoksa None."""
    if m == 'M11':  # 7: [1,3]; 5: [0.5,1) ∪ (3,5]; 2: (0,0.5) ∪ >5
        if pd.isna(v) or v <= 0: return None
        if 1 <= v <= 3: return (None, None, (v - 1) if v - 1 < 3 - v else (3 - v), 5)
        if 0.5 <= v < 1: return (1 - v, 7, v - 0.5, 2)
        if 3 < v <= 5: return (v - 3, 7, 5 - v, 2)
        if v < 0.5: return (0.5 - v, 5, None, None)
        return (v - 5, 5, None, None)
    _, yon, bands, taban = BANT[m]
    if pd.isna(v): return None
    x = yon * v
    seviyeler = [(yon * t, pt) for t, pt, _ in bands]  # iyi yönde artan eşikler, puan azalan
    up = dn = None
    ust = [(t, pt) for t, pt in seviyeler if pt > p]
    alt = [(t, pt) for t, pt in seviyeler if pt == p]
    if ust: t, pt = min(ust, key=lambda a: a[1]); up = (t - x, pt)       # bir üst bandın eşiği
    if alt: t, _ = alt[0]; nxt = [pt for _, pt in seviyeler if pt < p]
    if alt: dn = (x - t, max(nxt) if nxt else taban)                      # mevcut bandın alt eşiği
    return (up[0] if up else None, up[1] if up else None, dn[0] if dn else None, dn[1] if dn else None)

# --- uzun tablo: şirket × dönem × metrik
rows = []
for _, r in F.iterrows():
    for m, (col, yon, _, _) in BANT.items():
        v, p = r[col], r[m + ' Puan']
        if pd.isna(p): continue
        rows.append(dict(Kod=r.Kod, D=r['Dönem'], m=m, v=v, p=p))
L = pd.DataFrame(rows)
L['iy'] = [BANT[m][1] * v if m != 'M11' else (-abs(v - 2) if pd.notna(v) else np.nan) for m, v in zip(L.m, L.v)]  # iyi-yön değeri
L = L.sort_values(['Kod', 'm', 'D'])
L['iy_onceki'] = L.groupby(['Kod', 'm']).iy.shift(1)
L['D_onceki'] = L.groupby(['Kod', 'm']).D.shift(1)
L['p_sonra'] = L.groupby(['Kod', 'm']).p.shift(-1)
L['D_sonra'] = L.groupby(['Kod', 'm']).D.shift(-1)
sira = {d: i for i, d in enumerate(D)}
L.loc[L.D_onceki.map(sira) != L.D.map(sira) - 1, 'iy_onceki'] = np.nan
L.loc[L.D_sonra.map(sira) != L.D.map(sira) + 1, 'p_sonra'] = np.nan
# metrik ölçeği: çeyreklik iyi-yön değişiminin evren medyan mutlak değeri (outlier'a dayanıklı)
SKALA = (L.iy - L.iy_onceki).abs().groupby(L.m).median().to_dict()
E = [esikler(m, v, p) for m, v, p in zip(L.m, L.v, L.p)]
L['z_up'] = [e[0] / SKALA[m] if e and e[0] is not None else np.nan for e, m in zip(E, L.m)]
L['g_up'] = [e[1] - p if e and e[1] is not None else 0 for e, p in zip(E, L.p)]
L['z_dn'] = [e[2] / SKALA[m] if e and e[2] is not None else np.nan for e, m in zip(E, L.m)]
L['g_dn'] = [p - e[3] if e and e[3] is not None else 0 for e, p in zip(E, L.p)]
L['mom'] = ((L.iy - L.iy_onceki) / L.m.map(SKALA)).clip(-5, 5)
L['mom_var'] = L.mom.notna().astype(float); L['mom'] = L.mom.fillna(0)
# değer yok / rejim dışı (ör. net kâr ≤ 0 → M1/M5/M11 = 0): ayrı taban oranı
# değer ile puan bandı tutarsızsa (net kâr ≤ 0 / brüt kâr ≤ 0 / net borç < 0 / M10 "prior yok" şeması) → rejim:
# eşik uzaklığı anlamsız; o metrik-rejim için geçmiş taban oranları kullanılır
tutarsiz = (L.z_up < -1e-9) | (L.z_dn < -1e-9)
L.loc[tutarsiz, ['z_up', 'z_dn']] = np.nan
L['rejim'] = tutarsiz | (L.z_up.isna() & (L.p < L.m.map(MAXP)))

def sig(x): return 1 / (1 + np.exp(-x))
def lojistik(X, y, l2=1.0, it=3000, lr=0.1):
    X = np.column_stack([np.ones(len(X)), X]); w = np.zeros(X.shape[1])
    for _ in range(it):
        g = X.T @ (sig(X @ w) - y) / len(y) + l2 * np.r_[0, w[1:]] / len(y)
        w -= lr * g
    return w

def egit(T):
    """Metrik başına yukarı/aşağı geçiş modelleri + rejim taban oranları."""
    M = {}
    for m in MAXP:
        t = T[(T.m == m) & T.p_sonra.notna()]
        u = t[t.z_up.notna()]
        yu = (u.p_sonra > u.p).astype(float).values
        Xu = np.column_stack([np.log1p(u.z_up.clip(0, 50)), u.mom, u.mom_var])
        d = t[t.z_dn.notna()]
        yd = (d.p_sonra < d.p).astype(float).values
        Xd = np.column_stack([np.log1p(d.z_dn.clip(0, 50)), d.mom, d.mom_var])
        rj = t[t.rejim]
        M[m] = dict(up=lojistik(Xu, yu) if len(yu) > 30 else None, dn=lojistik(Xd, yd) if len(yd) > 30 else None,
                    rejim_up=float((rj.p_sonra > rj.p).mean()) if len(rj) > 10 else 0.0,
                    rejim_dn=float((rj.p_sonra < rj.p).mean()) if len(rj) > 10 else 0.0,
                    rejim_kayip=float((rj.p - rj.p_sonra).clip(lower=0).mean() / max((rj.p_sonra < rj.p).mean(), 1e-9)) if len(rj) > 10 and (rj.p_sonra < rj.p).any() else 0.0,
                    rejim_kazanc=float((rj.p_sonra - rj.p).clip(lower=0).mean() / max((rj.p_sonra > rj.p).mean(), 1e-9)) if len(rj) > 10 and (rj.p_sonra > rj.p).any() else 0.0)
    return M

def tahmin(M, X):
    X = X.copy()
    pu = np.zeros(len(X)); pd_ = np.zeros(len(X)); gu = X.g_up.values.astype(float).copy(); gd = X.g_dn.values.astype(float).copy()
    for m, w in M.items():
        i = (X.m == m).values
        if w['up'] is not None:
            j = i & X.z_up.notna().values
            pu[j] = sig(np.column_stack([np.ones(j.sum()), np.log1p(X.z_up[j].clip(0, 50)), X.mom[j], X.mom_var[j]]) @ w['up'])
        j = i & X.rejim.values
        pu[j] = w['rejim_up']; gu[j] = np.minimum(w['rejim_kazanc'], MAXP[m] - X.p.values[j])
        if w['dn'] is not None:
            j = i & X.z_dn.notna().values
            pd_[j] = sig(np.column_stack([np.ones(j.sum()), np.log1p(X.z_dn[j].clip(0, 50)), X.mom[j], X.mom_var[j]]) @ w['dn'])
        j = i & X.rejim.values & (X.p.values > 0)
        pd_[j] = w['rejim_dn']; gd[j] = np.minimum(w['rejim_kayip'], X.p.values[j])
    X['P_up'], X['P_dn'], X['kazanc'], X['g_dn'] = pu, pd_, gu, gd
    X['E_up'] = X.P_up * X.kazanc; X['E_dn'] = X.P_dn * X.g_dn
    return X

def sirket(X, n_mc=4000, seed=0):
    rng = np.random.default_rng(seed)
    out = []
    for (k, d), g in X.groupby(['Kod', 'D']):
        ku = rng.random((n_mc, len(g))) < g.P_up.values
        kd = (rng.random((n_mc, len(g))) < g.P_dn.values) & ~ku
        delta = (ku * g.kazanc.values - kd * g.g_dn.values).sum(1)
        f0 = g.p.sum(); f1 = f0 + delta
        gercek = (g.p_sonra.sum()) if g.p_sonra.notna().all() else np.nan
        out.append(dict(Kod=k, D=d, Funnel=f0, E_delta=g.E_up.sum() - g.E_dn.sum(), Yukari=g.E_up.sum(), Asagi=g.E_dn.sum(),
                        P_sicrama=(delta >= 8).mean(), P_dusus=(delta <= -8).mean(),
                        P_60=(f1 >= 60).mean() if f0 < 60 else np.nan, P_70=(f1 >= 70).mean() if f0 < 70 else np.nan,
                        P_kat=((f1 >= 70).mean() if f0 >= 60 else (f1 >= 60).mean()) if f0 < 70 else np.nan,
                        Gercek_kat=(float(gercek >= 70) if f0 >= 60 else float(gercek >= 60)) if f0 < 70 and pd.notna(gercek) else np.nan,
                        M10_payi=(g[g.m == 'M10'].E_up.sum() / g.E_up.sum()) if g.E_up.sum() > 0 else np.nan,
                        Gercek_delta=(g.p_sonra.sum() - g.p.sum()) if g.p_sonra.notna().all() else np.nan,
                        Surukleyici='; '.join(f"{m} {p:.0f}→{p + kz:.0f} (%{100 * pu:.0f})" for m, p, kz, pu in
                                              sorted(zip(g.m, g.p, g.kazanc, g.P_up), key=lambda a: -a[2] * a[3])[:3] if pu * kz >= 0.5),
                        Risk='; '.join(f"{m} {p:.0f}→{p - gd:.0f} (%{100 * pdn:.0f})" for m, p, gd, pdn in
                                       sorted(zip(g.m, g.p, g.g_dn, g.P_dn), key=lambda a: -a[2] * a[3])[:3] if pdn * gd >= 0.5)))
    return pd.DataFrame(out)

if __name__ == '__main__':
    L.to_pickle('kurulu_yay/uzun.pkl')
    json.dump({k: float(v) for k, v in SKALA.items()}, open('kurulu_yay/skala.json', 'w'), indent=1)
    print(L.groupby('D').Kod.nunique(), SKALA)
