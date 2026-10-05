"""NULL satırlar için belge TTM'leri: TTM = YTD_cari + FY_önceki − YTD_önceki (Aralık dönemi: FY_cari).
YTD_önceki, cari raporun karşılaştırmalı sütunundan alınır (V7 köprüsüyle aynı tanım).
Girdi : null_satirlar.csv, rapor_kalemleri.csv  → Çıktı: null_ttm.csv
Kalem statüsü:
  TEYITLI   kullanılan her değer PDF'te bulundu ya da XBRL'de boş/0 ve PDF'te o kaleme ait satır yok
  ELLE      en az bir değer PDF'te bulunamadı / PDF metni yok (taranmış) / PDF'te XBRL dışı satır var
  BELGE_YOK gereken rapor KAP'ta yok ya da tabloda dönem sütunu yok
Tutarlar mn TL; işaret belgedeki gibi (çıkış negatif)."""
import csv, collections, json
import pandas as pd

K = pd.read_csv('rapor_kalemleri.csv', dtype={'pdf_sayfa': str})
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
        return None, 'BELGE_YOK', f"{y}/{m:02d} {next(iter(rk['*'].values())).durum}"
    d = rk.get(kalem, {})
    r = d.get(sut)
    if r is None or r.durum == 'SUTUN_YOK': return None, 'BELGE_YOK', f'{y}/{m:02d} {sut} sütunu yok'
    ek = d.get('*')
    v = None if pd.isna(r.deger_tl) else r.deger_tl / 1e6
    kanit = f'KAP {int(r.idx)} {y}/{m:02d} {sut}'
    if r.durum == 'TEYITLI': kanit += f' · PDF s.{r.pdf_sayfa} ({r.pdf_birim}): {r.pdf_satir}'
    if ek is not None:
        return v, 'ELLE', kanit + f' · PDF’te XBRL dışı satır: {ek.pdf_satir}'
    if r.durum in ('TEYITLI', 'SIFIR'): return (v or 0.0), 'TEYITLI', kanit
    return v, 'ELLE', kanit + f' · {r.durum}'

SIRA = {'TEYITLI': 0, 'ELLE': 1, 'BELGE_YOK': 2}
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
pd.DataFrame(out).to_csv('null_ttm.csv', index=False)
D = pd.DataFrame(out)
print(D['Satır statü'].value_counts().to_dict())
for k in ('CFO', 'MDV+MODV', 'YAGM', 'KIRA'):
    print(k, D[f'{k} statü'].value_counts().to_dict())
