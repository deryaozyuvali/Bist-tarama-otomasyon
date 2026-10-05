"""Karar katmanı + teslim dosyası. V7 rakamlarını DEĞİŞTİRMEZ; yalnız statü önerir."""
import os
import sys
import pandas as pd
SFX = os.environ.get('K13_SFX', '')
NET = os.environ.get('K13_NET', '1') == '1'

V7, DS, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
ORAN = float(sys.argv[4]) if len(sys.argv) > 4 else 0.05
TABAN = 1.0  # mn TL — GEM K7 emsali

m = pd.read_excel(V7, sheet_name='FCF_TTM')
R = pd.read_pickle(f'seri_kalem{SFX}.pkl')
FCFCOL = 'FCF ana · TTM · tanım=FCF türü · statü=FCF statü (mn TL)'


def esik(fcf):
    return max(TABAN, ORAN * abs(fcf)) if pd.notna(fcf) else float('inf')


R['Eşik (mn TL)'] = R['V7 FCF'].map(esik)
R['A1/A2 seri alarmı'] = R['Karar ölçüsü (mn TL)'] >= R['Eşik (mn TL)']
R['A3 net alarmı'] = (R['A3 net davranış (maks pozitif YTD)'] >= R['Eşik (mn TL)']) & NET


def teshis(r):
    t = []
    if r['Şüpheli köprü noktası (kesin)']:
        t.append(f"M-SERİ tek nokta bozuk ({r['Şüpheli köprü noktası (kesin)']})")
    if r['Şüpheli köprü noktası (olası)']:
        t.append(f"M-SERİ atama belirsiz ({r['Şüpheli köprü noktası (olası)']}{'; zayıf' if r['Zayıf atama'] else ''})")
    if r['S1 cari pozitif']:
        t.append('M-İŞARET cari YTD > 0')
    if r['A3 net davranış (maks pozitif YTD)'] > 0:
        t.append(f"M-NET kalem bu şirkette pozitif değer almış (maks {r['A3 net davranış (maks pozitif YTD)']:.1f})")
    return ' · '.join(t)


R['Teşhis'] = R.apply(teshis, axis=1)
R['Alarm'] = R['A1/A2 seri alarmı'] | R['A3 net alarmı']
R['Düzeltme katkısı'] = R['V7 kullanılan'] - R['En az düzeltilmiş kalem (mn TL)']

g = R.groupby(['Kod', 'Dönem'])
F = pd.DataFrame({
    'Alarm': g['Alarm'].any(),
    'Seri alarmı': g['A1/A2 seri alarmı'].any(),
    'Net alarmı': g['A3 net alarmı'].any(),
    'Etkilenen kalemler': g.apply(lambda d: ' + '.join(d.loc[d['Etki alt sınır (mn TL)'] > 0.01, 'Kalem'])),
    'Alarm kalemleri': g.apply(lambda d: ' + '.join(d.loc[d['Alarm'], 'Kalem'])),
    'Toplam etki alt sınır (mn TL)': g['Etki alt sınır (mn TL)'].sum(),
    'Toplam karar ölçüsü (mn TL)': g['Karar ölçüsü (mn TL)'].sum(),
    'Düzeltme toplamı': g['Düzeltme katkısı'].sum(),
    'Teşhis': g.apply(lambda d: ' | '.join(f"{k}: {t}" for k, t in zip(d['Kalem'], d['Teşhis']) if t)),
}).reset_index()

K = m[['Kod', 'Tip', 'Sektör', 'Dönem', 'CFO_TTM', 'CAPEX_STD', '|Kira anapara|', FCFCOL, 'FCF statü', 'FCF türü',
       'K6 dışlanan satır', 'KOŞULLU nedeni']].rename(columns={FCFCOL: 'V7 FCF (mn TL)', 'FCF statü': 'V7 statü'})
K['V7 statü'] = K['V7 statü'].fillna('NULL')
K = K.merge(F, on=['Kod', 'Dönem'], how='left')
K['Alarm'] = K['Alarm'].fillna(False).astype(bool)
K['Seri alarmı'] = K['Seri alarmı'].fillna(False).astype(bool)
K['Net alarmı'] = K['Net alarmı'].fillna(False).astype(bool)
K['Eşik (mn TL)'] = K['V7 FCF (mn TL)'].map(esik)


def yeni_statu(r):
    st = r['V7 statü']
    if st in ('KESİN', 'TÜRETİLMİŞ') and r['Alarm']:
        return 'KOŞULLU'
    return st


def gerekce(r):
    if r['V7 statü'] == 'NULL':
        return 'V7 NULL — değişmedi' + (' (seri anomalisi de var)' if r['Alarm'] else '')
    if r['Alarm']:
        why = []
        if r['Seri alarmı']:
            why.append(f"K13 seri tutarlılığı: köprü noktası bozuk, karar ölçüsü {r['Toplam karar ölçüsü (mn TL)']:.1f} ≥ eşik {r['Eşik (mn TL)']:.1f}")
        if r['Net alarmı']:
            why.append('K13 net davranış: kalem bu şirkette brüt çıkış gibi davranmıyor; dipnot şart')
        pre = 'V7 zaten KOŞULLU; ek neden: ' if r['V7 statü'] == 'KOŞULLU' else ''
        return pre + ' · '.join(why)
    if pd.notna(r['Teşhis']) and r['Teşhis']:
        return 'Anomali var, eşik altı — statü korunur, not düşülür'
    return ''


K['Önerilen statü'] = K.apply(yeni_statu, axis=1)
K['Gerekçe'] = K.apply(gerekce, axis=1)
K['En az düzeltilmiş FCF (TEŞHİS — FCF DEĞİLDİR)'] = K.apply(
    lambda r: r['V7 FCF (mn TL)'] + r['Düzeltme toplamı'] if r['Seri alarmı'] and pd.notna(r['V7 FCF (mn TL)']) else None, axis=1)
K['Statü değişti'] = K['V7 statü'] != K['Önerilen statü']

# ----------------------------------------------------------------- doğrulama
X = pd.read_pickle('dogrulama.pkl')
o = pd.read_excel(DS, sheet_name='ORNEKLEM')
key = ['Kod', 'Kalem', 'Dönem']
D = o.merge(R[key + ['Alarm', 'Etki alt sınır (mn TL)', 'Karar ölçüsü (mn TL)', 'Zayıf atama', 'A3 net davranış (maks pozitif YTD)', 'Teşhis']], on=key, how='left')
D['Alarm'] = D['Alarm'].fillna(False).astype(bool)


def sonuc(r):
    st, gd = r['V7 FCF statü'], r['Gerçek durum']
    if st == 'KOŞULLU':
        return 'V7 zaten KOŞULLU'
    if st == 'NULL' or pd.isna(st):
        return 'V7 zaten NULL'
    if gd == 'BELİRSİZ':
        return 'BELİRSİZ — işaretlendi' if r['Alarm'] else 'BELİRSİZ — işaretlenmedi'
    if gd == 'HATA':
        return 'YAKALANDI' if r['Alarm'] else 'SESSİZ HATA'
    return 'YANLIŞ ALARM' if r['Alarm'] else 'DOĞRU SESSİZ'


D['YENİ sonuç'] = D.apply(sonuc, axis=1)
OZ = pd.DataFrame({c: D[c].value_counts() for c in ['P0 sonuç (formül)', 'P1 sonuç (formül)', 'P2 sonuç (formül)', 'YENİ sonuç']}).fillna(0).astype(int)
sirket = {}
for c in ['P1 sonuç (formül)', 'YENİ sonuç']:
    sirket[c] = {k: D.loc[D[c] == k, 'Kod'].nunique() for k in ['YAKALANDI', 'SESSİZ HATA', 'YANLIŞ ALARM']}
SK = pd.DataFrame(sirket)

pd.to_pickle(dict(K=K, R=R, D=D, OZ=OZ, SK=SK), f'karar_{int(ORAN*100)}{SFX}.pkl')
print(f'ORAN={ORAN}')
print(OZ)
print('Şirket bazında:'); print(SK)
print('\nStatü geçişleri (evren):')
print(pd.crosstab(K['V7 statü'], K['Önerilen statü'], margins=True))
ch = K[K['Statü değişti']]
print('Değişen FCF satırı:', len(ch), '| şirket:', ch.Kod.nunique(),
      '| seri:', ch['Seri alarmı'].sum(), '| yalnız net:', (ch['Net alarmı'] & ~ch['Seri alarmı']).sum())
