"""KAP bildirimlerinden kalem değerlerini çıkarır ve her değeri imzalı PDF metninde arar.

Girdi : ONBELLEK/<idx>.json (+ PDF metinleri), rapor_bildirim_haritasi.json
Çıktı : rapor_kalemleri.csv — her (kod, yıl, ay, kalem, sütun) için XBRL değeri, PDF teyidi, PDF satırı
Kalemler (XBRL elemanı, TL tam tutar, işaret belgedeki gibi):
  CFO        ifrs-full_CashFlowsFromUsedInOperatingActivities
  MDV+MODV   kap-fr_PurchaseOfPropertyPlantEquipmentAndIntangibleAssets…  (yoksa MDV + MODV alt kalemleri)
  YAGM       kap-fr_CashOutflowsFromAcquitionOfInvestmentsProperty…
  KIRA       kap-fr_PaymentsOfLeaseLiabilities…
PDF teyidi: değerin mutlak tutarı nakit akış sayfasında TL, bin TL veya mn TL biriminde (±1 yuvarlama) geçiyor mu.
Ayrıca PDF nakit akış sayfasında kira / MDV / YAGM etiketli satırlar XBRL'den bağımsız taranır;
XBRL'de 0/boş olup PDF'te tutar taşıyan satır 'PDF_EK_SATIR' olarak işaretlenir (elle bakılır)."""
import csv, json, os, re, sys
from datetime import date

OB = os.environ.get('ONBELLEK', 'onbellek')

ELEMAN = {
    'CFO': ['ifrs-full_CashFlowsFromUsedInOperatingActivities'],
    'MDV+MODV': ['kap-fr_PurchaseOfPropertyPlantEquipmentAndIntangibleAssets'],
    'MDV': ['ifrs-full_PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvesting'],
    'MODV': ['ifrs-full_PurchaseOfIntangibleAssetsClassifiedAsInvesting'],
    'YAGM': ['kap-fr_CashOutflowsFromAcquitionOfInvestmentsProperty'],
    'KIRA': ['kap-fr_PaymentsOfLeaseLiabilities'],
}
PDF_ETIKET = {
    'KIRA': r'kira|kiralama|leasing|tfrs\s*16|lease',
    'MDV+MODV': r'maddi.*(alım|alin|edinim|satın|yatırım|değişim|ilave|giriş|harcama)|duran varl[ıi]k.*(alım|alın|edinim)|purchase of property',
    'YAGM': r'yatırım amaçlı gayrimenkul',
}

def _tarih(s):
    d, m, y = s.split('.')
    return date(int(y), int(m), int(d))

def sutunlar(baslik, yil, ay):
    """Cari ve önceki YTD sütun indekslerini başlıktaki tarih aralıklarından bulur."""
    son = {3: (3, 31), 6: (6, 30), 9: (9, 30), 12: (12, 31)}[ay]
    cari = onceki = None
    for i, b in enumerate(baslik):
        r = re.findall(r'(\d\d\.\d\d\.\d{4})\s*-\s*(\d\d\.\d\d\.\d{4})', b)
        if not r: continue
        a, e = map(_tarih, r[0])
        if (e.month, e.day) != son: continue
        uzun = (e - a).days > 80 or ay == 3
        if e.year == yil and uzun and cari is None: cari = i
        elif e.year == yil - 1 and uzun and onceki is None: onceki = i
    return cari, onceki

def deger(satirlar, onekler, i):
    if i is None: return None
    for s in satirlar:
        if any(s['eleman'].startswith(o) for o in onekler) and not s['boyut']:
            v = s['degerler'][i] if i < len(s['degerler']) else None
            return v
    return None

SAYI = re.compile(r'\(?-?\d{1,3}(?:[.,]\d{3})+(?:,\d+)?\)?|\(?-?\d+(?:,\d+)?\)?')

def _say(tok):
    neg = tok.startswith('(') or tok.startswith('-')
    t = tok.strip('()-')
    if re.fullmatch(r'\d{1,3}(?:\.\d{3})+(?:,\d+)?', t): t = t.replace('.', '').replace(',', '.')
    elif re.fullmatch(r'\d{1,3}(?:,\d{3})+(?:\.\d+)?', t): t = t.replace(',', '')
    else: t = t.replace(',', '.')
    try: v = float(t)
    except ValueError: return None
    return -v if neg else v

def kucuk(s):
    return s.replace('İ', 'i').replace('I', 'ı').lower()

def nakit_sayfalari(metin):
    """Nakit akış tablosu sayfaları: faaliyet bölümü başlığı taşıyan sayı yoğun sayfalar + bir sonraki sayfa."""
    metin = re.sub(r'\(\s+', '(', metin)
    ps = metin.split('\f')
    sec = set()
    for no, p in enumerate(ps):
        l = kucuk(p)
        if (re.search(r'(yatırım|işletme|finansman) faaliyetler\w* (kaynaklanan |elde edilen |kullanılan |sağlanan )?nakit', l)
                and len(SAYI.findall(p)) > 40):
            sec.update({no, no + 1})
    return [(no + 1, ps[no]) for no in sorted(sec) if no < len(ps)]

def pdf_ara(sayfalar, v):
    """|v| (TL) sayfalarda TL / bin TL / mn TL biriminde geçiyor mu → (birim, sayfa, satır) | None."""
    if v is None or v == 0: return None
    a = abs(v)
    for no, p in sayfalar:
        for satir in p.split('\n'):
            for tok in SAYI.findall(satir):
                x = _say(tok)
                if x is None or x == 0: continue
                x = abs(x)
                for birim, k, tol in (('TL', 1, 1), ('bin TL', 1e3, 1), ('mn TL', 1e6, 0.051)):
                    if a >= k * 0.5 and abs(x - a / k) <= tol and (k == 1 or x >= 10):
                        return birim, no, ' '.join(satir.split())[:160]
    return None

def pdf_etiket_satirlari(sayfalar, kalem):
    rx = re.compile(PDF_ETIKET[kalem], re.I)
    out = []
    for no, p in sayfalar:
        for satir in p.split('\n'):
            etiket = re.split(r'\s{2,}', satir.strip())[0] if satir.strip() else ''
            if etiket and rx.search(etiket) and len(SAYI.findall(satir)) >= 1:
                nums = [_say(t) for t in SAYI.findall(satir)]
                nums = [n for n in nums if n is not None and abs(n) >= 1000 or (n and abs(n) >= 1 and ',' in satir)]
                if nums: out.append((no, ' '.join(satir.split())[:160]))
    return out

def isle(kod, yil, ay, idx):
    j = json.load(open(f'{OB}/{idx}.json'))
    kayit = []
    if 'hata' in j or not j.get('nakit_akis'):
        return [dict(kod=kod, yil=yil, ay=ay, idx=idx, kalem='*', durum='NAKIT_AKIS_YOK', not_=j.get('hata', ''))]
    roller = j['nakit_akis']
    role = sorted(roller, key=lambda r: (roller[r]['nitelik'] != 'Konsolide', r))[0]
    T = roller[role]
    ci, oi = sutunlar(T['baslik'], yil, ay)
    sayfalar = []
    for e in j.get('ekler', []):
        if e.get('metin') and os.path.exists(f"{OB}/{e['metin']}"):
            metin = open(f"{OB}/{e['metin']}", encoding='utf-8', errors='replace').read()
            sec = nakit_sayfalari(metin)
            # başlık metni bozuk / CFO etiketsiz satırda olabilir: XBRL CFO tutarının geçtiği sayfa ve
            # bir sonraki sayfa da nakit akış sayfası sayılır (yalnız sayfa bulmak için; teyit yine kalem kalem)
            tum = [(no + 1, p) for no, p in enumerate(re.sub(r'\(\s+', '(', metin).split('\f'))]
            var = {no for no, _ in sec}
            for i in (ci, oi):
                b = pdf_ara(tum, deger(T['satirlar'], ELEMAN['CFO'], i))
                if b:
                    for no in (b[1], b[1] + 1):
                        if no not in var and no <= len(tum): sec.append(tum[no - 1]); var.add(no)
            sayfalar += sec
    for kalem in ('CFO', 'MDV+MODV', 'YAGM', 'KIRA'):
        for sut, i in (('cari', ci), ('onceki', oi)):
            v = deger(T['satirlar'], ELEMAN[kalem], i)
            kaynak = 'XBRL'
            if kalem == 'MDV+MODV' and v is None:
                a, b = deger(T['satirlar'], ELEMAN['MDV'], i), deger(T['satirlar'], ELEMAN['MODV'], i)
                if a is not None or b is not None:
                    v, kaynak = (a or 0) + (b or 0), 'XBRL(MDV+MODV alt)'
            bul = pdf_ara(sayfalar, v)
            if kalem == 'MDV+MODV' and v and not bul:
                # PDF'te MDV ve MODV ayrı satırlarsa: alt elemanların her biri ayrı ayrı aranır
                alt = [deger(T['satirlar'], ELEMAN[k], i) for k in ('MDV', 'MODV')]
                alt = [x for x in alt if x]
                if alt and abs(sum(alt) - v) < 2:
                    bb = [pdf_ara(sayfalar, x) for x in alt]
                    if all(bb): bul = (bb[0][0], bb[0][1], ' + '.join(b[2] for b in bb)); kaynak = 'XBRL(alt kalemler PDF)'
            if i is None: durum = 'SUTUN_YOK'
            elif not sayfalar: durum = 'PDF_YOK'
            elif v in (None, 0): durum = 'SIFIR'
            elif bul: durum = 'TEYITLI'
            else: durum = 'PDF_TUTMADI'
            kayit.append(dict(kod=kod, yil=yil, ay=ay, idx=idx, role=role, nitelik=T['nitelik'], kalem=kalem,
                              sutun=sut, deger_tl=v, kaynak=kaynak, durum=durum,
                              pdf_birim=bul[0] if bul else '', pdf_sayfa=bul[1] if bul else '',
                              pdf_satir=bul[2] if bul else '', not_=''))
        if kalem != 'CFO' and sayfalar:
            ek = pdf_etiket_satirlari(sayfalar, kalem)
            sifir = all(k['deger_tl'] in (None, 0) for k in kayit if k['kalem'] == kalem)
            if sifir and ek:
                kayit.append(dict(kod=kod, yil=yil, ay=ay, idx=idx, role=role, nitelik=T['nitelik'], kalem=kalem,
                                  sutun='*', deger_tl=None, kaynak='PDF', durum='PDF_EK_SATIR',
                                  pdf_sayfa=ek[0][0], pdf_satir=' || '.join(s for _, s in ek[:3]), not_=''))
    return kayit

if __name__ == '__main__':
    H = json.load(open('rapor_bildirim_haritasi.json'))
    alan = ['kod', 'yil', 'ay', 'idx', 'role', 'nitelik', 'kalem', 'sutun', 'deger_tl', 'kaynak', 'durum',
            'pdf_birim', 'pdf_sayfa', 'pdf_satir', 'not_']
    w = csv.DictWriter(open('rapor_kalemleri.csv', 'w', newline=''), fieldnames=alan)
    w.writeheader()
    for anahtar, bl in H.items():
        kod, yil, ay = anahtar.split('|'); yil, ay = int(yil), int(ay)
        if not bl: continue
        # aynı dönemde birden çok bildirim: en son yayımlanan (düzeltme) esas alınır
        b = sorted(bl, key=lambda x: _tarih(x['tarih'].split()[0]))[-1]
        if not os.path.exists(f"{OB}/{b['idx']}.json"):
            w.writerow(dict(kod=kod, yil=yil, ay=ay, idx=b['idx'], kalem='*', durum='INDIRILMEDI')); continue
        for k in isle(kod, yil, ay, b['idx']):
            if len(bl) > 1: k['not_'] = (k.get('not_') or '') + f" {len(bl)} bildirim; son kullanıldı"
            w.writerow({a: k.get(a, '') for a in alan})
