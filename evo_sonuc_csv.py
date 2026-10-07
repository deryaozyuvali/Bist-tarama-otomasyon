"""
EVO `veri_sorgula` sonucunu (JSON: row_count + markdown tablo) CSV'ye çevirir
ve okunabilir uyarı/bayrak sütunları ekler.

    python evo_sonuc_csv.py <evo_sonuc.txt> <cikti.csv>
"""
import csv
import json
import sys

UYARI = [("ALACAK", "u_alacak"), ("TMS38", "u_tms38"),
         ("MARJ_OYNAK", "u_oynak"), ("TEMETTU_YOK", "u_temettu")]
BAYRAK = [("ZARAR_AMA_FAVOK", "b_zarar_ama_favok"), ("DIGER_GELIR", "b_diger_gelir"),
          ("ISTIRAK_ZARARI", "b_istirak_zarari"), ("DURDURULAN", "b_durdurulan"),
          ("FINANSAL_GELIR", "b_finansal_gelir")]


def oku(yol):
    d = json.loads(open(yol, encoding="utf-8").read())
    if isinstance(d, list):              # MCP içerik zarfı
        d = json.loads(d[0]["text"])
    satirlar = d["table"].split("\n")
    hdr = [c.strip() for c in satirlar[0].strip("|").split("|")]
    veri = [[c.strip() for c in s.strip("|").split("|")]
            for s in satirlar[2:] if s.strip()]
    assert all(len(r) == len(hdr) for r in veri), "sütun sayısı tutmuyor"
    return d, hdr, veri


if __name__ == "__main__":
    d, hdr, veri = oku(sys.argv[1])
    kayit = [dict(zip(hdr, r)) for r in veri]
    for r in kayit:
        r["uyari"] = " ".join(a for a, c in UYARI if r.get(c, "0") not in ("", "0"))
        r["bayrak"] = " ".join(a for a, c in BAYRAK if r.get(c) == "X")
    with open(sys.argv[2], "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=hdr + ["uyari", "bayrak"])
        w.writeheader()
        w.writerows(kayit)
    print(f"{len(kayit)} satır → {sys.argv[2]}  (notlar: {d.get('notes')})")
