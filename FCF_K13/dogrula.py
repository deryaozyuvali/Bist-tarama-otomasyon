"""Seri motorunu DiffSet'in belgeli örneklemine (ORNEKLEM, 125 satır) karşı sınar.
Sonuç taksonomisi DiffSet ile aynıdır (yalnız V7 statüsü KESİN/TÜRETİLMİŞ satırlar)."""
import sys
import pandas as pd

DS = sys.argv[1]
o = pd.read_excel(DS, sheet_name='ORNEKLEM')
R = pd.read_pickle('seri_kalem.pkl')
key = ['Kod', 'Kalem', 'Dönem']
X = o.merge(R[key + ['A3 net davranış (maks pozitif YTD)', 'Etki alt sınır (mn TL)', 'CFO_TTM', 'V7 FCF', 'Şüpheli köprü noktası (kesin)',
                     'Şüpheli köprü noktası (olası)', 'S1 cari pozitif', 'Zayıf atama']],
            on=key, how='left', suffixes=('', '_m'))
X['etki'] = X['Etki alt sınır (mn TL)'].fillna(0.0)
X['etkilendi'] = X['Etki alt sınır (mn TL)'].notna()
cfo = X['CFO_TTM'].abs()
fcf = pd.to_numeric(X['V7 FCF'], errors='coerce').abs()

X['net'] = X['A3 net davranış (maks pozitif YTD)'].fillna(0.0)
ESIKLER = {
    'T6 etki ≥ max(1 mn; %5|FCF|)': lambda: X.etki >= (fcf * 0.05).clip(lower=1.0),
    'T7 T6 + A3 net ≥ max(1 mn; %5|FCF|)': lambda: (X.etki >= (fcf * 0.05).clip(lower=1.0)) | (X.net >= (fcf * 0.05).clip(lower=1.0)),
    'T0 etkilenen her satır': lambda: X.etkilendi,
    'T1 etki > 0': lambda: X.etki > 0.01,
    'T2 etki ≥ max(1 mn; %0,5|CFO|)  [GEM K7 emsali]': lambda: X.etki >= (cfo * 0.005).clip(lower=1.0),
    'T3 etki ≥ %5|FCF|': lambda: X.etki >= fcf * 0.05,
    'T4 etki ≥ 1 mn VE (≥ %0,5|CFO| VEYA ≥ %5|FCF|)': lambda: (X.etki >= 1.0) & ((X.etki >= cfo * 0.005) | (X.etki >= fcf * 0.05)),
    'T5 etki ≥ 1 mn VE ≥ %1|FCF|': lambda: (X.etki >= 1.0) & (X.etki >= fcf * 0.01),
}


def sonuc(row, alarm):
    st, gd = row['V7 FCF statü'], row['Gerçek durum']
    if st in ('KOŞULLU',):
        return 'V7 zaten KOŞULLU'
    if st in ('NULL',) or pd.isna(st):
        return 'V7 zaten NULL'
    if gd == 'BELİRSİZ':
        return 'BELİRSİZ'
    if gd == 'HATA':
        return 'YAKALANDI' if alarm else 'SESSİZ HATA'
    return 'YANLIŞ ALARM' if alarm else 'DOĞRU SESSİZ'


tablo = {}
for ad, f in ESIKLER.items():
    a = f()
    X[ad] = [sonuc(r, al) for (_, r), al in zip(X.iterrows(), a)]
    tablo[ad] = X[ad].value_counts()
T = pd.DataFrame(tablo).fillna(0).astype(int)
ref = o[['P0 sonuç (formül)', 'P1 sonuç (formül)', 'P2 sonuç (formül)']].apply(pd.Series.value_counts).fillna(0).astype(int)
pd.set_option('display.width', 250)
print(T.T)
print('\nReferans (DiffSet):'); print(ref.T)

sec = 'T7 T6 + A3 net ≥ max(1 mn; %5|FCF|)'
print('\nSeçili eşikte SESSİZ HATA / YANLIŞ ALARM satırları:')
cols = key + ['V7 FCF statü', 'Gerçek durum', 'etki', 'net', 'CFO_TTM', 'V7 FCF', 'Şüpheli köprü noktası (kesin)',
              'Şüpheli köprü noktası (olası)', 'S1 cari pozitif', 'Mekanizma / kanıt özeti']
for t in ESIKLER:
    pass
print(X[X[sec].isin(['SESSİZ HATA', 'YANLIŞ ALARM'])][cols + [sec]].to_string())
X.to_pickle('dogrulama.pkl')
