# MOD=K6: Kontrol 6 (pozitif alım/kira satırı dışlanan) ve Kontrol 7 ihmal eşiği satırları — GEM v6.2 belge kontrolü
"""NULL satırlar için belge TTM'leri: TTM = YTD_cari + FY_önceki − YTD_önceki (Aralık dönemi: FY_cari).
YTD_önceki, cari raporun karşılaştırmalı sütunundan alınır (V7 köprüsüyle aynı tanım).
Girdi : null_satirlar.csv, rapor_kalemleri.csv  → Çıktı: null_ttm.csv
Kalem statüsü:
  TEYITLI   kullanılan her değer PDF'te bulundu ya da XBRL'de boş/0 ve PDF'te o kaleme ait satır yok
  ELLE      en az bir değer PDF'te bulunamadı / PDF metni yok (taranmış) / PDF'te XBRL dışı satır var
  BELGE_YOK gereken rapor KAP'ta yok ya da tabloda dönem sütunu yok
Tutarlar mn TL; işaret belgedeki gibi (çıkış negatif).
TMS 29: Evo (ve V7) TMS 29 uygulayan şirketlerde her raporu şirketin son raporunun satın alma gücüne taşır.
Belge değeri de aynı esasa çevrilir: değer × F(rapor tarihi) / F(şirketin son rapor tarihi).
F, Evo dönemsel CFO / belge CFO oranından ampirik bulundu (BIOEN, BUCIM, DESA, OZSUB, YEOTK, AFYON, PETKM;
dönem başına şirketler arası sapma < %0,01). TMS 29 uygulamayan raporlar (PDF'te 'satın alma gücü' yok) çevrilmez."""
import csv, collections, json, os
import pandas as pd

# MOD=KOSULLU: aynı hesap KOŞULLU satırlar için (kosullu_satirlar.csv → kosullu_ttm.csv; V7 değerleriyle kıyas)
MOD = os.environ.get('MOD', 'NULL')
# MOD=HOLDING: tüm holding satırları (FCF_HLD temettü okumasının V7'ye karşı doğrulaması; holding_satirlar.csv)
SATIRLAR, CIKTI = {'KOSULLU': ('kosullu_satirlar.csv', 'kosullu_ttm.csv'),
                   'HOLDING': ('holding_satirlar.csv', 'holding_ttm.csv'),
                   'K6': ('k6_satirlar.csv', 'k6_ttm.csv'),
                   'SISTEM': ('sistem_satirlar.csv', 'sistem_ttm.csv')}.get(MOD, ('null_satirlar.csv', 'null_ttm.csv'))

K = pd.read_csv('rapor_kalemleri.csv', dtype={'pdf_sayfa': str})
# KAP sayfası geçici olarak indirilemeyen raporlar (504): aynı bildirimin önceki başarılı çıkarımı kullanılır
if os.path.exists('rapor_kalemleri_yedek.csv'):
    _Y = pd.read_csv('rapor_kalemleri_yedek.csv', dtype={'pdf_sayfa': str})
    _bozuk = set(K[(K.kalem == '*') & K.durum.isin(['NAKIT_AKIS_YOK', 'INDIRILMEDI'])].idx) & set(_Y.idx)
    K = pd.concat([K[~K.idx.isin(_bozuk)], _Y[_Y.idx.isin(_bozuk)]], ignore_index=True)
# KAP erişilemeyen raporlar: Evo belge havuzundaki orijinal PDF'ten XBRL'siz okunan kalemler (cikar_pdf.py)
if os.path.exists('rapor_kalemleri_evo.csv'):
    _E = pd.read_csv('rapor_kalemleri_evo.csv', dtype={'pdf_sayfa': str})
    _tam = {(r.kod, r.yil, r.ay) for r in K.itertuples() if r.kalem != '*'}
    _E = _E[[(r.kod, r.yil, r.ay) not in _tam for r in _E.itertuples()]]
    _ek = {(r.kod, r.yil, r.ay) for r in _E.itertuples()}
    K = pd.concat([K[[(r.kod, r.yil, r.ay) not in _ek for r in K.itertuples()]], _E], ignore_index=True)
# KAP ve Evo'da okunamayan raporlar: şirket sitesindeki orijinal PDF'ten aynı okuyucuyla (site/site_oku.py)
if os.path.exists('rapor_kalemleri_site.csv'):
    _S = pd.read_csv('rapor_kalemleri_site.csv', dtype={'pdf_sayfa': str})
    _cfo = {(r.kod, r.yil, r.ay) for r in K.itertuples() if r.kalem == 'CFO' and pd.notna(r.deger_tl)}
    _S = _S[[(r.kod, r.yil, r.ay) not in _cfo for r in _S.itertuples()]]
    _ek = {(r.kod, r.yil, r.ay) for r in _S.itertuples()}
    K = pd.concat([K[[(r.kod, r.yil, r.ay) not in _ek for r in K.itertuples()]], _S], ignore_index=True)
F = {(2024, 12): 1.5414, (2025, 3): 1.4004, (2025, 6): 1.3211, (2025, 9): 1.2289,
     (2025, 12): 1.1776, (2026, 3): 1.0701, (2026, 6): 1.0}
PER = {'3 Aylık': 3, '6 Aylık': 6, '9 Aylık': 9, 'Yıllık': 12}
son_rapor = {}
for x in json.load(open('kap_fr.json')):
    if x['subject'] != 'Finansal Rapor' or x['ruleType'] not in PER: continue
    t = (x['year'], PER[x['ruleType']])
    if t not in F: continue
    for s in (x['stockCodes'] or '').replace(' ', '').split(','):
        son_rapor[s] = max(son_rapor.get(s, t), t)
H = json.load(open('rapor_bildirim_haritasi.json'))
# TMS 29 şirket düzeyindedir: raporlarından herhangi birinin tablo başlığında 'satın alma gücü esasına göre'
# varsa şirketin tüm raporları TMS 29'ludur (taranmış PDF / farklı başlık ifadesi tek raporu yanlış sınıflamasın)
BASLIK = set(K[K.tms29 == True].kod)
# TMS 29 TL raporlayanlar için zorunlu → varsayılan: uygular. İstisna yalnız iki koşul birlikte varsa:
# (a) hiçbir raporun başlığında 'satın alma gücü esasına göre' yok VE (b) V7/Evo CFO_TTM, belge rakamının
# çevrilmemiş hâliyle örtüşüyor (çevrilmiş hâliyle değil). (BIMAS testi: Evo = PDF × F(rapor), 21/21 kalem.)
_V7 = pd.read_excel('../FCF_V8_aday_K13.xlsx', sheet_name='KARAR', keep_default_na=False, na_values=[''])
_V7 = _V7.set_index(['Kod', 'Dönem'])['CFO_TTM'].dropna()  # TMS 29 oylaması: V7'de CFO_TTM olan tüm satırlar
def _cfo(k, y, m, s):
    r = K[(K.kod == k) & (K.yil == y) & (K.ay == m) & (K.kalem == 'CFO') & (K.sutun == s) & (K.durum == 'TEYITLI')]
    return None if r.empty else r.deger_tl.iloc[0] / 1e6
TMS29_YOK = {}
for kod in sorted(set(K.kod) - BASLIK):
    oy = collections.Counter()
    for (k, d), e in _V7.items():
        if k != kod or abs(e) < 1: continue
        y, m = map(int, d.split('/'))
        a, b, c = (_cfo(k, y, 12, 'cari'), 0, 0) if m == 12 else (_cfo(k, y, m, 'cari'), _cfo(k, y - 1, 12, 'cari'), _cfo(k, y, m, 'onceki'))
        if None in (a, b, c): continue
        fa, fb = (F[(y, 12)], 0) if m == 12 else (F[(y, m)], F[(y - 1, 12)])
        nom, bir = a + b - c, (a - c) * fa + b * fb
        if abs(nom - e) < 0.005 * abs(e) + 0.05 and abs(bir - e) > 0.005 * abs(e) + 0.05: oy['nominal'] += 1
        elif abs(bir - e) < 0.005 * abs(e) + 0.05: oy['cevrilmis'] += 1
    if oy['nominal'] > oy['cevrilmis']: TMS29_YOK[kod] = dict(oy)
TMS29_SIRKET = set(K.kod) - set(TMS29_YOK)
idx = collections.defaultdict(dict)
for r in K.itertuples():
    idx[(r.kod, int(r.yil), int(r.ay))].setdefault(r.kalem, {})[r.sutun] = r

ELLE_KARAR = json.load(open('elle_kararlar.json')) if os.path.exists('elle_kararlar.json') else {}
EVO_METIN = json.load(open('evo_metin_teyit.json')) if os.path.exists('evo_metin_teyit.json') else {}
def _kat(kod, y, m):
    return F[(y, m)] / F[son_rapor.get(kod, (2026, 6))] if kod in TMS29_SIRKET else 1.0

# Aynı raporun ikinci kopyası (Evo havuzu / şirket sitesi PDF'i, XBRL'siz okunmuş): KAP PDF'i okunamadığında ya da
# XBRL tutarı KAP PDF'inde bulunamadığında XBRL değeri bu kopyanın satırıyla karşılaştırılır.
ALT = {}
for _f, _ad in (('rapor_kalemleri_evo.csv', 'Evo PDF'), ('rapor_kalemleri_site.csv', 'Şirket sitesi PDF')):
    if os.path.exists(_f):
        for _r in pd.read_csv(_f).itertuples():
            if _r.durum == 'PDF_OKUNDU' and pd.notna(_r.deger_tl):
                ALT.setdefault((_r.kod, int(_r.yil), int(_r.ay), _r.kalem, _r.sutun), (_r.deger_tl, _ad, str(_r.pdf_satir)[:120]))

def al(kod, y, m, kalem, sut):
    """→ (değer mn TL | None, statü, kanıt)"""
    if not H.get(f'{kod}|{y}|{m}'): return None, 'BELGE_YOK', f'{y}/{m:02d} raporu KAP’ta yok'
    rk = idx.get((kod, y, m))
    if rk is None: return None, 'BELGE_YOK', f'{y}/{m:02d} işlenmedi'
    if '*' in rk and kalem not in rk:
        r0 = next(iter(rk['*'].values()))
        return None, 'BELGE_YOK', f"{y}/{m:02d} {r0.durum} {'' if pd.isna(r0.not_) else r0.not_}"
    d = rk.get(kalem, {})
    r = d.get(sut)
    if r is None or r.durum == 'SUTUN_YOK': return None, 'BELGE_YOK', f'{y}/{m:02d} {sut} sütunu yok'
    v = None if pd.isna(r.deger_tl) else r.deger_tl / 1e6
    kanit = f'KAP {int(r.idx)} {y}/{m:02d} {sut}'
    if str(r.kaynak).startswith('PDF (şirket sitesi)'):
        kanit = f"Şirket sitesi {str(r.kaynak).split(' ', 3)[-1]} {y}/{m:02d} {sut}"
    if v is not None and kod in TMS29_SIRKET:
        a = son_rapor.get(kod, (2026, 6))
        k = F[(y, m)] / F[a]
        v *= k
        kanit += f' · TMS29 ×{k:.4f} ({y}/{m:02d}→{a[0]}/{a[1]:02d})'
    if r.durum == 'TEYITLI': kanit += f' · PDF s.{r.pdf_sayfa} ({r.pdf_birim}): {r.pdf_satir}'
    ek = ELLE_KARAR.get(f'{kod}|{y}|{m}|{kalem}|{sut}') or ELLE_KARAR.get(f'{kod}|{y}|{m}|{kalem}|*')
    if ek:
        if 'deger' in ek:
            return ek['deger'] / 1e6 * _kat(kod, y, m), 'PDF_OKUNDU', kanit + f" · elle karar (PDF): {ek['not']}"
        return (v or 0.0), ek.get('durum', 'TEYITLI'), kanit + f" · elle karar: {ek['not']}"
    alt = ALT.get((kod, y, m, kalem, sut))
    if alt and r.durum in ('PDF_YOK', 'PDF_TUTMADI', 'ETIKET_UYMADI') and not (ELLE_KARAR.get(f'{kod}|{y}|{m}|{kalem}|{sut}') or ELLE_KARAR.get(f'{kod}|{y}|{m}|{kalem}|*')):
        k_ = _kat(kod, y, m); a = alt[0]
        if pd.notna(r.deger_tl) and abs(a - r.deger_tl) <= max(0.001 * abs(r.deger_tl), 2000):
            return r.deger_tl / 1e6 * k_, 'TEYITLI', kanit + f' · XBRL = {alt[1]} satırı (aynı rapor): {alt[2]}'
        # uyuşmazlıkta ikinci kopya kullanılmaz (XBRL'siz okuma alt satır/birim/sütun karıştırabiliyor; ARZUM, CIMSA, TUREX
        # testinde yanlış) → aşağıdaki normal akış (ELLE) sürer, ikinci kopyanın değeri kanıta yazılır
        kanit += f" · {alt[1]} (aynı rapor) satırı farklı: {a / 1e6:.3f} mn ({alt[2][:80]})"
    if r.durum == 'PDF_YOK' and str(int(r.idx)) in EVO_METIN:
        # taranmış PDF: Evo belge havuzundaki OCR metninden elle kontrol (evo_metin_teyit.json)
        t = EVO_METIN[str(int(r.idx))]
        k = t.get(f'{kalem}|{sut}', t.get(f'{kalem}|*'))
        if isinstance(k, dict):
            return k['deger'] / 1e6 * _kat(kod, y, m), 'PDF_OKUNDU', kanit + f" · {t['kaynak']}: {k['not']}"
        if isinstance(k, str) and k.startswith('TEYITLI'):
            return (v or 0.0), 'TEYITLI', kanit + f" · {t['kaynak']}: {k}"
        if isinstance(k, str):
            return v, 'ELLE', kanit + f" · {t['kaynak']}: {k}"
    if r.durum == 'PDF_SATIR_YOK':
        # XBRL'siz PDF: kalem satırı yok → 0. Testte (XBRL'e karşı) YAGM %99, kira %97 doğru; MDV+MODV yalnız %45 → elle
        if kalem in ('YAGM', 'KIRA', 'TEMETTU'): return 0.0, 'PDF_OKUNDU', kanit + ' · Evo PDF: nakit akışta kalem satırı yok → 0'
        return 0.0, 'ELLE', kanit + ' · Evo PDF: MDV+MODV satırı bulunamadı (etiket okunamamış olabilir)'
    if r.durum == 'PDF_ADAY':
        return v, 'ELLE', kanit + f' · Evo PDF: tek CFO adayı, özdeşlik kurulamadı (düşük güven): {r.pdf_satir}'
    if (kod, y, m, kalem) in tekrar:
        return v, 'ELLE', kanit + ' · aynı cari tutar şirketin başka bir dönem raporunda da var (kopya şüphesi)'
    if r.durum in ('TEYITLI', 'SIFIR'): return (v or 0.0), 'TEYITLI', kanit
    if r.durum == 'PDF_OKUNDU':
        return v, 'PDF_OKUNDU', kanit + f' · XBRL standart elemanında yok, PDF satırından okundu ({r.pdf_birim}): {r.pdf_satir}'
    if r.durum == 'PDF_EK_SATIR':
        return None, 'ELLE', kanit + f' · PDF satırı otomatik okunamadı ({r.not_}): {r.pdf_satir}'
    return v, 'ELLE', kanit + f" · {r.durum}{'' if pd.isna(r.not_) else ' ' + str(r.not_)}"

def al_yedek(kod, y, m, kalem, sut):
    """al() + kaynak rapor tarihi. Rapor yoksa aynı dönemin değeri başka raporun sütunundan alınır:
    cari (y, m) → (y+1, m) raporunun karşılaştırmalı sütunu; onceki (y, m) → (y−1, m) raporunun cari sütunu.
    TMS 29 çevrimi kaynak raporun tarihiyle yapılır (karşılaştırmalı sütun o raporun satın alma gücündedir)."""
    r = al(kod, y, m, kalem, sut)
    if r[1] != 'BELGE_YOK': return r + ((y, m),)
    yy, ss = (y + 1, 'onceki') if sut == 'cari' else (y - 1, 'cari')
    if (yy, m) not in F: return r + ((y, m),)
    r2 = al(kod, yy, m, kalem, ss)
    if r2[1] == 'BELGE_YOK': return r + ((y, m),)
    return (r2[0], r2[1], f'{r[2]} → yedek: {y}/{m:02d} değeri {yy}/{m:02d} raporunun {ss} sütunundan · {r2[2]}', (yy, m))

SIRA = {'TEYITLI': 0, 'PDF_OKUNDU': 1, 'IZAHNAME': 1, 'XBRL_ESAS': 1, 'ELLE': 2, 'BELGE_YOK': 3}

# Halka arz izahnamesi (izahname_oku.py): KAP'ta finansal rapor bulunmayan dönemler için. Tüm sütunlar tek
# tablodan ve aynı satın alma gücü tarihinde (sap) → TTM bu tarihte kurulur, sonra × F(sap)/F(son rapor).
import os, ast
IZ = pd.read_csv('izahname_kalemleri.csv') if os.path.exists('izahname_kalemleri.csv') else pd.DataFrame()
EVO_IZ = json.load(open('evo_izahname.json')) if os.path.exists('evo_izahname.json') else {}
def izahname(kod, y, m, kalem):
    if IZ.empty: return None
    g = IZ[(IZ.kod == kod) & (IZ.kalem == kalem)]
    def v(yy, mm):
        r = g[(g.yil == yy) & (g.ay == mm)]
        return None if r.empty else r.iloc[0]
    parca = [v(y, m)] if m == 12 else [v(y, m), v(y - 1, 12), v(y - 1, m)]
    if any(p is None for p in parca) or len({p.idx for p in parca}) > 1: return None
    s = ast.literal_eval(parca[0].sap) if isinstance(parca[0].sap, str) else None
    if s is None and kod in TMS29_SIRKET:  # başlıkta okunamadıysa: tablodaki en son dönem (izahnamenin tarihi)
        g2 = g[g.idx == parca[0].idx]; s = max(zip(g2.yil, g2.ay))
    # Evo kontrolü (CFO, MDV+MODV): Evo bu dönemleri de izahnameden alır; belge × F(sap)/F(son) Evo dönemseliyle
    # %0,5 içinde tutmalı. Tutmazsa ya da Evo'da karşılık yoksa yalnız belge içi özdeşlik sağlanıyorsa kullanılır (yoksa elle).
    # Kontrol tablo düzeyinde: aynı izahname tablosunda bu kalemin Evo'da karşılığı olan tüm dönemleri tutmalı
    # (en az biri); Evo'da karşılığı olmayan dönemler de o zaman kabul edilir.
    onay = ELLE_KARAR.get(f'{kod}|IZAHNAME|{kalem}')  # belgeyle teyit edilip Evo farkı açıklanan tablolar
    # Belge içi özdeşlik (izahname_oku: A+B+C(+etki) = net değişim) bu tablonun ilgili tüm sütunlarında sağlanıyorsa
    # tablo ve sütun eşlemesi doğrulanmıştır → Evo'nun karşılığı yoksa ya da farklı satırı almışsa belge esas alınır.
    cf = IZ[(IZ.kod == kod) & (IZ.kalem == 'CFO') & (IZ.idx == parca[0].idx)]
    ozd = 'ozdeslik' in IZ and all(((cf.yil == p.yil) & (cf.ay == p.ay) & (cf.ozdeslik == True)).any() for p in parca)
    if kalem in EVO_IZ and not onay:
        kat0 = F.get(s, 1) / F[son_rapor.get(kod, (2026, 6))] if kod in TMS29_SIRKET and s else 1
        tut = 0
        for p in g[g.idx == parca[0].idx].itertuples():
            e = EVO_IZ[kalem].get(f'{kod}|{p.yil}|{p.ay}')
            if e is None: continue
            b = p.deger_tl / 1e6 * kat0
            if abs(b - e) > 0.005 * abs(e) + 0.05:
                if ozd: onay = {'not': f'Evo {p.yil}/{p.ay:02d} {e} ≠ belge {b:.1f}; belge A+B+C = net değişim özdeşliğini sağlıyor → belge'}; break
                return 'EVO_TUTMADI', p, e, b
            tut += 1
        if tut == 0 and not onay:
            if not ozd: return 'EVO_TUTMADI', parca[0], None, parca[0].deger_tl / 1e6 * kat0
            onay = {'not': "Evo'da karşılık yok; belge A+B+C = net değişim özdeşliğini sağlıyor"}
    ttm = (parca[0].deger_tl if m == 12 else parca[0].deger_tl + parca[1].deger_tl - parca[2].deger_tl) / 1e6
    kat = 1.0
    if s and kod in TMS29_SIRKET:
        if s not in F: return None
        kat = F[s] / F[son_rapor.get(kod, (2026, 6))]
    kanit = (f"İzahname KAP {int(parca[0].idx)} ({parca[0].ek}, s.{parca[0].sayfa}); sap {s}; ×{kat:.4f}; "
             f"{'okundu' if parca[0].durum == 'OKUNDU' else 'satır yok → 0'}: {'' if pd.isna(parca[0].satir) else parca[0].satir}"
             + (f" ‖ Evo farkı elle incelendi: {onay['not']}" if onay else ''))
    return ttm * kat, [round(p.deger_tl / 1e6, 3) for p in parca], kanit

# aynı şirketin farklı rapor tarihlerinde birebir aynı sıfır dışı cari tutar: belge içi kopya şüphesi
tekrar = set()
c = K[(K.sutun == 'cari') & K.deger_tl.notna() & (K.deger_tl != 0)]
# Aynı yıl içinde birikimli (YTD) çıkış kalemi değişmeden kalabilir (ara dönemde yeni harcama yok) → şüphe değil.
# Şüpheli: tekrar farklı yıllara yayılıyor (ör. FY24 = Q1-25) ya da kalem CFO (birikimli CFO kuruşu kuruşuna sabit kalmaz).
for (kod, kalem, v), g in c.groupby(['kod', 'kalem', 'deger_tl']):
    if g[['yil', 'ay']].drop_duplicates().shape[0] > 1 and (g.yil.nunique() > 1 or kalem == 'CFO'):
        for r in g.itertuples(): tekrar.add((kod, int(r.yil), int(r.ay), kalem))
out = []
for r in csv.DictReader(open(SATIRLAR)):
    kod = r['Kod']; y, m = map(int, r['Dönem'].split('/'))
    satir = {'Kod': kod, 'Tip': r['Tip'], 'Dönem': r['Dönem']}
    genel = 'TEYITLI'
    for kalem in ('CFO', 'MDV+MODV', 'YAGM', 'KIRA') + (('TEMETTU',) if r['Tip'] == 'Holding' else ()):
        if m == 12:
            parca = [(1, al_yedek(kod, y, 12, kalem, 'cari'))]
        else:
            parca = [(1, al_yedek(kod, y, m, kalem, 'cari')), (1, al_yedek(kod, y - 1, 12, kalem, 'cari')),
                     (-1, al_yedek(kod, y, m, kalem, 'onceki'))]
        st = max((p[1][1] for p in parca), key=SIRA.get)
        vals = [p[1][0] for p in parca]
        ttm = None if any(v is None for v in vals) else sum(s * v for (s, _), v in zip(parca, vals))
        if st == 'BELGE_YOK':
            iz = izahname(kod, y, m, kalem)
            if isinstance(iz, tuple) and iz[0] == 'EVO_TUTMADI':
                st = 'ELLE'; p, e, b = iz[1], iz[2], iz[3]
                parca = [(1, (None, st, f"İzahname KAP {int(p.idx)} {p.yil}/{p.ay:02d}: belge (çevrilmiş) {b:.1f} ≠ Evo {e} → elle"))]
                iz = None
            if iz is not None:
                ttm, vals, st = iz[0], iz[1], 'IZAHNAME'
                parca = [(1, (None, st, iz[2]))]
        satir[f'{kalem} TTM'] = None if ttm is None else round(ttm, 3)
        if MOD == 'KOSULLU':
            # Evo bazı şirketlerde her dönemi kendi raporundaki (çevrilmemiş) haliyle saklayıp TTM'i karışık kuruyor;
            # bu farkı ayırt etmek için belge TTM'inin çevrimsiz (nominal) hali de verilir
            don = [p[1][3] if len(p[1]) > 3 else (y, m) for p in parca]
            satir[f'{kalem} TTM nominal'] = (None if st == 'IZAHNAME' or any(v is None for v in vals) else
                                             round(sum(s * v / _kat(kod, *d) for (s, _), v, d in zip(parca, vals, don)), 3))
        satir[f'{kalem} statü'] = st
        satir[f'{kalem} bileşen'] = ' | '.join('—' if v is None else f'{v:.3f}' for v in vals)
        satir[f'{kalem} kanıt'] = ' ‖ '.join(p[1][2] for p in parca)
        if kalem != 'TEMETTU': genel = max(genel, st, key=SIRA.get)  # temettü yalnız FCF_HLD'yi etkiler
    satir['Satır statü'] = genel
    out.append(satir)
D = pd.DataFrame(out)
V7 = pd.read_excel('../FCF_V8_aday_K13.xlsx', sheet_name='KARAR', keep_default_na=False, na_values=[''])
V7 = V7[(V7['Önerilen statü'] == 'KOŞULLU') if MOD == 'KOSULLU' else (V7.Tip == 'Holding') if MOD == 'HOLDING' else (V7.Kod == V7.Kod) if MOD in ('K6', 'SISTEM') else (V7['V7 statü'] == 'NULL')][['Kod', 'Dönem', 'CFO_TTM', 'CAPEX_STD', '|Kira anapara|']]
V7.columns = ['Kod', 'Dönem', 'V7 CFO_TTM (Evo)', 'V7 CAPEX_STD (Evo)', 'V7 |Kira| (Evo)']
D = D.merge(V7, on=['Kod', 'Dönem'], how='left')
_H = pd.read_excel('../girdi/FCF_TTM_2025-03_2026-06_v7_nihai.xlsx', sheet_name='FCF_TTM')
_H = _H[['Kod', 'Dönem', 'FCF türü', 'Alınan temettü (CFO dışı)', 'FCF_HLD (②) · TTM (mn TL)']]
_H.columns = ['Kod', 'Dönem', 'V7 FCF türü', 'V7 Alınan temettü (Evo)', 'V7 FCF_HLD (Evo)']
D = D.merge(_H, on=['Kod', 'Dönem'], how='left')
D['CFO fark (belge−Evo)'] = (D['CFO TTM'] - D['V7 CFO_TTM (Evo)']).round(3)

# V7 formülü (KARAR'daki 2.262 FCF_STD satırının 2.261'inde birebir): FCF_STD = CFO − CAPEX_STD − |Kira|,
# CAPEX_STD = |MDV+MODV| + |YAGM|; TTM'i pozitif çıkan çıkış kalemi formülde 0 alınır (K6).
# FCF_HLD (holding) tanımı KARAR'dan türetilemiyor → holding satırlarında yalnız bileşenler verilir.
def cikis(v):
    return None if pd.isna(v) else (-v if v < 0 else 0.0)
D['CAPEX_STD (belge)'] = [None if pd.isna(a) or pd.isna(b) else round(cikis(a) + cikis(b), 3)
                          for a, b in zip(D['MDV+MODV TTM'], D['YAGM TTM'])]
D['|Kira| (belge)'] = [None if pd.isna(v) else round(cikis(v), 3) for v in D['KIRA TTM']]
D['K6 dışlanan (belge)'] = ['; '.join(f'{k} TTM {D.at[i, k + " TTM"]:+.3f} (pozitif) → 0' for k in ('MDV+MODV', 'YAGM', 'KIRA')
                                      if not pd.isna(D.at[i, k + ' TTM']) and D.at[i, k + ' TTM'] > 0) for i in D.index]
# FCF_HLD (V7 Notlar ②): CFO + Alınan temettüler (yatırım bölümü, CFO dışı) − CAPEX_STD − |Kira|; yalnız holding satırları
D['FCF_HLD (belge)'] = [round(c + max(t, 0) - x - k, 3) if tip == 'Holding' and not any(pd.isna(v) for v in (c, t, x, k)) else None
                        for tip, c, t, x, k in zip(D['Tip'], D['CFO TTM'], D.get('TEMETTU TTM', pd.Series(index=D.index, dtype=float)),
                                                   D['CAPEX_STD (belge)'], D['|Kira| (belge)'])]
D['FCF_STD (belge)'] = [round(c - x - k, 3) if t == 'Standart' and not any(pd.isna(v) for v in (c, x, k)) else None
                        for t, c, x, k in zip(D['Tip'], D['CFO TTM'], D['CAPEX_STD (belge)'], D['|Kira| (belge)'])]
D.to_csv(CIKTI, index=False)
print(D['Satır statü'].value_counts().to_dict())
for k in ('CFO', 'MDV+MODV', 'YAGM', 'KIRA', 'TEMETTU'):
    print(k, D[f'{k} statü'].value_counts().to_dict())
