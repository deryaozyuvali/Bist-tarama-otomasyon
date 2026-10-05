"""XBRL'siz (yalnız PDF) çıkarım: KAP erişilemediğinde Evo belge havuzundaki orijinal PDF'ler (storage.fintables.com,
KAP ekinin aynısı) indirilip nakit akış tablosundan dört kalem okunur.
Girdi : evo_pdf/<yıl>_<ay>.txt (satır: KOD|<kap-attachments altındaki dosya yolu>), rapor_bildirim_haritasi.json
Çıktı : rapor_kalemleri_evo.csv (rapor_kalemleri.csv ile aynı alanlar; idx = haritadaki son bildirim)
Kurallar:
  CFO      : aday satırlar (işletme faaliyetlerinden … nakit) arasından sütun başına A+B+C(+kur/enflasyon etkisi) =
             nakitteki net değişim özdeşliğini sağlayan tek değer → PDF_OKUNDU. Özdeşlik satırları okunamıyor ve
             tek aday varsa → PDF_ADAY (düşük güven). Diğer durumlar PDF_TUTMADI (elle). (net − B − C türetmesi
             XBRL'e karşı testte 159'da 155 yanlış çıktığı için kullanılmaz.)
  diğerleri: etiketli satır(lar) (cikar.pdf_etiket_satirlari) → PDF_OKUNDU; satır yoksa 0 → PDF_SATIR_YOK;
             sütun/işaret belirsizliği → PDF_EK_SATIR (elle); alım+satış tek net satır → NET_SATIR.
  birim    : nakit akış sayfasının başlığından (TL / bin TL / milyon TL)."""
import csv, glob, json, os, re, subprocess, sys, tempfile
from cikar import _alanlar, kucuk, nakit_sayfalari, pdf_etiket_satirlari, NET_SATIR

OB = os.environ.get('ONBELLEK', 'onbellek')
TABAN = 'https://storage.fintables.com/media/uploads/kap-attachments/'
TMS29 = re.compile(r'satın ?alma gücü esas|itibar[ıi]y?la satın ?alma gücü|20\d\d tarihindeki satın ?alma gücü cinsinden')
CFO = re.compile(r'(işletme|esas) faaliyetler\w*\s+(elde edilen |sağlanan |kaynaklanan |kullanılan )?(net )?nakit ak'
                 r'|(işletme|esas) faaliyetler\w*\s+.{0,35}net nakit'
                 r'|^a[.)]?\s*(işletme|esas|şirket) faaliyet\w*.{0,40}nakit|^faaliyetlerden (elde edilen|kaynaklanan) (net )?nakit')

def indir(kod, y, m, yol):
    hedef = f'{OB}/E_{kod}_{y}_{m}_0.txt'
    if os.path.exists(hedef) and os.path.getsize(hedef) > 0: return hedef
    with tempfile.TemporaryDirectory() as td:
        p = f'{td}/r.pdf'
        r = subprocess.run(['curl', '-sS', '-L', '--max-time', '180', '-o', p, '-w', '%{http_code}', TABAN + yol],
                           capture_output=True, text=True)
        if r.stdout.strip() != '200' or not os.path.exists(p) or os.path.getsize(p) < 1000: return None
        subprocess.run(['pdftotext', '-layout', p, hedef])
    return hedef

def birim(sayfa):
    t = kucuk(' '.join(sayfa.split('\n')[:25]))
    if re.search(r'milyon\s*(türk lira|tl)|tl\s*\(?milyon', t): return 'mn TL', 1e6
    if re.search(r'bin\s*(türk lira|tl)|tl\s*[’\']?\s*\(?bin|\(000\)|000 tl', t): return 'bin TL', 1e3
    return 'TL', 1.0

def satirlar(sayfalar, desen, n=2):
    r = []
    for no, p in sayfalar:
        onceki = ''
        ls = p.split('\n')
        for si, satir in enumerate(ls):
            et, vals, _ = _alanlar(satir)
            if not et: onceki = ''; continue
            if re.fullmatch(r'\(?[\d.,]+\)?|[-–]+|(?i:dipnot|not)', et):
                # etiketsiz değer satırı: etiket üstte başlayıp altta bitiyor
                _, vals, _ = _alanlar('X  ' + satir.strip())
                et = ls[si + 1].strip() if si + 1 < len(ls) and not _alanlar(ls[si + 1])[1] else ''
            elif not vals: onceki = et if len(et) < 140 else ''; continue
            tam = kucuk((onceki + ' ' + et).strip()); onceki = ''
            if len(vals) == n and re.search(desen, tam) and 'sermaye' not in tam:
                r.append((no, ' '.join(satir.split())[:160], vals))
    return r

def isle(kod, y, m, idx, metin_yolu):
    kayit = []
    def ekle(kalem, sut, v, durum, satir='', not_='', sayfa=''):
        kayit.append(dict(kod=kod, yil=y, ay=m, idx=idx, role='PDF', nitelik='', kalem=kalem, sutun=sut,
                          deger_tl=v, kaynak='PDF (Evo havuzu)', durum=durum, pdf_birim=b_ad, pdf_sayfa=sayfa,
                          pdf_satir=satir, tms29=tms, not_=not_))
    metin = open(metin_yolu, encoding='utf-8', errors='replace').read()
    b_ad = ''
    if len(metin) < 5000:
        tms = None
        return [dict(kod=kod, yil=y, ay=m, idx=idx, kalem='*', durum='PDF_METIN_YOK', not_='taranmış PDF (metin yok)')]
    km = ' '.join(kucuk(metin[:400000]).split())
    tms = bool(TMS29.search(km[:150000]))
    sayfalar = nakit_sayfalari(metin)
    if not sayfalar:
        return [dict(kod=kod, yil=y, ay=m, idx=idx, kalem='*', durum='NAKIT_AKIS_YOK', not_='PDF’te nakit akış sayfası bulunamadı')]
    b_ad, carp = birim(sayfalar[0][1])
    # CFO: özdeşlik
    aday = satirlar(sayfalar, CFO)
    yat = satirlar(sayfalar, r'^b?[.)]?\s*yatırım faaliyet\w*.{0,40}nakit')
    fin = satirlar(sayfalar, r'^c?[.)]?\s*finansman faaliyet\w*.{0,40}nakit')
    net = satirlar(sayfalar, r'nakit benzerlerindeki.{0,40}(artış|azalış|değişim)|^net (artış|azalış)')
    etki = [e for e in satirlar(sayfalar, r'etki') if re.search(r'enflasyon|yabancı para|çevrim|kur', e[1].lower())]
    # net değişim satırı okunamadıysa: dönem sonu − dönem başı nakit (etki satırları tutar() içinde ayrıca denenir)
    bas = satirlar(sayfalar, r'dönem başı.{0,40}nakit')
    son = satirlar(sayfalar, r'dönem sonu.{0,40}nakit')
    if bas and son:
        net = net + [(son[0][0], 'dönem sonu − başı', [son[0][2][i] - bas[0][2][i] for i in (0, 1)])]
    for j, sut in enumerate(('cari', 'onceki')):
        def tutar(t):
            return any(abs(t - n[2][j]) <= 2 or any(abs(t + e[2][j] - n[2][j]) <= 2 for e in etki)
                       or abs(t + sum(e[2][j] for e in etki) - n[2][j]) <= 2 for n in net)
        # B ya da C toplam satırı okunamadıysa 0 kabul edilip denenir (bölüm boş/tek satırlı tablolar)
        sifir = [(0, '', [0.0, 0.0])]
        gecerli = {a[2][j]: a for a in aday for y_ in (yat[:3] or sifir) for f_ in (fin[:3] or sifir)
                   if tutar(a[2][j] + y_[2][j] + f_[2][j])}
        if len(gecerli) == 1:
            a = next(iter(gecerli.values()))
            ekle('CFO', sut, a[2][j] * carp, 'PDF_OKUNDU', a[1], 'özdeşlik A+B+C(+etki)=net değişim tuttu', a[0])
        elif not gecerli and len({a[2][j] for a in aday}) == 1 and not (yat and fin and net):
            # özdeşlik kurulamıyor (B/C/net satırı okunamadı) ve tek CFO adayı var: düşük güven
            a = aday[0]
            ekle('CFO', sut, a[2][j] * carp, 'PDF_ADAY', a[1], 'tek CFO adayı; B/C/net satırları okunamadığından özdeşlik kontrol edilemedi', a[0])
        else:
            ekle('CFO', sut, None, 'PDF_TUTMADI', ' || '.join(a[1] for a in aday[:3]),
                 'özdeşliği sağlayan tek CFO adayı yok' + (f' ({len(gecerli)} aday)' if gecerli else ''))
    for kalem in ('MDV+MODV', 'YAGM', 'KIRA'):
        ek = pdf_etiket_satirlari(sayfalar, kalem)
        if kalem == 'MDV+MODV':
            nt = [' '.join(l.split())[:140] for _, p in sayfalar for l in p.split('\n') if NET_SATIR.search(kucuk(l))]
        else: nt = []
        for n, sut in enumerate(('cari', 'onceki')):
            if not ek:
                ekle(kalem, sut, 0.0, 'PDF_SATIR_YOK', '', 'nakit akış tablosunda kalem satırı yok → 0')
                continue
            sorun = '; '.join(e[4] for e in ek if e[4])
            satir = ' || '.join(e[1] for e in ek[:3])
            if sorun:
                ekle(kalem, sut, None, 'PDF_EK_SATIR', satir, sorun, ek[0][0]); continue
            v = sum(e[2 + n] for e in ek) * carp
            if nt: ekle(kalem, sut, v, 'NET_SATIR', satir, 'alım+satış tek net satır: ' + nt[0], ek[0][0])
            else: ekle(kalem, sut, v, 'PDF_OKUNDU', satir, f'{len(ek)} satır', ek[0][0])
    return kayit

if __name__ == '__main__':
    H = json.load(open('rapor_bildirim_haritasi.json'))
    alan = ['kod', 'yil', 'ay', 'idx', 'role', 'nitelik', 'kalem', 'sutun', 'deger_tl', 'kaynak', 'durum',
            'pdf_birim', 'pdf_sayfa', 'pdf_satir', 'tms29', 'not_']
    w = csv.DictWriter(open('rapor_kalemleri_evo.csv', 'w', newline=''), fieldnames=alan); w.writeheader()
    for f in sorted(glob.glob('evo_pdf/*.txt')):
        y, m = map(int, os.path.basename(f)[:-4].split('_'))
        for satir in open(f):
            if '|' not in satir: continue
            kod, yol = satir.strip().split('|', 1)
            bl = H.get(f'{kod}|{y}|{m}') or [{'idx': 0}]
            idx = max(e['idx'] for e in bl)
            hedef = indir(kod, y, m, yol)
            if not hedef:
                w.writerow(dict(kod=kod, yil=y, ay=m, idx=idx, kalem='*', durum='INDIRILMEDI', not_='Evo PDF indirilemedi')); continue
            for r in isle(kod, y, m, idx, hedef): w.writerow({k: r.get(k) for k in alan})
            print(kod, y, m, 'tamam', file=sys.stderr)
