"""NULL satırların belge okuma sonuçlarını tek Excel'de toplar → FCF_K13/belge/NULL_belge_okuma.xlsx"""
import pandas as pd

D = pd.read_csv('null_ttm.csv')
K = pd.read_csv('rapor_kalemleri.csv')
V = pd.read_csv('dogrulama_kalemleri.csv')

# elle okunmuş kayıtlar (oos_test/OOS_SONUCLAR.json, YEDEK_SONUCLAR.json) ile program okuması — nominal, rapor TL'si
EL = [  # kod, yıl, ay, kalem, sütun, elle okunan (mn TL), kaynak
    ('EPLAS', 2025, 3, 'MDV+MODV', 'cari', -2.534, 'OOS EPLAS'), ('EPLAS', 2025, 3, 'MDV+MODV', 'onceki', -103.923, 'OOS EPLAS'),
    ('OZRDN', 2025, 6, 'KIRA', 'cari', -0.367, 'OOS OZRDN'), ('OZRDN', 2025, 6, 'KIRA', 'onceki', -7.988, 'OOS OZRDN'),
    ('OZRDN', 2024, 12, 'KIRA', 'cari', -1.474, 'OOS OZRDN'),
    ('TTRAK', 2025, 6, 'KIRA', 'cari', -28.967, 'OOS TTRAK'), ('TTRAK', 2025, 6, 'KIRA', 'onceki', -121.049, 'OOS TTRAK'),
    ('TTRAK', 2024, 12, 'KIRA', 'cari', -52.520, 'OOS TTRAK'),
    ('OYLUM', 2025, 3, 'MDV+MODV', 'cari', -0.702, 'OOS OYLUM (0.472+0.230)'),
    ('OYLUM', 2025, 3, 'MDV+MODV', 'onceki', -13.417, 'OOS OYLUM (13.362+0.055)'),
    ('OYLUM', 2024, 12, 'MDV+MODV', 'cari', -41.774, 'OOS OYLUM (41.327+0.447)'),
    ('IZFAS', 2026, 6, 'MDV+MODV', 'cari', -18.091, 'OOS IZFAS'), ('IZFAS', 2026, 6, 'MDV+MODV', 'onceki', -47.280, 'OOS IZFAS'),
    ('IZFAS', 2025, 9, 'MDV+MODV', 'cari', -36.424, 'OOS IZFAS'), ('IZFAS', 2025, 12, 'MDV+MODV', 'cari', -11.041, 'OOS IZFAS'),
    ('ASUZU', 2025, 3, 'KIRA', 'cari', -138.117, 'OOS ASUZU'), ('ASUZU', 2026, 3, 'KIRA', 'onceki', -180.748, 'OOS ASUZU'),
    ('ASUZU', 2025, 6, 'KIRA', 'cari', -72.935, 'OOS ASUZU'), ('ASUZU', 2026, 3, 'KIRA', 'cari', -39.097, 'OOS ASUZU'),
    ('PNSUT', 2026, 3, 'KIRA', 'cari', 22.273, 'OOS PNSUT (giriş)'), ('PNSUT', 2026, 6, 'KIRA', 'cari', -5.204, 'OOS PNSUT'),
    ('PNSUT', 2026, 6, 'KIRA', 'onceki', -54.826, 'OOS PNSUT'), ('PNSUT', 2026, 3, 'KIRA', 'onceki', -8.707, 'OOS PNSUT'),
    ('CATES', 2025, 6, 'MDV+MODV', 'cari', -18.652, 'OOS CATES'),
    ('CATES', 2025, 6, 'MDV+MODV', 'onceki', -55.133, 'OOS CATES (54.789+0.344)'),
    ('DENGE', 2026, 3, 'MDV+MODV', 'cari', -0.055, 'OOS DENGE (alım; satış 50.288 ayrı)'),
    ('DENGE', 2026, 6, 'MDV+MODV', 'cari', -0.490, 'OOS DENGE'),
    ('MARBL', 2025, 3, 'KIRA', 'cari', -26.860, 'OOS MARBL'), ('MARBL', 2025, 12, 'KIRA', 'cari', -1.919, 'OOS MARBL'),
    ('TCKRC', 2025, 12, 'KIRA', 'cari', -0.541, 'OOS TCKRC'),
    ('FORTE', 2025, 12, 'MDV+MODV', 'cari', -249.0, 'OOS FORTE'), ('FORTE', 2026, 3, 'MDV+MODV', 'onceki', -72.5, 'OOS FORTE'),
    ('FORTE', 2026, 3, 'MDV+MODV', 'cari', -122.8, 'OOS FORTE'),
    ('GUNDG', 2026, 6, 'MDV+MODV', 'cari', -25.17, 'OOS GUNDG'), ('GUNDG', 2026, 6, 'MDV+MODV', 'onceki', -71.93, 'OOS GUNDG'),
    ('GUNDG', 2025, 12, 'MDV+MODV', 'cari', -62.79, 'OOS GUNDG'),
    ('ENSRI', 2025, 9, 'MDV+MODV', 'cari', -3.64, 'OOS ENSRI'), ('ENSRI', 2025, 9, 'KIRA', 'cari', -3.68, 'OOS ENSRI'),
    ('SANEL', 2025, 6, 'MDV+MODV', 'cari', -31.97, 'OOS SANEL'), ('SANEL', 2025, 6, 'MDV+MODV', 'onceki', -0.134, 'OOS SANEL'),
    ('MEGMT', 2025, 9, 'MDV+MODV', 'cari', -180.0, 'OOS MEGMT'), ('MEGMT', 2025, 9, 'MDV+MODV', 'onceki', -191.9, 'OOS MEGMT'),
    ('ARMGD', 2025, 9, 'MDV+MODV', 'cari', -923.4, 'OOS ARMGD'), ('ARMGD', 2025, 9, 'MDV+MODV', 'onceki', -467.9, 'OOS ARMGD'),
    ('ARMGD', 2024, 12, 'MDV+MODV', 'cari', -494.8, 'OOS ARMGD'),
    ('YATAS', 2026, 3, 'MDV+MODV', 'cari', -217.4, 'OOS YATAS'), ('YATAS', 2026, 3, 'KIRA', 'cari', -169.0, 'OOS YATAS'),
    ('YATAS', 2026, 3, 'MDV+MODV', 'onceki', -538.1, 'OOS YATAS'), ('YATAS', 2026, 3, 'KIRA', 'onceki', -91.3, 'OOS YATAS'),
    ('YATAS', 2025, 12, 'MDV+MODV', 'cari', -2426.3, 'OOS YATAS'), ('YATAS', 2025, 12, 'KIRA', 'cari', -804.5, 'OOS YATAS'),
    ('BERA', 2026, 6, 'MDV+MODV', 'cari', None, 'OOS BERA (alım+satış tek net satır +195.5)'),
    ('EPLAS', 2024, 12, 'MDV+MODV', 'cari', -43.038, 'OOS EPLAS'),
]
H = pd.concat([K, V])
rows = []
for kod, y, m, kal, sut, el, kay in EL:
    r = H[(H.kod == kod) & (H.yil == y) & (H.ay == m) & (H.kalem == kal) & (H.sutun == sut)]
    p = r.iloc[0] if len(r) else None
    pv = None if p is None or pd.isna(p.deger_tl) else round(p.deger_tl / 1e6, 3)
    durum = None if p is None else p.durum
    if el is None:
        sonuc = 'DOĞRU (işaretlendi)' if durum not in ('TEYITLI', 'SIFIR') else 'YANLIŞ (sessiz)'
    elif durum in ('TEYITLI', 'SIFIR', 'PDF_OKUNDU'):
        sonuc = 'AYNI' if pv is not None and abs(pv - el) <= max(0.06, 0.0005 * abs(el)) else 'FARKLI (sessiz!)'
    else:
        sonuc = 'İŞARETLENDİ (elle)' if pv is None or abs(pv - el) > max(0.06, 0.0005 * abs(el)) else 'AYNI ama işaretli'
    rows.append(dict(Kod=kod, Rapor=f'{y}/{m:02d}', Kalem=kal, Sütun=sut, **{'Elle okunan (mn TL, nominal)': el},
                     **{'Program (mn TL, nominal)': pv}, **{'Program statü': durum}, Sonuç=sonuc, Kaynak=kay))
DG = pd.DataFrame(rows)

TMS = pd.DataFrame([('2024/12', 1.5414), ('2025/03', 1.4004), ('2025/06', 1.3211), ('2025/09', 1.2289),
                    ('2025/12', 1.1776), ('2026/03', 1.0701), ('2026/06', 1.0)], columns=['Rapor tarihi', 'F (→ Haz 2026 TL)'])

KAL = ['CFO', 'MDV+MODV', 'YAGM', 'KIRA']
elle = []
for _, r in D[D['Satır statü'] == 'ELLE'].iterrows():
    for k in KAL:
        if r[f'{k} statü'] == 'ELLE':
            elle.append(dict(Kod=r.Kod, Tip=r.Tip, Dönem=r['Dönem'], Kalem=k, Bileşenler=r[f'{k} bileşen'], Kanıt=r[f'{k} kanıt']))
EL_DF = pd.DataFrame(elle)
by = D[D['Satır statü'] == 'BELGE_YOK'][['Kod', 'Tip', 'Dönem', 'CFO kanıt']].rename(columns={'CFO kanıt': 'Neden'})
by['Neden'] = by['Neden'].str.replace(r'KAP \d+ \d{4}/\d\d \w+ · ', '', regex=True)

def kategori(n):
    if 'MALI_YIL' in n: return 'Hesap yılı takvim dışı'
    if 'KAP’ta yok' in n: return 'Rapor KAP’ta yok (halka arz öncesi / çeyrek yayımlamıyor / kod eşleşmedi)'
    if 'NAKIT_AKIS_YOK' in n: return 'KAP sayfasında XBRL nakit akış tablosu yok'
    return 'Diğer'
by['Kategori'] = by['Neden'].map(kategori)

st = D['Satır statü'].value_counts()
ozet = pd.DataFrame([
    ('NULL satır (V7)', len(D)),
    ('BELGE TEYİTLİ — tüm kalemler XBRL = imzalı PDF (etiket dahil)', int(st.get('TEYITLI', 0))),
    ('BELGE PDF OKUNDU — ≥1 kalem XBRL’de yok, PDF satırından okundu', int(st.get('PDF_OKUNDU', 0))),
    ('İZAHNAME — halka arz izahnamesinden (Evo ile tablo düzeyinde kontrollü)', int(st.get('IZAHNAME', 0))),
    ('ELLE BAKILACAK', int(st.get('ELLE', 0))),
    ('BELGE YOK', int(st.get('BELGE_YOK', 0))),
    ('FCF_STD hesaplanan (Standart, tüm bileşen var)', int(D['FCF_STD (belge)'].notna().sum())),
    ('CFO belge vs V7 Evo: kıyaslanabilir / |fark|<%0,5', ''),
    ('Elle okunmuş kayıtlarla kıyas: nokta sayısı', len(DG)),
    ('  → AYNI', int((DG['Sonuç'] == 'AYNI').sum())),
    ('  → işaretlendi (elle)', int(DG['Sonuç'].str.startswith('İŞARET').sum() + DG['Sonuç'].str.startswith('DOĞRU').sum())),
    ('  → FARKLI ama sessiz', int(DG['Sonuç'].str.contains('sessiz').sum())),
], columns=['Ölçü', 'Değer'])
x = D[(D['CFO statü'] == 'TEYITLI') & D['V7 CFO_TTM (Evo)'].notna()]
f = (x['CFO fark (belge−Evo)'].abs() / x['V7 CFO_TTM (Evo)'].abs().clip(lower=1))
ozet.loc[6, 'Değer'] = f'{len(x)} / {(f < 0.005).sum()}'
ozet = pd.concat([ozet, by.Kategori.value_counts().rename_axis('Ölçü').reset_index(name='Değer')
                  .assign(**{'Ölçü': lambda d: 'BELGE YOK: ' + d['Ölçü']})])

oku = pd.DataFrame([
    ('Ne', 'V7’de NULL kalan 734 satırın CFO / MDV+MODV / YAGM / kira TTM’leri şirketlerin KAP’a verdiği finansal rapor '
           'bildirimlerinden okundu. V7 dosyası ve hiçbir V7 FCF rakamı değiştirilmedi.'),
    ('Kaynak', 'KAP bildirimi (kap.org.tr/tr/Bildirim/<no>): XBRL nakit akış tablosu + aynı bildirimin imzalı PDF eki. '
               'Evo belge havuzunda bu şirketlerin raporlarının çoğu yoktu (NULL’ların ana nedeni); bu yüzden KAP’tan alındı.'),
    ('Teyit', 'Her XBRL tutarı PDF nakit akış sayfasında aranır; tutar bulunmalı VE bulunduğu satırın etiketi kaleme ait olmalı '
              '(ör. yatırım toplamı satırındaki aynı sayı teyit sayılmaz). XBRL’de standart elemanda olmayan kalem PDF satırından okunur '
              '(PDF_OKUNDU). Alım+satış tek net satır, kopya tutar, sütun/işaret belirsizliği → ELLE.'),
    ('Birim', 'XBRL tutarı KAP başlığındaki “Sunum Para Birimi” ile çarpılır (TL / 1.000 TL / 1.000.000 TL; 65 rapor bin TL).'),
    ('TTM', 'TTM = YTD_cari + FY_önceki − YTD_önceki (Aralık: FY). YTD_önceki cari raporun karşılaştırmalı sütunu (V7 köprüsüyle aynı).'),
    ('TMS 29', 'PDF rakamları TMS 29’a göre düzeltilmiştir ama RAPORUN KENDİ TARİHİNE göre (Ara24 raporu Ara24 TL’si). Evo/V7 '
               'her raporu şirketin son raporunun satın alma gücüne taşır. Belge değeri bir kez × F(rapor)/F(son rapor) çevrilir. '
               'Test: TMS29_BIMAS_TESTI — 21/21 kalemde Evo = PDF × F; TTM’de yalnız “1 kez çevrim” Evo’yu tutuyor (2 kez %50 şişirir). '
               'Varsayılan: şirket TMS 29 uygular; istisna yalnız hiçbir rapor başlığında “satın alma gücü esasına göre” yoksa VE '
               'Evo rakamı çevrilmemiş hâliyle örtüşüyorsa (A1YEN, ALCTL, BESTE, KOPOL, KORDS, NETAS, ODINE, SEKUR).'),
    ('FCF', 'FCF_STD = CFO − CAPEX_STD − |Kira|, CAPEX_STD = |MDV+MODV| + |YAGM|, pozitif TTM kalem 0 (K6) — KARAR’daki 2.262 '
            'FCF_STD satırının 2.261’inde birebir tutan V7 formülü. Holding (FCF_HLD) tanımı türetilemedi → yalnız bileşenler.'),
    ('Tutarlar', 'mn TL, Haz 2026 satın alma gücü (TMS 29 uygulayanlar), işaret belgedeki gibi (çıkış negatif).'),
    ('Yeniden üretim', 'belge/: kap_liste.py → kap_indir.py (indirilecek.txt) → cikar.py → ttm.py → teslim_belge.py'),
], columns=['Başlık', 'Açıklama'])

import re
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
def temiz(df):
    return df.apply(lambda c: c.map(lambda v: ILLEGAL_CHARACTERS_RE.sub(' ', v) if isinstance(v, str) else v))
D, EL_DF, by, DG, K = temiz(D), temiz(EL_DF), temiz(by), temiz(DG), temiz(K)

with pd.ExcelWriter('NULL_belge_okuma.xlsx') as w:
    oku.to_excel(w, sheet_name='OKUBENI', index=False)
    ozet.to_excel(w, sheet_name='OZET', index=False)
    on = ['Kod', 'Tip', 'Dönem', 'Satır statü', 'FCF_STD (belge)', 'CFO TTM', 'CAPEX_STD (belge)', '|Kira| (belge)',
          'K6 dışlanan (belge)', 'V7 CFO_TTM (Evo)', 'V7 CAPEX_STD (Evo)', 'V7 |Kira| (Evo)', 'CFO fark (belge−Evo)']
    D[on + [c for c in D.columns if c not in on]].to_excel(w, sheet_name='NULL_BELGE', index=False)
    EL_DF.to_excel(w, sheet_name='ELLE', index=False)
    by.to_excel(w, sheet_name='BELGE_YOK', index=False)
    DG.to_excel(w, sheet_name='DOGRULAMA', index=False)
    TMS.to_excel(w, sheet_name='TMS29', index=False)
    pd.read_csv('bimas_testi.csv').to_excel(w, sheet_name='TMS29_BIMAS_TESTI', index=False)
    pd.read_csv('TUPRS_testi.csv').to_excel(w, sheet_name='TMS29_TUPRS_TESTI', index=False)
    K.to_excel(w, sheet_name='RAPOR_KALEMLERI', index=False)
print(ozet.to_string(index=False))
print(DG['Sonuç'].value_counts().to_dict())
print(DG[~DG['Sonuç'].isin(['AYNI'])].to_string(index=False))
