"""Aday listesine unvan/sektör ve Dropbox GEM puanlarını ekler, markdown tablo üretir.
Kullanım: python3 tarama/tablo_olustur.py [yillik|q3]"""
import csv, sys
MOD = sys.argv[1] if len(sys.argv) > 1 else "yillik"
EK = "_q3" if MOD == "q3" else ""
info = {r["kod"]: r for r in csv.DictReader(open("tarama/sirket_bilgi.csv"), delimiter="|")}
gem = {r["kod"]: r for r in csv.DictReader(open("tarama/gem_puanlari.csv"), delimiter="|")}
FIN = {"Aracı Kurum", "Girişim Sermayesi Yat. Ort.", "Holding"}
rows = list(csv.DictReader(open(f"tarama/sonuc_tum{EK}.csv")))
ina = [c for c in rows[0] if c.startswith("ina_nk_") and c != "ina_nk_ttm"]
out = []
for r in rows:
    if r["katman"] == "Elendi":
        continue
    i = info.get(r["kod"], {}); g = gem.get(r["kod"], {})
    sek = i.get("sektor", "")
    r2 = {"kod": r["kod"], "unvan": i.get("unvan", ""), "sektor": sek, "pd_mlr_tl": i.get("pd_mlr", ""),
          "not": "Finansal yapı" if sek in FIN else ("GYO/gayrimenkul" if sek == "Gayrimenkul" else ""),
          "gem_bilanco": g.get("bilanco", ""), "gem_hikaye": g.get("hikaye", ""), "gem_funnel": g.get("funnel", ""), "gem_sinif": g.get("sinif", "")}
    r2.update(r); out.append(r2)
w = csv.DictWriter(open(f"tarama/sonuc_adaylar{EK}.csv", "w", newline=""), fieldnames=list(out[0].keys()))
w.writeheader(); w.writerows(out)

def fm(x):
    if x in ("", None): return "–"
    if x == "inf": return "∞"
    return f"{float(x):.2f}".replace(".", ",")
kis = {"İNA/Net kâr ≥ 1 (her yıl)": "İNA/NK≥1", "Faiz/Esas faal. kârı ≤ %15": "Faiz≤%15", "Temettü SNA'dan karşılanmış": "Temettü≤SNA",
       "SNA (kira dahil) son dönem > 0": "SNA>0", "SNA (kira dahil) 2025 > 0": "SNA>0", "SNA son 2 yıl üst üste negatif değil": "SNA 2 yıl −",
       "Faiz karşılama ≥ 2": "Faiz karş.≥2", "Cari oran ≥ 1,2": "Cari≥1,2", "Alacak+stok günü bozulmuyor": "Alacak+stok",
       "Net borç/FAVÖK < 2": "NB/FAVÖK<2", "3 yıl net kâr > 0": "3 yıl kâr", "Faal.gid/Brüt kâr < %80": "Opex/Brüt<80",
       "Düzeltilmiş net kâr > 0 (son dönem)": "Düz. kâr>0", "Düzeltilmiş net kâr > 0 (2025)": "Düz. kâr>0"}
baslik = "9'dan 9'a TTM (Eyl.24 · Eyl.25 · Eyl.26)" if MOD == "q3" else "Yıllık (2023 · 2024 · 2025)"
md = [f"# Tarama sonuçları – {baslik} + GEM puanları\n",
      "GEM: Dropbox /BIST/GEM Analizleri/INDEX.md (26.11.2026). '—' = GEM analizi yok.\n"]
for kat, ad in [("A", "A – Tüm şartlar"), ("B", "B – Bayraksız, 1-2 ideal şart eksik"), ("C", "C – Bayraksız, 3+ ideal şart eksik"), ("D", "D – Tek kırmızı bayrak")]:
    rr = [r for r in out if r["katman"].startswith(kat)]
    md += [f"\n## {ad} ({len(rr)})\n", "| Kod | Şirket | Kırmızı bayrak | Eksik ideal şart | İNA/NK | B | H | F | GEM sınıf | Not |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rr:
        eks = " · ".join(kis.get(x, x) for x in r["kalan_sartlar"].split(" | ") if x)
        notlar = " · ".join(x for x in [r["not"], r.get("veri_notu", ""), r.get("son_durum_uyari", "").replace(" | ", " · ")] if x)
        md.append(f"| {r['kod']} | {r['unvan']} | {r['kirmizi_bayraklar'] or '—'} | {eks or '—'} | {' · '.join(fm(r[c]) for c in ina)} | "
                  f"{r['gem_bilanco'] or '—'} | {r['gem_hikaye'] or '—'} | {r['gem_funnel'] or '—'} | {r['gem_sinif'] or '—'} | {notlar or '—'} |")
open(f"tarama/TABLO_GEM{EK}.md", "w").write("\n".join(md) + "\n")
print(len(out), "aday;", sum(1 for r in out if r["gem_funnel"]), "GEM eşleşmesi")
