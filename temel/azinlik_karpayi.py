"""
Kâr payı dağıtım tablolarından (KAP 'Kar Payı Dağıtım İşlemlerine İlişkin Bildirim', 2025 dönemi)
azınlık aleyhine olabilecek kalemleri çıkarır. Videoda: kâr payı imtiyazı, vakfa/bağış, patronun
şirket kârını kendi lehine kullanması ("bardağın altı delik").

Veri nasıl çekildi (EVO dokumanlarda_ara / dokuman_chunk_yukle):
  filter: dokuman_tipi="kap_haberi" AND kap_bildirim_konu="Kar Payı Dağıtım İşlemlerine İlişkin Bildirim"
          AND yayinlanma_tarihi_utc >= "2026-01-01" AND iliskili_semboller IN [adaylar]
Çıktı: ham/azinlik/karpayi_ozet.csv
"""
import csv, json, os, re
import pandas as pd

D = os.path.join(os.path.dirname(__file__), "ham", "azinlik")


def sayi(s):
    s = (s or "").strip().replace(" ", "")
    if not s or s in "-–":
        return 0.0
    neg = s.startswith("(") or s.startswith("-")
    s = s.strip("()-")
    # TR biçimi: 1.234.567,89 ; EN biçimi: 1,234,567.89 ; düz: 1234567
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".") if len(s.split(",")[-1]) <= 2 else s.replace(",", "")
    elif s.count(".") > 1 or (s.count(".") == 1 and len(s.split(".")[-1]) == 3):
        s = s.replace(".", "")
    try:
        v = float(s)
    except ValueError:
        return 0.0
    return -v if neg else v


def satir(txt, desen, sutun=1):
    """'| 9. Yıl İçinde Yapılan Bağışlar ( + ) | 36.083.000 |  |' → SPK (1) veya yasal kayıt (2) sütunu."""
    m = re.search(r"\|\s*" + desen + r"[^|]*\|\s*([^|]*)\|\s*([^|\n]*)", txt, re.I)
    return sayi(m.group(sutun)) if m else 0.0


def parse(txt):
    imt = re.search(r"kâr dağıtımında imtiyaz var ise söz konusu imtiyaza ilişkin bilgi\s*\|\s*([^|]*)\|", txt, re.I)
    imt = imt.group(1).strip() if imt else ""
    r = dict(
        imtiyaz_metni=imt,
        net_donem_kari=satir(txt, r"5\.\s*Net Dönem K[âa]r"),
        net_donem_kari_yasal=satir(txt, r"5\.\s*Net Dönem K[âa]r", 2),
        bagis=satir(txt, r"9\.\s*Yıl İçinde Yapılan Bağış"),
        imtiyazli_kar_payi=satir(txt, r"12\.\s*İmtiyazlı Pay"),
        calisanlara=satir(txt, r"\*\s*Çalışanlara"),
        yk_uyelerine=satir(txt, r"\*\s*Yönetim Kurulu Üyelerine"),
        pay_sahibi_disi=satir(txt, r"\*\s*Pay Sahibi Dışındaki"),
        birinci_kar_payi=satir(txt, r"11\.\s*Ortaklara Birinci"),
        ikinci_kar_payi=satir(txt, r"15\.\s*Ortaklara İkinci"),
    )
    # Pay grubu başına BRÜT tutar (Nakit Kar Payı Ödeme Tutar ve Oranları). Net tutar stopaj yüzünden
    # gruplar arasında farklı çıkabilir (tüzel kişi ortaklar stopajsız) → imtiyaz sanılmasın.
    gruplar = {}
    m = re.search(r"Nakit Kar Payı Ödeme Tutar ve Oranları(.*?)(?:\n\n[^|]|\Z)", txt, re.S)
    if m:
        for l in m.group(1).split("\n"):
            c = [x.strip() for x in l.strip().strip("|").split("|")]
            if len(c) >= 3 and "Grub" in c[0] and c[1] in ("Peşin", "TOPLAM", "Toplam"):
                gruplar[c[0].split(",")[0]] = sayi(c[2])
    r["grup_brut_pay_basi"] = json.dumps(gruplar, ensure_ascii=False)
    vals = [v for v in gruplar.values() if v > 0]
    r["grup_farkli"] = bool(vals) and (max(vals) - min(vals)) / max(vals) > 0.01  # %1 tolerans (yuvarlama)
    return r


def main():
    liste = {r["chunk_id"]: r for r in csv.DictReader(open(os.path.join(D, "karpayi_liste.csv"), encoding="utf-8"))}
    ic = json.load(open(os.path.join(D, "karpayi_icerik.json"), encoding="utf-8"))
    rows = []
    for cid, txt in ic.items():
        if not re.search(r"5\.\s*Net Dönem K[âa]r", txt):
            continue
        r = parse(txt)
        r.update(kod=liste[cid]["kod"], tarih=liste[cid]["tarih"], kap_bildirim_id=liste[cid]["kap_bildirim_id"])
        rows.append(r)
    df = pd.DataFrame(rows).sort_values(["kod", "tarih"])
    # Şirket başına: tablolu son bildirim (genel kurulda kesinleşen hali genelde sondadır)
    son = df.groupby("kod").tail(1).copy()
    yok = re.compile(r"^(-|0|yok|yoktur|bulunmama|.*imtiyaz (yok|bulunmama)|.*imtiyazı bulunmama|.*imtiyazlı pay grubu yoktur|kar dağıtımında imtiyaz yok)", re.I)
    son["imtiyaz_beyan"] = son["imtiyaz_metni"].apply(lambda x: "YOK" if (not x or yok.search(x.strip())) else "VAR/BELİRSİZ")
    son["yk_calisan_kar_payi"] = son["yk_uyelerine"] + son["calisanlara"] + son["pay_sahibi_disi"]
    # TMS 29 nedeniyle SPK net kârı yasal kârdan çok farklı olabiliyor → büyük olanı payda yap
    nk = son[["net_donem_kari", "net_donem_kari_yasal"]].max(axis=1)
    nk = nk.where(nk > 0)
    son["bagis_net_kar_orani"] = son["bagis"] / nk
    son["yk_calisan_net_kar_orani"] = son["yk_calisan_kar_payi"] / nk
    son["imtiyazli_net_kar_orani"] = son["imtiyazli_kar_payi"] / nk
    son["tablo_tutarsiz"] = son["bagis_net_kar_orani"] > 1  # şirket tabloyu kaydırmış (ör. bağış satırında başka tutar)
    son.loc[son["tablo_tutarsiz"], "bagis_net_kar_orani"] = float("nan")
    son.to_csv(os.path.join(D, "karpayi_ozet.csv"), index=False)
    print(len(df), "tablolu bildirim |", len(son), "şirket")
    return son


if __name__ == "__main__":
    s = main()
    pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 70)
    print(s[(s.imtiyaz_beyan != "YOK") | (s.imtiyazli_kar_payi > 0) | (s.yk_calisan_kar_payi > 0) | s.grup_farkli]
          [["kod", "imtiyaz_metni", "imtiyazli_kar_payi", "yk_calisan_kar_payi", "yk_calisan_net_kar_orani", "grup_farkli", "grup_brut_pay_basi"]].to_string())
    print(s.sort_values("bagis_net_kar_orani", ascending=False)[["kod", "bagis", "net_donem_kari", "bagis_net_kar_orani"]].head(15).to_string())
