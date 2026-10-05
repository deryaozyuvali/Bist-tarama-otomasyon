"""KOŞULLU satırların belge kontrolü sonucu: kosullu_ttm.csv (ttm.py MOD=KOSULLU) → kosullu_sonuc.csv
Karşılaştırma bileşen bazında: CFO_TTM, CAPEX_STD (|MDV+MODV|+|YAGM|, K6), |Kira| — tolerans %0,5 + 0,05 mn.
Sonuç:
  KESİN_ONERI   üç bileşen de belgeyle V7 aynı (belge statüsü ne olursa olsun: iki bağımsız kaynak örtüşüyor)
  KESİN_ONERI_YAKIN  bileşenler V7 ile en fazla %3 farklı (TMS 29 yeniden ifade ayrıntısı düzeyinde; V7 kabul edilebilir)
  BELGE_DEGERI  belge değerleri güvenilir (TEYITLI / PDF_OKUNDU / İZAHNAME) ve en az bir bileşen V7'den farklı →
                belge değeri önerilir; fark nedeni: EVO_NOMINAL (V7 = belgenin TMS29 çevrimsiz hali) ya da FARKLI
  ELLE          belge değerlerinden en az biri düşük güvenli / okunamadı ve V7 ile örtüşme tam değil
  BELGE_YOK     gereken raporlar indirilemedi (KAP erişimi) ya da Evo havuzunda yok"""
import pandas as pd

d = pd.read_csv('kosullu_ttm.csv')
def es(a, b): return pd.notna(a) and pd.notna(b) and abs(a - b) <= 0.005 * abs(b) + 0.05
def cik(v): return None if pd.isna(v) else (-v if v < 0 else 0.0)
d['CAPEX nominal'] = [None if pd.isna(a) or pd.isna(b) else cik(a) + cik(b) for a, b in zip(d['MDV+MODV TTM nominal'], d['YAGM TTM nominal'])]
d['KIRA nominal'] = [cik(v) for v in d['KIRA TTM nominal']]
BIL = [('CFO', 'CFO TTM', 'CFO TTM nominal', 'V7 CFO_TTM (Evo)'),
       ('CAPEX', 'CAPEX_STD (belge)', 'CAPEX nominal', 'V7 CAPEX_STD (Evo)'),
       ('KIRA', '|Kira| (belge)', 'KIRA nominal', 'V7 |Kira| (Evo)')]
out = []
for _, x in d.iterrows():
    kar = {}
    for n, c, cn, v in BIL:
        if pd.isna(x[c]) or pd.isna(x[v]): kar[n] = 'YOK'
        elif es(x[c], x[v]): kar[n] = 'AYNI'
        elif es(x[cn], x[v]): kar[n] = 'EVO_NOMINAL'
        elif abs(x[c] - x[v]) <= 0.03 * abs(x[v]) + 0.05: kar[n] = 'YAKIN'
        else: kar[n] = 'FARKLI'
    st = x['Satır statü']
    if st == 'BELGE_YOK': s = 'BELGE_YOK'
    elif all(k == 'AYNI' for k in kar.values()): s = 'KESİN_ONERI'
    elif all(k in ('AYNI', 'YAKIN') for k in kar.values()): s = 'KESİN_ONERI_YAKIN'
    elif st in ('TEYITLI', 'PDF_OKUNDU', 'IZAHNAME', 'XBRL_ESAS') and 'YOK' not in kar.values(): s = 'BELGE_DEGERI'
    else: s = 'ELLE'
    fark = '; '.join(f'{n} {k}' for n, k in kar.items() if k not in ('AYNI',))
    out.append(dict(Sonuç=s, **{f'{n} kıyas': k for n, k in kar.items()}, **{'Fark özeti': fark}))
R = pd.concat([d[['Kod', 'Tip', 'Dönem', 'Satır statü']], pd.DataFrame(out, index=d.index),
               d[[c for c in d.columns if c not in ('Kod', 'Tip', 'Dönem', 'Satır statü')]]], axis=1)
R.to_csv('kosullu_sonuc.csv', index=False)
print(R['Sonuç'].value_counts().to_dict())
for n, *_ in BIL: print(n, R[f'{n} kıyas'].value_counts().to_dict())
