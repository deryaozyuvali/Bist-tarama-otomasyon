"""
Bölüm 6 istisnası: "Şirket yatırım dönemindeyse SNA'nın 1-1,5 yıl eksi olması normaldir;
2 yıldan fazla SNA üretemeyen ve borcu artan şirket kırmızı alarm."

Bu betik SNA'sı negatif olup istisnaya uyabilecek şirketleri ayıklar.
Girdi: tarama/ham_veri.csv   Çıktı: tarama/yatirim_donemi.csv
"""
import csv
from collections import defaultdict

def f(x):
    try: return float(x) if x not in ("", None) else None
    except ValueError: return None

D = defaultdict(dict)
for r in csv.DictReader(open("tarama/ham_veri.csv")):
    D[r["k"]][r["yil"]] = {k: f(v) for k, v in r.items() if k not in ("k", "yil")}

def z(d, k): return d.get(k) or 0.0
def sna(d):  # İNA - capex - kira (kira işletme nakdi sayılır)
    return None if d.get("ina") is None else d["ina"] + z(d, "capex") + z(d, "kira")
def efk(d): return None if d.get("brut") is None else d["brut"] + z(d, "opex")

out = []
for k, yy in D.items():
    if not all(y in yy for y in ("2023", "2024", "2025")):
        continue
    P = ["2023", "2024", "2025"] + (["2026"] if "2026" in yy else [])
    S = {p: sna(yy[p]) for p in P}
    if any(S[p] is None for p in ("2023", "2024", "2025")):
        continue
    neg = {p: S[p] is not None and S[p] < 0 for p in P}
    son = "2026" if "2026" in yy else "2025"

    # 1) Negatiflik süresi: en fazla ~1,5 yıl
    if neg["2023"] and neg["2024"] and neg["2025"]:
        continue                              # >2 yıl: videoya göre alarm
    if neg["2024"] and neg["2025"]:
        sure = "2 yıl (sınırda)"
    elif neg["2025"] and neg.get("2026"):
        sure = "≈1,5 yıl (2025 + TTM)"
    elif neg["2025"]:
        sure = "1 yıl (2025)"
    elif neg.get("2026"):
        sure = "Yeni (yalnız TTM 2026/9)"
    else:
        continue                              # SNA negatif değil, istisna konusu değil
    negp = [p for p in P if neg[p]]

    # 2) Negatifliğin nedeni yatırım olmalı: işletme nakdi pozitif, yatırım amortismanı aşıyor
    # YORUM: yatırım amortisman (bakım) düzeyinde kalsaydı SNA pozitif olurdu → negatifliği büyüme yatırımı yaratıyor
    ok_neden = all((yy[p].get("ina") or 0) + z(yy[p], "kira") - z(yy[p], "amort") > 0 for p in negp)
    capex_amort = [abs(z(yy[p], "capex")) / yy[p]["amort"] if yy[p].get("amort") else None for p in negp]
    ok_capex = all(c is not None and c > 1 for c in capex_amort)   # YORUM: bakımın ötesinde yatırım
    # 3) Kârlı şirket
    ok_kar = all((yy[y].get("nk") or 0) > 0 for y in ("2023", "2024", "2025"))
    # 4) Borç yönetilebilir (videodaki alarm eşikleri)
    d = yy[son]; d25 = yy["2025"]
    fav = d.get("favok"); nb = d.get("netborc")
    nbf = (nb / fav) if (fav and fav > 0 and nb is not None) else (None if nb is None else (float("inf") if nb > 0 else -1))
    e = efk(d25); faiz = abs(z(d25, "fingid"))
    fk = (e / faiz if faiz else float("inf")) if e is not None else None
    ok_borc = nbf is not None and nbf <= 3 and fk is not None and fk >= 2
    # 5) Diğer kalite kırmızı bayrakları yok
    ob = abs(z(d25, "opex")) / d25["brut"] if (d25.get("brut") or 0) > 0 else None
    tek = z(d25, "npp") + max(z(d25, "evg"), 0) + z(d25, "yfg")
    cari = [ (yy[y].get("dv") or 0) / yy[y]["kvy"] if yy[y].get("kvy") else None for y in ("2023","2024","2025")]
    ok_kalite = ob is not None and ob < 0.80 and (z(d25, "nk") - tek) > 0 and not all(c is not None and c < 1 for c in cari)

    if not (ok_neden and ok_capex and ok_kar and ok_borc and ok_kalite):
        continue

    nb_bas = yy["2024"].get("netborc"); 
    temettu_neg = [p for p in negp if z(yy[p], "tem") < 0]
    ina = {p: yy[p].get("ina") for p in P}
    out.append({
        "kod": k, "sure": sure,
        "sna_2023_mn": S["2023"]/1e6, "sna_2024_mn": S["2024"]/1e6, "sna_2025_mn": S["2025"]/1e6,
        "sna_ttm_mn": (S.get("2026") or 0)/1e6 if "2026" in S else None,
        "capex_amort_neg_donem": " / ".join(f"{c:.1f}" for c in capex_amort),
        "ina_nk_2025": (d25["ina"]/d25["nk"]) if d25.get("nk") else None,
        "nb_favok_son": nbf, "faiz_karsilama_2025": fk,
        "net_borc_2024_mn": (nb_bas or 0)/1e6, "net_borc_son_mn": (nb or 0)/1e6,
        "borc_artiyor": (nb or 0) > (nb_bas or 0) and (nb or 0) > 0,
        "neg_donemde_temettu": ",".join(temettu_neg),
        "ina_2024_mn": (ina["2024"] or 0)/1e6, "ina_son_mn": (ina[son] or 0)/1e6,
    })

w = csv.DictWriter(open("tarama/yatirim_donemi.csv", "w", newline=""), fieldnames=list(out[0].keys()))
w.writeheader(); [w.writerow({k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items()}) for r in out]
print(len(out))
from collections import Counter; print(Counter(r["sure"] for r in out))
for r in sorted(out, key=lambda r: r["sure"]):
    print(r["kod"], "|", r["sure"], "| SNA", round(r["sna_2023_mn"]), round(r["sna_2024_mn"]), round(r["sna_2025_mn"]), r["sna_ttm_mn"] and round(r["sna_ttm_mn"]), "| capex/amort", r["capex_amort_neg_donem"], "| NB/FAV", round(r["nb_favok_son"],2), "| FK", round(r["faiz_karsilama_2025"],1), "| NB", round(r["net_borc_2024_mn"]), "->", round(r["net_borc_son_mn"]), "| tem:", r["neg_donemde_temettu"], "| İNA", round(r["ina_2024_mn"]), "->", round(r["ina_son_mn"]))
