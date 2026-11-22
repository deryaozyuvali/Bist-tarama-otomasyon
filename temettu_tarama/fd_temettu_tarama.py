"""
FD / Temettü ("kira çarpanı") taraması — v1
-------------------------------------------
Yayıncının yöntemi: Bir şirketi ev gibi düşün. Ödediğin gerçek bedel (Firma Değeri,
"düzeltilmiş değer") kaç yılda, şirketin cebine koyacağı TEMETTÜLERLE geri döner?
  * ≤ 10 yıl  -> kabul, 3-5 yıl çok iyi
  * > 10 yıl  -> sorun (istisnai durumda 15'e kadar esnetilir)

Girdi 1: evo_ham_*.csv   (EVO / Fintables SQL çıktısı, mn TL)
Girdi 2: FCF_MASTER xlsx (ANA sayfası: FCF TTM, statü, Funnel MIN)

Kullanım: python3 fd_temettu_tarama.py <evo_ham.csv> <FCF_MASTER.xlsx> <cikti.xlsx>
"""
import csv
import sys

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

HOLDING_KODLARI = {"KCHOL", "SAHOL", "AGHOL", "ALARK", "DOHOL", "GLYHO", "GOLTS"}


def nakit_iskontosu(n_tem: int, n_kar: int) -> float:
    """Videodaki 'gece kulübü' kuralı: kasadaki nakde ne kadar güveniyoruz?
    5/5 yıl temettü + 5/5 yıl kâr -> %95 ; 4 yıl -> %70 ; 3 yıl -> %40 ; daha az -> %10"""
    s = min(n_tem, n_kar)
    return {5: 0.95, 4: 0.70, 3: 0.40}.get(s, 0.10)


def oku_evo(yol):
    with open(yol, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k, v in r.items():
            if k != "kod":
                r[k] = float(v) if v not in ("", None) else 0.0
        r["n_tem"] = int(r["n_tem"])
        r["n_kar"] = int(r["n_kar"])
    return rows


def oku_fcf(yol):
    wb = openpyxl.load_workbook(yol, data_only=True, read_only=True)
    ws = wb["ANA"]
    out = {}
    for row in ws.iter_rows(min_row=5, values_only=True):
        kod = row[0]
        if not kod:
            continue
        out[kod] = {
            "tip": row[3], "sektor": row[4], "unvan": row[1],
            "fcf_0326": row[9], "fcf_0626": row[10], "fcf_0926": row[11],
            "fcf_statu": row[18], "funnel": row[24], "funnel_kat": row[30],
        }
    return out


def hesapla(r, fcf):
    kod = r["kod"]
    f = fcf.get(kod, {})
    kira = min(r["rou"], r["fb"])                   # kira yükümlülüğü ≈ kullanım hakkı varlığı
    fin_borc = r["fb"] - kira                        # banka kredisi + tahvil
    geri_alim = abs(r["gap"])                        # geri alınmış paylar (maliyet bedeli)
    h = nakit_iskontosu(r["n_tem"], r["n_kar"])
    pd_duz = r["pd"] - geri_alim
    fd = pd_duz - r["nakit"] * h + fin_borc

    # Dağıtım oranı: son 12 ayda ödenen temettü (büyük kısmı 2025 kârından) / 2025 net kârı.
    # 3 yıllık ortalama TMS29 nedeniyle yanıltıcı (nominal temettü / enflasyonla şişmiş eski kâr).
    kar3 = r["np23"] + r["np24"] + r["np25"]
    if r["np25"] > 0 and r["d12"] > 0:
        payout = r["d12"] / r["np25"]
    elif kar3 > 0:
        payout = r["d3y"] / kar3
    elif r["np_ttm"] > 0:
        payout = r["d12"] / r["np_ttm"]
    else:
        payout = 0.0
    payout = max(0.0, min(payout, 1.0))
    tem_tahmin = r["np_ttm"] * payout                # bu yıl dağıtılabilecek temettü
    tem_baz = max(tem_tahmin, 0.0)

    def oran(a, b):
        return round(a / b, 1) if b and b > 0 else None

    fd_tem_gecmis = oran(fd, r["d12"])
    fd_tem_tahmin = oran(fd, tem_baz)
    fd_nk = oran(fd, r["np_ttm"])
    pd_tem = oran(r["pd"], r["d12"])

    fcf09 = f.get("fcf_0926")
    fcf_kapsama = round(fcf09 / tem_baz, 2) if isinstance(fcf09, (int, float)) and tem_baz > 0 else None
    fcf_poz3 = sum(1 for k in ("fcf_0326", "fcf_0626", "fcf_0926")
                   if isinstance(f.get(k), (int, float)) and f[k] > 0)

    bayrak = []
    if kod in HOLDING_KODLARI or (f.get("tip") or "").lower().startswith("holding"):
        bayrak.append("HOLDİNG: konsolide FD yanıltır, solo/NAV bak")
    if r["n_kar"] < 5:
        bayrak.append(f"Son 5 yılın {5 - r['n_kar']}'inde zarar")
    if r["n_tem"] < 5:
        bayrak.append(f"Son 5 yılın {5 - r['n_tem']}'inde temettü yok")
    if r["d12"] == 0:
        bayrak.append("Son 12 ayda temettü yok")
    if fd < 0:
        bayrak.append("FD negatif (nakit > PD+borç) — veri/varlık kontrolü")
    if f.get("fcf_statu") in ("KOŞULLU", "NULL"):
        bayrak.append(f"FCF statü {f.get('fcf_statu')}")
    if fcf_kapsama is not None and fcf_kapsama < 1:
        bayrak.append("FCF temettüyü karşılamıyor")
    if not f:
        bayrak.append("FCF master'da yok")

    # ---- Sınıflama ----
    temiz = (r["n_tem"] == 5 and r["n_kar"] == 5 and kod not in HOLDING_KODLARI and fd > 0)
    fcf_ok = (fcf_kapsama is not None and fcf_kapsama >= 1.0
              and f.get("fcf_statu") not in ("KOŞULLU", "NULL"))
    ana = [x for x in (fd_tem_gecmis, fd_tem_tahmin) if x is not None]
    en_kotu = max(ana) if len(ana) == 2 else None

    if temiz and en_kotu is not None and en_kotu <= 10 and fcf_ok:
        sinif = "A · ≤10 yıl + FCF karşılıyor"
    elif temiz and en_kotu is not None and en_kotu <= 10:
        sinif = "B · ≤10 yıl, FCF teyidi zayıf"
    elif temiz and en_kotu is not None and en_kotu <= 15:
        sinif = "C · 10–15 yıl (istisna bandı)"
    elif fd_tem_tahmin is not None and fd_tem_tahmin <= 10:
        sinif = "D · ucuz ama geçmiş/yapı sorunlu"
    else:
        sinif = "E · >15 yıl ya da hesaplanamaz"

    return {
        "Kod": kod, "Ünvan": f.get("unvan"), "Sektör": f.get("sektor"), "Son bilanço": int(r["don"]),
        "Sınıf": sinif,
        "FD/Temettü (son 12 ay)": fd_tem_gecmis, "FD/Temettü (tahmin)": fd_tem_tahmin,
        "FD/Net kâr (TTM)": fd_nk, "PD/Temettü": pd_tem,
        "Temettü verimi FD'ye (%)": round(100 * r["d12"] / fd, 1) if fd > 0 else None,
        "PD (mn)": r["pd"], "Geri alınan pay (mn)": geri_alim, "Nakit (mn)": r["nakit"],
        "Nakit iskontosu": h, "Finansal borç (kira hariç, mn)": round(fin_borc),
        "Kira yük. tahmini (mn)": round(kira), "FD düzeltilmiş (mn)": round(fd),
        "Net kâr TTM (mn)": r["np_ttm"], "Dağıtım oranı": round(payout, 2),
        "Temettü son 12 ay (mn)": r["d12"], "Temettü tahmini (mn)": round(tem_baz),
        "Kâr yılı (5)": r["n_kar"], "Temettü yılı (5)": r["n_tem"],
        "FCF TTM 2026/09 (mn)": fcf09, "FCF statü": f.get("fcf_statu"),
        "FCF>0 son 3 dönem": fcf_poz3, "FCF / Temettü": fcf_kapsama,
        "Funnel MIN 2026/09": f.get("funnel"), "Funnel kategori": f.get("funnel_kat"),
        "Bayraklar": " | ".join(bayrak),
    }


YONTEM = [
    ("Fikir", "Hisseyi kiralık ev gibi düşün: ödediğin gerçek bedel (Firma Değeri) kaç yılda temettüyle geri döner? Hedef ≤10 yıl, 3–5 yıl çok iyi."),
    ("Evren", "EVO standart şablon şirketleri; son 5 takvim yılının (2022–2026) en az 3'ünde nakit temettü + TTM ana ortaklık kârı > 0. Banka/sigorta/leasing hariç (FD kavramı uymaz)."),
    ("PD", "hisse_senetleri.piyasa_degeri − geri alınmış paylar (bilanço maliyet bedeli). Yayıncı: geri alınan pay yok sayılır."),
    ("Finansal borç", "KV+UV 'Finansal Borçlar' − kira yükümlülüğü. Kira yükümlülüğü ≈ 'Kullanım Hakkı Varlıkları' (EVO'da ayrı kira satırı yok; GRSEL'de video 362 mn, bu yaklaşım 373 mn verdi)."),
    ("Nakit iskontosu", "Kasadaki nakde güven: 5/5 yıl kâr+temettü %95, 4 yıl %70, 3 yıl %40, altı %10 (videodaki 'gece kulübü' kuralı)."),
    ("FD", "PD_düz − Nakit × iskonto + Finansal borç (kira hariç)."),
    ("Net kâr", "Ana ortaklık payı, TTM. 6 ay ×2 yerine TTM kullanıldı → mevsimsellik sorunu (Datça pansiyonu örneği) otomatik çözülür."),
    ("Temettü tahmini", "TTM net kâr × dağıtım oranı. Oran = son 12 ayda ödenen temettü / 2025 net kârı (yoksa 2024–26 temettü / 2023–25 kâr), [0,1] aralığında. 3 yıllık ortalama TMS29 yüzünden düşük çıkıyor."),
    ("Sınıf A", "5/5 yıl kâr, 5/5 yıl temettü, holding değil; FD/Temettü hem son 12 ay hem tahminde ≤10; FCF TTM (GEM v6.2 master) temettü tahmininin en az 1 katı ve statü KESİN/TÜRETİLMİŞ."),
    ("Sınıf B", "A ile aynı ama FCF teyidi yok/zayıf."),
    ("Sınıf C", "10–15 yıl (yayıncının 'istisna' bandı)."),
    ("Sınıf D", "Tahmini FD/Temettü ≤10 ama kâr/temettü geçmişi kesintili, holding ya da FD negatif → elle inceleme."),
    ("Bilinen sınırlar", "Geçmiş temettüler nominal TL (TMS29 sonrası bilanço ise cari alım gücü); yayıncı USD bazında düşünür. Geri alınan paylar maliyet bedeliyle düşüldü (adet yok). İmtiyazlı pay, ilişkili taraf alacakları, stok/alacak düzeltmesi elle bakılacak başlıklar. 10 yıllık temettü projeksiyonu yapılmadı: tek yıl 'bugünkü kira' ölçüsü."),
]


def yaz(sonuc, yol):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "SONUC"
    basl = list(sonuc[0].keys())
    ws.append(basl)
    renk = {"A": "C6EFCE", "B": "E2EFDA", "C": "FFF2CC", "D": "FCE4D6", "E": "EDEDED"}
    for s in sonuc:
        ws.append([s[k] for k in basl])
        fill = PatternFill("solid", fgColor=renk[s["Sınıf"][0]])
        ws.cell(ws.max_row, basl.index("Sınıf") + 1).fill = fill
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="305496")
        c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "C2"
    ws.auto_filter.ref = ws.dimensions
    for i, k in enumerate(basl, 1):
        ws.column_dimensions[get_column_letter(i)].width = 60 if k == "Bayraklar" else (34 if k in ("Ünvan", "Sınıf") else 13)

    ws2 = wb.create_sheet("YONTEM")
    ws2.append(["Başlık", "Açıklama"])
    for r in YONTEM:
        ws2.append(list(r))
    ws2.column_dimensions["A"].width = 18
    ws2.column_dimensions["B"].width = 140
    for c in ws2[1]:
        c.font = Font(bold=True)
    wb.save(yol)


def main():
    evo, fcf_yol, cikti = sys.argv[1], sys.argv[2], sys.argv[3]
    fcf = oku_fcf(fcf_yol)
    sonuc = [hesapla(r, fcf) for r in oku_evo(evo)]
    sira = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4}
    sonuc.sort(key=lambda s: (sira[s["Sınıf"][0]], s["FD/Temettü (tahmin)"] or 9e9))
    yaz(sonuc, cikti)
    for s in sonuc:
        if s["Sınıf"][0] in "ABCD":
            print(f"{s['Sınıf'][:1]} {s['Kod']:6} FD/T12={s['FD/Temettü (son 12 ay)']!s:>6} "
                  f"FD/Ttah={s['FD/Temettü (tahmin)']!s:>6} FD/NK={s['FD/Net kâr (TTM)']!s:>6} "
                  f"FCF/T={s['FCF / Temettü']!s:>6} Fun={s['Funnel MIN 2026/09']!s:>4} | {s['Bayraklar']}")


if __name__ == "__main__":
    main()
