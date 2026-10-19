"""İki koşunun şirket bazında karşılaştırması: eski sonuç → yeni sonuç → neden."""
import argparse
import collections
import csv
import json


def ozet(x):
    l = x.get("liste", "")
    if l.startswith("1-"):
        return f"{l.split(' (')[0]} · K{x['kuyruk']} · {x['on_puan_alt']:g}–{x['on_puan_ust']:g}"
    return l


def _sat(x):
    if x["durum"] == "HESAPLANDI":
        return f"{x['puan']:g}"
    if x["durum"] == "EKSİK" and x.get("alt") is not None and x.get("ust") is not None:
        return f"EKSİK ({x['alt']:g}–{x['ust']:g})"
    return x["durum"]


def nedenler(a, b):
    n = []
    if any(s.startswith("SERİ KIRILMASI") for s in a.get("notlar", [])):
        n.append("otomatik seri kesme kaldırıldı")
    eski_rq = [d for d in a.get("dip_tarihleri", []) if d.get("yol") == "R-ÇEYREK"]
    yeni_rqe = [d for d in b.get("dip_tarihleri", []) if d.get("yol") == "R-ÇEYREK (EKSİK)"]
    if eski_rq and yeni_rqe:
        n.append("2023 çeyrekleri doğrulanamadı (R-ÇEYREK → EKSİK)")
    if any("KAYNAK İSTİSNASI" in m.get("sonuc", "") for m in b.get("ifna_mutabakat", [])) and \
            not any("KAYNAK İSTİSNASI" in m.get("sonuc", "") for m in a.get("ifna_mutabakat", [])):
        n.append("İFNA: belgeyle düzeltilmiş master CFO kaynak istisnası olarak kullanıldı")
    if b.get("liste", "").startswith("4-") and "dönem eşlemesi" in b.get("neden", ""):
        n.append("dönem eşlemesi şüphesi (yayın gecikmesi deseni)")
    if b.get("ifna_mutabakat_bekliyor"):
        n.append(f"Evo–master İFNA farkı ({b['ifna_mutabakat_bekliyor']}): ilgili nakit kalemleri EKSİK")
    if a.get("liste", "").startswith("DİP KANITI YOK") and b.get("liste") == "DİP DEĞERLENDİRMESİ EKSİK — KISMİ PENCERE":
        n.append("en eski aday dip tarihi değerlendirilemedi → 'dip yok' denmedi")
    pa, pb = a.get("puan_satirlari", {}), b.get("puan_satirlari", {})
    for k in ("A5", "B1", "B2", "C1", "D1", "D3"):
        if k in pa and k in pb and (pa[k]["puan"], pa[k]["durum"], pa[k].get("alt"), pa[k].get("ust")) != \
                (pb[k]["puan"], pb[k]["durum"], pb[k].get("alt"), pb[k].get("ust")):
            n.append(f"{k}: {_sat(pa[k])} → {_sat(pb[k])}")
    return "; ".join(n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eski", required=True)
    ap.add_argument("--yeni", required=True)
    ap.add_argument("--cikti", required=True)
    a = ap.parse_args()
    E = {x["kod"]: x for x in json.load(open(a.eski, encoding="utf-8"))["sirketler"]}
    Y = {x["kod"]: x for x in json.load(open(a.yeni, encoding="utf-8"))["sirketler"]}
    satirlar = []
    for k in sorted(Y):
        e, y = E.get(k, {}), Y[k]
        if not y["kapsam"].startswith("ANA"):
            continue
        liste_degisti = e.get("liste", "").split(" (KISA")[0] != y.get("liste", "").split(" (KISA")[0]
        kuyruk_degisti = e.get("kuyruk") != y.get("kuyruk")
        puan_degisti = (e.get("on_puan_alt"), e.get("on_puan_ust")) != (y.get("on_puan_alt"), y.get("on_puan_ust"))
        if liste_degisti or kuyruk_degisti or puan_degisti:
            satirlar.append({"kod": k, "eski": ozet(e), "yeni": ozet(y), "neden": nedenler(e, y),
                             "tur": "liste" if liste_degisti else ("kuyruk" if kuyruk_degisti else "puan")})
    with open(a.cikti, "w", newline="", encoding="utf-8-sig") as fo:
        w = csv.DictWriter(fo, fieldnames=["kod", "tur", "eski", "yeni", "neden"])
        w.writeheader()
        w.writerows(satirlar)
    print(collections.Counter(s["tur"] for s in satirlar))
    gec = collections.Counter((s["eski"].split(" ·")[0], s["yeni"].split(" ·")[0]) for s in satirlar if s["tur"] == "liste")
    for (x, y), v in gec.most_common():
        print(f"{v:3d}  {x}  →  {y}")


if __name__ == "__main__":
    main()
