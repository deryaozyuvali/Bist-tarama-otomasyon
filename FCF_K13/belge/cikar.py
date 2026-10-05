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
    'KIRA': r'kira|kiralama|leasing|lease',
    'MDV+MODV': r'maddi.*(alım|alın|alış|edinim|satın al|ilave|harcama|değişim|yatırım|çıkış)|duran varl\w*\s+(alım|alın|alış|edinim)|purchase of property',
    'YAGM': r'ya\w{0,3}r?ıı?m amaçlı gayrimenkul.*(alım|alın|edinim|ilave|çıkış|harcama|değişim)|yatrıım amaçlı gayrimenkul.*(alım|alın)',
}
# etiket bu kalıplardan birini taşıyorsa kalem satırı sayılmaz (düzeltme, satış, bilanço/dipnot satırları)
PDF_DISLA = {
    'KIRA': r'alacak|gelir|alınan kira|kira geliri|faiz|tfrs|standard|taksonomi|amortisman|kullanım hakkı|ilişkin düzeltme|ile ilgili düzeltme|karşılık',
    'MDV+MODV': r'satış|satın?ılması|elden çıkar|amortisman|itfa|değer düşüklüğü|kazanç|kayıp|avans|düzeltme|yeniden değerleme|gerçeğe uygun',
    'YAGM': r'satış|satım|elden çıkar|gerçeğe uygun|değer artış|kazanç|kayıp|düzeltme|kira',
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
    # PDF metin çıkarma artıkları: harf aralığı ('M addi' → 'Maddi'), bozuk 'ş' ('`')
    s = re.sub(r'\b([A-ZÇĞİÖŞÜ]) (?=[a-zçğıöşü]{2})', r'\1', s)
    return s.replace('İ', 'i').replace('I', 'ı').replace('`', 'ş').lower()

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

def pdf_ara(sayfalar, v, kalem=None):
    """|v| (TL) sayfalarda TL / bin TL / mn TL biriminde geçiyor mu → (birim, sayfa, satır, etiket_uygun) | None.
    kalem verilirse satır etiketi (iki satıra bölünmüşse bir önceki satırla birlikte) kalem kalıbıyla
    kontrol edilir; etiketi uyan eşleşme tercih edilir (ör. yatırım toplamı satırındaki aynı sayı teyit sayılmaz)."""
    if v is None or v == 0: return None
    a = abs(v)
    rx = re.compile(PDF_ETIKET[kalem], re.I) if kalem in PDF_ETIKET else None
    dx = re.compile(PDF_DISLA[kalem], re.I) if kalem in PDF_DISLA else None
    ilk = None
    for no, p in sayfalar:
        onceki = []
        satirlar = p.split('\n')
        for si, satir in enumerate(satirlar):
            etiket = re.split(r'\s{2,}', satir.strip())[0] if satir.strip() else ''
            if re.fullmatch(r'[\d\s().,\-–]*', etiket or ''): etiket = ''  # satır yalnız sayı/dipnot
            bul = None
            for tok in SAYI.findall(satir):
                x = _say(tok)
                if x is None or x == 0: continue
                x = abs(x)
                for birim, k, tol in (('TL', 1, 1), ('bin TL', 1e3, 1), ('mn TL', 1e6, 0.051)):
                    if a >= k * 0.5 and abs(x - a / k) <= tol and (k == 1 or x >= 10):
                        bul = birim; break
                if bul: break
            if bul:
                sonraki = ''
                if si + 1 < len(satirlar) and not re.search(r'\d{1,3}[.,]\d{3}', satirlar[si + 1]):
                    sonraki = satirlar[si + 1].strip()  # etiketin devamı alt satırda olabilir
                tam = kucuk(' '.join(onceki[-2:]) + ' ' + etiket + ' ' + sonraki)
                uygun = rx is None or (bool(rx.search(tam)) and not dx.search(kucuk(etiket)))
                sonuc = (bul, no, ' '.join(satir.split())[:160], uygun)
                if uygun: return sonuc
                ilk = ilk or sonuc
            if re.search(r'\d{1,3}[.,]\d{3}', satir): onceki = []
            elif etiket: onceki.append(etiket)
    return ilk

NET_SATIR = re.compile(r'(maddi|duran varl).{0,80}(alım|alın).{0,20}(ve|/|ile)\s*(satı|elden)|(satış|satım).{0,20}(ve|/)\s*(alım|alın).{0,60}(maddi|duran varl)')

BOS = {'-', '--', '–', '—', '- -', '(-)'}

def _alanlar(satir):
    """Satırı etiket + değer alanlarına böler → (etiket, [değer|0.0], dipnot_var)."""
    parca = [p.strip() for p in re.split(r'\s{2,}', satir.strip()) if p.strip()]
    if not parca: return '', [], False
    etiket, vals = parca[0], []
    for p in parca[1:]:
        if p in BOS: vals.append(0.0); continue
        if re.fullmatch(r'\d{1,2}(?:\s*[,\-\.]\s*\d{1,2})*[a-zA-Z]?', p) and not vals: continue  # dipnot no
        x = _say(p.replace(' ', ''))
        if x is None: return etiket, [], False
        vals.append(x)
    return etiket, vals, True

def pdf_etiket_satirlari(sayfalar, kalem):
    """Kaleme ait PDF satırları → [(sayfa, satır metni, cari, önceki)] (değerler PDF biriminde, işaretli).
    Etiketi bir önceki satırda kalan (iki satıra bölünmüş) kalemler birleştirilir."""
    rx, dx = re.compile(PDF_ETIKET[kalem], re.I), re.compile(PDF_DISLA[kalem], re.I)
    out = []
    for no, p in sayfalar:
        onceki_etiket = ''
        for satir in p.split('\n'):
            etiket, vals, ok = _alanlar(satir)
            if not etiket: onceki_etiket = ''; continue
            if not vals:
                onceki_etiket = etiket if len(etiket) < 140 else ''
                continue
            tam = kucuk((onceki_etiket + ' ' + etiket).strip())
            onceki_etiket = ''
            if not (rx.search(tam) and not dx.search(tam) and len(tam) < 220): continue
            if not re.search(r'[çğışöüÇĞİŞÖÜ]', tam) and re.search(r'\b(cash|lease|payments?|purchase|outflows?)\b', tam):
                continue  # iki dilli raporun İngilizce tekrarı
            if 'giriş' in tam and 'çıkış' not in tam: continue  # yalnız giriş satırı (yeni kiralama/satış)
            sorun = []
            if len(vals) != 2: sorun.append(f'{len(vals)} sütun')
            if 'çıkış' in tam and 'giriş' not in tam and any(v > 0 for v in vals[-2:]): sorun.append('çıkış satırında pozitif (işaret?)')
            out.append((no, ' '.join(satir.split())[:160], vals[-2] if len(vals) >= 2 else None,
                        vals[-1] if vals else None, '; '.join(sorun)))
    # toplam + alt satır birlikte yakalandıysa: değerleri diğerlerinin toplamına eşit satır tek başına alınır
    if len(out) >= 2:
        for t in out:
            diger = [o for o in out if o is not t]
            if all(o[2] is not None and o[3] is not None for o in out) and \
                    abs(sum(o[2] for o in diger) - t[2]) <= 2 and abs(sum(o[3] for o in diger) - t[3]) <= 2:
                return [t]
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
    # XBRL tutarları KAP başlığındaki 'Sunum Para Birimi' cinsindendir (TL / 1.000 TL / 1.000.000 TL)
    xk = {'TL': 1, '1.000 TL': 1e3, '1.000.000 TL': 1e6}.get(T.get('birim', 'TL'))
    if xk is None:
        return [dict(kod=kod, yil=yil, ay=ay, idx=idx, kalem='*', durum='BIRIM_BILINMIYOR', not_=T.get('birim'))]
    sayfalar = []
    tms29 = None
    for e in j.get('ekler', []):
        if e.get('metin') and os.path.exists(f"{OB}/{e['metin']}"):
            metin = open(f"{OB}/{e['metin']}", encoding='utf-8', errors='replace').read()
            if len(metin) > 5000:
                km = ' '.join(kucuk(metin[:400000]).split())
                # yalnız tablo başlığındaki ifade: '… tarihi itibarıyla satın alma gücü esasına göre ifade edilmiştir'
                # ('TMS 29' / 'satın alma gücünü kaybeder' gibi genel metinler — KGK duyurusu paragrafı — sayılmaz)
                tms29 = bool(tms29) or bool(re.search(
                    r'satın ?alma gücü esas|itibar[ıi]y?la satın ?alma gücü', km[:150000]))
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
            bul = pdf_ara(sayfalar, v, kalem)
            if kalem == 'MDV+MODV' and v and not (bul and bul[3]):
                # PDF'te MDV ve MODV ayrı satırlarsa: alt elemanların her biri ayrı ayrı aranır
                alt = [deger(T['satirlar'], ELEMAN[k], i) for k in ('MDV', 'MODV')]
                alt = [x for x in alt if x]
                if alt and abs(sum(alt) - v) < 2:
                    bb = [pdf_ara(sayfalar, x, kalem) for x in alt]
                    if all(bb) and all(b[3] for b in bb):
                        bul = (bb[0][0], bb[0][1], ' + '.join(b[2] for b in bb), True); kaynak = 'XBRL(alt kalemler PDF)'
            if i is None: durum = 'SUTUN_YOK'
            elif not sayfalar: durum = 'PDF_YOK'
            elif v in (None, 0): durum = 'SIFIR'
            elif bul and bul[3]: durum = 'TEYITLI'
            elif bul: durum = 'ETIKET_UYMADI'
            else: durum = 'PDF_TUTMADI'
            kayit.append(dict(kod=kod, yil=yil, ay=ay, idx=idx, role=role, nitelik=T['nitelik'], kalem=kalem,
                              sutun=sut, deger_tl=None if v is None else v * xk, kaynak=kaynak, durum=durum,
                              pdf_birim=bul[0] if bul else '', pdf_sayfa=bul[1] if bul else '',
                              pdf_satir=bul[2] if bul else '', not_=''))
        if kalem != 'CFO' and sayfalar:
            ek = pdf_etiket_satirlari(sayfalar, kalem)
            sifir = all(k['deger_tl'] in (None, 0) for k in kayit if k['kalem'] == kalem)
            if sifir and ek:
                # XBRL bu kalemi standart elemana bağlamamış ama PDF'te satır var: tutar PDF'ten okunur.
                # Birim aynı raporun PDF'te teyitli CFO satırından; bilinmiyorsa okunmaz (elle).
                carp = {'TL': 1, 'bin TL': 1e3, 'mn TL': 1e6}.get(birim)
                satirlar = ' || '.join(e[1] for e in ek[:3])
                sorun = '; '.join(e[4] for e in ek if e[4]) or ('birim belirlenemedi' if carp is None else '')
                for k in [k for k in kayit if k['kalem'] == kalem]: kayit.remove(k)
                for n, (sut, i) in enumerate((('cari', ci), ('onceki', oi))):
                    if sorun or i is None:
                        kayit.append(dict(kod=kod, yil=yil, ay=ay, idx=idx, role=role, nitelik=T['nitelik'],
                                          kalem=kalem, sutun=sut, deger_tl=None, kaynak='PDF', durum='PDF_EK_SATIR',
                                          pdf_sayfa=ek[0][0], pdf_satir=satirlar, not_=sorun))
                        continue
                    v = sum(e[2 + n] for e in ek) * carp * xk
                    kayit.append(dict(kod=kod, yil=yil, ay=ay, idx=idx, role=role, nitelik=T['nitelik'],
                                      kalem=kalem, sutun=sut, deger_tl=v, kaynak=f'PDF ({len(ek)} satır)',
                                      durum='PDF_OKUNDU', pdf_birim=birim, pdf_sayfa=ek[0][0],
                                      pdf_satir=satirlar, not_='XBRL standart elemanında yok'))
        if kalem == 'MDV+MODV' and sayfalar:
            net = [' '.join(l.split())[:140] for _, p in sayfalar for l in p.split('\n') if NET_SATIR.search(kucuk(l))]
            if net:
                for k in kayit:
                    if k['kalem'] == kalem and k['durum'] in ('TEYITLI', 'SIFIR'):
                        k['durum'] = 'NET_SATIR'; k['not_'] = 'PDF’te alım+satış tek net satır: ' + net[0]
        if kalem == 'CFO':
            b = [k for k in kayit if k['kalem'] == 'CFO' and k['durum'] == 'TEYITLI']
            birim = b[0]['pdf_birim'] if b else None
    # XBRL CFO PDF'te bulunamadıysa (şirketin XBRL girişi imzalı rapordan farklı): CFO PDF satırından okunur.
    # Birim, aynı raporda PDF'te teyitli herhangi bir kalemden; CFO satırı tek ve iki sütunluysa alınır.
    cfo = [k for k in kayit if k['kalem'] == 'CFO']
    if sayfalar and cfo and all(k['durum'] == 'PDF_TUTMADI' for k in cfo):
        bb = [k['pdf_birim'] for k in kayit if k['durum'] == 'TEYITLI' and k.get('pdf_birim')]
        carp = {'TL': 1, 'bin TL': 1e3, 'mn TL': 1e6}.get(bb[0]) if bb else None
        rx = re.compile(r'(işletme|esas) faaliyetler\w*\s+(elde edilen |sağlanan |kaynaklanan |kullanılan )?(net )?nakit ak')
        aday = []
        for no, p in sayfalar:
            for satir in p.split('\n'):
                et, vals, ok = _alanlar(satir)
                if et and len(vals) == 2 and rx.search(kucuk(et)) and 'sermaye' not in kucuk(et):
                    aday.append((no, ' '.join(satir.split())[:160], vals))
        degerler = {tuple(a[2]) for a in aday}
        for n, k in enumerate(cfo):
            if carp and len(degerler) == 1:
                # özdeşlik: işletme + yatırım + finansman = nakitteki net değişim (aynı sayfalardan)
                def tek(desen):
                    r = []
                    for _, p in sayfalar:
                        for satir in p.split('\n'):
                            et, vals, _ = _alanlar(satir)
                            if et and len(vals) == 2 and re.search(desen, kucuk(et)): r.append(vals)
                    return r[0] if r else None
                yat = tek(r'yatırım faaliyetler\w*\s+.{0,25}nakit')
                fin = tek(r'finansman faaliyetler\w*\s+.{0,25}nakit')
                net = tek(r'nakit ve nakit benzerlerindeki.{0,25}(net )?(artış|azalış|değişim)(?!.*(kur|enflasyon|etkisi))')
                j = 0 if k['sutun'] == 'cari' else 1
                if yat and fin and net and abs(aday[0][2][j] + yat[j] + fin[j] - net[j]) <= 2:
                    k['not_'] = 'özdeşlik A+B+C=D tuttu; '
                else:
                    k['not_'] = 'özdeşlik kurulamadı; '
                    if yat and fin and net: k['durum'] = 'PDF_TUTMADI'; continue
                v = aday[0][2][j] * carp * xk
                k['not_'] += f"XBRL {k['deger_tl'] / 1e6:.3f} mn ≠ PDF; PDF satırı kullanıldı"
                k.update(deger_tl=v, durum='PDF_OKUNDU', kaynak='PDF (CFO satırı)', pdf_birim=bb[0],
                         pdf_sayfa=aday[0][0], pdf_satir=aday[0][1])
            elif len(degerler) > 1:
                k['not_'] = 'PDF’te birden çok farklı CFO satırı: ' + ' || '.join(a[1] for a in aday[:3])
    for k in kayit: k['tms29'] = tms29
    return kayit

if __name__ == '__main__':
    # kullanım: python3 cikar.py [harita.json] [çıktı.csv]
    H = json.load(open(sys.argv[1] if len(sys.argv) > 1 else 'rapor_bildirim_haritasi.json'))
    alan = ['kod', 'yil', 'ay', 'idx', 'role', 'nitelik', 'kalem', 'sutun', 'deger_tl', 'kaynak', 'durum',
            'pdf_birim', 'pdf_sayfa', 'pdf_satir', 'tms29', 'not_']
    w = csv.DictWriter(open(sys.argv[2] if len(sys.argv) > 2 else 'rapor_kalemleri.csv', 'w', newline=''), fieldnames=alan)
    w.writeheader()
    for anahtar, bl in H.items():
        kod, yil, ay = anahtar.split('|'); yil, ay = int(yil), int(ay)
        if not bl: continue
        # aynı dönemde birden çok bildirim: dönem sütunu takvim dönemine uyanların en son yayımlananı
        # (düzeltme) esas alınır; hiçbiri uymuyorsa şirketin hesap yılı takvim dışıdır
        adaylar = sorted(bl, key=lambda x: _tarih(x['tarih'].split()[0]), reverse=True)
        b = None
        for a in adaylar:
            if not os.path.exists(f"{OB}/{a['idx']}.json"): continue
            j = json.load(open(f"{OB}/{a['idx']}.json"))
            if any(sutunlar(v['baslik'], yil, ay)[0] is not None for v in j.get('nakit_akis', {}).values()):
                b = a; break
        if b is None:
            a = adaylar[0]
            j = json.load(open(f"{OB}/{a['idx']}.json")) if os.path.exists(f"{OB}/{a['idx']}.json") else {}
            if j.get('nakit_akis'):
                bas = next(iter(j['nakit_akis'].values()))['baslik']
                w.writerow(dict(kod=kod, yil=yil, ay=ay, idx=a['idx'], kalem='*', durum='MALI_YIL',
                                not_='takvim dönemine uyan sütun yok: ' + ' / '.join(bas[:2])))
                continue
            b = a
        if not os.path.exists(f"{OB}/{b['idx']}.json"):
            w.writerow(dict(kod=kod, yil=yil, ay=ay, idx=b['idx'], kalem='*', durum='INDIRILMEDI')); continue
        for k in isle(kod, yil, ay, b['idx']):
            if len(bl) > 1: k['not_'] = (k.get('not_') or '') + f" {len(bl)} bildirim; son kullanıldı"
            w.writerow({a: k.get(a, '') for a in alan})
