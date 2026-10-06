"""Nihai FCF tablosu: V7 (Evo) + belge sonuçları (NULL doldurma, KOŞULLU teyit/düzeltme) tek tabloda.
Girdi: ../girdi/FCF_TTM_2025-03_2026-06_v7_nihai.xlsx, null_ttm.csv, kosullu_sonuc.csv, teslim_kosullu.ACIKLAMA
Çıktı: ../FCF_TTM_nihai_belgeli.xlsx
Tutarlar mn TL, Haziran 2026 satın alma gücü (V7/Evo esası; belge tutarları TMS 29 katsayısıyla aynı baza çevrildi)."""
import re
import pandas as pd

V7 = '../girdi/FCF_TTM_2025-03_2026-06_v7_nihai.xlsx'
ESKI_KOD = {'KOZAL': 'TRALT', 'KOZAA': 'TRMET', 'IPEKE': 'TRENJ', 'MARKA': 'USHOL', 'SNKRN': None}
DONEMLER = ['2025/03', '2025/06', '2025/09', '2025/12', '2026/03', '2026/06']

import ast
_m = ast.parse(open('teslim_kosullu.py').read())
ACIKLAMA = next(ast.literal_eval(n.value) for n in _m.body
                if isinstance(n, ast.Assign) and getattr(n.targets[0], 'id', '') == 'ACIKLAMA')


def sayi(x):
    if x is None or x == '' or (isinstance(x, float) and pd.isna(x)):
        return None
    try:
        return float(x)
    except ValueError:
        return None  # 'VERİ YETERSİZ' vb.


v = pd.read_excel(V7, sheet_name='FCF_TTM')
nul = pd.read_csv('null_ttm.csv', keep_default_na=False).set_index(['Kod', 'Dönem'])
kos = pd.read_csv('kosullu_sonuc.csv', keep_default_na=False).set_index(['Kod', 'Dönem'])
import os
SIS = set()
if os.path.exists('sistem_ttm.csv'):
    _s = pd.read_csv('sistem_ttm.csv', keep_default_na=False); SIS = set(zip(_s.Kod, _s['Dönem']))
_k6 = [pd.read_csv(f, keep_default_na=False) for f in ('k6_ttm.csv', 'sistem_ttm.csv') if os.path.exists(f)]
k6 = (pd.concat(_k6).drop_duplicates(['Kod', 'Dönem']).set_index(['Kod', 'Dönem']) if _k6
      else pd.DataFrame(columns=['Kod', 'Dönem']).set_index(['Kod', 'Dönem']))
KALEMLER = ['CFO', 'MDV+MODV', 'YAGM', 'KIRA', 'TEMETTU']


def belge_degerleri(r):
    tur = r['V7 FCF türü'] or 'FCF_STD'
    std, hld = sayi(r['FCF_STD (belge)']), sayi(r['FCF_HLD (belge)'])
    fcf = hld if tur == 'FCF_HLD' else std
    tem = sayi(r['TEMETTU TTM']) if 'TEMETTU TTM' in r else None
    cfo, capex, kira = sayi(r['CFO TTM']), sayi(r['CAPEX_STD (belge)']), sayi(r['|Kira| (belge)'])
    if std is None and None not in (cfo, capex, kira): std = round(cfo - capex - kira, 3)
    if tur == 'FCF_HLD' and hld is None and std is not None and tem is not None: hld = round(std + max(tem, 0), 3)
    fcf = hld if tur == 'FCF_HLD' else std
    return dict(cfo=sayi(r['CFO TTM']), capex=sayi(r['CAPEX_STD (belge)']), kira=sayi(r['|Kira| (belge)']),
                tem=tem, std=std, hld=hld, fcf=fcf, tur=tur)


def kanit(r):
    from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
    return ILLEGAL_CHARACTERS_RE.sub('', ' ‖‖ '.join(f'{k}: {r[k + " kanıt"]}' for k in KALEMLER if (k + ' kanıt') in r and r[k + ' kanıt']))


satirlar, kanitlar, cikan = [], [], []
for _, r in v.iterrows():
    kod, don = r['Kod'], r['Dönem']
    v7_fcf = sayi(r['FCF ana · TTM · tanım=FCF türü · statü=FCF statü (mn TL)'])
    v7_st = r['FCF statü'] if isinstance(r['FCF statü'], str) else 'NULL'
    tur = r['FCF türü'] if isinstance(r['FCF türü'], str) else 'FCF_STD'
    o = dict(Kod=kod, Tip=r['Tip'], Sektör=r['Sektör'], Dönem=don, PD=sayi(r['Piyasa değeri (mn TL)']),
             cfo=sayi(r['CFO_TTM']), capex=sayi(r['CAPEX_STD']), kira=sayi(r['|Kira anapara|']),
             tem=sayi(r['Alınan temettü (CFO dışı)']), std=sayi(r['FCF_STD (①) · TTM (mn TL)']),
             hld=sayi(r['FCF_HLD (②) · TTM (mn TL)']) if tur == 'FCF_HLD' else None,
             fcf=v7_fcf, tur=tur, statu=v7_st, kaynak='EVO', aciklama='', v7_fcf=v7_fcf, v7_st=v7_st)
    k9 = isinstance(r['KOŞULLU nedeni'], str) and 'Kontrol 9' in r['KOŞULLU nedeni']

    if kod in ESKI_KOD:
        o['aciklama'] = f'Kod değişti → {ESKI_KOD[kod]}' if ESKI_KOD[kod] else 'Kod hiçbir kaynakta yok'
        cikan.append(o)
        continue

    if (kod, don) in kos.index:
        b = kos.loc[(kod, don)]
        sonuc = b['Sonuç']
        if sonuc in ('KESİN_ONERI', 'KESİN_ONERI_YAKIN', 'BELGE_DEGERI'):
            d = belge_degerleri(b)
            karma_k = False
            if d['fcf'] is None and tur == 'FCF_HLD' and d['std'] is not None and o['tem'] is not None:
                d['hld'] = d['std'] + max(o['tem'], 0); d['fcf'] = d['hld']; karma_k = True  # temettü belgede yok → Evo
            if d['fcf'] is not None:
                o.update({x: d[x] for x in ('cfo', 'capex', 'kira', 'std', 'hld', 'fcf')})
                if d['tem'] is not None:
                    o['tem'] = d['tem']
            o['kaynak'] = 'EVO (belgeyle teyitli)' if sonuc == 'KESİN_ONERI' else 'BELGE'
            if karma_k or (tur == 'FCF_HLD' and d['tem'] is None and o['tem'] is not None and sonuc != 'KESİN_ONERI'):
                o['kaynak'] = 'KARMA (temettü: EVO; diğerleri: BELGE)'
            if k9:
                o['statu'] = 'KOŞULLU'
                o['aciklama'] = (('Evo rakamı belgeyle uyuşmadı, belge rakamı yazıldı (' + b['Fark özeti'] + '). '
                                  if sonuc == 'BELGE_DEGERI' else 'Bileşenler belgeyle doğrulandı. ') +
                                 'KOŞULLU nedeni: Kontrol 9 artığı (yatırım bölümü "Diğer") dipnotla sınıflandırılmadı')
            else:
                o['statu'] = 'KESİN'
                o['aciklama'] = {'KESİN_ONERI': 'Belge V7 rakamını teyit etti',
                                 'KESİN_ONERI_YAKIN': 'Belge V7 ile yakın (yuvarlama/küçük fark); belge rakamı',
                                 'BELGE_DEGERI': 'Evo rakamı belgeyle uyuşmadı; belge rakamı: ' + b['Fark özeti']}[sonuc]
            kanitlar.append(dict(Kod=kod, Dönem=don, Grup='KOŞULLU', Sonuç=sonuc, Kanıt=kanit(b)))
        elif sonuc == 'ELLE':
            o['statu'] = 'KOŞULLU'
            o['aciklama'] = 'Belge çözemedi: ' + ACIKLAMA.get((kod, don), ACIKLAMA.get(kod, 'elle inceleme gerekli'))
            d = belge_degerleri(b)
            o['belge_fcf'] = d['fcf']
            kanitlar.append(dict(Kod=kod, Dönem=don, Grup='KOŞULLU', Sonuç=sonuc, Kanıt=kanit(b)))
        else:  # BELGE_YOK
            o['statu'] = 'KOŞULLU'
            o['aciklama'] = 'Seri tutarsızlığı (K13) var, rapor bulunamadı' if not k9 else r['KOŞULLU nedeni']

    elif v7_st == 'NULL' and (kod, don) in nul.index:
        b = nul.loc[(kod, don)]
        d = belge_degerleri(b)
        karma_k = False
        if d['fcf'] is None and tur == 'FCF_HLD' and d['std'] is not None and o['tem'] is not None:
            d['hld'] = d['std'] + max(o['tem'], 0); d['fcf'] = d['hld']; karma_k = True
        if d['fcf'] is not None:
            o.update({x: d[x] for x in ('cfo', 'capex', 'kira', 'std', 'hld', 'fcf')})
            if d['tem'] is not None:
                o['tem'] = d['tem']
            o['statu'] = 'KESİN'
            o['kaynak'] = 'BELGE (izahname)' if b['Satır statü'] == 'IZAHNAME' else 'BELGE'
            if karma_k or (tur == 'FCF_HLD' and d['tem'] is None and o['tem'] is not None):
                o['kaynak'] = 'KARMA (temettü: EVO; diğerleri: BELGE)'
            o['aciklama'] = 'V7\'de NULL idi; belgeden dolduruldu (' + b['Satır statü'] + ')'
        else:
            o['statu'] = 'NULL'
            o['aciklama'] = ('Belge bulunamadı' if b['Satır statü'] == 'BELGE_YOK'
                             else 'Bileşen okunamadı/elle gerekli (' + b['Satır statü'] + ')')
            o['aciklama'] += '; V7 nedeni: ' + (r['NULL nedeni'] if isinstance(r['NULL nedeni'], str) else '')
        kanitlar.append(dict(Kod=kod, Dönem=don, Grup='NULL', Sonuç=b['Satır statü'], Kanıt=kanit(b)))
    elif (kod, don) in k6.index:  # GEM v6.2: Kontrol 6 işaret anomalisi / Kontrol 7 ihmal eşiği / 0/4 tablo yok
        b = k6.loc[(kod, don)]
        d = belge_degerleri(b)
        neden = ('Sistematik Evo hatası kontrolü (şirketin başka bir döneminde Evo belgeyle uyuşmadı)' if (kod, don) in SIS else
                 'K6: ' + r['K6 dışlanan satır'] if isinstance(r['K6 dışlanan satır'], str) else
                 'K7: ' + r['K7 notu'] if isinstance(r['K7 notu'], str) and 'ihmal' in r['K7 notu'] else 'K7: capex 0/4, tablo Evo\'da kayıtlı değil')
        if d['fcf'] is None and tur == 'FCF_HLD' and d['std'] is not None and o['tem'] is not None:
            d['hld'] = d['std'] + o['tem']; d['fcf'] = d['hld']; karma = True
        else:
            karma = False
        kanitlar.append(dict(Kod=kod, Dönem=don, Grup='SİSTEM' if (kod, don) in SIS else 'K6/K7', Sonuç=b['Satır statü'], Kanıt=kanit(b)))
        TAMAM = ('TEYITLI', 'PDF_OKUNDU', 'IZAHNAME', 'XBRL_ESAS')
        kab = b['Satır statü'] in TAMAM
        # CFO PDF'te özdeşlikle tek satıra bağlanamadı ama XBRL CFO'su Evo ile aynıysa CFO teyitli sayılır (iki bağımsız kaynak)
        if not kab and all(b[k + ' statü'] in TAMAM for k in ('MDV+MODV', 'YAGM', 'KIRA')) and d['cfo'] is not None \
                and o['cfo'] is not None and abs(d['cfo'] - o['cfo']) <= max(0.005 * abs(o['cfo']), 0.5):
            kab = True; neden += ' · CFO: PDF satırı özdeşlikle seçilemedi, XBRL CFO = Evo CFO'
        if not kab:
            d['fcf'] = None; karma = False  # belge okuması elle karar bekliyor → çözülmemiş say
        if d['fcf'] is not None:
            ayni = v7_fcf is not None and abs(d['fcf'] - v7_fcf) <= max(0.005 * abs(v7_fcf), 0.5)
            o.update({x: d[x] for x in ('cfo', 'capex', 'kira', 'std', 'hld', 'fcf')})
            if d['tem'] is not None: o['tem'] = d['tem']
            o['kaynak'] = 'KARMA (temettü: EVO; diğerleri: BELGE)' if karma else 'EVO (belgeyle teyitli)' if ayni else 'BELGE'
            o['statu'] = 'KESİN' if v7_st in ('KESİN', 'TÜRETİLMİŞ') and not k9 else v7_st
            o['aciklama'] = (neden + (' → belge V7 rakamını teyit etti' if ayni else ' → Evo rakamı belgeyle uyuşmadı; belge rakamı (V7 '
                             + (f'{v7_fcf:,.1f}' if v7_fcf is not None else '—') + ')'))
            o['k6'] = 'COZULDU'
        else:
            m_ = re.search(r'TTM \+([\d.]+)', neden)
            tutar = float(m_.group(1)) if m_ else None
            if (kod, don) in SIS:
                o['aciklama'] = neden + '; belge bulunamadı/okunamadı (' + b['Satır statü'] + ') → Evo rakamı, kontrol edilemedi'
                o['k6'] = 'SIS_YOK'
            elif neden.startswith('K6') and tutar is not None and v7_fcf is not None:
                maddi = tutar > 0.10 * abs(v7_fcf) or tutar >= abs(v7_fcf)
                o['statu'] = 'KOŞULLU' if maddi else v7_st
                o['aciklama'] = neden + ('; belge bulunamadı/okunamadı → maddi işaret anomalisi (> |FCF|×%10) → KOŞULLU' if maddi
                                         else '; belge bulunamadı/okunamadı; anomali maddi değil → statü korunur, not')
                o['k6'] = 'MADDI' if maddi else 'MADDI_DEGIL'
            else:  # K7 ihmal / 0/4 tablo yok: belge yoksa NULL
                o.update(cfo=o['cfo'], capex=None, std=None, hld=None, fcf=None)
                o['statu'] = 'NULL'
                o['aciklama'] = neden + '; belge eksik çeyrekleri doğrulayamadı → NULL (GEM v6.2 Kontrol 7)'
                o['k6'] = 'NULL'
    else:
        if v7_st == 'KOŞULLU':
            o['aciklama'] = r['KOŞULLU nedeni'] if isinstance(r['KOŞULLU nedeni'], str) else ''
    satirlar.append(o)

A = pd.DataFrame(satirlar)
A['P/FCF'] = [round(p / f, 2) if p and f and f > 0 else None for p, f in zip(A.PD, A.fcf)]
A['Değişti'] = [('YENİ (NULL→rakam)' if pd.isna(a) and not pd.isna(b) else
                 'EVET' if not pd.isna(a) and not pd.isna(b) and abs(a - b) > max(0.005 * abs(a), 0.05) else '')
                for a, b in zip(A.v7_fcf, A.fcf)]
KOLON = {'Kod': 'Kod', 'Tip': 'Tip', 'Sektör': 'Sektör', 'Dönem': 'Dönem',
         'fcf': 'FCF · TTM (mn TL)', 'tur': 'FCF türü', 'statu': 'Statü', 'kaynak': 'Kaynak',
         'cfo': 'CFO_TTM', 'capex': 'CAPEX_STD', 'kira': '|Kira anapara|', 'tem': 'Alınan temettü (CFO dışı)',
         'std': 'FCF_STD (①)', 'hld': 'FCF_HLD (②)', 'PD': 'Piyasa değeri (mn TL)', 'P/FCF': 'P/FCF',
         'aciklama': 'Açıklama', 'v7_fcf': 'V7 FCF', 'v7_st': 'V7 statü', 'Değişti': 'V7\'ye göre değişti',
         'belge_fcf': 'Belge FCF (çözülmemiş)'}
A = A[[c for c in KOLON if c in A]].rename(columns=KOLON)

# Seri görünümü: şirket × dönem
S = A.pivot(index='Kod', columns='Dönem', values='FCF · TTM (mn TL)').reindex(columns=DONEMLER)
St = A.pivot(index='Kod', columns='Dönem', values='Statü').reindex(columns=DONEMLER)
St.columns = [c + ' statü' for c in St.columns]
seri = pd.concat([S, St], axis=1).reset_index()

ozet = A.groupby('Statü').size().rename('Satır').reset_index()
kay = A.groupby(['Statü', 'Kaynak']).size().rename('Satır').reset_index()
deg = A["V7'ye göre değişti"].replace('', 'aynı').value_counts().rename_axis('V7 karşılaştırma').rename('Satır').reset_index()

OKUBENI = [
    ('Ne', 'BIST FCF TTM, 2025/03–2026/06, 508 şirket. V7 (Evo) tablosu + iki günlük belge çalışması tek tabloda.'),
    ('Birim', 'mn TL, Haziran 2026 satın alma gücü (Evo esası). Belgeden okunan rakamlar TMS 29 katsayısıyla aynı baza çevrildi.'),
    ('FCF tanımı', 'GEM FCF v2.1: FCF_STD = CFO − |MDV+MODV alımı| − |YAGM alımı| − |kira anapara|; holdingde FCF_HLD = FCF_STD + '
                   'yatırım bölümündeki alınan temettü. "FCF · TTM" sütunu FCF türüne göre ana rakamdır.'),
    ('Statü', 'KESİN: kullanılabilir · TÜRETİLMİŞ: V7 köprü yöntemiyle üretildi, kullanılabilir · KOŞULLU: rakam var ama FCF\'e '
              'dayalı yorum yapılmamalı (nedeni Açıklama\'da) · NULL: rakam yok.'),
    ('Kaynak', 'EVO: V7 rakamı, belgeyle kontrol edilmedi (seri tutarlı, şüphe yok) · EVO (belgeyle teyitli): belge aynı rakamı '
               'verdi · BELGE: rakam şirket raporundan (KAP / şirket sitesi / Evo belge havuzu); kanıtı BELGE_KANIT sayfasında.'),
    ('Değişenler', 'V7\'ye göre değişti = EVET: Evo rakamı belgeyle uyuşmadı, belge rakamı yazıldı. YENİ: V7\'de NULL idi.'),
    ('P/FCF', 'Dönem sonu piyasa değeri ÷ TTM FCF; FCF ≤ 0 ise boş. Statüsü KOŞULLU/NULL olan satırda kullanmayın.'),
    ('Seri sorguları', 'SERI sayfası şirket × dönem; "son 3 dönem pozitif" gibi sorgular buradan (statü sütunlarıyla birlikte).'),
    ('Çıkarılanlar', 'Kodu değişen/geçersiz 5 kod (30 satır) KOD_DEGISTI sayfasında; yeni kodları ana tabloda zaten var.'),
    ('Kontrol 9', 'V7\'de yatırım bölümü "Diğer" artığı nedeniyle KOŞULLU olan satırlar, bileşenleri belgeyle doğrulansa da '
                  'KOŞULLU kalır (artığın ne olduğunu yalnız dipnot söyler).'),
    ('Kapsam dışı', 'Çeyreklik (tek çeyrek) FCF bu dosyada yok; yalnız TTM.'),
]

with pd.ExcelWriter('../FCF_TTM_nihai_belgeli.xlsx') as w:
    pd.DataFrame(OKUBENI, columns=['Konu', 'Açıklama']).to_excel(w, sheet_name='OKUBENI', index=False)
    A.to_excel(w, sheet_name='FCF_TTM', index=False)
    seri.to_excel(w, sheet_name='SERI', index=False)
    pd.concat([ozet, pd.DataFrame([{}]), kay, pd.DataFrame([{}]), deg]).to_excel(w, sheet_name='OZET', index=False)
    pd.DataFrame(kanitlar).to_excel(w, sheet_name='BELGE_KANIT', index=False)
    pd.DataFrame(cikan).rename(columns=KOLON).to_excel(w, sheet_name='KOD_DEGISTI', index=False)
print(ozet.to_string(index=False)); print(kay.to_string(index=False)); print(deg.to_string(index=False))
