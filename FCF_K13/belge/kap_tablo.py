"""KAP 'Finansal Rapor' bildirim sayfasındaki XBRL taksonomi tablolarını çözer.
tablolar(html) → {role: {'baslik': [sütun başlığı], 'nitelik': 'Konsolide'/..., 'birim': 'TL',
                         'satirlar': [{'eleman','etiket','boyut','degerler':[TL|None]}]}}
Değerler sayfada görünen biçimden okunur (1.234.567 / -1.234.567 / 1.234,5); birim sayfa başlığındaki
'Sunum Para Birimi' (TL tam tutar)."""
import re, html as H

def _metin(t):
    t = t.replace('\\u003c', '<').replace('\\u003e', '>').replace('\\u0026', '&').replace('\\"', '"')
    return t.replace('\\r\\n', '\n').replace('\\n', '\n').replace('\\/', '/')

def _sayi(s):
    s = H.unescape(re.sub(r'<[^>]+>', '', s or '')).strip().replace('\xa0', '')
    if s in ('', '-', '--'): return None
    neg = s.startswith('(') and s.endswith(')')
    s = s.strip('()').replace('.', '').replace(',', '.')
    try: v = float(s)
    except ValueError: return None
    return -v if neg else v

def _txt(s):
    return ' '.join(H.unescape(re.sub(r'<[^>]+>', ' ', s)).split())

def tablolar(raw):
    t = _metin(raw)
    out = {}
    starts = [m for m in re.finditer(r'<table class="financial-table tbl_general_role_(\d+)">', t)]
    for n, m in enumerate(starts):
        role = m.group(1)
        end = starts[n + 1].start() if n + 1 < len(starts) else len(t)
        body = t[m.end():end]
        on = t[max(0, m.start() - 1500):m.start()]
        nit = re.findall(r'Finansal Tablo Niteliği</td>\s*<td>([^<]*)</td>', on)
        bir = re.findall(r'Sunum Para Birimi</td>\s*<td>([^<]*)</td>', on)
        bas = [_txt(h) for h in re.findall(r'class="context-header"[^>]*>(.*?)</td>', body, re.S)]
        rows = re.split(r'<tr class="general_role_\d+-row-\d+', body)[1:]
        sat = []
        for r in rows:
            el = re.search(r'taxonomy-field-name">([^<|]*)', r)
            lab = re.search(r'multi-language-content content-tr" style="display: block;">(.*?)</div>', r, re.S)
            dim = re.search(r'taxonomy-(non)?dimensional-context-cell">(.*?)</td>', r, re.S)
            vals = [_sayi(v) for v in re.findall(r'class="taxonomy-context-value[^"]*"><div><div[^>]*>(.*?)</div>', r, re.S)]
            sat.append({'eleman': el.group(1) if el else '', 'etiket': _txt(lab.group(1)) if lab else '',
                        'boyut': _txt(dim.group(2)) if dim else '', 'degerler': vals})
        out.setdefault(role, {'baslik': bas, 'nitelik': nit[-1].strip() if nit else '',
                              'birim': bir[-1].strip() if bir else '', 'satirlar': sat})
    return out

if __name__ == '__main__':
    import sys
    T = tablolar(open(sys.argv[1], encoding='utf-8').read())
    for r, v in T.items():
        print('ROLE', r, v['nitelik'], v['birim'], v['baslik'][:2], len(v['satirlar']))
    for s in T.get(sys.argv[2] if len(sys.argv) > 2 else '520003', {}).get('satirlar', []):
        print(s['eleman'][:70].ljust(70), s['etiket'][:70].ljust(70), s['degerler'])
