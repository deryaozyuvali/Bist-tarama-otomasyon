"""Seri Tutarlılığı Motoru (K6/K11 alt-kalem yerine aday) — V7 üzerinde paralel çalışır.

İlke: Brüt bir nakit ÇIKIŞI kaleminin (MDV+MODV alımı, YAGM alımı, kira anaparası)
yıl içi kümülatif (YTD) serisi şu kısıtı sağlamalıdır:
  (S2) yıl içinde kümülatif çıkış küçülmez: YTD_q ≤ YTD_(q−1)
Kısıtı bozan noktalar, "seriyi tutarlı yapmak için çıkarılması gereken EN AZ nokta"
ile atanır (en uzun tutarlı alt dizi). Eşit açıklamalar arasında tutulan pozitif
tutarı en küçük olan seçilir (işaret yalnız eşitlik bozucu). Tek optimum varsa atama
kesin; birden çok varsa olası; noktaların yarısı ya da fazlası atılıyorsa zayıf.
(S1) İşaret yalnız YTD_cari için kısıttır: önceki yıl noktaları TTM'e yalnız fark
olarak girer (VESBE 2025/03).
Net davranış: kalem şirkette pozitif YTD almışsa (kesin atanmış tekil nokta hariç).

Bir FCF satırı yalnız TTM köprüsünün üç noktasından (YTD_cari, FY_önceki, YTD_önceki)
biri şüpheliyse etkilenir. Ara noktalar TTM'e girmez.

Etki = en az düzeltme: şüpheli noktalar, tutarlı komşularının izin verdiği aralığa
kırpılır; TTM yeniden kurulur. Bu bir TAHMİN DEĞİLDİR ve FCF'e YAZILMAZ — yalnız
"bu satırdaki hata en az bu kadardır" der. Karar ölçüsü: zayıf atamada köprü
aralığındaki tutarsızlık, aksi halde etki alt sınırı.

Çıktı rakam değiştirmez; yalnız statü önerir:
  etkilenmiş + önemli  → KOŞULLU (V7 rakamı + alternatif FCF gösterilir)
  etkilenmiş + önemsiz → mevcut statü + not
  etkilenmemiş         → mevcut statü
"""
import itertools
import re
import sys

import os

import pandas as pd

TIE = os.environ.get('K13_TIE', '1') == '1'      # eşitlik bozucu açık mı
ZAYIF = os.environ.get('K13_ZAYIF', '1')  # zayıf ölçüsü: '1' açık, '0' kapalı, '2' yalnız alt sınır > 0 iken (R1')
SFX = os.environ.get('K13_SFX', '')
R2 = os.environ.get('K13_R2', '0') == '1'   # net bayrağı yalnız TTM penceresi (CATES dersi)
R4 = os.environ.get('K13_R4', '0') == '1'   # yıl içi önceki nokta varken 0 = veri (BERA dersi)

V7, OUT = sys.argv[1], sys.argv[2]
TOL = 0.01  # mn TL — yuvarlama gürültüsü
KALEMLER = ['MDV+MODV alımı', 'YAGM alımı', 'Kira anapara']
PAT = re.compile(r'([+−-])D(\d{4})=(-?[\d.]+)')

m = pd.read_excel(V7, sheet_name='FCF_TTM')
b = pd.read_excel(V7, sheet_name='Bileşenler')

# ---------------------------------------------------------------- kaynak noktalar
S = {}
for _, r in b[b['Bileşen'].isin(KALEMLER)].iterrows():
    for _, yymm, val in PAT.findall(str(r['Not / kanıt'])):
        S[(r['Kod'], r['Bileşen'], 2000 + int(yymm[:2]), int(yymm[2:]))] = float(val)


def seri(kod, kalem, yil):
    """Yıl içi YTD noktaları; 0 değerler kayıt yok sayılır (DiffSet ile aynı)."""
    out = []
    for ay in (3, 6, 9, 12):
        k = (kod, kalem, yil, ay)
        if k not in S:
            continue
        onceki_fy = abs(S.get((kod, kalem, yil - 1, 12), 0.0))
        if abs(S[k]) > TOL or (R4 and out and onceki_fy >= max(abs(v) for _, v in out) - TOL
                               and any(abs(v) > TOL for _, v in out)):
            out.append((ay, S[k]))
    return out


def tutarli(alt):
    # S2 yalnız: yıl içi kümülatif çıkış küçülmez. İşaret (S1) burada YOK —
    # önceki yıl noktaları TTM'e yalnız fark olarak girer (VESBE 2024/03 dersi).
    return all(alt[i][1] <= alt[i - 1][1] + TOL for i in range(1, len(alt)))


def optimumlar(pts):
    """En uzun tutarlı alt diziler (tutulacak noktaların ay kümeleri)."""
    for n in range(len(pts), -1, -1):
        sol = [c for c in itertools.combinations(pts, n) if tutarli(list(c))]
        if sol:
            # Eşitlik bozucu (S1): tutulan noktalardaki pozitif tutar toplamı en küçük
            # olan açıklamalar kalır. Brüt çıkış kaleminde pozitif YTD ekonomik olarak
            # olağandışıdır; kısıt değil, yalnız eşit açıklamalar arasında tercih.
            skor = [sum(max(v, 0.0) for _, v in c) for c in sol]
            en_az = min(skor) if TIE else float('inf')
            sol = [c for c, s in zip(sol, skor) if s <= en_az + TOL]
            if R4:
                # Yıl içinde dolu noktadan sonra gelen 0 büyük olasılıkla eksik veridir
                # (BERA 2026/06: net satır kırpılmış) → sıfırı tutan açıklama elenir.
                sifir = [sum(abs(v) <= TOL for _, v in c) for c in sol]
                sol = [c for c, z in zip(sol, sifir) if z == min(sifir)]
            return [frozenset(a for a, _ in c) for c in sol]
    return [frozenset()]


def kirp(pts, tut):
    """Tutulmayan noktaları tutarlı komşu aralığına kırp (en az düzeltme)."""
    out, son_ust = {}, float('inf')
    tutulan = [(a, v) for a, v in pts if a in tut]
    for a, v in pts:
        if a in tut:
            out[a] = v
            son_ust = v
            continue
        sonraki = [tv for ta, tv in tutulan if ta > a]
        alt = sonraki[0] if sonraki else float('-inf')
        nv = min(max(v, alt), son_ust)  # [alt, son_ust] aralığına
        out[a] = nv
        son_ust = nv
    return out


ANALIZ = {}  # (kod, kalem, yil) -> dict
NET = {}
for (kod_, kal_, yy_, aa_), v_ in S.items():
    if v_ > TOL:
        NET[(kod_, kal_)] = max(NET.get((kod_, kal_), 0.0), v_)


def analiz(kod, kalem, yil):
    key = (kod, kalem, yil)
    if key not in ANALIZ:
        pts = seri(kod, kalem, yil)
        opts = optimumlar(pts)
        hepsi = {a for a, _ in pts}
        kesin = set.intersection(*[hepsi - o for o in opts]) if opts else set()
        olasi = set.union(*[hepsi - o for o in opts]) if opts else set()
        # Zayıf atama: tutarlılık için noktaların yarısı ya da fazlası atılıyorsa
        # hangi noktanın bozuk olduğu seriden söylenemez → tüm noktalar olası.
        cikan = len(pts) - max((len(o) for o in opts), default=0)
        zayif = cikan > 0 and 2 * cikan >= len(pts)
        if R4 and zayif and all(abs(v) <= TOL for a, v in pts if a not in max(opts, key=len)):
            zayif = False  # yalnız sıfır(lar) atılıyor: atama belirsiz değil
        if zayif:
            kesin, olasi = set(), set(hepsi)
        # tutarsızlık büyüklüğü: yıl içi pozitif örtük çeyreklerin toplamı
        # aralık bazlı gerileme: (önceki_ay, ay] -> pozitif örtük artış
        gerileme = {pts[i][0]: max(0.0, pts[i][1] - pts[i - 1][1]) for i in range(1, len(pts))}
        ANALIZ[key] = dict(pts=pts, opts=opts, kesin=kesin, olasi=olasi, zayif=zayif,
                           gerileme=gerileme, kirpik=[kirp(pts, o) for o in opts])
    return ANALIZ[key]


POZ = {}  # (kod, kalem, yıl) -> pozitif YTD nokta sayısı
for (k_, c_, y_, a_), v_ in S.items():
    if v_ > TOL:
        POZ[(k_, c_, y_)] = POZ.get((k_, c_, y_), 0) + 1


def net_davranis(kod, kalem, y=None, ay=None):
    """Kalemin şirkette pozitif YTD alması; seri tarafından KESİN atanmış tekil
    bozuk noktalar hariç (ALCAR 2025/06 dersi: tek bozuk nokta net sunum değildir)."""
    mx = 0.0
    for (k_, c_, y_, a_), v_ in S.items():
        if R2 and y is not None and not (y_ == y and a_ <= ay or ay != 12 and y_ == y - 1 and a_ >= ay):
            # pencere dışı: yalnız o yıl tek (yalıtılmış) pozitif noktaysa yok say (CATES);
            # yıl boyu yaygın pozitiflik seri düzeyinde sunum/işaret sorunudur (PGSUS, ODAS)
            if POZ.get((kod, kalem, y_), 0) <= 1:
                continue
        if k_ == kod and c_ == kalem and v_ > TOL and a_ not in analiz(kod, kalem, y_)['kesin']:
            mx = max(mx, v_)
    return mx


def nokta(kod, kalem, yil, ay, varyant=None):
    """Orijinal ya da kırpılmış nokta değeri; kayıt yoksa 0."""
    a = analiz(kod, kalem, yil)
    if varyant is None:
        return S.get((kod, kalem, yil, ay), 0.0)
    return a['kirpik'][varyant].get(ay, S.get((kod, kalem, yil, ay), 0.0))


def num(x):
    return pd.to_numeric(x, errors='coerce')


rows = []
for _, r in m.iterrows():
    kod, donem = r['Kod'], r['Dönem']
    y, ay = map(int, donem.split('/'))
    k6 = str(r['K6 dışlanan satır'])
    for kalem in KALEMLER:
        kopru = [(y, ay)] + ([] if ay == 12 else [(y - 1, 12), (y - 1, ay)])
        if not any((kod, kalem, yy, aa) in S for yy, aa in kopru):
            continue
        sup_kesin, sup_olasi = [], []
        for yy, aa in kopru:
            a = analiz(kod, kalem, yy)
            if aa in a['kesin']:
                sup_kesin.append(f'{yy % 100:02d}{aa:02d}')
            elif aa in a['olasi']:
                sup_olasi.append(f'{yy % 100:02d}{aa:02d}')
        c_val = S.get((kod, kalem, y, ay))
        s1 = c_val is not None and c_val > TOL
        net_max = net_davranis(kod, kalem, y, ay)
        if not sup_kesin and not sup_olasi and not s1 and not net_max:
            continue

        def ttm(var_cur=None, var_prev=None):
            c = nokta(kod, kalem, y, ay, var_cur)
            if var_cur is not None:
                c = min(c, 0.0)  # S1: cari YTD brüt çıkışta pozitif olamaz
            if ay == 12:
                return c
            return c + nokta(kod, kalem, y - 1, 12, var_prev) - nokta(kod, kalem, y - 1, ay, var_prev)

        t0 = ttm()
        k6_disladi = kalem.split()[0] in k6
        b_row = b[(b.Kod == kod) & (b['Dönem'] == donem) & (b['Bileşen'] == kalem)]
        kullanilan = 0.0 if k6_disladi else float(num(b_row['Formülde (mn TL)']).fillna(0).iloc[0]) if len(b_row) else abs(t0)
        nc = len(analiz(kod, kalem, y)['opts'])
        npv = 1 if ay == 12 else len(analiz(kod, kalem, y - 1)['opts'])
        etkiler, projler = ([0.0], [kullanilan]) if not (sup_kesin or sup_olasi or s1) else ([], [])
        for i in range(nc if etkiler == [] else 0):
            for j in range(npv):
                tp = ttm(i, None if ay == 12 else j)
                etkiler.append(abs(max(0.0, -tp) - kullanilan))
                projler.append(max(0.0, -tp))
        imin = min(range(len(etkiler)), key=etkiler.__getitem__)
        zayif_yillar = [yy for yy in {y, y - 1} if (yy == y or ay != 12)
                        and analiz(kod, kalem, yy)['zayif']
                        and any(f'{yy % 100:02d}{aa:02d}' in sup_olasi for y2, aa in kopru if y2 == yy)]
        # Zayıf atamada seri hangi noktanın bozuk olduğunu söyleyemez; alt sınır
        # (en az düzeltme) belirsizliği ölçmez. Karar ölçüsü: köprünün kapsadığı
        # aralıktaki tutarsızlığın kendisi (cari yıl (0, ay], önceki yıl (ay, 12]).
        karar_olcusu = min(etkiler)
        if zayif_yillar:
            zg = 0.0
            for yy in zayif_yillar:
                g = analiz(kod, kalem, yy)['gerileme']
                zg += sum(v for a2, v in g.items() if (a2 <= ay if yy == y else a2 > ay))
            if ZAYIF == '1' or (ZAYIF == '2' and min(etkiler) > TOL):
                karar_olcusu = max(karar_olcusu, zg)
        rows.append(dict(
            Kod=kod, Dönem=donem, Kalem=kalem,
            **{'V7 statü': r['FCF statü'] if pd.notna(r['FCF statü']) else 'NULL',
               'V7 FCF': num(r['FCF ana · TTM · tanım=FCF türü · statü=FCF statü (mn TL)']),
               'CFO_TTM': num(r['CFO_TTM']),
               'V7 TTM (işaretli)': t0, 'V7 kullanılan': kullanilan, 'V7 K6 dışladı': k6_disladi,
               'Şüpheli köprü noktası (kesin)': ','.join(sup_kesin),
               'Şüpheli köprü noktası (olası)': ','.join(sup_olasi),
               'Etki alt sınır (mn TL)': min(etkiler),
               'Karar ölçüsü (mn TL)': karar_olcusu,
               'En az düzeltilmiş kalem (mn TL)': projler[imin],
               'Kaynak (V7)': b_row['Kaynak'].iloc[0] if len(b_row) else None, 'Etki üst (alternatifler)': max(etkiler),
               'S1 cari pozitif': s1,
               'A3 net davranış (maks pozitif YTD)': net_max,
               'Zayıf atama': bool(zayif_yillar),
               'Atama': 'TEK' if not sup_olasi else 'BELİRSİZ'}))

R = pd.DataFrame(rows)
# satır (FCF) düzeyinde topla
F = (R.groupby(['Kod', 'Dönem'])
       .agg(**{'Etkilenen kalem': ('Kalem', lambda s: ' + '.join(s)),
               'Toplam etki alt sınır': ('Etki alt sınır (mn TL)', 'sum'),
               'Atama': ('Atama', lambda s: 'BELİRSİZ' if 'BELİRSİZ' in set(s) else 'TEK')})
       .reset_index())
F = F.merge(m[['Kod', 'Dönem', 'CFO_TTM', 'FCF statü',
               'FCF ana · TTM · tanım=FCF türü · statü=FCF statü (mn TL)']], on=['Kod', 'Dönem'], how='left')
F = F.rename(columns={'FCF statü': 'V7 statü', 'FCF ana · TTM · tanım=FCF türü · statü=FCF statü (mn TL)': 'V7 FCF'})
F['V7 statü'] = F['V7 statü'].fillna('NULL')
F['Önemlilik eşiği'] = F['CFO_TTM'].abs().mul(0.005).clip(lower=1.0)
F['Önemli'] = F['Toplam etki alt sınır'] >= F['Önemlilik eşiği']

R.to_pickle(f'seri_kalem{SFX}.pkl')
F.to_pickle('seri_satir.pkl')
pd.to_pickle(ANALIZ, f'seri_analiz{SFX}.pkl')
print('kalem satırı:', len(R), '| FCF satırı:', len(F), '| şirket:', F.Kod.nunique())
print(pd.crosstab(F['V7 statü'], F['Önemli'], margins=True))
