"""Şirket sitelerinden finansal rapor PDF bağlantılarını toplar (KAP erişilemediğinde alternatif kaynak).
Girdi: siteler.json {KOD: alan adı}. Çıktı: pdf_linkleri.json {KOD: [[url, bağlantı metni, bulunduğu sayfa]]}.
Ana sayfadan başlayıp aynı alan adında, yatırımcı ilişkileri / finansal rapor çağrışımlı bağlantıları en fazla 3 adım izler."""
import json, re, sys, html
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor
import requests

CA = '/root/.ccr/ca-bundle.crt'
UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36'}
IZ = re.compile(r'yat[ıi]r[ıi]mc|investor|finansal|financial|mali[-_ ]?tablo|rapor|report|\bir\b|/ir/|kap|bilgi[-_ ]?toplum|sunum|faaliyet', re.I)
HREF = re.compile(r'''<a\b[^>]*?href\s*=\s*["']([^"'#]+)["'][^>]*>(.*?)</a>''', re.I | re.S)
PDFRX = re.compile(r'''["'(]([^"'()\s]+?\.pdf(?:\?[^"'()\s]*)?)["')]''', re.I)

def al(url):
    try:
        r = requests.get(url, headers=UA, timeout=25, verify=CA, allow_redirects=True)
        if r.status_code != 200 or 'html' not in r.headers.get('content-type', 'text/html'): return None, url
        return r.text, r.url
    except Exception:
        return None, url

def tara(kod, alan, azami=70):
    bas = alan if alan.startswith('http') else 'https://' + alan
    kok = urlparse(bas).netloc.replace('www.', '')
    kuyruk, gor, pdf = [(bas, 0)], set(), {}
    while kuyruk and len(gor) < azami:
        url, d = kuyruk.pop(0)
        if url in gor: continue
        gor.add(url)
        t, son = al(url)
        if t is None:
            if d == 0 and url.startswith('https://'): kuyruk.append(('http://' + url[8:], 0))
            continue
        for h, metin in HREF.findall(t):
            u = urljoin(son, html.unescape(h.strip()))
            m = re.sub(r'<[^>]+>', ' ', metin); m = ' '.join(html.unescape(m).split())[:120]
            if u.lower().split('?')[0].endswith('.pdf'):
                pdf.setdefault(u, [m, son])
            elif kok in urlparse(u).netloc and d < 3 and (IZ.search(u) or IZ.search(m)) and u not in gor:
                kuyruk.append((u.split('#')[0], d + 1))
        for h in PDFRX.findall(t):  # JSON/JS içindeki pdf yolları
            u = urljoin(son, html.unescape(h.replace('\\/', '/')))
            pdf.setdefault(u, ['', son])
    return kod, [[u, m, s] for u, (m, s) in pdf.items()], len(gor)

if __name__ == '__main__':
    S = json.load(open('siteler.json'))
    kodlar = sys.argv[1:] or list(S)
    out = {}
    with ThreadPoolExecutor(8) as ex:
        for kod, l, n in ex.map(lambda k: tara(k, S[k]), kodlar):
            out[kod] = l; print(kod, 'sayfa', n, 'pdf', len(l), flush=True)
    json.dump(out, open('pdf_linkleri.json', 'w'), ensure_ascii=False, indent=0)
