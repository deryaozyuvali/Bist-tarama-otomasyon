"""Halka arz öncesi NULL satırları için şirket izahnamelerini bulur ve içindeki nakit akış tablolarının dönemlerini çıkarır.
1) şirketin KAP üye kimliği (mkkMemberOid) — şirketin herhangi bir FR bildirim sayfasından
2) o üyenin 'İzahname (SPK Tarafından Onaylanan)' bildirimleri (6 aylık pencereler; API ≤2000 kayıt)
3) ekleri indir (kap_indir.py), nakit akış sayfası taşıyan eki ve başlıktaki dönem sütunlarını bul
→ izahname_donemleri.json"""
import json, os, re, subprocess, sys, datetime as dt
from kap_indir import isle
OB = os.environ.get('ONBELLEK', 'onbellek')
U = "https://www.kap.org.tr/tr/api/disclosure/members/byCriteria"
AY = {'mart': 3, 'haziran': 6, 'eylül': 9, 'aralık': 12, 'eylul': 9, 'aralik': 12}

def oid(idx):
    r = subprocess.run(['curl', '-sS', '-L', '--max-time', '120', f'https://www.kap.org.tr/tr/Bildirim/{idx}'], capture_output=True, text=True)
    m = re.search(r'mkkMemberOid\\?":\\?"([0-9a-f]{32})', r.stdout)
    return m.group(1) if m else None

def bildirimler(o, a, b):
    body = {"fromDate": a, "toDate": b, "memberType": "IGS", "mkkMemberOidList": [o], "disclosureClass": "", "subjectList": [],
            "isLate": "", "mainSector": "", "sector": "", "subSector": "", "marketOidList": [], "index": "", "bdkReview": "",
            "bdkMemberOidList": [], "year": "", "term": "", "ruleType": "", "period": "", "fromSrc": False, "srcCategory": "", "discIndex": []}
    r = subprocess.run(["curl", "-sS", "--max-time", "120", "-X", "POST", "-H", "Content-Type: application/json", U, "-d", json.dumps(body)],
                       capture_output=True, text=True)
    try:
        x = json.loads(r.stdout); return x if isinstance(x, list) else []
    except Exception: return []

def donemler(baslik):
    """'30 Eylül 2025 2024 ve 31 Aralık 2024, 2023' gibi başlıktan değil, sütun başlığı satırlarından (YYYY, ay) listesi."""
    t = baslik.lower()
    out = []
    for m in re.finditer(r'(\d{1,2})\s+(mart|haziran|eylül|eylul|aralık|aralik)\s+(20\d\d)', t):
        out.append((int(m.group(3)), AY[m.group(2)]))
    return out

if __name__ == '__main__':
    H = json.load(open('rapor_bildirim_haritasi.json'))
    hedef = sys.argv[1:]  # şirket kodları
    os.makedirs('izahname', exist_ok=True)
    sonuc = json.load(open('izahname_donemleri.json')) if os.path.exists('izahname_donemleri.json') else {}
    for kod in hedef:
        if kod in sonuc or os.path.exists(f'izahname/{kod}.json'): continue
        ornek = next((b['idx'] for k, v in H.items() if k.startswith(kod + '|') for b in v), None)
        o = oid(ornek) if ornek else None
        kayit = {'oid': o, 'izahname': [], 'tablolar': []}
        if o:
            d = dt.date(2023, 1, 1)
            while d < dt.date(2026, 10, 5):
                e = min(d + dt.timedelta(days=180), dt.date(2026, 10, 5))
                for x in bildirimler(o, d.isoformat(), e.isoformat()):
                    if x['subject'].startswith('İzahname') and 'Onaylanan' in x['subject']:
                        kayit['izahname'].append((x['disclosureIndex'], x['publishDate'][:10], x['subject']))
                d = e + dt.timedelta(days=1)
            for idx, tarih, _ in kayit['izahname']:
                isle(idx, ek_filtre=r'denetim|finansal|mali tablo|bağımsız|bagimsiz|\bBDR\b|tablo')
                j = json.load(open(f'{OB}/{idx}.json'))
                for e in j.get('ekler', []):
                    if not e.get('metin'): continue
                    ps = open(f"{OB}/{e['metin']}", errors='replace').read().split('\f')
                    for n, p in enumerate(ps):
                        l = p.lower()
                        if 'nakit ak' in l and 'yatırım faaliyet' in l and len(re.findall(r'\d{1,3}(?:\.\d{3})+', p)) > 30:
                            bas = ' '.join(p.split('\n')[0:16])
                            kayit['tablolar'].append({'idx': idx, 'tarih': tarih, 'ek': e['ad'], 'metin': e['metin'], 'sayfa': n + 1,
                                                      'donemler': donemler(bas), 'baslik': ' '.join(bas.split())[:400]})
        json.dump(kayit, open(f'izahname/{kod}.json', 'w'), ensure_ascii=False, indent=0)  # paralel çalıştırma için şirket başına dosya
        print(kod, o, len(kayit['izahname']), 'izahname bildirimi,', len(kayit['tablolar']), 'NA sayfası', file=sys.stderr)
