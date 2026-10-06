"""Kontrol 9 artık sınıflandırması (GEM v6.2 Kontrol 9): V7'de yatırım bölümü artığı nedeniyle KOŞULLU olan satırlar.
Her satırın TTM penceresindeki raporların (A = dönem YTD, B = önceki FY, C = A raporunun karşılaştırmalı sütunu)
yatırım bölümü KAP XBRL'inden kalem kalem okunur ve GEM listesine göre sınıflanır:
  CAPEX      → CAPEX_STD'ye giren isimli satırlar (MDV+MODV alımı, YAGM alımı)
  ✗ kapsam dışı isimli satırlar (GEM 'FCF'ye girmeyen kalemler'): duran varlık satışı, menkul kıymet/fon/türev,
             alınan faiz, alınan temettü (FCF_HLD'de ayrıca), M&A, verilen avans ve borçlar, TMS 29 enflasyon etkisi
  ARTIK      → XBRL 'Diğer Nakit Girişleri (Çıkışları)' ve niteliği belirsiz satırlar.
'Diğer' satırı imzalı PDF'in yatırım bölümünden ayrıştırılır: PDF'te XBRL'deki isimli satırlarla eşleşmeyen satırların
toplamı 'Diğer'e (cari ve önceki sütunda) eşitse, 'Diğer' bu PDF satırlarından oluşur ve her biri etiketinden sınıflanır.
Sınıflanamayan kalan |TTM| ≤ Kontrol 9 eşiği → artık sınıflandı, satır KOŞULLU'dan çıkar; aksi halde elle bakılır.
Girdi : V7 (Kontrol 9 satırları), ONBELLEK/<idx>.json + PDF metinleri, ../FCF_MASTER.xlsx (CFO_TTM, CAPEX_STD)
Çıktı : k9_sonuc.csv (satır bazında), k9_rapor.csv (rapor bazında satır dökümü)"""
import collections, itertools, json, os, re, sys
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cikar import nakit_sayfalari as _ns, yatirim_bolumu, _alanlar, kucuk, sutunlar, SAYI

OB = os.environ.get('ONBELLEK', 'onbellek')

def nakit_sayfalari(metin):
    """cikar.nakit_sayfalari + daha geniş başlık kalıbı ('YATIRIM FAALİYETLERİNDEN ELDE EDİLEN / (KULLANILAN) NAKİT')."""
    s = _ns(metin)
    if s: return s
    metin = re.sub(r'\(\s+', '(', metin); ps = metin.split('\f'); sec = set()
    for no, p in enumerate(ps):
        l = kucuk(' '.join(p.split()))
        if re.search(r'yatırım faaliyetler\w*.{0,60}nakit', l) and re.search(r'finansman faaliyetler\w*.{0,60}nakit|işletme faaliyetler\w*.{0,60}nakit', l) and len(SAYI.findall(p)) > 40:
            sec.update({no, no + 1})
    return [(no + 1, ps[no]) for no in sorted(sec) if no < len(ps)]
_src = open('ttm.py').read()
exec(_src[:_src.index('idx = collections.defaultdict')])  # K, F, son_rapor, H, TMS29_SIRKET

# 2024 ara dönem katsayıları (yalnız C yedeği için): TÜFE oranı ile F(2024/12)'den türetildi
# (TÜFE 2003=100: Mar24 2139,47 · Haz24 2319,29 · Eyl24 2526,16 · Ara24 2684,55)
F.update({(2024, 3): 1.5414 * 2684.55 / 2139.47, (2024, 6): 1.5414 * 2684.55 / 2319.29, (2024, 9): 1.5414 * 2684.55 / 2526.16})

def kat(kod, y, m):
    return F[(y, m)] / F[son_rapor.get(kod, (2026, 6))] if kod in TMS29_SIRKET else 1.0

S = 'ClassifiedAsInvestingActivities'
SINIF = {
    'kap-fr_PurchaseOfPropertyPlantEquipmentAndIntangibleAssets' + S: 'CAPEX',
    'ifrs-full_PurchaseOfPropertyPlantAndEquipment' + S: 'CAPEX',
    'ifrs-full_PurchaseOfIntangibleAssets' + S: 'CAPEX',
    'kap-fr_CashOutflowsFromAcquitionOfInvestmentsProperty' + S: 'CAPEX',
    'kap-fr_ProceedsFromSalesOfPropertyPlantEquipmentAndIntangibleAssets' + S: 'SATIS',
    'ifrs-full_ProceedsFromSalesOfPropertyPlantAndEquipment' + S: 'SATIS',
    'ifrs-full_ProceedsFromSalesOfIntangibleAssets' + S: 'SATIS',
    'kap-fr_CashInflowsFromSaleOfInvestmentProperty' + S: 'SATIS',
    'kap-fr_CashInflowsFromSalesOfAssetsHeldForSale' + S: 'SATIS',
    'ifrs-full_ProceedsFromOtherLongtermAssets' + S: 'SATIS',
    'ifrs-full_OtherCashPaymentsToAcquireEquityOrDebtInstrumentsOfOtherEntities' + S: 'FINANSAL',
    'ifrs-full_OtherCashReceiptsFromSalesOfEquityOrDebtInstrumentsOfOtherEntities' + S: 'FINANSAL',
    'kap-fr_CashInflowsFromParticipationProfitSharesOrOtherFinancialInstruments' + S: 'FINANSAL',
    'kap-fr_CashOutflowsFromParticipationProfitSharesOrOtherFinancialInstruments' + S: 'FINANSAL',
    'ifrs-full_CashReceiptsFromFutureContractsForwardContractsOptionContractsAndSwapContracts' + S: 'FINANSAL',
    'ifrs-full_CashPaymentsForFutureContractsForwardContractsOptionContractsAndSwapContracts' + S: 'FINANSAL',
    'ifrs-full_InterestReceived' + S: 'FAIZ',
    'ifrs-full_DividendsReceived' + S: 'TEMETTU',
    'ifrs-full_CashFlowsUsedInObtainingControlOfSubsidiariesOrOtherBusinesses' + S: 'MA',
    'ifrs-full_CashFlowsFromLosingControlOfSubsidiariesOrOtherBusinesses' + S: 'MA',
    'kap-fr_CashOutflowsArisingFromPurchaseOfSharesOrCapitalIncreaseOfAssociatesAndOrJointVentures' + S: 'MA',
    'kap-fr_CashInflowsArisingFromShareSalesOrCapitalDecreaseOfAssociatesAndOrJointVentures' + S: 'MA',
    'kap-fr_CashOutflowsFromPurchaseOfAdditionalSharesOfSubsidiaries' + S: 'MA',
    'kap-fr_CashOutflowsArisingFromCapitalAdvancePaymentsToAssociatesAndOrJointVentures' + S: 'MA',
    'kap-fr_CashInflowsFromSaleOfSharesOfSsubsidiariesThatDoesntCauseLoseOfControl' + S: 'MA',
    'ifrs-full_CashAdvancesAndLoansMadeToOtherParties' + S: 'AVANS',
    'kap-fr_OtherCashAdvancesAndLoansMadeToOtherParties' + S: 'AVANS',
    'kap-fr_CashAdvancesAndLoansMadeToRelatedParties' + S: 'AVANS',
    'ifrs-full_CashReceiptsFromRepaymentOfAdvancesAndLoansMadeToOtherParties' + S: 'AVANS',
    'kap-fr_PaybacksFromOtherCashAdvancesAndLoansMadeToOtherParties' + S: 'AVANS',
    'kap-fr_PaybacksFromCashAdvancesAndLoansMadeToRelatedParties' + S: 'AVANS',
    'kap-fr_InflationEffectOnInvestingActivities': 'ENFLASYON',
    'ifrs-full_OtherInflowsOutflowsOfCash' + S: 'DIGER',
}
AD = {'CAPEX': 'capex (CAPEX_STD içinde)', 'SATIS': 'duran varlık satışı ✗', 'FINANSAL': 'menkul kıymet/fon/türev ✗',
      'FAIZ': 'alınan faiz ✗', 'TEMETTU': 'alınan temettü (FCF_HLD’de)', 'MA': 'iştirak/bağlı ortaklık (M&A) ✗',
      'AVANS': 'verilen avans/borç ✗', 'ENFLASYON': 'TMS 29 enflasyon etkisi ✗', 'TESVIK': 'devlet teşviki/hibe ✗',
      'KUR': 'kur farkı (nakit dışı sunum) ✗', 'FINANSMAN': 'geri alınan paylar (finansman niteliğinde) ✗', 'ARTIK': 'SINIFLANMADI', 'KIRA_GELIRI': 'yatırım amaçlı gayrimenkul kira geliri ✗', 'CAPEX_DIPNOT': 'capex (dipnot: Diğer içindeki yatırım harcaması → CAPEX’e eklendi)'}
KAPSAM_DISI = {'KIRA_GELIRI', 'FINANSMAN', 'SATIS', 'FINANSAL', 'FAIZ', 'TEMETTU', 'MA', 'AVANS', 'ENFLASYON', 'TESVIK', 'KUR'}

# PDF etiketinden sınıf ('Diğer'in içeriği); sıra önemlidir. Duran varlık ALIMI gibi capex niteliği taşıyan
# etiketler ARTIK kalır (otomatik capex'e eklenmez, otomatik göz ardı edilmez — GEM Kontrol 9).
ETIKET = [
    (r'yatırım harcama|yapılmakta olan yatırım|sabit kıymet alım|maddi duran varlık alım|duran varlık alım', 'CAPEX_DIPNOT'),
    (r'enflasyon|parasal (kazanç|kayıp|pozisyon)|satın alma gücü', 'ENFLASYON'),
    (r'kur fark|yabancı para çevrim|çevrim fark', 'KUR'),
    (r'faiz|katılım (kar|kâr) pay', 'FAIZ'),
    (r'temettü|kar pay|kâr pay', 'TEMETTU'),
    (r'teşvik|hibe', 'TESVIK'),
    (r'kira gelir|gayrimenkul\w*.{0,40}kira', 'KIRA_GELIRI'),
    (r'işletme birleşme|iştirak|bağlı ortaklık|iş ortaklı|müşterek|özkaynak yöntem|şirket (alım|edinim|satış)|pay (alım|edinim)', 'MA'),
    (r'türev|finansal (yatırım|varlık|araç)|(?<!gayri)menkul|\bfon\b|fonlar|borçlanma araç|hisse senedi|tahvil|bono|eurobond|vadeli mevduat|mevduat|repo|'
     r'serbest mevduat|kısa vadeli yatırım|devlet iç borçlanma|varlığa dayalı|gerçeğe uygun değer farkı', 'FINANSAL'),
    (r'(verilen|tahsil edilen|ilişkili taraf\w*).{0,40}(avans|borç|kredi)|(avans|borç|kredi).{0,30}(verilen|tahsil|geri ödeme)|'
     r'ilişkili taraflardan (alacak|tahsil)|ilişkili taraflara verilen', 'AVANS'),
    (r'geri alınan pay|geri alnan pay|kendi pay', 'FINANSMAN'),
    (r'konsolidasyon kapsam', 'MA'),
    (r'(satış|satım|satılma|elden çıkar).{0,40}(duran varlık|maddi|gayrimenkul|varlık)|(duran varlık|maddi|gayrimenkul).{0,60}(satış|satım|satılma|elden çıkar)', 'SATIS'),
]

def etiket_sinif(e):
    k = kucuk(e)
    for rx, s in ETIKET:
        if re.search(rx, k): return s
    return 'ARTIK'

def xbrl_yatirim(j, y, m):
    """→ (satırlar [(eleman, etiket, cari, önceki)], toplam (cari, önceki)) — TL."""
    na = j['nakit_akis']; t = na[list(na)[0]]
    ci, oi = sutunlar(t['baslik'], y, m)
    if ci is None: return None, None
    al = lambda x, i: (x['degerler'][i] if i is not None and i < len(x['degerler']) and x['degerler'][i] is not None else 0.0)
    sat, top = [], None
    for x in t['satirlar']:
        if x['boyut']: continue
        e = x['eleman']
        if e == 'ifrs-full_CashFlowsFromUsedInInvestingActivities':
            top = (al(x, ci), al(x, oi)); continue
        if not (e.endswith(S) or e == 'kap-fr_InflationEffectOnInvestingActivities'): continue
        c, o = al(x, ci), al(x, oi)
        if c == 0 and o == 0: continue
        sat.append([e, x['etiket'], c, o])
    # üst toplam + alt kırılım birlikte gelmişse (ör. MDV+MODV toplamı ve MDV, MODV) üst satır atılır
    tut = []
    for i, s in enumerate(sat):
        ust = False
        for jx in range(i + 1, len(sat)):
            alt = sat[i + 1:jx + 1]
            if (abs(sum(a[2] for a in alt) - s[2]) <= 2 and abs(sum(a[3] for a in alt) - s[3]) <= 2
                    and {SINIF.get(a[0], 'X') for a in alt} <= {SINIF.get(s[0], 'Y')}):
                ust = True; break
        if not ust: tut.append(s)
    return tut, top

def pdf_metinleri(idx):
    out = []
    for i in range(6):
        f = f'{OB}/{idx}_{i}.txt'
        if os.path.exists(f): out.append(open(f, errors='ignore').read())
    return out

def pdf_nakit(idx):
    """PDF nakit akış sayfalarının tüm tutar satırları → [(sayfa, etiket, [değerler])] (PDF biriminde), sırayla;
    iki satıra bölünmüş etiket birleştirilir. Yatırım bölümü başlığına bağlı değildir (başlıksız tablolar)."""
    for metin in pdf_metinleri(idx):
        sonuc = []
        for no, p in nakit_sayfalari(metin):
            onceki = ''
            for satir in p.split('\n'):
                et, vals, ok = _alanlar(re.sub(r'^(\s*)[−–-]\s+', r'\1', satir))  # madde işaretli etiket ('− Finansal ...')
                if not et: continue
                if not vals:
                    onceki = (onceki + ' ' + et).strip() if len(onceki) < 120 else et
                    continue
                tam = (onceki + ' ' + et).strip() if onceki and (not et[:1].isupper() or len(et) < 25) else et
                sonuc.append((no, tam, vals))
                onceki = ''
        if sonuc: return sonuc, metin
    return [], ''

def dipnot_ara(metin, deger, birim):
    """'Diğer' satırının tutarı (raporun kendi biriminde, tam belirteç olarak) dipnotlarda geçiyor mu
    → [(dipnot satırı, sınıf)]. Yalnız nakit akış tablosundan sonraki sayfalar; ≥ 1.000.000 birimlik tutarlar
    (rastlantısal eşleşme olmasın)."""
    if not metin: return []
    a = round(abs(deger) / birim)
    if a < 1_000_000: return []
    ps = metin.split('\f'); nak = {no - 1 for no, _ in nakit_sayfalari(metin)}
    son = min(nak) if nak else 0  # ana tablolar nakit akıştan öncedir
    rx = re.compile(r'(?<![\d.,])\(?' + re.escape(f'{a:,}'.replace(',', '.')) + r'\)?(?![\d]|[.,]\d)')
    out = []
    for no, p in enumerate(ps):
        if no <= son: continue
        for satir in p.split('\n'):
            if rx.search(satir):
                et = re.split(r'\s{2,}', satir.strip())[0]
                if et and not re.fullmatch(r'[\d\s().,\-–]*', et):
                    out.append((f's.{no + 1}: ' + ' '.join(satir.split())[:140], etiket_sinif(et)))
    return out

def diger_ayristir(idx, xs, diger):
    """'Diğer' (cari, önceki, TL) → [(etiket, sınıf, cari, önceki)] | None. PDF nakit akışında XBRL isimli satırlarıyla
    eşleşmeyen satırlardan toplamı 'Diğer'e eşit alt küme aranır (birim: TL / bin TL / mn TL). Bulunan PDF satırı da
    'diğer' etiketliyse tutarı dipnotlarda aranır; dipnot satırı sınıflanabiliyorsa o sınıf kullanılır."""
    ps, metin = pdf_nakit(idx)
    if not ps: return None, 'PDF nakit akışı okunamadı'
    isimli = [(s[2], s[3]) for s in xs if SINIF.get(s[0]) != 'DIGER']
    for birim in (1, 1e3, 1e6):
        tol = 2 if birim == 1 else birim * 1.01
        aday = []
        for no, et, vals in ps:
            if len(vals) < 2: continue
            c, o = vals[-2] * birim, vals[-1] * birim
            if c == 0 and o == 0: continue
            if any(abs(c - a) <= tol and abs(o - b) <= tol for a, b in isimli): continue
            if re.search(r'faaliyet\w* (kaynaklanan|elde edilen|ilişkin|kullanılan|sağlanan)\W*(\(?kullanılan\)?\W*)?(net )?nakit (akış|çıkış|giriş)|'
                         r'net (nakit|artış|azalış)|^toplam|dönem (başı|sonu)', kucuk(et)): continue
            aday.append((et, c, o))
        if not aday: continue
        bul = None
        for n in (1, 2, 3):
            if bul: break
            havuz = aday if n == 1 else aday[:30]
            for alt in itertools.combinations(havuz, n):
                if abs(sum(a[1] for a in alt) - diger[0]) <= tol * n and abs(sum(a[2] for a in alt) - diger[1]) <= tol * n:
                    bul = alt; break
        if not bul: continue
        out, notlar = [], []
        for et, c, o in bul:
            sn = etiket_sinif(et); sc = so = sn; etc = et
            if sn == 'ARTIK' and re.search(r'diğer', kucuk(et)):
                # 'Diğer' PDF'te de 'diğer' → her sütunun tutarı dipnotta ayrı aranır (sınıf sütun bazında)
                for d, sd in dipnot_ara(metin, c, birim):
                    notlar.append(d)
                    if sd != 'ARTIK': sc = sd; etc = et + ' [cari dipnot: ' + d + ']'; break
                for d, sd in dipnot_ara(metin, o, birim):
                    if sd != 'ARTIK': so = sd; etc += ' [önceki dipnot: ' + d + ']'; break
            out.append((etc, sc, so, c, o))
        return out, f'PDF ({"TL" if birim == 1 else "bin TL" if birim == 1e3 else "mn TL"})' + (' · dipnot adayları: ' + ' ‖ '.join(notlar[:3]) if notlar else '')
    return None, 'PDF satırlarıyla eşleşmedi'

ELLE = {k: v for k, v in json.load(open('k9_elle.json')).items() if not k.startswith('_')} if os.path.exists('k9_elle.json') else {}

H24 = json.load(open('rapor_bildirim_haritasi_2024ara.json')) if os.path.exists('rapor_bildirim_haritasi_2024ara.json') else {}

def rapor(kod, y, m):
    """→ ({sınıf: [cari, önceki] TL}, döküm satırları, sorun). k9_elle.json:
    'satirlar' → raporun yatırım bölümü elle (XBRL yok); 'diger' → XBRL 'Diğer' satırının elle (PDF/dipnot) ayrıştırması.
    Satır biçimi: [etiket, sınıf_cari, sınıf_önceki, cari_TL, önceki_TL]."""
    r = K[(K.kod == kod) & (K.yil == y) & (K.ay == m)].idx.dropna()
    if not r.empty: idx = int(r.iloc[0])
    elif H24.get(f'{kod}|{y}|{m}'): idx = int(H24[f'{kod}|{y}|{m}'][-1]['idx'])  # 2024 ara dönem (C yedeği için)
    else: return None, [], 'rapor yok'
    if not os.path.exists(f'{OB}/{idx}.json'): return None, [], f'KAP {idx} indirilmedi'
    j = json.load(open(f'{OB}/{idx}.json'))
    xs, top = xbrl_yatirim(j, y, m) if j.get('nakit_akis') else (None, None)
    ek = ELLE.get(f'{kod}|{y}|{m}', {})
    sk = ELLE.get(f'{kod}|*', {})  # şirket düzeyi: 'Diğer' her raporda aynı dipnota/PDF satırına referans veriyor
    if 'diger_sinif' in sk and 'diger' not in ek and 'diger_sinif' not in ek: ek = {**ek, 'diger_sinif': sk['diger_sinif'], 'not': sk.get('not', '')}
    if 'sinif' in sk: ek = {**ek, 'sinif': {**sk['sinif'], **ek.get('sinif', {})}}
    cnt, dok, sorun = collections.defaultdict(lambda: [0.0, 0.0]), [], ''
    def ekle(et, sc, so, c, o, kay):
        cnt[sc][0] += c; cnt[so][1] += o
        dok.append(dict(Kod=kod, Rapor=f'{y}/{m:02d}', idx=idx, Kaynak=kay, Etiket=et,
                        Sınıf=sc if sc == so else f'{sc} / önceki: {so}', Cari=c, Önceki=o))
    if 'satirlar' in ek:  # XBRL yok/eksik: yatırım bölümü imzalı PDF'ten elle okundu
        for et, sc, so, c, o in ek['satirlar']: ekle(et, sc, so, c, o, 'elle (PDF) · ' + ek.get('not', ''))
        return cnt, dok, ''
    if not xs: return None, [], f'KAP {idx}: XBRL yatırım bölümü yok'
    if top and (abs(sum(s[2] for s in xs) - top[0]) > 2 or abs(sum(s[3] for s in xs) - top[1]) > 2):
        sorun = f'KAP {idx}: XBRL satır toplamı yatırım toplamını tutmuyor'
    for e, et, c, o in xs:
        s = SINIF.get(e, 'ARTIK')
        if s == 'DIGER' and 'diger_sinif' in ek:
            ekle(et, ek['diger_sinif'], ek['diger_sinif'], c, o, 'XBRL Diğer → elle (PDF/dipnot) · ' + ek.get('not', '')); continue
        if s == 'DIGER' and 'diger' in ek:
            for pet, sc, so, pc, po in ek['diger']: ekle(pet, sc, so, pc, po, 'XBRL Diğer → elle (PDF/dipnot) · ' + ek.get('not', ''))
            continue
        if s == 'DIGER':
            par, kay = diger_ayristir(idx, xs, (c, o))
            if par:
                for pet, sc, so, pc, po in par: ekle(pet, sc, so, pc, po, f'XBRL Diğer → {kay}')
                continue
            ekle(et, 'ARTIK', 'ARTIK', c, o, 'XBRL (ayrışmadı) ' + kay[:300]); continue
        if e in ek.get('sinif', {}): s = ek['sinif'][e]  # XBRL isimli satırın etiketi PDF'te farklı (ör. 'Diğer uzun vadeli varlık' = finansal yatırım)
        ekle(et, s, s, c, o, 'XBRL')
    return cnt, dok, sorun

if __name__ == '__main__':
    v = pd.read_excel('../girdi/FCF_TTM_2025-03_2026-06_v7_nihai.xlsx', sheet_name='FCF_TTM')
    v = v[v['KOŞULLU nedeni'].astype(str).str.contains('Kontrol 9')]
    M = pd.read_excel('../FCF_MASTER.xlsx', sheet_name='FCF', keep_default_na=False).set_index('Anahtar')
    sonuc, doku, onb = [], [], {}
    for _, r in v.iterrows():
        kod, don = r['Kod'], r['Dönem']
        y, m = map(int, don.split('/'))
        parcalar = [((y, m), 'cari', 1)] + ([] if m == 12 else [((y, m), 'onceki', -1), ((y - 1, 12), 'cari', 1)])
        ttm, sorunlar = collections.defaultdict(float), []
        for (yy, mm), sut, isaret in parcalar:
            if (kod, yy, mm) not in onb:
                onb[(kod, yy, mm)] = rapor(kod, yy, mm)
                doku += onb[(kod, yy, mm)][1]
            cnt, _, sorun = onb[(kod, yy, mm)]
            if sorun: sorunlar.append(sorun)
            if cnt is None: continue
            if sut == 'onceki' and abs(cnt.get('ARTIK', [0, 0])[1]) > 0:
                # C = A raporunun karşılaştırmalı sütunu; 'Diğer'i orada ayrışmıyorsa geçen yılın aynı dönem raporunun
                # cari sütunu kullanılır (yatırım toplamları TMS 29 katsayısıyla tutarlıysa — yalnız yeniden ifade)
                if (kod, y - 1, m) not in onb:
                    onb[(kod, y - 1, m)] = rapor(kod, y - 1, m)
                    doku += onb[(kod, y - 1, m)][1]
                c2 = onb[(kod, y - 1, m)][0]
                if c2 is not None and abs(c2.get('ARTIK', [0, 0])[0]) < abs(cnt['ARTIK'][1]) * kat(kod, y, m) / kat(kod, y - 1, m):
                    t1 = sum(v[1] for v in cnt.values()) * kat(kod, y, m)
                    t2 = sum(v[0] for v in c2.values()) * kat(kod, y - 1, m)
                    if abs(t1 - t2) <= 0.03 * max(abs(t1), abs(t2)) + 1e6:
                        for s_, (c_, o_) in c2.items():
                            ttm[s_] -= c_ * kat(kod, y - 1, m) / 1e6
                        sorunlar.append(f'C: {y - 1}/{m:02d} raporunun cari sütunu (karşılaştırmalı sütunda Diğer ayrışmadı)')
                        continue
            for s, (c, o) in cnt.items():
                ttm[s] += isaret * (c if sut == 'cari' else o) * kat(kod, yy, mm) / 1e6
        mr = M.loc[f'{kod}|{don}']
        cfo, capex = float(mr['CFO_TTM'] or 0), float(mr['CAPEX_STD'] or 0)
        esik = max(abs(capex) * 0.5, abs(cfo) * 0.1)
        artik = ttm.get('ARTIK', 0.0)
        eksik = any(onb[(kod, yy, mm)][0] is None for (yy, mm), _, _ in parcalar)
        kapandi = not eksik and abs(artik) <= esik
        dokum = '; '.join(f'{AD[s]} {ttm[s]:+,.1f}' for s in sorted(ttm, key=lambda s: -abs(ttm[s])) if s != 'CAPEX' and abs(ttm[s]) >= 0.05)
        sonuc.append(dict(Kod=kod, Dönem=don, V7_artik=r['K9 artık (mn TL)'],
                          Esik=round(esik, 1), Siniflanmayan=round(artik, 1), Kapandi=kapandi,
                          CAPEX_belge_ttm=round(-ttm.get('CAPEX', 0.0), 1), Capex_ek=round(-ttm.get('CAPEX_DIPNOT', 0.0), 3), CAPEX_master=capex,
                          Dokum=dokum, Sorun=' | '.join(sorunlar)))
    pd.DataFrame(sonuc).to_csv('k9_sonuc.csv', index=False)
    pd.DataFrame(doku).to_csv('k9_rapor.csv', index=False)
    S_ = pd.DataFrame(sonuc)
    print(S_.Kapandi.value_counts())
