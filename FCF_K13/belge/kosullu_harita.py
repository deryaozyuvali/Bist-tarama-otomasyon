"""KOŞULLU satırları için gereken raporlar (dönem + önceki yıl sonu) → KAP bildirim eşlemesi (kap_fr.json).
Çıktı: kosullu_satirlar.csv, rapor_bildirim_haritasi.json'a eklenen anahtarlar (mevcut eşlemeler korunur)."""
import json, csv, collections
import pandas as pd
AY = {('3 Aylık', 1): 3, ('6 Aylık', 2): 6, ('9 Aylık', 3): 9, ('Yıllık', 4): 12}
K = pd.read_excel('../FCF_V8_aday_K13.xlsx', sheet_name='KARAR', keep_default_na=False)
K = K[K['Önerilen statü'] == 'KOŞULLU']
K[['Kod', 'Tip', 'Dönem']].to_csv('kosullu_satirlar.csv', index=False)
fr = collections.defaultdict(list)
for x in json.load(open('kap_fr.json')):
    a = AY.get((x['ruleType'], x['period']))
    if not a or not x['subject'].startswith('Finansal Rapor') or not x['stockCodes']: continue
    for kod in [s.strip() for s in x['stockCodes'].split(',')]:
        fr[(kod, x['year'], a)].append({'idx': x['disclosureIndex'], 'tarih': x['publishDate'], 'ozet': x['summary'], 'unvan': x['kapTitle']})
H = json.load(open('rapor_bildirim_haritasi.json'))
gerek, eklenen, yok = set(), 0, []
for r in K.itertuples():
    y, m = map(int, r.Dönem.split('/'))
    gerek |= {(r.Kod, y, m), (r.Kod, y - 1, 12)}
for kod, y, m in sorted(gerek):
    a = f'{kod}|{y}|{m}'
    if a in H: continue
    if fr.get((kod, y, m)):
        H[a] = sorted(fr[(kod, y, m)], key=lambda e: e['idx']); eklenen += 1
    else: yok.append(a)
json.dump(H, open('rapor_bildirim_haritasi.json', 'w'), ensure_ascii=False)
print('gerekli rapor', len(gerek), '· eklenen', eklenen, '· KAP listesinde yok', len(yok), yok[:15])
