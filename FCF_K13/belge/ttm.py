"""NULL satırlar için belge TTM'leri: TTM = YTD_cari + FY_önceki − YTD_önceki (Aralık dönemi: FY_cari).
YTD_önceki, cari raporun karşılaştırmalı sütunundan alınır (V7 köprüsüyle aynı tanım).
Girdi : null_satirlar.csv, rapor_kalemleri.csv  → Çıktı: null_ttm.csv
Kalem statüsü:
  TEYITLI   kullanılan her değer PDF'te bulundu ya da XBRL'de boş/0 ve PDF'te o kaleme ait satır yok
  ELLE      en az bir değer PDF'te bulunamadı / PDF metni yok (taranmış) / PDF'te XBRL dışı satır var
  BELGE_YOK gereken rapor KAP'ta yok ya da tabloda dönem sütunu yok
Tutarlar mn TL; işaret belgedeki gibi (çıkış negatif).
TMS 29: Evo (ve V7) TMS 29 uygulayan şirketlerde her raporu şirketin son raporunun satın alma gücüne taşır.
Belge değeri de aynı esasa çevrilir: değer × F(rapor tarihi) / F(şirketin son rapor tarihi).
F, Evo dönemsel CFO / belge CFO oranından ampirik bulundu (BIOEN, BUCIM, DESA, OZSUB, YEOTK, AFYON, PETKM;
dönem başına şirketler arası sapma < %0,01). TMS 29 uygulamayan raporlar (PDF'te 'satın alma gücü' yok) çevrilmez."""
import csv, collections, json
import pandas as pd

K = pd.read_csv('rapor_kalemleri.csv', dtype={'pdf_sayfa': str})
F = {(2024, 12): 1.5414, (2025, 3): 1.4004, (2025, 6): 1.3211, (2025, 9): 1.2289,
     (2025, 12): 1.1776, (2026, 3): 1.0701, (2026, 6): 1.0}
PER = {'3 Aylık': 3, '6 Aylık': 6, '9 Aylık': 9, 'Yıllık': 12}
son_rapor = {}
for x in json.load(open('kap_fr.json')):
    if x['subject'] != 'Finansal Rapor' or x['ruleType'] not in PER: continue
    t = (x['year'], PER[x['ruleType']])
    if t not in F: continue
    for s in (x['stockCodes'] or '').replace(' ', '').split(','):
        son_rapor[s] = max(son_rapor.get(s, t), t)
H = json.load(open('rapor_bildirim_haritasi.json'))
idx = collections.defaultdict(dict)
for r in K.itertuples():
    idx[(r.kod, int(r.yil), int(r.ay))].setdefault(r.kalem, {})[r.sutun] = r

def al(kod, y, m, kalem, sut):
    """→ (değer mn TL | None, statü, kanıt)"""
    if not H.get(f'{kod}|{y}|{m}'): return None, 'BELGE_YOK', f'{y}/{m:02d} raporu KAP’ta yok'
    rk = idx.get((kod, y, m))
    if rk is None: return None, 'BELGE_YOK', f'{y}/{m:02d} işlenmedi'
    if '*' in rk and kalem not in rk:
        r0 = next(iter(rk['*'].values()))
        return None, 'BELGE_YOK', f"{y}/{m:02d} {r0.durum} {'' if pd.isna(r0.not_) else r0.not_}"
    d = rk.get(kalem, {})
    r = d.get(sut)
    if r is None or r.durum == 'SUTUN_YOK': return None, 'BELGE_YOK', f'{y}/{m:02d} {sut} sütunu yok'
    v = None if pd.isna(r.deger_tl) else r.deger_tl / 1e6
    kanit = f'KAP {int(r.idx)} {y}/{m:02d} {sut}'
    if v is not None and r.tms29 is True:
        a = son_rapor.get(kod, (2026, 6))
        k = F[(y, m)] / F[a]
        v *= k
        kanit += f' · TMS29 ×{k:.4f} ({y}/{m:02d}→{a[0]}/{a[1]:02d})'
    if r.durum == 'TEYITLI': kanit += f' · PDF s.{r.pdf_sayfa} ({r.pdf_birim}): {r.pdf_satir}'
    if (kod, y, m, kalem) in tekrar:
        return v, 'ELLE', kanit + ' · aynı cari tutar şirketin başka bir dönem raporunda da var (kopya şüphesi)'
    if r.durum in ('TEYITLI', 'SIFIR'): return (v or 0.0), 'TEYITLI', kanit
    if r.durum == 'PDF_OKUNDU':
        return v, 'PDF_OKUNDU', kanit + f' · XBRL standart elemanında yok, PDF satırından okundu ({r.pdf_birim}): {r.pdf_satir}'
    if r.durum == 'PDF_EK_SATIR':
        return None, 'ELLE', kanit + f' · PDF satırı otomatik okunamadı ({r.not_}): {r.pdf_satir}'
    return v, 'ELLE', kanit + f" · {r.durum}{'' if pd.isna(r.not_) else ' ' + str(r.not_)}"

SIRA = {'TEYITLI': 0, 'PDF_OKUNDU': 1, 'ELLE': 2, 'BELGE_YOK': 3}

# aynı şirketin farklı rapor tarihlerinde birebir aynı sıfır dışı cari tutar: belge içi kopya şüphesi
tekrar = set()
c = K[(K.sutun == 'cari') & K.deger_tl.notna() & (K.deger_tl != 0)]
for (kod, kalem, v), g in c.groupby(['kod', 'kalem', 'deger_tl']):
    if g[['yil', 'ay']].drop_duplicates().shape[0] > 1:
        for r in g.itertuples(): tekrar.add((kod, int(r.yil), int(r.ay), kalem))
out = []
for r in csv.DictReader(open('null_satirlar.csv')):
    kod = r['Kod']; y, m = map(int, r['Dönem'].split('/'))
    satir = {'Kod': kod, 'Tip': r['Tip'], 'Dönem': r['Dönem']}
    genel = 'TEYITLI'
    for kalem in ('CFO', 'MDV+MODV', 'YAGM', 'KIRA'):
        if m == 12:
            parca = [(1, al(kod, y, 12, kalem, 'cari'))]
        else:
            parca = [(1, al(kod, y, m, kalem, 'cari')), (1, al(kod, y - 1, 12, kalem, 'cari')),
                     (-1, al(kod, y, m, kalem, 'onceki'))]
        st = max((p[1][1] for p in parca), key=SIRA.get)
        vals = [p[1][0] for p in parca]
        ttm = None if any(v is None for v in vals) else sum(s * v for (s, _), v in zip(parca, vals))
        satir[f'{kalem} TTM'] = None if ttm is None else round(ttm, 3)
        satir[f'{kalem} statü'] = st
        satir[f'{kalem} bileşen'] = ' | '.join('—' if v is None else f'{v:.3f}' for v in vals)
        satir[f'{kalem} kanıt'] = ' ‖ '.join(p[1][2] for p in parca)
        genel = max(genel, st, key=SIRA.get)
    satir['Satır statü'] = genel
    out.append(satir)
D = pd.DataFrame(out)
V7 = pd.read_excel('../FCF_V8_aday_K13.xlsx', sheet_name='KARAR', keep_default_na=False, na_values=[''])
V7 = V7[V7['V7 statü'] == 'NULL'][['Kod', 'Dönem', 'CFO_TTM', 'CAPEX_STD', '|Kira anapara|']]
V7.columns = ['Kod', 'Dönem', 'V7 CFO_TTM (Evo)', 'V7 CAPEX_STD (Evo)', 'V7 |Kira| (Evo)']
D = D.merge(V7, on=['Kod', 'Dönem'], how='left')
D['CFO fark (belge−Evo)'] = (D['CFO TTM'] - D['V7 CFO_TTM (Evo)']).round(3)

# V7 formülü (KARAR'daki 2.262 FCF_STD satırının 2.261'inde birebir): FCF_STD = CFO − CAPEX_STD − |Kira|,
# CAPEX_STD = |MDV+MODV| + |YAGM|; TTM'i pozitif çıkan çıkış kalemi formülde 0 alınır (K6).
# FCF_HLD (holding) tanımı KARAR'dan türetilemiyor → holding satırlarında yalnız bileşenler verilir.
def cikis(v):
    return None if pd.isna(v) else (-v if v < 0 else 0.0)
D['CAPEX_STD (belge)'] = [None if pd.isna(a) or pd.isna(b) else round(cikis(a) + cikis(b), 3)
                          for a, b in zip(D['MDV+MODV TTM'], D['YAGM TTM'])]
D['|Kira| (belge)'] = [None if pd.isna(v) else round(cikis(v), 3) for v in D['KIRA TTM']]
D['K6 dışlanan (belge)'] = ['; '.join(f'{k} TTM {D.at[i, k + " TTM"]:+.3f} (pozitif) → 0' for k in ('MDV+MODV', 'YAGM', 'KIRA')
                                      if not pd.isna(D.at[i, k + ' TTM']) and D.at[i, k + ' TTM'] > 0) for i in D.index]
D['FCF_STD (belge)'] = [round(c - x - k, 3) if t == 'Standart' and not any(pd.isna(v) for v in (c, x, k)) else None
                        for t, c, x, k in zip(D['Tip'], D['CFO TTM'], D['CAPEX_STD (belge)'], D['|Kira| (belge)'])]
D.to_csv('null_ttm.csv', index=False)
print(D['Satır statü'].value_counts().to_dict())
for k in ('CFO', 'MDV+MODV', 'YAGM', 'KIRA'):
    print(k, D[f'{k} statü'].value_counts().to_dict())
