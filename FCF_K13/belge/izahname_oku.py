"""İzahnamedeki (halka arz) çok sütunlu nakit akış tablolarından kalem değerlerini okur.
Girdi : izahname_donemleri.json (izahname_bul.py), ONBELLEK/<ek metni>
Çıktı : izahname_kalemleri.csv — kod, dönem (yıl, ay; YTD), kalem, değer (TL, belgedeki satın alma gücü),
        sap_tarihi (tablonun satın alma gücü tarihi), kaynak (bildirim, ek, sayfa, satır)
Sütunlar başlıktaki tarih satırından ('30 Eylül 2025   30 Eylül 2024   31 Aralık 2024 ...') sırayla alınır;
her kalem satırının son N değeri bu sütunlara eşlenir (N = sütun sayısı; eşit değilse satır alınmaz)."""
import csv, json, os, re
from cikar import _alanlar, kucuk, PDF_ETIKET, PDF_DISLA

OB = os.environ.get('ONBELLEK', 'onbellek')
AY = {'mart': 3, 'haziran': 6, 'eylül': 9, 'eylul': 9, 'aralık': 12, 'aralik': 12}
TARIH = re.compile(r'(\d{1,2})\s+(mart|haziran|eylül|eylul|aralık|aralik)\s+(20\d\d)')
CFO = re.compile(r'(işletme|esas) faaliyetler\w*\s+(elde edilen|sağlanan|kaynaklanan|kullanılan)?.{0,30}nakit ak')

def sutunlar(sayfa):
    """Veri satırlarındaki modal değer sayısı N; başlıkta tam N tarih taşıyan satır → [(yıl, ay)] sırayla.
    (Tablo başlığı '30 EYLÜL 2025, 2024 VE 31 ARALIK 2024 ...' gibi özet satırlar N ile tutmadığı için elenir.)"""
    import collections
    say = collections.Counter()
    for l in sayfa.split('\n'):
        et, vals, _ = _alanlar(l)
        if et and len(vals) >= 2: say[len(vals)] += 1
    if not say: return []
    n = say.most_common(1)[0][0]
    for l in sayfa.split('\n')[:40]:
        t = [(int(m.group(3)), AY[m.group(2)]) for m in TARIH.finditer(kucuk(l))]
        if len(t) == n: return t
    # tarih ve yıl iki ayrı satırdaysa ('30 Haziran' / '2025'): ay satırı + yıl satırı
    satirlar = [kucuk(l) for l in sayfa.split('\n')[:40]]
    for i, l in enumerate(satirlar[:-1]):
        aylar = re.findall(r'(\d{1,2})\s+(mart|haziran|eylül|eylul|aralık|aralik)\b(?!\s+20\d\d)', l)
        yillar = re.findall(r'\b(20\d\d)\b', satirlar[i + 1])
        if len(aylar) == n and len(yillar) == n:
            return [(int(y), AY[a[1]]) for a, y in zip(aylar, yillar)]
    return []

def sap(sayfa):
    m = re.search(r'(\d{1,2})\s+(mart|haziran|eylül|eylul|aralık|aralik)\s+(20\d\d)\s+tarihi\s+itibar\w*\s+satın ?alma gücü',
                  kucuk(' '.join(sayfa.split())))
    return (int(m.group(3)), AY[m.group(2)]) if m else None

def birim(sayfa):
    t = kucuk(' '.join(sayfa.split('\n')[:12]))
    return 1e3 if re.search(r'bin\s*(türk lira|tl)|tl\s*[’\']?\s*\(?bin|\(000\)', t) else 1.0

def oku(kod, tablo):
    ps = open(f"{OB}/{tablo['metin']}", errors='replace').read().split('\f')
    no = tablo['sayfa'] - 1
    sayfa = ps[no]
    sut = sutunlar(sayfa)
    if not sut: return []
    d, k = sap(sayfa), birim(sayfa)
    metin = sayfa + ('\n' + ps[no + 1] if no + 1 < len(ps) else '')  # tablo sonraki sayfaya taşabilir
    out = []
    onceki = ''
    satirlar = {'CFO': [], 'MDV+MODV': [], 'YAGM': [], 'KIRA': []}
    for satir in metin.split('\n'):
        etiket, vals, ok = _alanlar(satir)
        if not etiket: onceki = ''; continue
        if not vals: onceki = etiket if len(etiket) < 140 else ''; continue
        tam = kucuk((onceki + ' ' + etiket).strip()); onceki = ''
        if len(vals) < len(sut): continue
        v = vals[-len(sut):]
        if CFO.search(tam) and not re.search(r'işletme sermayesi', tam):
            satirlar['CFO'].append((satir, v))
        for kal in ('MDV+MODV', 'YAGM', 'KIRA'):
            if re.search(PDF_ETIKET[kal], tam, re.I) and not re.search(PDF_DISLA[kal], tam, re.I) \
                    and not ('giriş' in tam and 'çıkış' not in tam):
                satirlar[kal].append((satir, v))
    for kal, ls in satirlar.items():
        if kal == 'CFO': ls = ls[-1:]  # ara toplam ve net satırı varsa sonuncusu (net) alınır
        if not ls:
            if kal != 'CFO':
                for (y, m) in sut:
                    out.append(dict(kod=kod, yil=y, ay=m, kalem=kal, deger_tl=0.0, sap=d, durum='SATIR_YOK',
                                    idx=tablo['idx'], ek=tablo['ek'], sayfa=tablo['sayfa'], satir=''))
            continue
        for i, (y, m) in enumerate(sut):
            out.append(dict(kod=kod, yil=y, ay=m, kalem=kal, deger_tl=sum(v[i] for _, v in ls) * k, sap=d,
                            durum='OKUNDU', idx=tablo['idx'], ek=tablo['ek'], sayfa=tablo['sayfa'],
                            satir=' || '.join(' '.join(s.split())[:150] for s, _ in ls[:3])))
    return out

if __name__ == '__main__':
    import glob
    J = json.load(open('izahname_donemleri.json')) if os.path.exists('izahname_donemleri.json') else {}
    for f in glob.glob('izahname/*.json'): J[os.path.basename(f)[:-5]] = json.load(open(f))
    alan = ['kod', 'yil', 'ay', 'kalem', 'deger_tl', 'sap', 'durum', 'idx', 'ek', 'sayfa', 'satir']
    w = csv.DictWriter(open('izahname_kalemleri.csv', 'w', newline=''), fieldnames=alan); w.writeheader()
    for kod, v in J.items():
        gor = set()
        # en güncel izahname önce (aynı dönem birden çok izahnamede varsa en yeni satın alma gücü tarihli olan)
        for t in sorted(v['tablolar'], key=lambda t: t['idx'], reverse=True):
            for r in oku(kod, t):
                a = (r['yil'], r['ay'], r['kalem'])
                if a in gor: continue
                gor.add(a); w.writerow({k: r.get(k) for k in alan})
