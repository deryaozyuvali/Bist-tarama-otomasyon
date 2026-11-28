"""
Sabri Çakar "Tez Defteri" Bölüm 4-5-6 taraması.

Girdi : tarama/ham_veri.csv (Fintables/EVO, standart şablon, 2023-2025 yılsonu + 2026/9 TTM)
Çıktı : tarama/sonuc_tum.csv, tarama/sonuc_sikI.csv, tarama/sonuc_bayraksiz.csv

Eşikler videolarda söylenenlerdir. Videoda sayı verilmeyen yerlerde
kullanılan yorumlar 'YORUM' etiketiyle işaretlidir.
"""
import csv, statistics, sys
from collections import defaultdict

IN = "tarama/ham_veri.csv"
YILLAR = ["2023", "2024", "2025"]
SON = "2026"  # 2026/9 TTM gelir+nakit akışı, 30.09.2026 bilanço


def f(x):
    try:
        return float(x) if x not in ("", None) else None
    except ValueError:
        return None


def div(a, b):
    if a is None or b in (None, 0):
        return None
    return a / b


data = defaultdict(dict)
for r in csv.DictReader(open(IN)):
    data[r["k"]][r["yil"]] = {k: f(v) for k, v in r.items() if k not in ("k", "yil")}


def metrikler(d):
    z = lambda k: d.get(k) or 0.0
    m = {}
    brut, opex = d.get("brut"), z("opex")
    m["sat"] = d.get("sat")
    m["nk"] = d.get("nk")
    m["ina"] = d.get("ina")
    # Net esas faaliyet kârı = Brüt kâr - faaliyet giderleri (diğer faaliyet gelir/giderleri hariç) — Bölüm 4
    m["efk"] = (brut + opex) if brut is not None else None
    faiz = abs(z("fingid"))
    m["faiz"] = faiz
    m["brut_marj"] = div(brut, d.get("sat"))
    m["efk_marj"] = div(m["efk"], d.get("sat"))
    m["opex_brut"] = div(abs(opex), brut) if brut and brut > 0 else None
    m["faiz_efk"] = div(faiz, m["efk"]) if m["efk"] and m["efk"] > 0 else None
    m["faiz_karsilama"] = (div(m["efk"], faiz) if faiz else float("inf")) if m["efk"] is not None else None
    # Tek seferlik / nakit dışı kalemler (Bölüm 4: 5 kalem) — net parasal pozisyon, ertelenmiş vergi geliri, yatırım faaliyeti gelirleri
    tek = z("npp") + max(z("evg"), 0) + z("yfg")
    m["tek_seferlik"] = tek
    m["duz_nk"] = (d["nk"] - tek) if d.get("nk") is not None else None
    m["ina_nk"] = div(d.get("ina"), d.get("nk")) if (d.get("nk") or 0) > 0 else None
    capex = z("capex")  # negatif
    m["capex_amort"] = div(abs(capex), d.get("amort"))
    m["sna"] = (d["ina"] + capex) if d.get("ina") is not None else None
    # Kira ödemeleri işletme nakdi gibi düşünülmeli — Bölüm 6 sınırlar
    m["sna_kira"] = (m["sna"] + z("kira")) if m["sna"] is not None else None
    m["temettu"] = abs(z("tem"))
    m["cari"] = div(d.get("dv"), d.get("kvy"))
    m["asit"] = div((d.get("dv") or 0) - z("stok"), d.get("kvy")) if d.get("dv") else None
    m["nakit_oran"] = div(d.get("nakit"), d.get("kvy"))
    nb, fav = d.get("netborc"), d.get("favok")
    if nb is None or fav is None:
        m["nb_favok"] = None
    elif fav <= 0:
        m["nb_favok"] = float("inf") if nb > 0 else -1.0
    else:
        m["nb_favok"] = nb / fav
    m["netborc"] = nb
    m["nakit_kvfb"] = div(d.get("nakit"), d.get("kvfb")) if (d.get("kvfb") or 0) > 0 else float("inf")
    smm = abs(z("smm"))
    m["stok_gun"] = div(z("stok"), smm) * 365 if smm else None
    m["alacak_gun"] = div(z("alac"), d.get("sat")) * 365 if d.get("sat") else None
    m["borc_gun"] = div(z("tborc"), smm) * 365 if smm else None
    if None not in (m["stok_gun"], m["alacak_gun"], m["borc_gun"]):
        m["ndd"] = m["stok_gun"] + m["alacak_gun"] - m["borc_gun"]
    else:
        m["ndd"] = None
    m["oz"] = d.get("oz")
    m["roe"] = div(d.get("nk"), d.get("oz")) if (d.get("oz") or 0) > 0 else None
    # Stres testi: satış -%20, brüt marj ve faaliyet gideri sabit, faiz x2 — Bölüm 5
    if brut is not None:
        efk_s = brut * 0.8 + opex
        m["stres_efk"] = efk_s
        m["stres_karsilama"] = efk_s / (2 * faiz) if faiz else float("inf")
        m["stres_nb_favok"] = (div(nb, efk_s + z("amort")) if (efk_s + z("amort")) > 0 else float("inf")) if nb is not None else None
    else:
        m["stres_efk"] = m["stres_karsilama"] = m["stres_nb_favok"] = None
    return m


sonuc = []
for k, yy in data.items():
    if not all(y in yy for y in YILLAR):
        continue
    M = {y: metrikler(yy[y]) for y in YILLAR}
    S = metrikler(yy[SON]) if SON in yy else None
    m25 = M["2025"]
    if not m25["sat"] or m25["sat"] <= 0 or m25.get("efk") is None:
        continue

    bayrak, sart = [], {}

    # ---------- NAKİT AKIŞI (Bölüm 6) ----------
    kar_her_yil = all((M[y]["nk"] or 0) > 0 for y in YILLAR)
    sart["3 yıl net kâr > 0"] = kar_her_yil
    ina_nk = [M[y]["ina_nk"] for y in YILLAR]
    sart["İNA/Net kâr ≥ 1 (her yıl)"] = kar_her_yil and all(r is not None and r >= 1 for r in ina_nk)
    sna = [M[y]["sna_kira"] for y in YILLAR]
    neg = [s is not None and s < 0 for s in sna]
    if all(neg):
        bayrak.append("SNA 3 yıl üst üste negatif (>2 yıl)")
    elif neg[1] and neg[2] and (M["2025"]["netborc"] or 0) > (M["2024"]["netborc"] or 0) > (M["2023"]["netborc"] or 0):
        bayrak.append("SNA 2 yıl negatif + net borç artıyor")
    sart["SNA (kira dahil) 2025 > 0"] = (sna[2] or -1) > 0
    sart["SNA son 2 yıl üst üste negatif değil"] = not (neg[1] and neg[2])
    tem_borctan = [y for y in YILLAR if M[y]["temettu"] > 0 and (M[y]["sna_kira"] or 0) < M[y]["temettu"]]
    if tem_borctan:
        bayrak.append("Temettü SNA'yı aşıyor: " + ",".join(tem_borctan))
    sart["Temettü SNA'dan karşılanmış"] = not tem_borctan
    # YORUM: "birkaç yıl üst üste kârın çok altında" → 3 yıl üst üste İNA/NK < 0,5
    if kar_her_yil and all(r is not None and r < 0.5 for r in ina_nk):
        bayrak.append("İNA 3 yıl üst üste net kârın yarısından az")

    # ---------- GELİR TABLOSU (Bölüm 4) ----------
    ob = m25["opex_brut"]
    if ob is None or ob >= 0.80:
        bayrak.append("Faal.gid/Brüt kâr ≥ %80 (veya brüt kâr ≤ 0)")
    sart["Faal.gid/Brüt kâr < %80"] = ob is not None and ob < 0.80
    fe = m25["faiz_efk"]
    sart["Faiz/Esas faal. kârı ≤ %15"] = m25["efk"] > 0 and (fe is None or fe <= 0.15)
    sart["Düzeltilmiş net kâr > 0 (2025)"] = (m25["duz_nk"] or -1) > 0
    if (m25["nk"] or 0) > 0 and (m25["duz_nk"] or 0) <= 0:
        bayrak.append("2025 kârı tek seferlik/nakit dışı kalemlerden")

    # ---------- BİLANÇO (Bölüm 5) ----------
    fk = m25["faiz_karsilama"]
    if fk is None or fk < 2:
        bayrak.append("Faiz karşılama < 2")
    sart["Faiz karşılama ≥ 2"] = fk is not None and fk >= 2
    nbf = m25["nb_favok"]
    if nbf is None or nbf > 3:
        bayrak.append("Net borç/FAVÖK > 3 (veya FAVÖK ≤ 0)")
    sart["Net borç/FAVÖK < 2"] = nbf is not None and nbf < 2
    cari = [M[y]["cari"] for y in YILLAR]
    if all(c is not None and c < 1 for c in cari):
        bayrak.append("Cari oran 3 yıl < 1 (perakendede olağan olabilir)")
    sart["Cari oran ≥ 1,2"] = (cari[2] or 0) >= 1.2
    # YORUM: "nakit borcun çok altında ve uzun süre" → 3 yıl nakit < KV finansal borcun %50'si
    if all(M[y]["nakit_kvfb"] is not None and M[y]["nakit_kvfb"] < 0.5 for y in YILLAR):
        bayrak.append("Nakit 3 yıl KV fin. borcun %50'sinden az")
    # YORUM: "alacak/stok günleri satıştan hızlı artıyorsa" → (alacak+stok günü) 2023→2025 %20'den fazla arttıysa
    g23 = (M["2023"]["alacak_gun"] or 0) + (M["2023"]["stok_gun"] or 0)
    g25 = (m25["alacak_gun"] or 0) + (m25["stok_gun"] or 0)
    gun_bozulma = g23 > 0 and g25 > g23 * 1.2 and (g25 - g23) > 10
    if gun_bozulma:
        bayrak.append(f"Alacak+stok günü {g23:.0f}→{g25:.0f}")
    sart["Alacak+stok günü bozulmuyor"] = not gun_bozulma

    stres = m25["stres_karsilama"]
    stres_not = "Stres sonrası faaliyet zararı" if (m25["stres_efk"] or 0) <= 0 else (
        "Stres sonrası faiz karşılama < 2" if stres is not None and stres < 2 else "")

    # ---------- SON DURUM (2026/9) ----------
    son_not = []
    if S:
        if (S["nk"] or 0) > 0 and S["ina_nk"] is not None and S["ina_nk"] < 1:
            son_not.append(f"TTM İNA/NK {S['ina_nk']:.2f}")
        if (S["nk"] or 0) <= 0:
            son_not.append("TTM zarar")
        if S["nb_favok"] is not None and S["nb_favok"] > 3:
            son_not.append("TTM NB/FAVÖK>3")
        if (S["sna_kira"] or 0) < 0:
            son_not.append("TTM SNA<0")

    sikI = all(sart.values()) and not bayrak
    eksik = sum(not v for v in sart.values())
    if sikI:
        katman = "A - Tüm şartlar"
    elif not bayrak and kar_her_yil and eksik <= 2:
        katman = "B - Bayraksız, 1-2 ideal şart eksik"
    elif not bayrak and kar_her_yil:
        katman = "C - Bayraksız, 3+ ideal şart eksik"
    elif len(bayrak) == 1 and kar_her_yil:
        katman = "D - Tek kırmızı bayrak"
    else:
        katman = "Elendi"
    sonuc.append({
        "kod": k,
        "katman": katman,
        "sikI_liste": sikI,
        "kirmizi_bayrak_yok": not bayrak,
        "gecen_sart": sum(sart.values()), "toplam_sart": len(sart),
        "kirmizi_bayraklar": " | ".join(bayrak),
        "kalan_sartlar": " | ".join(s for s, v in sart.items() if not v),
        "ina_nk_2023": ina_nk[0], "ina_nk_2024": ina_nk[1], "ina_nk_2025": ina_nk[2],
        "ina_nk_ttm": S["ina_nk"] if S else None,
        "sna_kira_2025_mn": (sna[2] or 0) / 1e6,
        "brut_marj_2023": M["2023"]["brut_marj"], "brut_marj_2025": m25["brut_marj"],
        "efk_marj_2023": M["2023"]["efk_marj"], "efk_marj_2025": m25["efk_marj"],
        "opex_brut_2025": ob, "faiz_efk_2025": fe, "faiz_karsilama_2025": fk,
        "nb_favok_2025": nbf, "nb_favok_ttm": S["nb_favok"] if S else None,
        "cari_2025": cari[2], "asit_2025": m25["asit"], "nakit_oran_2025": m25["nakit_oran"],
        "ndd_2025": m25["ndd"], "capex_amort_2025": m25["capex_amort"], "roe_2025": m25["roe"],
        "stres_karsilama": stres, "stres_not": stres_not,
        "son_durum_uyari": " | ".join(son_not),
    })

def yaz(path, rows):
    if not rows:
        return
    w = csv.DictWriter(open(path, "w", newline=""), fieldnames=list(rows[0].keys()))
    w.writeheader()
    for r in rows:
        w.writerow({k: (round(v, 3) if isinstance(v, float) and v not in (float("inf"),) else v) for k, v in r.items()})

sonuc.sort(key=lambda r: (-r["gecen_sart"], len(r["kirmizi_bayraklar"])))
yaz("tarama/sonuc_tum.csv", sonuc)
yaz("tarama/sonuc_adaylar.csv", [r for r in sonuc if r["katman"] != "Elendi"])
print(Counter(r["katman"] for r in sonuc)) if False else None
print("taranan:", len(sonuc), "sıkı:", sum(r["sikI_liste"] for r in sonuc), "bayraksız:", sum(r["kirmizi_bayrak_yok"] for r in sonuc))
from collections import Counter
print(Counter(r["katman"] for r in sonuc))
c = Counter()
for r in sonuc:
    for s in r["kalan_sartlar"].split(" | "):
        if s: c[s] += 1
print("Şart başına elenen:", c.most_common())
b = Counter()
for r in sonuc:
    for x in r["kirmizi_bayraklar"].split(" | "):
        if x: b[x.split(":")[0] if "Temettü" in x else ("Alacak+stok günü bozuluyor" if x.startswith("Alacak") else x)] += 1
print("Bayrak sayıları:", b.most_common())
