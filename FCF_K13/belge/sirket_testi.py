"""TMS 29 çevrim testi, şirket bazında: KAP PDF'teki YTD rakamı vs Evo dönemsel/TTM, ayrıca V7 KARAR ile.
Kullanım: python3 sirket_testi.py KOD  (girdi: kod_kalemleri.csv, evo_KOD.json {kalem: {"YYYY/MM": [donemsel, ttm]}})
Çıktı: KOD_testi.csv"""
import json, sys
import pandas as pd
kod = sys.argv[1]
K = pd.read_csv(f'{kod.lower()}_kalemleri.csv')
E = json.load(open(f'evo_{kod}.json'))
F = {(2024, 12): 1.5414, (2025, 3): 1.4004, (2025, 6): 1.3211, (2025, 9): 1.2289, (2025, 12): 1.1776, (2026, 3): 1.0701, (2026, 6): 1.0}
V7 = pd.read_excel('../FCF_V8_aday_K13.xlsx', sheet_name='KARAR', keep_default_na=False, na_values=[''])
V7 = V7[V7.Kod == kod].set_index('Dönem')
def b(y, m, k, s): return K[(K.yil == y) & (K.ay == m) & (K.kalem == k) & (K.sutun == s)].deger_tl.iloc[0] / 1e6
out = []
for (y, m) in F:
    for k in E:
        p = b(y, m, k, 'cari'); ed, et = (v / 1e6 for v in E[k][f'{y}/{m:02d}'])
        if m == 12: a, bb, c, fa, fb = p, 0, 0, F[(y, 12)], 0
        else: a, bb, c, fa, fb = p, b(y - 1, 12, k, 'cari'), b(y, m, k, 'onceki'), F[(y, m)], F[(y - 1, 12)]
        d = f'{y}/{m:02d}'
        v7 = {'CFO': 'CFO_TTM', 'KIRA': '|Kira anapara|'}.get(k)
        out.append({'Rapor': d, 'Kalem': k, 'PDF YTD (rapor TL)': round(p, 1), 'Evo dönemsel': round(ed, 1),
                    'Evo/PDF': round(ed / p, 4), 'F (rapor→Haz26)': F[(y, m)], 'Evo TTM': round(et, 1),
                    'Belge TTM çevrilmemiş': round(a + bb - c, 1), 'Belge TTM 1 kez (kullanılan)': round((a - c) * fa + bb * fb, 1),
                    'Belge TTM 2 kez': round((a - c) * fa ** 2 + bb * fb ** 2, 1),
                    'V7 (KARAR)': (round(V7.at[d, v7], 1) if v7 and d in V7.index else None)})
D = pd.DataFrame(out); D.to_csv(f'{kod}_testi.csv', index=False)
pd.set_option('display.width', 250); print(D.to_string(index=False))
