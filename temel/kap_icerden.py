"""
KAP 'Pay Alım Satım Bildirimi'lerinden patron / yönetici / ana ortak işlemlerini çıkarır.

Videodaki kural: "Patron hisse satıyorsa genellikle uzak duruyorum ... Tersine patron
alıyorsa önemli." Şirket parasıyla yapılan geri alım bu kapsamda değil.

Veri nasıl çekildi (EVO dokümanlarda_ara / dokuman_chunk_yukle):
  1) filter: dokuman_tipi="kap_haberi" AND kap_bildirim_konu="Pay Alım Satım Bildirimi"
             AND yayinlanma_tarihi_utc >= "<12 ay önce>" AND iliskili_semboller IN [adaylar]
     → 50'lik sayfalarla tüm liste, sonra chunk içerikleri.
  2) MKK üzerinden gelen bildirimlerin (metinde "Kuruluşumuza gönderilen") asıl detayı PDF ekte:
     filter: dokuman_tipi="kap_haber_eki" AND sayfa_no=1 AND kap_bildirim_id IN [...]
     → 2. sayfa chunk id'si genelde 1. sayfa id'si + 1; ikisi birlikte yüklenir.

Girdi (temel/ham/kap/):
  pay_alim_satim_liste.csv   bildirim listesi (son 12 ay, aday şirketler)
  pay_alim_satim_icerik.json bildirim ana metinleri
  ek_liste.json / ek_icerik.json  MKK üzerinden gelen bildirimlerin PDF ekleri
Çıktı:
  ham/kap/icerden_islemler.csv  (her işlem günü bir satır)
  ham/kap/icerden_ozet.csv      (şirket bazında özet)

Sınıflama:
  - Bank of America, Goldman, FMR, yatırım/emeklilik fonları, portföy şirketleri → KURUM (sayılmaz)
  - Kişiler, ana ortak/holding, grup şirketleri, YK üyeleri → İÇERİDEN (patron tarafı)
  - "Pay Devri / Virman / teminat" → DEVİR (piyasa işlemi değil, ayrı gösterilir)
"""
import csv
import json
import os
import re
from collections import defaultdict

import pandas as pd

D = os.path.join(os.path.dirname(__file__), "ham", "kap")
KURUM = re.compile(r"Bank Of America|Bank of America|Goldman|FMR|FIL Limited|Swedbank|HOLD Alap|Arrowstreet|"
                   r"Portföy|yatırım fon|emeklilik|Emeklilik|i-SPK\.15\.2|kurucusu", re.I)
DEVIR = re.compile(r"devr|virman|teminat|bedelsiz pay devri", re.I)


def sayi(s):
    s = s.strip()
    if not s or s == "-":
        return 0.0
    s = s.replace(".", "").replace(",", ".") if "," in s or s.count(".") > 1 else s
    try:
        return float(s)
    except ValueError:
        return 0.0


def ek_parse(txt):
    """MKK PDF ekindeki standart formu ayrıştırır."""
    konu = re.search(r"Konu\s*:?\s*\n?\s*:?\s*(.+)", txt)
    ad = re.search(r"Ad Soyad / Ticaret Ünvanı\s*\n?\s*:\s*(.+)", txt)
    gorev = re.search(r"Görevi\s*\n?\s*:\s*(.+)", txt)
    rows = []
    for m in re.finditer(r"(\d{2}/\d{2}/\d{4}), İşlemlerin Net Nominal Tutarı \(TL\) \( \* \) = (-?[\d\.,]+)", txt):
        tarih = m.group(1)
        al = re.search(re.escape(tarih) + r", Alım İşlemine Konu Payların Toplam Nominal Tutarı \(TL\) = ([\d\.,]+)", txt)
        sat = re.search(re.escape(tarih) + r", Satım İşlemine Konu Payların Toplam Nominal Tutarı \(TL\) = ([\d\.,]+)", txt)
        o1 = re.search(re.escape(tarih) + r", Sahip Olunan Payların Gün Başı Bakiyesinin Sermayeye Oranı \(%\) = ([\d\.,]+)", txt)
        o2 = re.search(re.escape(tarih) + r",\s*Sahip\s+Olunan Payların Gün Sonu Bakiyesinin Sermayeye Oranı \(%\) = ([\d\.,]+)", txt)
        rows.append(dict(tarih=pd.to_datetime(tarih, dayfirst=True).strftime("%Y-%m-%d"),
                         alim=sayi(al.group(1)) if al else 0, satim=sayi(sat.group(1)) if sat else 0,
                         net=(sayi(al.group(1)) - sayi(sat.group(1))) if (al and sat) else sayi(m.group(2)), oran_bas=sayi(o1.group(1)) if o1 else None,
                         oran_son=sayi(o2.group(1)) if o2 else None))
    g = gorev.group(1).strip() if gorev else ""
    if g.startswith("Varsa") or g.startswith("Tüzel"):
        g = ""
    return dict(konu=(konu.group(1).strip(" :") if konu else ""), ad=(ad.group(1).strip() if ad else ""),
                gorev=g, rows=rows)


def tablo_parse(txt):
    """Şirketin/kurumun KAP'a doğrudan girdiği tablo formatı."""
    rows = []
    for m in re.finditer(r"\| (\d{4}-\d{2}-\d{2}) \| ([^|]*) \| ([^|]*) \| ([^|]*) \| ([^|]*) \| ([^|]*) \| ([^|]*) \| ([^|]*) \| ([^|]*) \|", txt):
        al, sat, net = (float(x) if x.strip() else 0.0 for x in (m.group(2), m.group(3), m.group(4)))
        rows.append(dict(tarih=m.group(1), alim=al, satim=sat, net=(al - sat) if (al or sat) else net,
                         oran_bas=float(m.group(7)) if m.group(7).strip() else None,
                         oran_son=float(m.group(9)) if m.group(9).strip() else None))
    acik = re.search(r"### Açıklamalar\s*(.+)", txt, re.S)
    return rows, re.sub(r"\s+", " ", acik.group(1)) if acik else ""


def main(aday_csv):
    aday = set(pd.read_csv(aday_csv).kod)
    liste = {r["chunk_id"]: r for r in csv.DictReader(open(os.path.join(D, "pay_alim_satim_liste.csv"), encoding="utf-8"))}
    ana = json.load(open(os.path.join(D, "pay_alim_satim_icerik.json"), encoding="utf-8"))
    ekl = json.load(open(os.path.join(D, "ek_liste.json"), encoding="utf-8"))
    eki = json.load(open(os.path.join(D, "ek_icerik.json"), encoding="utf-8"))

    kap2sym = {int(r["kap_bildirim_id"]): [s for s in r["semboller"].split() if s in aday] for r in liste.values()}
    islemler = []

    # 1) MKK ekleri
    for cid, meta in ekl.items():
        if meta["sayfa"] != 1:
            continue
        txt = eki.get(cid, "")
        nxt = eki.get(str(int(cid) + 1), "")
        if nxt and not nxt.lstrip().startswith("Konu") and "Nominal Tutarı" in nxt:
            txt += "\n" + nxt
        p = ek_parse(txt)
        tip = "DEVIR" if DEVIR.search(p["konu"]) else ("KURUM" if KURUM.search(p["ad"]) else "ICERIDEN")
        for s in kap2sym.get(meta["kap"], []):
            for r in p["rows"]:
                islemler.append(dict(kod=s, kaynak="MKK", tip=tip, kim=p["ad"], gorev=p["gorev"],
                                     kap_bildirim_id=meta["kap"], **r))

    # 2) Tablo formatlı bildirimler (şirket/kurum kendisi girmiş)
    for cid, txt in ana.items():
        if "Kuruluşumuza gönderilen" in txt:
            continue
        rows, acik = tablo_parse(txt)
        if KURUM.search(acik) or "Pay Sahipliği" in txt[:200]:
            tip = "KURUM"
        elif DEVIR.search(acik[:300]):
            tip = "DEVIR"
        else:
            tip = "ICERIDEN"
        semboller = liste[cid]["semboller"].split()
        kim = f"[{semboller[0]} bildirimi] " + acik[:110]
        hedef = kap2sym.get(int(liste[cid]["kap_bildirim_id"]), [])
        # Ana ortak, bağlı ortaklığının/iştirakinin hissesinde işlem bildiriyorsa: bildirimi yapan (ilk sembol)
        # kendi hissesinde işlem yapmış sayılmaz.
        if len(semboller) > 1 and re.search(r"[Bb]ağlı ortaklıklarımız|[Dd]olaylı [İi]ştiraki|Şirketimizin .{0,80}sermayesinde sahip", acik):
            hedef = [x for x in hedef if x != semboller[0]]
        for s in hedef:
            for r in rows:
                if r["alim"] == 0 and r["satim"] == 0 and r["net"] == 0:
                    continue
                islemler.append(dict(kod=s, kaynak="KAP", tip=tip, kim=kim, gorev="",
                                     kap_bildirim_id=int(liste[cid]["kap_bildirim_id"]), **r))

    df = pd.DataFrame(islemler)
    # Düzeltme bildirimleri ve aynı işlemin birden çok kanaldan gelmesi → tekilleştir
    df["kim_n"] = df["kim"].str.upper().str.replace(r"[^A-ZÇĞİÖŞÜ]", "", regex=True).str[:25]
    df = df.drop_duplicates(subset=["kod", "kim_n", "tarih", "alim", "satim"])
    # Ana ortak ile bağlı ortaklığı aynı işlemi ayrı ayrı bildirebiliyor (doğrudan + dolaylı).
    # Aynı gün, aynı tutar, iki farklı ŞİRKET → tek işlem say (kişileri birleştirme).
    sirket = df["kim"].str.contains(r"A\.Ş|ANON[İI]M|HOLD[İI]NG", case=False, regex=True)
    tekrar = sirket & df.duplicated(subset=["kod", "tarih", "alim", "satim"], keep=False) & (df["alim"] + df["satim"] > 0)
    df = pd.concat([df[~tekrar], df[tekrar].drop_duplicates(subset=["kod", "tarih", "alim", "satim"])]).drop(columns="kim_n")
    df.to_csv(os.path.join(D, "icerden_islemler.csv"), index=False)

    # Şirket bazında özet (sadece İÇERİDEN; DEVİR ayrı sayılır)
    p = pd.read_csv(os.path.join(os.path.dirname(__file__), "ham", "piyasa.csv"))
    p["sermaye"] = p["piyasa_degeri"] / p["son_fiyat"]
    ic = df[df.tip == "ICERIDEN"]
    oz = ic.groupby("kod").agg(icerden_net_nominal=("net", "sum"), icerden_alim_gun=("alim", lambda x: (x > 0).sum()),
                               icerden_satim_gun=("satim", lambda x: (x > 0).sum()),
                               icerden_kimler=("kim", lambda x: "; ".join(sorted(set(k[:60] for k in x))))).reset_index()
    dv = df[df.tip == "DEVIR"].groupby("kod").size().rename("devir_bildirim").reset_index()
    oz = oz.merge(dv, on="kod", how="outer").merge(p[["kod", "sermaye", "son_fiyat"]], on="kod", how="left")
    oz["icerden_net_sermaye_yuzde"] = 100 * oz["icerden_net_nominal"] / oz["sermaye"]
    oz["icerden_net_tl_yaklasik"] = oz["icerden_net_nominal"] * oz["son_fiyat"]
    oz.drop(columns=["sermaye", "son_fiyat"]).to_csv(os.path.join(D, "icerden_ozet.csv"), index=False)
    print(f"{len(df)} işlem satırı | içeriden: {len(ic)} | şirket: {oz.kod.nunique()}")
    return oz


if __name__ == "__main__":
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "results", "temel", "latest_on_eleme.csv"))
