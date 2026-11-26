"""Nihai tabloyu (README sayfalı Excel) üretir.

Girdi : results/temel/<TARIH>/tum_sirketler.csv  (temel_tarama.py çıktısı)
        temel/gem_karne.csv                       (Dropbox /BIST/GEM Analizleri/satirlar karne satırları)
        temel/yatirim_degerlendirme.csv           (yeni yatırım devreye giriyor mu? elle, kaynaklı)
Çıktı : results/temel/<TARIH>/Nihai_Tablo.xlsx

Kullanım: python temel/nihai_tablo.py --tarih 2026-11-25
"""
import argparse
import os

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo
import json
import re

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = "Arial"
BASLIK = PatternFill("solid", fgColor="1F3864")
ZEBRA = PatternFill("solid", fgColor="F2F2F2")
AGIR = PatternFill("solid", fgColor="FCE4E4")
INCE = Side(style="thin", color="BFBFBF")
CERCEVE = Border(left=INCE, right=INCE, top=INCE, bottom=INCE)

README = [
    ("BAŞLIK", "Yayıncının şirket inceleme yöntemiyle BIST taraması — nihai tablo"),
    ("", "Tarama tarihi: fiyatlar 25.11.2026; finansallar her şirketin son açıklanan dönemi (çoğunda 2026/9, MAVI ve RALYH'de 2026/6). Tablo 26.11.2026'da üretildi."),
    ("", "Kural: yalnız videoda söylenenler uygulandı. Veriden hesaplanamayan maddeler elle, kaynak bildirim numarasıyla eklendi. Bu bir ön elemedir, al/sat önerisi değildir."),
    ("BAŞLIK", "1. Veri kaynağı"),
    ("", "Sayısal veri: EVO / Fintables (veri_sorgula). Tutarlar TL; TMS 29 enflasyon muhasebesi uygulanmış, son dönemin satın alma gücünde."),
    ("", "TTM = son 12 ay (EVO try_ttm). Büyüme karşılaştırmaları USD ile yapıldı (TL'de enflasyon yanıltır)."),
    ("", "Metin verisi: KAP bildirimleri, faaliyet raporları ve finansal rapor dipnotları (EVO doküman araması). GEM puanları: Dropbox /BIST/GEM Analizleri/satirlar/<KOD>2026Q3 karne satırları."),
    ("BAŞLIK", "2. Kesin eleme (kriterlere bakılmadan dışarıda)"),
    ("", "Finansal yapılar: bankalar (veri kapsamı dışında), aracı kurumlar, menkul kıymet yatırım ortaklıkları, girişim sermayesi yatırım ortaklıkları."),
    ("", "Halka arzı 1 yıldan yeni olanlar (videoda: \"en az bir yıl geçsin\"). Piyasa değeri olmayanlar."),
    ("BAŞLIK", "3. Çekirdek 4 kriter (videoda: \"bu dört özellik tuttuğunda yatırım sinyalleri başlıyor\") — nihai listeye yalnız 4/4 girer"),
    ("K1", "ROIC > WACC.  ROIC = esas faaliyet kârı × (1 − vergi oranı) ÷ (özkaynak + net borç)."),
    ("", "Esas faaliyet kârı = brüt kâr − (pazarlama + genel yönetim + Ar-Ge giderleri); diğer faaliyet gelir/giderleri dahil değil. Vergi oranı = efektif oran, %0–35 aralığına kırpılır, hesaplanamazsa %25. Esas faaliyet zararı varsa ROIC ≤ 0 sayılır."),
    ("", "WACC = %10 (varsayım, tek oran). ROIC %8–12 aralığındaysa \"ROIC sınırda\" hafif bayrağı yazılır."),
    ("", "Not: Fintables'ın hazır ROIC'i farklı tanımlıdır: (esas faaliyet kârı − fiili vergi) ÷ ortalama(ana özkaynak + BRÜT finansal borç). Nakdi düşmediği için nakdi bol şirketlerde daha düşük çıkar (ör. BNTAS %8,1 vs bizim %13,7). Kullanıcı kararıyla ek kolon olarak eklenmedi."),
    ("K2", "Serbest nakit akışı (SNA) pozitif ve sürdürülebilir."),
    ("", "SNA = İşletme faaliyetlerinden nakit akışı (CFO) − bakım yatırımı − kira ödemeleri."),
    ("", "Bakım yatırımı = min(CAPEX, amortisman). Amortismanın üstündeki CAPEX büyüme yatırımı sayılıp düşülmez (videoda: \"büyüme yatırımı varsa çıkarın\"). Amortisman ≤ 0 ise CAPEX'in tamamı; CAPEX TTM verisi boşsa sıfır değil amortisman kullanılır ve bayrak yazılır."),
    ("", "CAPEX = 'Maddi ve Maddi Olmayan Duran Varlıkların Alımından Kaynaklanan Nakit Çıkışları'. Kira = 'Kira Ödemeleri' veya 'Kira Sözleşmelerinden Kaynaklanan Borç Ödemelerine İlişkin Nakit Çıkışları' (TFRS 16)."),
    ("", "Belgeyle düzeltme (temel/sna_duzeltme.csv): ARASE ve ENJSA'da imtiyaz şebeke yatırımı (TFRYK 12) ayrı satırda olduğu için düşüldü; YEOTK'de leasing şirketinin tedarikçiye ödediği ekipman bedeli (gizli finansman) düşüldü."),
    ("", "Sürdürülebilirlik: kayan 12 aylık pencereler — son dönem TTM, 1 yıl önceki ve 2 yıl önceki aynı dönem TTM (ör. 2026/9, 2025/9, 2024/9). Şart: son pencere > 0 ve en az 2/3 pencere > 0 (en az 2 pencere verisi). Pencereler farklı dönem TL'si olduğu için yalnız işaret karşılaştırılır; boş pencere sıfır sayılmaz. EVO'da 2023/9 TTM boş olduğundan en fazla 3 pencere var."),
    ("K3", "FD / SNA < 10.  FD (firma değeri) = piyasa değeri + net borç + azınlık payları özkaynağı. Net borç = EVO 'Net Borç' (finansal borçlar, kira yükümlülükleri dahil, − nakit ve benzerleri)."),
    ("", "Bilinen açık: kira yükümlülüğü hem FD'de (net borç) hem SNA'da (kira ödemesi) yer alıyor; kira ağır şirketlerde FD/SNA ihtiyatlı (yüksek) çıkar. TFRS 16 kira faizi ayrıca düşülmedi."),
    ("K4", "İşlerde ciddi daralma yok (vekil gösterge, gelecek tahmini değil): USD satış büyümesi > −%10 VE USD brüt kâr büyümesi > −%15 VE esas faaliyet kârı > 0."),
    ("BAŞLIK", "4. Ağır bayraklar (4/4 olsa bile nihai listeden çıkarır)"),
    ("⛔", "Patron/yönetici net satışı: son 12 ayda içeridekilerin net satışı sermayenin ≥ %0,25'i veya ≥ 25 mn TL ve gerekçe açıklanmamış (KAP pay alım satım bildirimleri)."),
    ("⚠", "İlişkili taraf – yüksek: ana ortağa/ortaklara borç verme; ana ortak/grup lehine büyük teminat-kefalet; ilişkili taraftan özkaynağın ≥ %10'u tutarında varlık/şirket alımı (dipnot ve KAP, elle; temel/iliskili_degerlendirme.csv)."),
    ("⚠", "Patron/ortak – ortakların adli süreci nedeniyle şirketin borç temerrüdü (KAP'tan belgeli; şu an SKYLP)."),
    ("⚠", "Kâr payı imtiyazı yalnız imtiyazlı paylara ayrılan tutar net kârın ≥ %5'i ise ⚠ yazılır (bilgi amaçlı, tek başına eleme değil)."),
    ("BAŞLIK", "5. Hafif bayraklar (eleme değil, sıralamada kullanılır)"),
    ("", "Ticari alacak yüksek: alacak/borç > 2 ve alacak/satış > %25.  Alacaklar satıştan hızlı büyüyor: USD alacak büyümesi − USD satış büyümesi > 25 puan ve alacak/satış > %15."),
    ("", "Cari oran < 1. Özkaynak negatif. Son 12 ay net zarar. Net kâr çok zayıf (F/K > 50). Kâr geçmişin 2 katı üstünde (son yıl USD ana ortaklık kârı > önceki 2 yıl ortalamasının 2 katı)."),
    ("", "Kârın > %20'si azınlığın. Maddi olmayan varlık/aktif > %25. Yatırım harcaması/satış > %15. Kira/FAVÖK > %20. Borç yükü ağır (net borç/FAVÖK > 3,5). Borçluyken temettü/geri alım (net borç/FAVÖK > 2,5)."),
    ("", "Sürekli bedelli (5 yılda ≥ 2) veya son 2 yılda bedelli. PD/DD < 1 ama ROIC < WACC (değer tuzağı). ROIC düşükken büyüme yatırımı."),
    ("", "ROIC sınırda (%8–12). SNA geçmiş penceresi negatif. SNA belgeyle düzeltildi. CAPEX TTM verisi eksik."),
    ("", "Yüksek bağış ≥ net kârın %5'i. Üst yönetim ücret/huzur hakkı ≥ net kârın veya esas faaliyet kârının %10'u (ikisinin küçüğü). Kârdan YK/çalışanlara pay. Beklentileri üst üste 2 yıl tutturamadı."),
    ("", "İlişkili taraf – orta: gruba ticari olmayan alacak ~özkaynağın ≥ %10'u; gruptan yüksek ticari alacak; orta ölçekli teminat; ilişkili taraftan satın alma (değerleme raporlu)."),
    ("", "Bilgi notu (bayrak sayılmaz): grup içi işlemler hasılat/SMM'nin ≥ %10'u (SPK m.10 raporu)."),
    ("BAŞLIK", "6. Sıralama"),
    ("", "Nihai liste: 4/4 kriter, kesin eleme yok, ağır bayrak yok. Sıra: önce hafif bayrak sayısı (az olan önce), sonra FD/SNA (düşük olan önce)."),
    ("", "\"Alt grup\": 4/4 ve ağır bayrak yok ama hafif bayrak sayısı ≥ 3 olup yapısal sorunu olanlar (ör. TKNSA özkaynak negatif)."),
    ("BAŞLIK", "7. Videodaki 5 göstergeden (\"beşine bakıyorsunuz, dördünden geçmiştir\")"),
    ("", "Düzenli pozitif nakit akışı (=K2) ve düşük FD/SNA (=K3) tüm nihai listede sağlanıyor. \"Yeni yatırım devreye giriyor mu?\" sütunu faaliyet raporu ve KAP'tan elle dolduruldu (anahtar kelime araması; \"yok\" = bulunamadı). Sektör büyümesi ve pazar payı ölçülmedi."),
    ("BAŞLIK", "8. GEM puanları"),
    ("", "Kullanıcının kendi GEM v6.2 analizlerinden (Dropbox). Bilanço /10, Hikâye /10, Funnel /100, Sınıf. Shortlist için Bilanço ≥ 7,5, Ana Liste için Funnel ≥ 70 (GEM METOT.md). GEM'i olmayanlar: DOHOL, MAVI (2026/9 bilançosu bekleniyor), TRMET, TKNSA, TRENJ, CEOEM, SKYLP, RALYH, TRILC."),
    ("BAŞLIK", "9. Dosyalar"),
    ("", "Kod: temel/temel_tarama.py (tarama), temel/nihai_tablo.py (bu tablo). Elle girdiler: temel/sna_duzeltme.csv, temel/iliskili_degerlendirme.csv, temel/gem_karne.csv, temel/yatirim_degerlendirme.csv, temel/guidance_degerlendirme.csv. Ham veri: temel/ham/."),
]


def mn(x):
    return None if pd.isna(x) else round(x / 1e6, 1)


def yuzde(x):
    return None if pd.isna(x) else float(x)


def bayrak_metni(s):
    if not isinstance(s, str) or not s:
        return ""
    return "\n".join("• " + b.strip() for b in s.split(" | "))


def satirlar(df, gem, yat):
    out = []
    for i, (_, r) in enumerate(df.iterrows(), 1):
        g = gem.get(r["kod"], {})
        y = yat.get(r["kod"], {})
        pozitif = int(r["sna_pozitif_yil"]) if pd.notna(r["sna_pozitif_yil"]) else 0
        veri = int(r["sna_veri_yil"]) if pd.notna(r["sna_veri_yil"]) else 0
        out.append([
            i, r["kod"], r["sektor"], f"{int(r['yil'])}/{int(r['ay'])}",
            r["fd_sna"], mn(r["sna_bakim"]), mn(r["fd"]),
            yuzde(r["roic"]), f"{pozitif}/{veri}",
            mn(r["sna_p0"]), mn(r["sna_p1"]), mn(r["sna_p2"]),
            yuzde(r["satis_usd_buyume"]), yuzde(r["brut_marj"]), r["fd_favok"],
            g.get("bilanco"), g.get("hikaye"), g.get("funnel"), g.get("sinif", "GEM yok"),
            y.get("durum", ""), y.get("aciklama", ""),
            int(r["bayrak_sayisi"]), bayrak_metni(r["kirmizi_bayraklar"]),
            bayrak_metni(r["artilar"]), r["iliskili_notlar"] if isinstance(r["iliskili_notlar"], str) else "",
            g.get("gem_not", ""),
        ])
    return out


KOLON = [
    ("Sıra", 6), ("Kod", 9), ("Sektör", 20), ("Son dönem", 10),
    ("FD/SNA (x)", 10), ("SNA son 12 ay (mn TL)", 13), ("FD (mn TL)", 13),
    ("ROIC", 9), ("SNA+ pencere", 10),
    ("SNA pencere: son (mn TL)", 13), ("SNA pencere: −1 yıl (mn TL)", 13), ("SNA pencere: −2 yıl (mn TL)", 13),
    ("USD satış büyümesi", 11), ("Brüt marj", 9), ("FD/FAVÖK (x)", 10),
    ("GEM Bilanço /10", 10), ("GEM Hikâye /10", 10), ("GEM Funnel /100", 11), ("GEM Sınıf", 24),
    ("Yeni yatırım", 10), ("Yeni yatırım açıklaması", 48),
    ("Hafif bayrak sayısı", 9), ("Bayraklar ve açıklamaları", 70),
    ("Artılar", 45), ("İlişkili taraf notları (bilgi)", 40), ("GEM notu / ana riskler", 60),
]
YUZDE_KOL = {"ROIC", "USD satış büyümesi", "Brüt marj"}
CARPAN_KOL = {"FD/SNA (x)", "FD/FAVÖK (x)"}
MN_KOL = {k for k, _ in KOLON if "mn TL" in k}


def tum_sayfa_yaz(wb, gruplar):
    """Tek sayfa, başlık 1. satırda, gerçek Excel Tablosu: filtre ve sıralama her Excel/Sheets'te çalışır."""
    ws = wb.create_sheet("Tablo")
    kolonlar = [("Liste", 12)] + KOLON
    for j, (k, w) in enumerate(kolonlar, 1):
        c = ws.cell(row=1, column=j, value=k)
        c.font = Font(name=FONT, bold=True, color="FFFFFF", size=9)
        c.fill = BASLIK
        c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.row_dimensions[1].height = 42
    rr = 2
    for liste, veri in gruplar:
        for satir in veri:
            for j, v in enumerate([liste] + satir, 1):
                if isinstance(v, float) and pd.isna(v):
                    v = None
                c = ws.cell(row=rr, column=j, value=v)
                k = kolonlar[j - 1][0]
                c.font = Font(name=FONT, size=9, bold=(k == "Kod"))
                c.alignment = Alignment(wrap_text=True, vertical="top")
                if k in YUZDE_KOL:
                    c.number_format = "0.0%;-0.0%;-"
                elif k in CARPAN_KOL:
                    c.number_format = "0.00\"x\""
                elif k in MN_KOL:
                    c.number_format = "#,##0.0;(#,##0.0);-"
                if liste.startswith("Elenen"):
                    c.fill = AGIR
            rr += 1
    ref = f"A1:{get_column_letter(len(kolonlar))}{rr - 1}"
    tab = Table(displayName="NihaiTablo", ref=ref)
    tab.tableStyleInfo = TableStyleInfo(name="TableStyleLight9", showRowStripes=True)
    ws.add_table(tab)
    ws.freeze_panes = "C2"
    return ws


def ilk_sayi(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    m = re.search(r"\d+(?:[.,]\d+)?", str(v))
    return float(m.group(0).replace(",", ".")) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tarih", default="2026-11-25")
    a = ap.parse_args()
    klasor = os.path.join(KOK, "results", "temel", a.tarih)
    d = pd.read_csv(os.path.join(klasor, "tum_sirketler.csv"))
    gem = pd.read_csv(os.path.join(KOK, "temel", "gem_karne.csv"), dtype=str).set_index("kod").to_dict("index")
    for v in gem.values():
        for k in ("bilanco", "hikaye"):
            try:
                v[k] = float(v[k])
            except (TypeError, ValueError):
                pass
        try:
            v["funnel"] = int(v["funnel"])
        except (TypeError, ValueError):
            pass
    yat = pd.read_csv(os.path.join(KOK, "temel", "yatirim_degerlendirme.csv"), dtype=str).fillna("").set_index("kod").to_dict("index")

    a4 = d[(d["cekirdek_puan"] == 4) & d["eleme"].isna()].copy()
    agir = a4["kirmizi_bayraklar"].fillna("").str.contains("⛔|⚠ İLİŞKİLİ|⚠ PATRON")
    alt_kosul = a4["kirmizi_bayraklar"].fillna("").str.contains("özkaynak negatif") | (a4["bayrak_sayisi"] >= 4)
    nihai = a4[~agir & ~alt_kosul].sort_values(["bayrak_sayisi", "fd_sna"])
    alt = a4[~agir & alt_kosul].sort_values(["bayrak_sayisi", "fd_sna"])
    elenen = a4[agir].sort_values(["bayrak_sayisi", "fd_sna"])

    wb = Workbook()
    ws = wb.active
    ws.title = "README"
    ws.column_dimensions["A"].width = 8
    ws.column_dimensions["B"].width = 150
    r = 1
    for etiket, metin in README:
        if etiket == "BAŞLIK":
            c = ws.cell(row=r, column=1, value=metin)
            c.font = Font(name=FONT, bold=True, size=12 if r == 1 else 11, color="1F3864")
            ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=2)
            r += 1
            continue
        ws.cell(row=r, column=1, value=etiket).font = Font(name=FONT, bold=True, size=10)
        c = ws.cell(row=r, column=2, value=metin)
        c.font = Font(name=FONT, size=10)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.cell(row=r, column=1).alignment = Alignment(vertical="top")
        r += 1

    gruplar = [("Nihai", satirlar(nihai, gem, yat)), ("Alt grup", satirlar(alt, gem, yat)),
               ("Elenen (ağır bayrak)", satirlar(elenen, gem, yat))]
    tum_sayfa_yaz(wb, gruplar)
    wb.move_sheet("Tablo", offset=-1)
    wb.active = 0

    # Web sayfası için JSON
    anahtar = ["sira", "kod", "sektor", "donem", "fd_sna", "sna_mn", "fd_mn", "roic", "sna_pencere", "p0", "p1", "p2",
               "satis_usd", "brut_marj", "fd_favok", "bilanco", "hikaye", "funnel", "sinif", "yatirim", "yatirim_acik",
               "bayrak_n", "bayraklar", "artilar", "iliskili", "gem_not"]
    kayit = []
    for liste, veri in gruplar:
        for s_ in veri:
            o = {k: (None if isinstance(v, float) and pd.isna(v) else v) for k, v in zip(anahtar, s_)}
            o["liste"] = liste
            o["funnel_n"] = ilk_sayi(o["funnel"])
            o["agir"] = liste.startswith("Elenen")
            kayit.append(o)
    with open(os.path.join(klasor, "nihai_tablo.json"), "w") as fh:
        json.dump({"satirlar": kayit, "readme": README}, fh, ensure_ascii=False, default=float)
    sablon = open(os.path.join(KOK, "temel", "nihai_sayfa_sablon.html"), encoding="utf-8").read()
    veri = json.dumps({"satirlar": kayit, "readme": README}, ensure_ascii=False, default=float).replace("</", "<\\/")
    with open(os.path.join(klasor, "Nihai_Tablo.html"), "w", encoding="utf-8") as fh:
        fh.write(sablon.replace("/*VERI*/null/*VERI*/", veri))

    cikti = os.path.join(klasor, "Nihai_Tablo.xlsx")
    wb.save(cikti)
    print(cikti, len(nihai), len(alt), len(elenen))
    print("nihai:", list(nihai["kod"]))
    print("alt:", list(alt["kod"]))
    print("elenen:", list(elenen["kod"]))


if __name__ == "__main__":
    main()
