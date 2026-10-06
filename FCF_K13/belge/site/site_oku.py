"""aday.json'daki şirket sitesi PDF'lerini indirir, dönemi doğrular, cikar_pdf.isle ile okur → ../rapor_kalemleri_site.csv
Doğrulama: metinde dönem sonu tarihi (ör. '30 Haziran 2025' / '30.06.2025') geçmeli ve CFO özdeşlikle okunmalı;
okunamazsa sıradaki aday denenir. Taranmış (metinsiz) PDF'ler site_ocr_gerek.json'a yazılır."""
import csv, json, os, re, subprocess, sys
sys.path.insert(0, '..')
from cikar_pdf import isle
OB = os.environ.get('ONBELLEK', 'onbellek')
CA = '/root/.ccr/ca-bundle.crt'
AYAD = {3: ('31', 'mart', 'march'), 6: ('30', 'haziran', 'june'), 9: ('30', 'eyl', 'september'), 12: ('31', 'aral', 'december')}

def indir(kod, y, m, i, url):
    pdf, txt = f'{OB}/S_{kod}_{y}_{m}_{i}.pdf', f'{OB}/S_{kod}_{y}_{m}_{i}.txt'
    if not os.path.exists(txt):
        r = subprocess.run(['curl', '-sS', '-L', '--max-time', '180', '--cacert', CA, '-A', 'Mozilla/5.0', '-o', pdf, '-w', '%{http_code}', url],
                           capture_output=True, text=True)
        if r.stdout.strip() != '200' or not os.path.exists(pdf) or os.path.getsize(pdf) < 2000: return None, 'indirilemedi'
        subprocess.run(['pdftotext', '-layout', pdf, txt])
    if not os.path.exists(txt): return None, 'pdftotext hata'
    return txt, ''

def donem_var(metin, y, m):
    g, tr, en = AYAD[m]
    k = metin.lower()[:200000]
    return bool(re.search(rf'{g}[ .]*{tr}\w*[ ]*{y}|{g}[./]{m:02d}[./]{y}|{en}\w*[ ]*{g},?[ ]*{y}|{g}[ ]*{en}\w*[ ]*{y}', k))

if __name__ == '__main__':
    A = json.load(open('aday.json'))
    H = json.load(open('../rapor_bildirim_haritasi.json'))
    alan = ['kod', 'yil', 'ay', 'idx', 'role', 'nitelik', 'kalem', 'sutun', 'deger_tl', 'kaynak', 'durum',
            'pdf_birim', 'pdf_sayfa', 'pdf_satir', 'tms29', 'not_']
    w = csv.DictWriter(open('../rapor_kalemleri_site.csv', 'w', newline=''), fieldnames=alan); w.writeheader()
    ocr, gunluk = {}, []
    for anahtar, adaylar in A.items():
        kod, y, m = anahtar.split('|'); y, m = int(y), int(m)
        idx = max([e['idx'] for e in H.get(anahtar) or [{'idx': 0}]])
        sonuc = None
        for i, (url, metin) in enumerate(adaylar):
            txt, hata = indir(kod, y, m, i, url)
            if not txt: gunluk.append((anahtar, url, hata)); continue
            t = open(txt, encoding='utf-8', errors='replace').read()
            if len(t) < 5000: ocr.setdefault(anahtar, url); gunluk.append((anahtar, url, 'taranmış')); continue
            if not donem_var(t, y, m): gunluk.append((anahtar, url, 'dönem tarihi yok')); continue
            kay = isle(kod, y, m, idx, txt)
            cfo = [k for k in kay if k['kalem'] == 'CFO' and k['sutun'] == 'cari']
            if cfo and cfo[0]['durum'] == 'PDF_OKUNDU':
                for k in kay: k['kaynak'] = 'PDF (şirket sitesi) ' + url; w.writerow({a: k.get(a, '') for a in alan})
                sonuc = url; gunluk.append((anahtar, url, 'OKUNDU')); break
            gunluk.append((anahtar, url, 'CFO okunamadı: ' + (cfo[0]['durum'] if cfo else (kay[0].get('durum') if kay else '?'))))
        if not sonuc and anahtar not in ocr: pass
    json.dump(ocr, open('site_ocr_gerek.json', 'w'), ensure_ascii=False, indent=0)
    with open('site_oku.log', 'w') as f:
        for g in gunluk: f.write(' | '.join(g) + '\n')
    import collections
    print(collections.Counter(g[2].split(':')[0] for g in gunluk))
    print('okunan anahtar', len({g[0] for g in gunluk if g[2] == 'OKUNDU'}), 'ocr gereken', len(ocr))
