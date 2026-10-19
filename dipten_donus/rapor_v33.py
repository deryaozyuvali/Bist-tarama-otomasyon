"""Pilot sonuç raporu (Markdown + CSV) — tarama_v33.py çıktısından üretilir.

Kullanım: python rapor_v33.py --sonuc sonuc.json --referans efk113.csv --cikti klasor
"""
import argparse
import collections
import csv
import json
import os


def yuzde(x):
    return "" if x is None else f"{x * 100:.1f}%"


def kisa_kanit(dip):
    return f"{dip['donem']} ({dip['yol']}{', zayıf ref.' if dip.get('zayif') else ''}; {'+'.join(dip['kanit'])})"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sonuc", required=True)
    ap.add_argument("--referans", required=True)
    ap.add_argument("--cikti", required=True)
    a = ap.parse_args()
    veri = json.load(open(a.sonuc, encoding="utf-8"))
    S = veri["sirketler"]
    by = {x["kod"]: x for x in S}
    ana = [x for x in S if x["kapsam"].startswith("ANA")]
    C = collections.Counter(x["liste"] for x in ana)

    havuz = [x for x in ana if x["liste"].startswith("1-")]
    havuz.sort(key=lambda x: (x["kuyruk"], -x["on_puan_alt"], -x["on_puan_ust"]))
    sinir = [x for x in ana if x["liste"].startswith("2-")]
    kisa = [x for x in havuz if "KISA" in x["liste"]]
    dipsiz = [x for x in ana if x["liste"].startswith("3-")]
    eksik = [x for x in ana if x["liste"].startswith("4-")]
    bayat = [x for x in ana if any(n.startswith("BAYAT") for n in x.get("notlar", []))]

    L = []
    w = L.append
    w("# Dipten Dönüş v3.3 — Pilot Sonuçları")
    w("")
    w("Veri: Evo (çekim 19.10.2026), son dönem çoğunlukla 2026/06. FCF: FCF_MASTER.xlsx (GEM v6.2 / FCF v2.2, kullanıcının onaylı standardı).")
    w("")
    w("## Özet")
    w("")
    w(f"- Ana evren: **{len(ana)}** şirket (kapsam dışı: {sum(1 for x in S if not x['kapsam'].startswith('ANA'))}).")
    w(f"- 1) Aday havuzu: **{len(havuz)}** (bunların {len(kisa)}'i kısa geçmişli aday) — Kuyruk 1: {sum(x['kuyruk']==1 for x in havuz)}, Kuyruk 2: {sum(x['kuyruk']==2 for x in havuz)}, Kuyruk 3: {sum(x['kuyruk']==3 for x in havuz)}")
    w(f"- 2) Tek koşulla sınırda: **{len(sinir)}** (erken sinyal: {C['2-SINIRDA (erken sinyal)']}, dip: {C['2-SINIRDA (dip)']})")
    w(f"- 3) Kısa geçmişli aday: {len(kisa)} · Dip doğrulanamadı / toparlanma izlemesi: **{len(dipsiz)}**")
    w(f"- 4) Veri eksiği nedeniyle değerlendirilemeyen: **{len(eksik)}** (+ {len(bayat)} şirket bayat dönemle değerlendirildi)")
    w(f"- Diğer: dip var ama sinyal yok {C['DİP VAR, SİNYAL YOK']}, bu modelde dip kanıtı yok {C['DİP KANITI YOK']}, "
      f"dip değerlendirmesi eksik — kısmi pencere (değerlendirilebilen tarihlerde dip kanıtı bulunmadı) {C['DİP DEĞERLENDİRMESİ EKSİK — KISMİ PENCERE']}")
    w("")

    # 1
    w("## 1) Aday havuzu")
    w("")
    w("Sıra: kuyruk, sonra ön puan alt sınırı. Ön puan = A1–A5, B1, B2, B4, C1, D1, D3 (azami 65). "
      "C1 ve D1 bu koşuda EKSİK (tanımlı net borç ve emsal sepeti yok); D3 yalnızca onaylı FCF ≤ 0 ise 0, aksi halde EKSİK. "
      "Teyit sütunları yalnız sayısal kısımdır; belge kısmı (op. teyit 4. madde, B3) bekleniyor.")
    w("")
    w("| # | Kod | Sektör | Dip (dönem, yol, kanıt) | Sinyal | Ön puan | Kuyruk | Op. teyit (sayısal) | Nakit teyit (sayısal) | B4 (FCF) | Risk işaretleri |")
    w("|---|---|---|---|---|---|---|---|---|---|---|")
    for i, x in enumerate(havuz, 1):
        b4 = x["puan_satirlari"]["B4"]
        b4s = f"{b4['puan']:g}" if b4["durum"] == "HESAPLANDI" else f"? ({b4['alt'] or 0:g}–{b4['ust'] if b4['ust'] is not None else 5:g})"
        etk = " · kısa geçmiş" if "KISA" in x["liste"] else ""
        w(f"| {i} | {x['kod']} | {x['sektor']} | {kisa_kanit(x['dip'])}{etk} | {'+'.join(x['erken_sinyal_yolu'])} | "
          f"{x['on_puan_alt']:g}–{x['on_puan_ust']:g} | {x['kuyruk']} | {'✓' if x['op_teyit_sayisal'] else '–'} | "
          f"{x['nakit_teyit_sayisal'] if isinstance(x['nakit_teyit_sayisal'], str) else ('✓' if x['nakit_teyit_sayisal'] else '–')} | {b4s} | {', '.join(x['risk_isaretleri']) or '–'} |")
    w("")

    # 2
    w("## 2) Tek koşul nedeniyle sınırda kalanlar")
    w("")
    w("Puansız, aday havuzunda değil. Amaç yanlış elemeyi görmek.")
    w("")
    w("| Kod | Sektör | Liste | Kaçırılan koşul |")
    w("|---|---|---|---|")
    for x in sorted(sinir, key=lambda x: (x["liste"], x["kod"])):
        w(f"| {x['kod']} | {x['sektor']} | {x['liste'][12:].strip('() ')} | {x.get('neden', '')} |")
    w("")
    neden_say = collections.Counter()
    for x in sinir:
        if "erken" in x["liste"]:
            for parca in x["neden"].split("; "):
                neden_say[parca.split("'")[1] if "'" in parca else parca] += 1
        else:
            neden_say["dip: tek kanıt (" + x["neden"].split("yalnızca ")[1].split(" ")[0] + ")"] += 1
    w("Kaçırılan koşulların dağılımı:")
    w("")
    for k, v in neden_say.most_common():
        w(f"- {k}: {v}")
    w("")

    # 3
    w("## 3) Kısa geçmişli adaylar ve dip doğrulanamayan toparlanma izlemeleri")
    w("")
    w("Kısa geçmişli adaylar (aday havuzunda, etiketli):")
    w("")
    for x in kisa:
        w(f"- **{x['kod']}** ({x['sektor']}): dip {kisa_kanit(x['dip'])}, ham çeyrek {x['n_ham_ceyrek']}"
          + ("; " + "; ".join(n for n in x.get("notlar", []) if n.startswith("İNCELEME")) if any(n.startswith("İNCELEME") for n in x.get("notlar", [])) else ""))
    w("")
    w("Dip doğrulanamadı — geçmiş sınırlı / toparlanma izlemesi (puansız):")
    w("")
    for x in dipsiz:
        w(f"- **{x['kod']}** ({x['sektor']}): {x.get('neden', '')}; " + "; ".join(x.get("notlar", [])))
    w("")

    # 4
    w("## 4) Veri eksikliği nedeniyle değerlendirilemeyenler")
    w("")
    for x in eksik:
        w(f"- **{x['kod']}** ({x['sektor']}): {x.get('neden', '')}" + ("; " + "; ".join(x.get("notlar", [])) if x.get("notlar") else ""))
    w("")
    w("Bayat dönemle değerlendirilenler (raporu henüz 2026/06 değil): " + ", ".join(f"{x['kod']} ({x.get('son_donem')})" for x in bayat))
    w("")

    # Referans karşılaştırma
    ref = list(csv.DictReader(open(a.referans, encoding="utf-8-sig")))
    w("## Önceki EFK+FCF operasyonel sinyal listesiyle (113 şirket, 09.10.2026) karşılaştırma")
    w("")
    w("Bu liste doğruluk ölçütü değildir; farklı tanımlarla (EFK tanımı ve Haziran-Haziran karşılaştırma) kurulmuştur.")
    w("")
    rc = collections.Counter()
    satir = []
    for r in ref:
        x = by.get(r["Kod"])
        l = x["liste"] if x else "Evo tablosunda yok"
        lk = l.split(" (KISA")[0]
        rc[lk] += 1
        if not lk.startswith("1-"):
            satir.append((r["Alt grup"], r["Kod"], r["EFK grubu"], l, x.get("neden", "") if x else ""))
    for k, v in rc.most_common():
        w(f"- {k}: {v}")
    w("")
    w("| Önceki alt grup | Kod | Önceki EFK grubu | Bu pilot | Neden |")
    w("|---|---|---|---|---|")
    for s in satir:
        w("| " + " | ".join(s) + " |")
    w("")

    os.makedirs(a.cikti, exist_ok=True)
    open(os.path.join(a.cikti, "pilot_rapor_v33.md"), "w", encoding="utf-8").write("\n".join(L))

    # CSV
    with open(os.path.join(a.cikti, "pilot_sonuc_v33.csv"), "w", newline="", encoding="utf-8-sig") as fo:
        cw = csv.writer(fo)
        cols = ["kod", "sektor", "kapsam", "liste", "son_donem", "n_ham_ceyrek", "dip", "erken_sinyal_yolu",
                "on_puan_alt", "on_puan_ust", "uygulanamaz_kapasite", "kuyruk", "op_teyit_sayisal", "nakit_teyit_sayisal",
                "ttm_favok_marji", "ttm_efk_marji", "ttm_ifna_marji", "ifna_mutabakat_bekliyor", "risk_isaretleri", "neden", "notlar"] + \
               [f"{k}_{f}" for k in ("A1", "A2", "A3", "A4", "A5", "B1", "B2", "B4", "C1", "D1", "D3") for f in ("puan", "durum", "not")]
        cw.writerow(cols)
        for x in S:
            row = []
            for c in cols[:21]:
                v = x.get(c, "")
                if c == "dip" and v:
                    v = kisa_kanit(v)
                elif c in ("ttm_favok_marji", "ttm_efk_marji", "ttm_ifna_marji"):
                    v = yuzde(v) if v != "" else ""
                elif isinstance(v, list):
                    v = "; ".join(map(str, v))
                row.append(v)
            for k in ("A1", "A2", "A3", "A4", "A5", "B1", "B2", "B4", "C1", "D1", "D3"):
                p = x.get("puan_satirlari", {}).get(k, {})
                row += [p.get("puan", ""), p.get("durum", ""), p.get("not", "")]
            cw.writerow(row)
    print("ok", len(havuz), len(sinir), len(kisa), len(dipsiz), len(eksik))


if __name__ == "__main__":
    main()
