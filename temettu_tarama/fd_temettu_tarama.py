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


def oku_geri_alim(yol):
    """Geri alınmış pay ADEDİ (KAP bildirimlerinden). Yoksa bilanço maliyet bedeli kullanılır."""
    try:
        with open(yol, encoding="utf-8") as f:
            return {r["kod"]: r for r in csv.DictReader(f)}
    except FileNotFoundError:
        return {}


def hesapla(r, fcf, geri_alim_adet=None, geri_alim_acik=None):
    kod = r["kod"]
    ga = (geri_alim_adet or {}).get(kod)
    f = fcf.get(kod, {})
    kira = min(r["rou"], r["fb"])                   # kira yükümlülüğü ≈ kullanım hakkı varlığı
    fin_borc = r["fb"] - kira                        # banka kredisi + tahvil
    # Geri alınmış paylar: doğru yöntem ADET × güncel fiyat (= PD × adet / ödenmiş sermaye).
    # Bilançodaki tutar TMS29'la endekslenmiş MALİYET bedelidir; fiyat değiştikçe sapar.
    # Paylar itfa edilip sermayeden düşülmüşse ödenmiş sermaye zaten azalmıştır, düzeltme gerekmez.
    if ga:
        geri_alim = r["pd"] * float(ga["adet"]) / float(ga["odenmis_sermaye"])
        ga_yontem = f"adet×fiyat ({int(float(ga['adet'])):,} adet, {ga['tarih']})".replace(",", ".")
    else:
        geri_alim = abs(r["gap"])
        ga_yontem = "bilanço maliyeti" if r["gap"] else "-"
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
    if r["gap"] and not ga:
        neden = (geri_alim_acik or {}).get(kod)
        bayrak.append("Geri alınmış pay: adet doğrulanamadı, maliyet bedeli kullanıldı"
                      + (f" — {neden}" if neden else " (KAP'a henüz bakılmadı)"))

    # ---- Sınıflama ----
    temiz = (r["n_tem"] == 5 and r["n_kar"] == 5 and kod not in HOLDING_KODLARI and fd > 0)
    fcf_ok = (fcf_kapsama is not None and fcf_kapsama >= 1.0
              and f.get("fcf_statu") not in ("KOŞULLU", "NULL"))
    ana = [x for x in (fd_tem_gecmis, fd_tem_tahmin) if x is not None]
    en_kotu = max(ana) if len(ana) == 2 else None

    # ---- Temettü vermeyen / yeni başlayan şirketler (canlı yayın, Zülfikar'ın sorusu) ----
    # "Yöntem aynı, ama hiç dağıtmamış şirketin temettüye geçme oranı düşük. Dağıtacağına ne kadar
    #  güvenebiliyoruz? Dağıtmazsa kurduğun bütün sistem gider." + 1. video: temettü vermeyen
    #  şirkette kasadaki nakit de iskontolanır (10 milyara 1 milyar). Bu yüzden:
    #   * nakit iskontosu %10 (nakit_iskontosu zaten min(n_tem, n_kar) ≤ 2 için 0,10 veriyor)
    #   * temettü geçmişi yok -> tahmin yok; yalnızca TAVAN hesaplanır: şirket kârının ve FCF'inin
    #     küçüğünü tamamen dağıtsa FD kaç yılda döner? Tavanda bile >10 yıl ise elenir.
    #   * tavanda ≤10 yıl çıksa bile A/B/C olamaz: "P" sınıfı = dağıtım KANITI aranacak liste
    #     (kâr dağıtım politikası, genel kurul kararı, guidance, son 12 ayda başlamış ödeme).
    if r["np_ttm"] > 0:
        tavan = min(r["np_ttm"], fcf09) if isinstance(fcf09, (int, float)) else r["np_ttm"]
    else:
        tavan = 0.0
    fd_tem_tavan = oran(fd, tavan)
    if r["n_tem"] == 0:
        tem_durum = "Hiç vermedi (5 yıl)"
    elif r["n_tem"] <= 2 and r["d12"] > 0:
        tem_durum = "Yeni başladı / seyrek"
    elif r["n_tem"] <= 2:
        tem_durum = "Seyrek, son 12 ayda yok"
    else:
        tem_durum = "Düzenli" if r["n_tem"] == 5 else "Kesintili"
    yeni = r["n_tem"] <= 2

    # Temettü geçmişi yoksa NAKİT kanıtı şart: FCF master'da sağlam (KESİN/TÜRETİLMİŞ) ve pozitif FCF
    # olmadan tavan sadece net kâra dayanır; GYO'larda bu büyük ölçüde değerleme kazancıdır, nakit değil.
    fcf_saglam = (isinstance(fcf09, (int, float)) and fcf09 > 0
                  and f.get("fcf_statu") not in ("KOŞULLU", "NULL"))
    holding = kod in HOLDING_KODLARI or (f.get("tip") or "").lower().startswith("holding")
    if yeni and not fcf_saglam:
        bayrak.append("P dışı: sağlam pozitif FCF yok, tavan yalnız kâra dayanır")

    if yeni:
        if (fd > 0 and r["n_kar"] >= 4 and fcf_saglam and not holding
                and fd_tem_tavan is not None and fd_tem_tavan <= 10):
            sinif = "P · temettü güveni yok: tavanda ≤10 yıl, dağıtım kanıtı şart"
        else:
            sinif = "E · >15 yıl ya da hesaplanamaz"
    elif temiz and en_kotu is not None and en_kotu <= 10 and fcf_ok:
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
        "Temettü durumu": tem_durum, "FD/Temettü tavanı (kâr ve FCF'in küçüğü)": fd_tem_tavan,
        "Temettü verimi FD'ye (%)": round(100 * r["d12"] / fd, 1) if fd > 0 else None,
        "PD (mn)": r["pd"], "Geri alınan pay (mn)": round(geri_alim), "Bilançodaki geri alım maliyeti (mn)": abs(r["gap"]),
        "Geri alım yöntemi": ga_yontem, "Nakit (mn)": r["nakit"],
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
    ("PD", "hisse_senetleri.piyasa_degeri − geri alınmış payların PİYASA değeri. Geri alınan pay temettü ve oy hakkı almaz, yok sayılır."),
    ("Geri alınan pay", "Doğru yöntem ADET × güncel fiyat (yorumda Serhan Ergün, yayıncı onayladı). Bilançodaki 'Geri Alınmış Paylar' tutarı TMS29 ile endekslenmiş MALİYETTİR, adet değil; fiyattan sapar (LKMNH: maliyet 351 mn, piyasa 134 mn). Adetler geri_alim_adet.csv'de, KAP bildirimlerinden: geri alınan paylar SATILABİLİYOR (PCILT 5 mn adedi 05/2026'da sattı, GRSEL 300 bini 07/2025'te sattı), bu yüzden tek bildirime değil son duruma bakılmalı. Adet yoksa maliyet bedeli kullanılır ve bayrak düşülür; KAP'ta arandığı halde çözülemeyenlerin nedeni geri_alim_acik.csv'de. Eski bildirimlerde ADET yerine SERMAYEYE ORAN kullanıldı: bedelsiz sermaye artırımında geri alınmış paylar da çoğalır, oran değişmez (MTRKS örneği). Paylar itfa edilip sermayeden düşülmüşse ödenmiş sermaye zaten azalmıştır, düzeltme gerekmez (yorumda ygttylmz, yayıncı onayladı)."),
    ("HBK notu", "Net kâr = ANA ORTAKLIK payı (TMS 33). Yayıncının GRSEL 06/2025 örneğinde şirket toplam kârı bölmüş ve geri alınan payı düşmemiş: doğrusu 1.111.000.802 / 101.700.000 = 10,92 TL, raporlanan 11,66 TL yanlış. Tarama ana ortaklık kârını ve toplam temettüyü kullandığı için hisse başı hatalardan etkilenmez."),
    ("Finansal borç", "KV+UV 'Finansal Borçlar' − kira yükümlülüğü. Kira yükümlülüğü ≈ 'Kullanım Hakkı Varlıkları' (EVO'da ayrı kira satırı yok; GRSEL'de video 362 mn, bu yaklaşım 373 mn verdi)."),
    ("Nakit iskontosu", "Kasadaki nakde güven: 5/5 yıl kâr+temettü %95, 4 yıl %70, 3 yıl %40, altı %10 (videodaki 'gece kulübü' kuralı)."),
    ("FD", "PD_düz − Nakit × iskonto + Finansal borç (kira hariç)."),
    ("Net kâr", "Ana ortaklık payı, TTM. 6 ay ×2 yerine TTM kullanıldı → mevsimsellik sorunu (Datça pansiyonu örneği) otomatik çözülür."),
    ("Temettü tahmini", "TTM net kâr × dağıtım oranı. Oran = son 12 ayda ödenen temettü / 2025 net kârı (yoksa 2024–26 temettü / 2023–25 kâr), [0,1] aralığında. 3 yıllık ortalama TMS29 yüzünden düşük çıkıyor."),
    ("Sınıf A", "5/5 yıl kâr, 5/5 yıl temettü, holding değil; FD/Temettü hem son 12 ay hem tahminde ≤10; FCF TTM (GEM v6.2 master) temettü tahmininin en az 1 katı ve statü KESİN/TÜRETİLMİŞ."),
    ("Sınıf B", "A ile aynı ama FCF teyidi yok/zayıf."),
    ("Sınıf C", "10–15 yıl (yayıncının 'istisna' bandı)."),
    ("Sınıf P", "Son 5 yılın en fazla 2'sinde temettü (hiç vermemiş ya da yeni başlamış). Yayıncı: yöntem aynı, ama hiç dağıtmamış şirketin temettüye geçme oranı düşük; dağıtmazsa sistem çöker. Bu yüzden nakit %10 sayılır, temettü tahmini yapılmaz, sadece TAVAN hesaplanır (kâr ve FCF'in küçüğü tamamen dağıtılsa FD kaç yılda döner). Tavanda ≤10 yıl + 5 yılın en az 4'ünde kâr + FCF master'da sağlam pozitif FCF (GYO kârı çoğunlukla değerleme kazancı, nakit değil) + holding değil → P: alım listesi DEĞİL, dağıtım kanıtı aranacak liste (kâr dağıtım politikası, genel kurul kararı, guidance, başlamış ödeme). Kanıt bulunursa bir sonraki taramada gerçek temettüyle değerlendirilir."),
    ("Sınıf D", "Tahmini FD/Temettü ≤10 ama kâr/temettü geçmişi kesintili, holding ya da FD negatif → elle inceleme."),
    ("Bilinen sınırlar", "Geçmiş temettüler nominal TL (TMS29 sonrası bilanço ise cari alım gücü); yayıncı USD bazında düşünür. Geri alınan paylar maliyet bedeliyle düşüldü (adet yok). İmtiyazlı pay, ilişkili taraf alacakları, stok/alacak düzeltmesi elle bakılacak başlıklar. 10 yıllık temettü projeksiyonu yapılmadı: tek yıl 'bugünkü kira' ölçüsü."),
]


def yaz(sonuc, yol):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "SONUC"
    basl = list(sonuc[0].keys())
    ws.append(basl)
    renk = {"A": "C6EFCE", "B": "E2EFDA", "C": "FFF2CC", "P": "DDEBF7", "D": "FCE4D6", "E": "EDEDED"}
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
    import os
    ga = oku_geri_alim(os.path.join(os.path.dirname(os.path.abspath(evo)), "geri_alim_adet.csv"))
    acik_yol = os.path.join(os.path.dirname(os.path.abspath(evo)), "geri_alim_acik.csv")
    acik = {}
    if os.path.exists(acik_yol):
        with open(acik_yol, encoding="utf-8") as f:
            acik = {r["kod"]: r["neden"] for r in csv.DictReader(f)}
    sonuc = [hesapla(r, fcf, ga, acik) for r in oku_evo(evo)]
    sira = {"A": 0, "B": 1, "C": 2, "P": 3, "D": 4, "E": 5}
    sonuc.sort(key=lambda s: (sira[s["Sınıf"][0]], s["FD/Temettü (tahmin)"] or 9e9))
    yaz(sonuc, cikti)
    for s in sonuc:
        if s["Sınıf"][0] in "ABCPD":
            print(f"{s['Sınıf'][:1]} {s['Kod']:6} FD/T12={s['FD/Temettü (son 12 ay)']!s:>6} "
                  f"FD/Ttah={s['FD/Temettü (tahmin)']!s:>6} FD/NK={s['FD/Net kâr (TTM)']!s:>6} "
                  f"FCF/T={s['FCF / Temettü']!s:>6} Fun={s['Funnel MIN 2026/09']!s:>4} | {s['Bayraklar']}")


if __name__ == "__main__":
    main()
