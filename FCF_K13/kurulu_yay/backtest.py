"""Kurulu Yay walk-forward testi: her test dönemi t, yalnız t'den önce gerçekleşmiş geçişlerle eğitilen modelle tahmin edilir."""
import os, sys, json
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ky
L = ky.L; D = ky.D

def skor_tablo(t, M):
    X = ky.tahmin(M, L[L.D == t])
    S = ky.sirket(X)
    onceki = L[L.D == D[D.index(t) - 1]].groupby('Kod').p.sum() if D.index(t) > 0 else pd.Series(dtype=float)
    S['Funnel_onceki'] = S.Kod.map(onceki)
    S['B_dusuk_puan'] = -S.Funnel
    S['B_skor_ivmesi'] = S.Funnel - S.Funnel_onceki
    S['B_esik_yakinligi'] = X.assign(y=X.g_up * (X.z_up < 1)).groupby('Kod').y.sum().reindex(S.Kod).values
    return S

def olc(S, kol, n=30, esik=8):
    s = S.dropna(subset=['Gercek_delta', kol])
    r = s[kol].rank().corr(s.Gercek_delta.rank())
    top = s.nlargest(n, kol); bot = s.nsmallest(n, kol)
    return dict(n=len(s), spearman=round(r, 3), ust30_isabet=round((top.Gercek_delta >= esik).mean(), 3), ust30_ort_delta=round(top.Gercek_delta.mean(), 2),
                alt30_ort_delta=round(bot.Gercek_delta.mean(), 2), taban_isabet=round((s.Gercek_delta >= esik).mean(), 3))

if __name__ == '__main__':
    sonuc, tum = [], []
    for t in D[1:4]:   # test: 2025/09, 2025/12, 2026/03 (gerçekleşen: bir sonraki dönem)
        egitim = L[L.D.map(D.index) < D.index(t)]
        M = ky.egit(egitim)
        S = skor_tablo(t, M); S['Test'] = t; tum.append(S)
        for kol, ad in (('E_delta', 'KURULU YAY (E[Δ])'), ('P_sicrama', 'KURULU YAY (P sıçrama)'), ('B_esik_yakinligi', 'Kıyas: eşik yakınlığı'),
                        ('B_dusuk_puan', 'Kıyas: düşük puan'), ('B_skor_ivmesi', 'Kıyas: skor ivmesi')):
            sonuc.append(dict(Test=f'{t}→{D[D.index(t) + 1]}', Yontem=ad, Egitim_gecis=egitim.D.nunique(), **olc(S, kol)))
        s = S.dropna(subset=['P_kat', 'Gercek_kat'])
        top = s.nlargest(20, 'P_kat')
        sonuc.append(dict(Test=f'{t}→{D[D.index(t) + 1]}', Yontem='KATEGORİ ATLAMA P(üst kategori)', Egitim_gecis=egitim.D.nunique(), n=len(s),
                          ust30_isabet=round(top.Gercek_kat.mean(), 3), taban_isabet=round(s.Gercek_kat.mean(), 3),
                          spearman=round(s.P_kat.rank().corr(s.Gercek_kat.rank()), 3),
                          ust30_ort_delta=round(top.Gercek_delta.mean(), 2), alt30_ort_delta=np.nan))
    R = pd.DataFrame(sonuc)
    pd.set_option('display.width', 200)
    print(R.to_string(index=False))
    print(R.groupby('Yontem')[['spearman', 'ust30_isabet', 'ust30_ort_delta', 'alt30_ort_delta']].mean().round(3))
    R.to_csv('kurulu_yay/backtest_sonuc.csv', index=False)
    pd.concat(tum).to_pickle('kurulu_yay/backtest_tahmin.pkl')
