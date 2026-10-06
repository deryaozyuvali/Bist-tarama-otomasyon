"""P/FCF + getiriler (GEM v6.2: piyasa değeri tarihi ve finansal baz tarihi yazılır, P/FCF düzeltilmez).
Girdi: FCF_MASTER.xlsx (FCF, ANA), girdi/fiyat/fiyat.csv (Evo hisse_senetleri + 01.10.2025 ve 21.09.2026 kapanışları),
girdi/fiyat/sicrama.csv (fiyat serisinde düzeltilmemiş sermaye hareketi sıçramaları; günlük ±%10 limit dışı).
Çıktı: PFCF_GETIRI.xlsx"""
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter as L
from openpyxl.formatting.rule import CellIsRule
from openpyxl.comments import Comment

F_ = Font(name='Arial', size=10); FH = Font(name='Arial', size=10, bold=True, color='FFFFFF'); FB = Font(name='Arial', size=10, bold=True)
FBL = Font(name='Arial', size=10, color='0000FF'); HDR = PatternFill('solid', fgColor='1F3864')
FCF = pd.read_excel('FCF_MASTER.xlsx', sheet_name='FCF', keep_default_na=False, na_values=[''])
FCF = FCF[FCF['Dönem'] == '2026/06'].set_index('Kod')
ANA = pd.read_excel('FCF_MASTER.xlsx', sheet_name='ANA', header=3, keep_default_na=False, na_values=['']).set_index('Kod')
P = pd.read_csv('girdi/fiyat/fiyat.csv', keep_default_na=False, na_values=[''])
G = pd.read_csv('girdi/fiyat/sicrama.csv', keep_default_na=False, na_values=[''])
for c in ('onceki', 'acilis', 'kapanis'): G[c] = G[c].astype(float)
G['t'] = pd.to_datetime(G['zaman_utc']); G['f'] = G['onceki'] / G['acilis']   # açılış ≈ düzeltilmiş baz fiyat
T1, T2 = pd.Timestamp('2025-10-01 21:00', tz='UTC'), pd.Timestamp('2026-09-21 21:00', tz='UTC')

P = P[P['son_fiyat'].notna() & P['piyasa_degeri'].notna()]
P = P[pd.to_datetime(P['son_fiyat_zaman_utc']) >= pd.Timestamp('2026-10-01', tz='UTC')]  # işlem görmeyenler çıkar
rows = []
for _, r in P.sort_values('kod').iterrows():
    k = r['kod']; g = G[G.kod == k]
    f1 = g[g.t >= T1].f.prod(); f2 = g[g.t >= T2].f.prod()
    ev1 = '; '.join(f"{t:%d.%m.%Y} ×{f:.3f}" for t, f in zip(g[g.t >= T1].t, g[g.t >= T1].f))
    x = FCF.loc[k] if k in FCF.index else None
    a = ANA.loc[k] if k in ANA.index else None
    rows.append(dict(Kod=k, Unvan=None if a is None else a['Ünvan'], Kapsam=None if a is None else a['Kapsam'],
                     Tip=None if x is None else x['Tip'], Sektor=None if x is None else x['Sektör'],
                     Fiyat=float(r['son_fiyat']), Zaman=pd.to_datetime(r['son_fiyat_zaman_utc']).tz_convert('Europe/Istanbul').strftime('%d.%m.%Y %H:%M'),
                     PD=float(r['piyasa_degeri']) / 1e6,
                     FCF=None if x is None or pd.isna(x['FCF · TTM (mn TL)']) else float(x['FCF · TTM (mn TL)']),
                     Tur=None if x is None else x['FCF türü'], Statu=None if x is None else x['Statü'], Kaynak=None if x is None else x['Kaynak'],
                     K1=None if pd.isna(r['k1']) else float(r['k1']), F1=f1, K2=None if pd.isna(r['k2']) else float(r['k2']), F2=f2,
                     Olay=ev1))
D = pd.DataFrame(rows)
wb = Workbook(); ws = wb.active; ws.title = 'P_FCF'
ws['A1'] = 'P/FCF ve getiriler — BIST (FCF: FCF_MASTER, GEM v6.2)'; ws['A1'].font = Font(name='Arial', size=14, bold=True)
ws['A2'] = ('Piyasa değeri ve fiyat: Evo, 06.10.2026 ~16:40 (seans içi). FCF: TTM 2026/06, mn TL, Haziran 2026 satın alma gücü. '
            'P/FCF düzeltilmez; FCF ≤ 0 ise "anlamsız". Getiriler fiyat getirisi (temettü hariç), bölünme/bedelsiz sıçramaları düzeltildi.')
ws['A2'].font = Font(name='Arial', size=9, italic=True)
C = ['Kod', 'Ünvan', 'Kapsam', 'Tip', 'Sektör', 'Güncel fiyat (TL)', 'Fiyat zamanı', 'Piyasa değeri (mn TL)', 'FCF TTM 2026/06 (mn TL)',
     'FCF türü', 'FCF statü', 'FCF kaynağı', 'P/FCF', 'P/FCF notu', 'Getiri 01.10.2025→bugün', 'Getiri son 15 gün (21.09.2026→bugün)',
     'Kapanış 01.10.2025 (TL)', 'Düzeltme katsayısı (01.10.2025→)', 'Kapanış 21.09.2026 (TL)', 'Düzeltme katsayısı (21.09.2026→)',
     'Sermaye hareketi sıçramaları (tarih ×katsayı)']
for j, c in enumerate(C, 1):
    x = ws.cell(4, j, c); x.font = FH; x.fill = HDR; x.alignment = Alignment(wrap_text=True, vertical='center')
for i, r in enumerate(D.itertuples(), 5):
    v = [r.Kod, r.Unvan, r.Kapsam, r.Tip, r.Sektor, r.Fiyat, r.Zaman, r.PD, r.FCF, r.Tur, r.Statu, r.Kaynak, None, None, None, None,
         r.K1, r.F1, r.K2, r.F2, r.Olay or None]
    for j, x in enumerate(v, 1):
        c = ws.cell(i, j, None if (isinstance(x, float) and pd.isna(x)) else x); c.font = FBL if j in (6, 8, 9, 17, 18, 19, 20) else F_
    ws.cell(i, 13, f'=IF(OR(H{i}="",I{i}=""),"",IF(I{i}>0,H{i}/I{i},""))')
    ws.cell(i, 14, f'=IF(I{i}="",IF(K{i}="NULL","FCF yok (NULL)","FCF kapsamı dışı"),IF(I{i}<=0,"anlamsız (FCF ≤ 0)",'
                   f'IF(OR(K{i}="KOŞULLU"),"FCF KOŞULLU — yorum yapılmaz","")))')
    ws.cell(i, 15, f'=IF(Q{i}="","",F{i}*R{i}/Q{i}-1)'); ws.cell(i, 16, f'=IF(S{i}="","",F{i}*T{i}/S{i}-1)')
    for j, fm in ((6, '#,##0.00'), (8, '#,##0'), (9, '#,##0.0;[Red]-#,##0.0'), (13, '0.0x'), (15, '0.0%;[Red]-0.0%'), (16, '0.0%;[Red]-0.0%'),
                  (17, '#,##0.00'), (18, '0.0000'), (19, '#,##0.00'), (20, '0.0000')):
        ws.cell(i, j).number_format = fm
    for j in (13, 14, 15, 16): ws.cell(i, j).font = F_
n = len(D) + 4
ws.freeze_panes = 'C5'; ws.auto_filter.ref = f'A4:{L(len(C))}{n}'
for j, w in enumerate([8, 34, 12, 10, 22, 11, 15, 14, 14, 10, 11, 20, 9, 28, 13, 15, 12, 12, 12, 12, 40], 1): ws.column_dimensions[L(j)].width = w
ws.row_dimensions[4].height = 45
ws.cell(4, 13).comment = Comment('P/FCF = Piyasa değeri / FCF TTM. Piyasa değeri bugünün, FCF Haziran 2026 satın alma gücünde (GEM v6.2: iki tarih yazılır, oran düzeltilmez).', 'GEM v6.2')
ws.cell(4, 18).comment = Comment('Evo fiyat serisinde son dönem bölünme/bedelsiz/temettü olayları düzeltilmemiş. Günlük ±%10 limit dışı sıçramalarda katsayı = önceki kapanış / olay günü açılış (yaklaşık). Getiri = Fiyat × katsayı / eski kapanış − 1.', 'hesap')
ws.conditional_formatting.add(f'M5:M{n}', CellIsRule(operator='between', formula=['0.0001', '10'], fill=PatternFill('solid', fgColor='C6EFCE')))
wo = wb.create_sheet('OKUBENI')
for i, (a, b) in enumerate([
    ('Fiyat / piyasa değeri', 'Evo hisse_senetleri.son_fiyat ve piyasa_degeri, 06.10.2026 seans içi (~16:40 TSİ). Seans kapanışı değil.'),
    ('FCF', 'FCF_MASTER.xlsx, 2026/06 TTM FCF (ana tanım: STD ya da HLD). Statü ve kaynak yanında. KOŞULLU satırlarda P/FCF gösterilir ama yorum yapılmamalı.'),
    ('P/FCF', 'Piyasa değeri / FCF TTM. FCF ≤ 0 → anlamsız. GEM v6.2: piyasa değeri tarihi (06.10.2026) ile finansal baz tarihi (30.06.2026) farklı; '
              'aradaki enflasyon farkı oranı yükseltir, oran düzeltilmedi. Evo\'da TÜFE serisi bulunmadığından fark yüzdesi verilemedi.'),
    ('Getiri 01.10.2025', '01.10.2025 kapanışından bugünkü fiyata fiyat getirisi (temettü hariç).'),
    ('Getiri son 15 gün', '15 takvim günü: 21.09.2026 kapanışından bugünkü fiyata.'),
    ('Düzeltme', 'Evo günlük fiyat serisinde 2026 Mart sonrası bazı bölünme/bedelsiz olayları düzeltilmemiş (45 olay; ör. A1YEN, BIMAS, KORDS). '
                 'Günlük ±%10 limitin dışındaki sıçramalar sermaye hareketi sayıldı; katsayı = önceki kapanış / olay günü açılışı. '
                 'Açılış baz fiyata çok yakın olduğu için hata genelde birkaç puandır; bu satırlar "Sermaye hareketi" sütununda listeli. '
                 'Daha küçük olaylar (±%15 içinde kalan bedelsiz/temettü) yakalanmamış olabilir.'),
    ('Kapsam', 'İşlem gören tüm hisseler. FCF yalnız FCF çalışmasının kapsamındaki (finansal olmayan) şirketlerde var.'),
], 1):
    wo.cell(i, 1, a).font = FB; x = wo.cell(i, 2, b); x.font = F_; x.alignment = Alignment(wrap_text=True)
wo.column_dimensions['A'].width = 20; wo.column_dimensions['B'].width = 130
wb.save('PFCF_GETIRI.xlsx'); print(len(D), 'hisse;', D.FCF.notna().sum(), 'FCF; düzeltilen', (D.F1 != 1).sum())
