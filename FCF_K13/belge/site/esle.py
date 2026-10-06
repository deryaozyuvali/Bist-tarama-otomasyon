"""pdf_linkleri.json → gereken (kod, yıl, ay) raporlarına aday PDF'ler (aday.json). Dönem URL/bağlantı metnindeki tarihten."""
import json, re, unicodedata
from urllib.parse import unquote
AY = {3: r'0?3|mart|march|q1|1\.?\s*ç|i\.?\s*çeyrek|3\s*ayl|ilk\s*3', 6: r'0?6|haziran|june|q2|h1|2\.?\s*ç|6\s*ayl|ilk\s*6|ilk\s*yar',
      9: r'0?9|eyl[uü]l|september|q3|3\.?\s*ç|9\s*ayl', 12: r'12|aral[ıi]k|december|q4|y[ıi]ll[ıi]k|annual|12\s*ayl|faaliyet\s*y'}
GUN = {3: '31', 6: '30', 9: '30', 12: '31'}
def norm(s):
    s = unquote(unquote(s)).lower().replace('ı', 'i').replace('İ', 'i')
    return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
def donem(u, m):
    t = norm(u + ' ' + m)
    out = set()
    for y in range(2024, 2027):
        for a, g in GUN.items():
            for p in (rf'{g}[.\-_ ]?{a:02d}[.\-_ ]?{y}', rf'{y}[.\-_ ]?{a:02d}[.\-_ ]?{g}', rf'{g}[.\-_ ]?{a}[.\-_ ]?{y}'):
                if re.search(p, t): out.add((y, a))
    if not out:
        ys = set(map(int, re.findall(r'20(2[4-6])', t)))
        ys = {2000 + y for y in ys}
        if len(ys) == 1:
            y = ys.pop()
            for a in (3, 6, 9, 12):
                w = {3: r'mart|march|q1|1q|3 ?ayl|3ay|1\.? ?ceyrek|i\. ?ceyrek', 6: r'haziran|june|q2|2q|h1|6 ?ayl|6ay|ilk ?yari|2\.? ?ceyrek',
                     9: r'eylul|september|q3|3q|9 ?ayl|9ay|3\.? ?ceyrek', 12: r'aralik|december|q4|4q|yillik|annual|12 ?ayl|12ay|yil ?sonu|4\.? ?ceyrek'}[a]
                if re.search(w, t): out.add((y, a))
    return out
FIN = re.compile(r'finans|mali|bdr|denetim|financial|tablo|dipnot|statement|audit|sinirli|konsolide|solo|bagimsiz|frs', re.I)
DIS = re.compile(r'sunum|present|surdurul|sustain|gundem|esas ?sozles|izahname|kurumsal ?yonetim|politika|karbon|iklim|vekalet|tutanak|bulten|ozel ?durum|ucret|temettu|bagis|cdp|tcfd|kar ?dagit', re.I)
G = json.load(open('../gerek.json')) if False else None
