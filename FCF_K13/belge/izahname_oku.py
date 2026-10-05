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
    # Başlık satırı ('30 EYLÜL 2025, 31 ARALIK 2024, 30 EYLÜL 2024 ...') sütun sırasını vermeyebilir: sütun başlığı
    # tablo başlığından sonra, verilere en yakın satırdadır → N tarih taşıyan (gün+ay+yıl, '30.06.2025' ya da
    # günsüz 'Mart 2026') son satır alınır.
    desenler = ((TARIH, lambda m: (int(m.group(3)), AY[m.group(2)])),
                (re.compile(r'\b\d{2}[./](03|06|09|12)[./](20\d\d)\b'), lambda m: (int(m.group(2)), int(m.group(1)))),
                (re.compile(r'(?<!\d\s)\b(mart|haziran|eylül|eylul|aralık|aralik)\s+(20\d\d)\b'), lambda m: (int(m.group(2)), AY[m.group(1)])))
    son = None
    satirlar = [kucuk(l) for l in sayfa.split('\n')[:40]]
    for i, l in enumerate(satirlar):
        for d_, f in desenler:
            t = [f(m) for m in d_.finditer(l)]
            if len(t) == n: son = t; break
        else:
            # gün+ay bir satırda, yıl alt satırda ('31 Mart  31 Aralık' / '2026  2025')
            aylar = re.findall(r'(\d{1,2})\s+(mart|haziran|eylül|eylul|aralık|aralik)\b(?!\s+20\d\d)', l)
            yillar = re.findall(r'\b(20\d\d)\b', satirlar[i + 1]) if i + 1 < len(satirlar) else []
            if len(aylar) == n and len(yillar) == n:
                son = [(int(y), AY[a[1]]) for a, y in zip(aylar, yillar)]
    if son: return son
    return []

def sap(sayfa):
    m = re.search(r'(\d{1,2})\s+(mart|haziran|eylül|eylul|aralık|aralik)\s+(20\d\d)\s+tarihi\s+itibar\w*\s+satın ?alma gücü',
                  kucuk(' '.join(sayfa.split())))
    return (int(m.group(3)), AY[m.group(2)]) if m else None

def birim(sayfa):
    t = kucuk(' '.join(sayfa.split('\n')[:12]))
    return 1e3 if re.search(r'bin\s*(türk lira|tl)|tl\s*[’\']?\s*\(?bin|\(000\)', t) else 1.0

def oku(kod, tablo, yeniden=False):
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
    toplam = {'yat': [], 'fin': [], 'net': [], 'etki': []}
    yedek_cfo = []  # A bölüm toplamı 'Faaliyetlerden elde edilen nakit akışları' adıyla verilmişse (işletme satırı yoksa)
    ls_ = metin.split('\n')
    for si, satir in enumerate(ls_):
        etiket, vals, ok = _alanlar(satir)
        if not etiket: onceki = ''; continue
        if re.fullmatch(r'\(?[\d.,]+\)?|[-–]+|(?i:dipnot|not)', etiket):
            # etiketsiz değer satırı: etiket üstte başlayıp altta bitiyor ('Maddi ... Alımından' / değerler / 'Kaynaklanan Nakit Çıkışları')
            _, vals, _ = _alanlar('X  ' + satir.strip())
            alt = ls_[si + 1].strip() if si + 1 < len(ls_) and not _alanlar(ls_[si + 1])[1] else ''
            etiket = alt
        elif not vals: onceki = etiket if len(etiket) < 140 else ''; continue
        tam = kucuk((onceki + ' ' + etiket).strip()); onceki = ''
        if len(vals) < len(sut): continue
        v = vals[-len(sut):]
        # bölüm başlığı ('A. İşletme faaliyetlerinden nakit akışları') değersizse ilk kalemle (dönem karı) birleşmesin
        if CFO.search(tam) and not re.search(r'işletme sermayesi', tam) \
                and not re.search(r'dönem\s*(net\s*)?\(?(kar|kâr|zarar)', kucuk(etiket)):
            satirlar['CFO'].append((satir, v))
        elif re.search(r'^faaliyetlerden (elde edilen|kaynaklanan) (net )?nakit ak', tam):
            yedek_cfo.append((satir, v))
        ke = kucuk(etiket)
        if any(re.search(r'^b?[.)]?\s*yatırım faaliyet\w*.{0,40}nakit', x) for x in (tam, ke)): toplam['yat'].append(v)
        if any(re.search(r'^c?[.)]?\s*finansman faaliyet\w*.{0,40}nakit', x) for x in (tam, ke)): toplam['fin'].append(v)
        if re.search(r'nakit benzerlerindeki.{0,40}(artış|azalış|değişim)|^net (artış|azalış)', tam) \
                and (not re.search(r'enflasyon|yabancı para|çevrim', tam) or 'önce' in tam): toplam['net'].append(v)
        elif re.search(r'etki', tam) and re.search(r'enflasyon|yabancı para|çevrim', tam): toplam['etki'].append(v)
        for kal in ('MDV+MODV', 'YAGM', 'KIRA'):
            if re.search(PDF_ETIKET[kal], tam, re.I) and not re.search(PDF_DISLA[kal], tam, re.I) \
                    and not ('giriş' in tam and 'çıkış' not in tam):
                satirlar[kal].append((satir, v))
    # Özdeşlik: A + B + C (+ kur/enflasyon etkisi) = nakitteki net değişim. Birden çok CFO adayı varsa
    # en çok sütunda özdeşliği sağlayan alınır; sağlanmazsa son aday (bölüm toplamı) ve özdeşlik=False.
    def ozd(v, i):
        for y_ in toplam['yat']:
            for f_ in toplam['fin']:
                t = v[i] + y_[i] + f_[i]
                for n_ in toplam['net']:
                    if abs(t - n_[i]) <= 2 or any(abs(t + e[i] - n_[i]) <= 2 for e in toplam['etki']) \
                            or abs(t + sum(e[i] for e in toplam['etki']) - n_[i]) <= 2: return True
        return False
    adaylar = satirlar['CFO'] + yedek_cfo
    if adaylar:
        puan = [sum(ozd(v, i) for i in range(len(sut))) for _, v in adaylar]
        en = max(puan)
        sec = [a for a, p in zip(adaylar, puan) if p == en][-1] if en else (satirlar['CFO'] or yedek_cfo)[-1]
        satirlar['CFO'] = [sec]
        ozdeslik = [ozd(sec[1], i) for i in range(len(sut))]
    if not satirlar['CFO']:
        # CFO satırı yoksa sayfa nakit akış tablosu değil (ör. gelir tablosu) → 'satır yok = 0' üretme;
        # izahname_bul yanlış sayfayı seçtiyse aynı ekte işletme + yatırım bölümlerini taşıyan ilk sayfa denenir
        if not yeniden:
            for i, pg in enumerate(ps):
                if i != no and re.search(r'işletme faaliyetlerinden', kucuk(pg)) and re.search(r'yatırım faaliyetlerinden', kucuk(pg)):
                    return oku(kod, dict(tablo, sayfa=i + 1), yeniden=True)
        return []
    for kal, ls in satirlar.items():
        if kal == 'CFO': ls = ls[-1:]  # ara toplam ve net satırı varsa sonuncusu (net) alınır
        if not ls:
            if kal != 'CFO':
                for (y, m) in sut:
                    out.append(dict(kod=kod, yil=y, ay=m, kalem=kal, deger_tl=0.0, sap=d, durum='SATIR_YOK', ozdeslik=ozdeslik[sut.index((y, m))],
                                    idx=tablo['idx'], ek=tablo['ek'], sayfa=tablo['sayfa'], satir=''))
            continue
        for i, (y, m) in enumerate(sut):
            out.append(dict(kod=kod, yil=y, ay=m, kalem=kal, deger_tl=sum(v[i] for _, v in ls) * k, sap=d,
                            durum='OKUNDU', idx=tablo['idx'], ek=tablo['ek'], sayfa=tablo['sayfa'], ozdeslik=ozdeslik[i],
                            satir=' || '.join(' '.join(s.split())[:150] for s, _ in ls[:3])))
    return out

if __name__ == '__main__':
    import glob
    J = json.load(open('izahname_donemleri.json')) if os.path.exists('izahname_donemleri.json') else {}
    for f in glob.glob('izahname/*.json'): J[os.path.basename(f)[:-5]] = json.load(open(f))
    alan = ['kod', 'yil', 'ay', 'kalem', 'deger_tl', 'sap', 'durum', 'ozdeslik', 'idx', 'ek', 'sayfa', 'satir']
    w = csv.DictWriter(open('izahname_kalemleri.csv', 'w', newline=''), fieldnames=alan); w.writeheader()
    for kod, v in J.items():
        gor = set()
        # en güncel izahname önce (aynı dönem birden çok izahnamede varsa en yeni satın alma gücü tarihli olan)
        for t in sorted(v['tablolar'], key=lambda t: t['idx'], reverse=True):
            for r in oku(kod, t):
                a = (r['yil'], r['ay'], r['kalem'])
                if a in gor: continue
                gor.add(a); w.writerow({k: r.get(k) for k in alan})
