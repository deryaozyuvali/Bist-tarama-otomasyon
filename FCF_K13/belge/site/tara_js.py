"""JavaScript ile içerik yükleyen şirket sitelerinde PDF bağlantılarını gerçek tarayıcıyla (Playwright/Chromium) toplar.
Girdi: siteler.json + kod listesi (argüman). Çıktı: pdf_linkleri_js.json {KOD: [[url, metin, sayfa]]}.
Ana sayfadan yatırımcı ilişkileri / finansal rapor çağrışımlı bağlantıları 2 adım izler; her sayfada 'Finansal Raporlar' gibi
sekme/akordeon öğelerine tıklayıp yeniden toplar."""
import json, os, re, sys
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
IZ = re.compile(r'yat[ıi]r[ıi]mc|investor|finansal|financial|mali|rapor|report|/ir', re.I)
TIK = re.compile(r'finansal (rapor|tablo)|mali tablo|financial (report|statement)|bağımsız denetim|20(24|25|26)', re.I)

def topla(sayfa):
    return sayfa.eval_on_selector_all('a[href]', 'els => els.map(e => [e.href, (e.innerText||"").trim().slice(0,120)])')

def tara(tarayici, kod, alan, azami=25):
    bas = alan if alan.startswith('http') else 'https://' + alan
    kok = urlparse(bas).netloc.replace('www.', '')
    ctx = tarayici.new_context(user_agent='Mozilla/5.0 (X11; Linux x86_64) Chrome/124 Safari/537.36')
    p = ctx.new_page(); p.set_default_timeout(30000)
    kuyruk, gor, pdf = [(bas, 0)], set(), {}
    while kuyruk and len(gor) < azami:
        url, d = kuyruk.pop(0)
        if url in gor: continue
        gor.add(url)
        try:
            p.goto(url, wait_until='networkidle', timeout=45000)
        except Exception:
            try: p.wait_for_timeout(3000)
            except Exception: continue
        try:
            linkler = topla(p)
            # sekme/akordeon: finansal rapor ve yıl başlıklarına tıkla, yeni bağlantıları topla
            for el in p.query_selector_all('button, [role=tab], .accordion, summary, li, span, div[onclick]')[:400]:
                try:
                    t = (el.inner_text() or '').strip()
                    if len(t) < 40 and TIK.search(t):
                        el.click(timeout=1500); p.wait_for_timeout(400)
                except Exception: pass
            linkler += topla(p)
        except Exception:
            continue
        for u, m in linkler:
            if not u.startswith('http'): continue
            if '.pdf' in u.lower(): pdf.setdefault(u, [m, url])
            elif kok in urlparse(u).netloc and d < 2 and (IZ.search(u) or IZ.search(m)) and u not in gor:
                kuyruk.append((u.split('#')[0], d + 1))
    ctx.close()
    return [[u, m, s] for u, (m, s) in pdf.items()], len(gor)

if __name__ == '__main__':
    S = json.load(open('siteler.json'))
    out = json.load(open('pdf_linkleri_js.json')) if os.path.exists('pdf_linkleri_js.json') else {}
    px = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
                               proxy={'server': px} if px else None)
        for kod in sys.argv[1:]:
            try: l, n = tara(b, kod, S[kod])
            except Exception as e: l, n = [], 0; print(kod, 'hata', str(e)[:100])
            out[kod] = l; print(kod, 'sayfa', n, 'pdf', len(l), flush=True)
            json.dump(out, open('pdf_linkleri_js.json', 'w'), ensure_ascii=False, indent=0)
        b.close()
