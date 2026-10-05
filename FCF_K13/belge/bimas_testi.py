"""TMS 29 çevrim testi (BIMAS, V7'de tüm satırları KESİN): KAP PDF'teki YTD rakamı vs Evo dönemsel/TTM.
Evo değerleri 2026-10-05'te veri_sorgula ile çekildi (hisse_finansal_tablolari_nakit_akis_tablosu_kalemleri).
Sonuç: Evo = PDF × F(rapor tarihi) her kalemde; TTM'de yalnız 'bir kez çevrim' Evo'yu tutuyor → bimas_testi.csv"""
import pandas as pd
K = pd.read_csv('bimas_kalemleri.csv')
P = [(2024, 12), (2025, 3), (2025, 6), (2025, 9), (2025, 12), (2026, 3), (2026, 6)]
F = {(2024, 12): 1.5414, (2025, 3): 1.4004, (2025, 6): 1.3211, (2025, 9): 1.2289, (2025, 12): 1.1776, (2026, 3): 1.0701, (2026, 6): 1.0}
E = {'CFO': [48097601541, 32463158486, 29454043000, 47877807224, 48167371930, 25598185644, 37907288000],
     'MDV+MODV': [-28441816390, -7192348240, -13835068000, -18898727863, -25062470974, -5135981928, -11724445000],
     'KIRA': [-11827970974, -3388216582, -6912515000, -10491740796, -13333208707, -3774746848, -7605060000]}
ET = {'CFO': [48097601541, 67149706896, 54334963622, 46633190766, 48167371930, 41302399088, 56620616930],
      'MDV+MODV': [-28441816390, -28933188165, -27242646712, -25203353628, -25062470974, -23006104661, -22951847974],
      'KIRA': [-11827970974, -12523742637, -13141492825, -13669109086, -13333208707, -13719738973, -14025753707]}
def b(y, m, k, s): return K[(K.yil == y) & (K.ay == m) & (K.kalem == k) & (K.sutun == s)].deger_tl.iloc[0] / 1e6
out = []
for i, (y, m) in enumerate(P):
    for k in E:
        p, e = b(y, m, k, 'cari'), E[k][i] / 1e6
        if m == 12: a, bb, c, fa, fb = p, 0, 0, F[(y, 12)], 0
        else: a, bb, c, fa, fb = p, b(y - 1, 12, k, 'cari'), b(y, m, k, 'onceki'), F[(y, m)], F[(y - 1, 12)]
        out.append({'Rapor': f'{y}/{m:02d}', 'Kalem': k, 'PDF YTD (rapor TL)': round(p, 1), 'Evo dönemsel': round(e, 1),
                    'Evo/PDF': round(e / p, 4), 'F (rapor→Haz26)': F[(y, m)], 'Evo TTM': round(ET[k][i] / 1e6, 1),
                    'Belge TTM çevrilmemiş': round(a + bb - c, 1), 'Belge TTM 1 kez çevrilmiş (kullanılan)': round((a - c) * fa + bb * fb, 1),
                    'Belge TTM 2 kez çevrilmiş': round((a - c) * fa ** 2 + bb * fb ** 2, 1)})
pd.DataFrame(out).to_csv('bimas_testi.csv', index=False)
print(pd.DataFrame(out).to_string(index=False))
