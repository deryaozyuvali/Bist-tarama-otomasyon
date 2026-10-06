"""Ek listesi boş kalmış KAP bildirimlerinin PDF eklerini yeniden indirir (json'daki tablo korunur).
Kullanım: python3 kap_ek_tamamla.py liste.txt [bekleme_sn]"""
import json, os, re, subprocess, sys, tempfile, time
from kap_indir import curl, OB
from kap_tablo import _metin
bek = float(sys.argv[2]) if len(sys.argv) > 2 else 6
for idx in [l.strip() for l in open(sys.argv[1]) if l.strip()]:
    p = f'{OB}/{idx}.json'; j = json.load(open(p))
    if j.get('ekler'): continue
    with tempfile.TemporaryDirectory() as td:
        h = f'{td}/b.html'
        if not curl(f'https://www.kap.org.tr/tr/Bildirim/{idx}', h): print(idx, 'html yok', flush=True); time.sleep(bek); continue
        t = _metin(open(h, encoding='utf-8', errors='replace').read())
        ekler = [{'url': u, 'ad': ad} for u, ad in dict.fromkeys(re.findall(
            r'href="(https://www\.kap\.org\.tr/tr/api/file/download/[0-9a-f]+)">([^<]*)</a>', t))]
        for n, e in enumerate(ekler):
            f = f'{td}/e{n}'
            if curl(e['url'], f):
                e['tip'] = 'PDF' if b'%PDF' in open(f, 'rb').read(1024) else 'diger'
                if e['tip'] == 'PDF':
                    subprocess.run(['pdftotext', '-layout', f, f'{OB}/{idx}_{n}.txt']); e['metin'] = f'{idx}_{n}.txt'
            time.sleep(1)
        j['ekler'] = ekler; json.dump(j, open(p, 'w'), ensure_ascii=False)
        print(idx, len(ekler), 'ek', flush=True)
    time.sleep(bek)
