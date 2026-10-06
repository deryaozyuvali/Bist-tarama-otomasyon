"""Kullanıcının 03.09.2026 Evo toplu tarama dosyaları (GEM_20xxQx_Funnel_V8_2_FCF_V2_1.xlsx) ↔ FCF_TTM_nihai_belgeli.xlsx."""
import sys, glob, re, pandas as pd
DOS = sys.argv[1:]
N = pd.read_excel('FCF_TTM_nihai_belgeli.xlsx', sheet_name='FCF_TTM')
Q = {'Q2': '06', 'Q3': '09', 'Q4': '12', 'Q1': '03'}
tum = []
for f in DOS:
    y, q = re.search(r'GEM_(\d{4})(Q\d)', f).groups(); don = f'{y}/{Q[q]}'
    d = pd.read_excel(f, sheet_name='FCF_Detay', header=2)
    d = d[d.Kod.notna() & (d.Kod != 'Kod')]
    e = pd.DataFrame({'Kod': d.Kod, 'Kapsam': d.Kapsam,
                      'E_CFO': d['CFO TTM (TL)'] / 1e6, 'E_CAPEX': d['CAPEX_STD'] / 1e6, 'E_KIRA': d['Kira kullanılan'] / 1e6,
                      'E_STD': pd.to_numeric(d['FCF_STD · TTM · KESİN/TÜRETİLMİŞ/KOŞULLU'], errors='coerce') / 1e6,
                      'E_statü': d['STD statü'],
                      'E_HLD': pd.to_numeric(d['FCF_HLD · TTM · KESİN/TÜRETİLMİŞ/KOŞULLU'], errors='coerce') / 1e6,
                      'E_tip': d['FCF tip/seçim'], 'E_not': d['Not']})
    g = pd.read_excel(f, sheet_name='Evo_Girdileri', header=2)[['hisse_senedi_kodu', 'yayinlanma_tarihi_utc']]
    e = e.merge(g.rename(columns={'hisse_senedi_kodu': 'Kod', 'yayinlanma_tarihi_utc': 'Yayın'}), on='Kod', how='left')
    e['Eski etiket'] = don
    # Mali yılı takvim yılı olmayan şirketlerde eski tarama dönemi şirketin kendi mali çeyreğiyle etiketliyor.
    # Takvim dönemine çevir: yayın, etiketin dönem sonundan 110 günden fazla sonraysa → yayından ≥20 gün önceki son çeyrek sonu.
    son = pd.Timestamp(f'{y}-{Q[q]}-01') + pd.offsets.MonthEnd(0)
    def takvim(yayin):
        yayin = pd.Timestamp(yayin)
        if pd.isna(yayin) or (yayin - son).days <= 110: return don
        q_ = (yayin - pd.Timedelta(days=20)) - pd.offsets.QuarterEnd(0) if False else None
        d_ = yayin - pd.Timedelta(days=20)
        qe = pd.Timestamp(d_.year, ((d_.month - 1) // 3) * 3 + 1, 1) - pd.Timedelta(days=1)
        return f'{qe.year}/{qe.month:02d}'
    e['Dönem'] = e['Yayın'].map(takvim)
    tum.append(e)
E_ = pd.concat(tum, ignore_index=True)
E_ = E_.drop_duplicates(['Kod', 'Dönem'], keep='last')
n = N[N['Dönem'].isin(sorted(E_['Eski etiket'].unique()))]
M = E_.merge(n, on=['Kod', 'Dönem'], how='outer', indicator=True)

def esit(a, b):
    return abs(a - b) <= max(0.005 * max(abs(a), abs(b)), 0.5)

def sinif(r):
    if r['_merge'] == 'left_only':
        return 'Yalnız eski dosyada (kapsam dışı: ' + str(r['Kapsam']) + ')'
    if r['_merge'] == 'right_only':
        return 'Yalnız nihai dosyada'
    eski = r['E_STD']; yeni = r['FCF_STD (①)']
    if pd.isna(yeni): yeni = r['FCF · TTM (mn TL)'] if r['FCF türü'] == 'FCF_STD' else None
    if (yeni is None or pd.isna(yeni)) and r['FCF türü'] == 'FCF_HLD' and not pd.isna(r['FCF_HLD (②)']):
        eski, yeni = r['E_HLD'], r['FCF_HLD (②)']   # holding: belgeden yalnız HLD kuruldu → HLD ile kıyas
    if pd.isna(eski) and (yeni is None or pd.isna(yeni)):
        return 'İkisinde de boş'
    if pd.isna(eski):
        return 'Eskide boş → nihai doldurdu'
    if yeni is None or pd.isna(yeni):
        return 'Eskide rakam var → nihai boş'
    if esit(eski, yeni):
        return 'Tutuyor'
    return 'Farklı'
M['Sınıf'] = M.apply(sinif, axis=1)
M['Nihai FCF_STD'] = M['FCF_STD (①)'].fillna(M['FCF_HLD (②)'].where(M['FCF türü'] == 'FCF_HLD'))
M['E_STD'] = M['E_STD'].where(M['FCF_STD (①)'].notna() | (M['FCF türü'] != 'FCF_HLD'), M['E_HLD'])
M['Fark (nihai−eski)'] = M['Nihai FCF_STD'] - M['E_STD']
M['İşaret değişti'] = (M['Sınıf'] == 'Farklı') & ((M['Nihai FCF_STD'] > 0) != (M['E_STD'] > 0))

def neden(r):
    if r['Sınıf'] != 'Farklı': return ''
    if r['Kaynak'] in ('BELGE', 'BELGE (izahname)'): return 'Belge düzeltmesi (Evo belgeyle uyuşmadı)'
    if not pd.isna(r['V7 FCF']) and r['FCF türü'] == 'FCF_STD' and esit(r['V7 FCF'], r['Nihai FCF_STD']):
        bil = []
        for k, a, b in (('CFO', 'E_CFO', 'CFO_TTM'), ('CAPEX', 'E_CAPEX', 'CAPEX_STD'), ('Kira', 'E_KIRA', '|Kira anapara|')):
            if not (pd.isna(r[a]) or pd.isna(r[b])) and not esit(r[a], r[b]): bil.append(k)
            elif pd.isna(r[a]) != pd.isna(r[b]): bil.append(k + '(boş)')
        return 'V7 kuralı/Evo farkı (belge değil): ' + ', '.join(bil)
    return 'V7 kuralı/Evo farkı (belge değil)'
M['Fark nedeni'] = M.apply(neden, axis=1)

ozet = pd.crosstab(M['Sınıf'], M['Dönem'], margins=True, margins_name='Toplam')
ned = M[M['Sınıf'] == 'Farklı']['Fark nedeni'].str.split(':').str[0].value_counts()
kol = ['Dönem', 'Eski etiket', 'Yayın', 'Kod', 'Kapsam', 'Sınıf', 'E_statü', 'E_STD', 'Nihai FCF_STD', 'Fark (nihai−eski)', 'İşaret değişti', 'Statü',
       'Kaynak', 'Fark nedeni', 'E_CFO', 'CFO_TTM', 'E_CAPEX', 'CAPEX_STD', 'E_KIRA', '|Kira anapara|', 'E_HLD', 'FCF_HLD (②)',
       'E_not', 'Açıklama']
R = M[kol].rename(columns={'E_statü': 'Eski statü', 'E_STD': 'Eski FCF_STD', 'E_CFO': 'Eski CFO', 'E_CAPEX': 'Eski CAPEX',
                           'E_KIRA': 'Eski kira', 'E_HLD': 'Eski FCF_HLD', 'E_not': 'Eski not', 'Statü': 'Nihai statü',
                           'Kaynak': 'Nihai kaynak', 'CFO_TTM': 'Nihai CFO', 'CAPEX_STD': 'Nihai CAPEX',
                           '|Kira anapara|': 'Nihai kira', 'FCF_HLD (②)': 'Nihai FCF_HLD', 'Açıklama': 'Nihai açıklama'})
with pd.ExcelWriter('ESKI_TARAMA_karsilastirma.xlsx') as w:
    pd.DataFrame([
        ('Ne', 'Eski toplu tarama dosyaları (Evo, çekim 03.09.2026; 2025/06–2026/06) ile FCF_TTM_nihai_belgeli.xlsx FCF_STD karşılaştırması.'),
        ('Birim', 'mn TL. İki dosya da Haziran 2026 satın alma gücünde (ikisi de 2026/06 raporları sonrası Evo verisi).'),
        ('Tutuyor', 'Fark ≤ %0,5 veya ≤ 0,5 mn TL.'),
        ('Karşılaştırılan', 'FCF_STD (①) — iki dosyada da her satırda var. Holdinglerde FCF_HLD ayrı sütunda.'),
        ('Fark nedeni', 'Belge düzeltmesi: nihai rakam şirket raporundan. V7 kuralı/Evo farkı: nihai = V7 (Evo), fark eski taramanın '
                        'kuralından (ör. kısmi kayıt, ihmal eşiği, işaret anomalisi, kira) — hangi bileşende olduğu yazılı.'),
    ], columns=['Konu', 'Açıklama']).to_excel(w, sheet_name='OKUBENI', index=False)
    ozet.to_excel(w, sheet_name='OZET')
    ned.rename('Satır').to_frame().to_excel(w, sheet_name='OZET', startrow=len(ozet) + 3)
    R.sort_values(['Sınıf', 'Kod', 'Dönem']).to_excel(w, sheet_name='TUMU', index=False)
    for s in ['Farklı', 'Eskide boş → nihai doldurdu', 'Eskide rakam var → nihai boş', 'İkisinde de boş']:
        R[R['Sınıf'] == s].sort_values(['Kod', 'Dönem']).to_excel(w, sheet_name=s[:31].replace('→', '-').replace('/', '-'), index=False)
print(ozet.to_string()); print(ned.to_string())
F = M[M['Sınıf'] == 'Farklı']
print('işaret değişen:', F['İşaret değişti'].sum(), '| belge kaynaklı işaret:', (F['İşaret değişti'] & F['Fark nedeni'].str.startswith('Belge')).sum())
print(M[M['Sınıf']=='Eskide rakam var → nihai boş'][['Dönem','Kod','E_STD','Statü','Açıklama']].head(15).to_string())
