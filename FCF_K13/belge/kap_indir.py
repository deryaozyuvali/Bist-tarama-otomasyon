"""Bir KAP FR bildirimini indirir: nakit akış XBRL satırları + PDF ek(ler)inin metni.
Kullanım: python3 kap_indir.py <disclosureIndex>  → ONBELLEK/<idx>.json, ONBELLEK/<idx>_<n>.txt
Ham HTML/PDF saklanmaz (disk); yalnız çözülmüş tablo ve pdftotext -layout çıktısı."""
import json, os, re, subprocess, sys, tempfile, time
from kap_tablo import tablolar, _metin
OB = os.environ.get('ONBELLEK', 'onbellek')
os.makedirs(OB, exist_ok=True)

def curl(url, out):
    for i in range(4):
        r = subprocess.run(['curl', '-sS', '-L', '--max-time', '180', '-o', out, '-w', '%{http_code}', url],
                           capture_output=True, text=True)
        if r.stdout.strip() == '200' and os.path.getsize(out) > 1000: return True
        time.sleep(2 ** i)
    return False

def isle(idx):
    hedef = f'{OB}/{idx}.json'
    if os.path.exists(hedef): return
    with tempfile.TemporaryDirectory() as td:
        h = f'{td}/b.html'
        if not curl(f'https://www.kap.org.tr/tr/Bildirim/{idx}', h):
            json.dump({'idx': idx, 'hata': 'html indirilemedi'}, open(hedef, 'w')); return
        raw = open(h, encoding='utf-8', errors='replace').read()
        T = tablolar(raw)
        nak = {r: v for r, v in T.items() if any(s['eleman'] == 'ifrs-full_CashFlowsFromUsedInOperatingActivities' for s in v['satirlar'])}
        t = _metin(raw)
        ekler = []
        for u, ad in dict.fromkeys(re.findall(r'href="(https://www\.kap\.org\.tr/tr/api/file/download/[0-9a-f]+)">([^<]*)</a>', t)):
            ekler.append({'url': u, 'ad': ad})
        for n, e in enumerate(ekler):
            p = f'{td}/e{n}'
            if curl(e['url'], p):
                bas = open(p, 'rb').read(1024)
                e['tip'] = 'PDF' if b'%PDF' in bas else bas[:8].hex()
                if e['tip'] == 'PDF':
                    subprocess.run(['pdftotext', '-layout', p, f'{OB}/{idx}_{n}.txt'])
                    e['metin'] = f'{idx}_{n}.txt'
            else:
                e['hata'] = 'indirilemedi'
        json.dump({'idx': idx, 'nakit_akis': nak, 'ekler': ekler,
                   'roller': {r: (v['nitelik'], v['baslik'][:2]) for r, v in T.items()}}, open(hedef, 'w'), ensure_ascii=False)

if __name__ == '__main__':
    for a in sys.argv[1:]:
        try: isle(int(a))
        except Exception as ex: print('HATA', a, ex, file=sys.stderr)
