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

def isle(idx, ek_filtre=None):
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
            if ek_filtre and not re.search(ek_filtre, e['ad'], re.I):
                e['atlandi'] = True; continue
            p = f'{td}/e{n}'
            if curl(e['url'], p):
                bas = open(p, 'rb').read(1024)
                e['tip'] = 'PDF' if b'%PDF' in bas else bas[:8].hex()
                if e['tip'] == 'PDF':
                    hedef_txt = f'{OB}/{idx}_{n}.txt'
                    subprocess.run(['pdftotext', '-layout', p, hedef_txt])
                    e['metin'] = f'{idx}_{n}.txt'
                    if os.environ.get('OCR') and (os.path.getsize(hedef_txt) < 5000 or os.environ.get('OCR') == 'zorla'):
                        # taranmış PDF: sayfaları 200 dpi görüntüye çevirip Tesseract (Türkçe) ile oku
                        subprocess.run(['pdftoppm', '-r', '200', '-gray', '-png', '-l', '20', p, f'{td}/s'])  # ilk 20 sayfa: tablolar raporun başında
                        parcalar = []
                        for g in sorted(f for f in os.listdir(td) if f.startswith('s') and f.endswith('.png')):
                            r = subprocess.run(['tesseract', f'{td}/{g}', '-', '-l', 'tur', '--psm', '6',
                                                '-c', 'preserve_interword_spaces=1'], capture_output=True, text=True)
                            parcalar.append(r.stdout); os.remove(f'{td}/{g}')
                        open(hedef_txt, 'w').write('\f'.join(parcalar))
                        e['ocr'] = True
            else:
                e['hata'] = 'indirilemedi'
        json.dump({'idx': idx, 'nakit_akis': nak, 'ekler': ekler,
                   'roller': {r: (v['nitelik'], v['baslik'][:2]) for r, v in T.items()}}, open(hedef, 'w'), ensure_ascii=False)

if __name__ == '__main__':
    for a in sys.argv[1:]:
        try: isle(int(a))
        except Exception as ex: print('HATA', a, ex, file=sys.stderr)
