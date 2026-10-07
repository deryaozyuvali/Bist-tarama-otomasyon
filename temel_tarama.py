"""
TEMEL ANALİZ TARAMASI — "taşın altına bakan" yayıncı yöntemi (EVO + FCF_MASTER)
===============================================================================
Polisan, Gimat, Fonet, Tınaztepe, Onur Yüksek Teknoloji ve Menderes
videolarındaki yaklaşım kurallara çevrildi. Ayrıntı: YONTEM.md

Veri:
  * EVO (Fintables MCP) — bilanço, gelir tablosu, nakit akış, piyasa değeri.
    TMS 29 ile son döneme düzeltilmiş olduğu için yıllık büyüme REEL.
  * FCF_MASTER.xlsx (Dropbox) — FCF TTM + statü ve Funnel V8.2 puanı.

EVO'ya dışarıdan bağlanılamadığı (sadece Claude'un MCP aracıyla erişilebildiği)
için bu script hesaplamayı kendisi yapmaz; FCF_MASTER verisini içine gömerek
tek bir SQL sorgusu üretir. Puanlamanın tamamı bu sorgunun içindedir:

    python temel_tarama.py FCF_MASTER.xlsx  >  sorgu.sql   # yayıncı + FCF/Funnel
    python temel_tarama.py --sadece-yayinci  >  sorgu.sql   # sadece yayıncı yöntemi

Üretilen sorgu EVO `veri_sorgula` aracıyla çalıştırılır (en fazla 300 satır,
PUAN'a göre sıralı). Şablon: temel_tarama.sql
"""
import sys
from pathlib import Path

import openpyxl

SABLON = Path(__file__).with_name("temel_tarama.sql")

# FCF_MASTER → ANA sayfası sütunları (0 tabanlı)
C_KOD, C_KAPSAM = 0, 2
C_FCF = range(5, 11)        # 2025/03 … 2026/06
C_STATU = range(11, 17)
C_FUNNEL = range(17, 22)    # 2025/06 … 2026/06
C_KAT = range(22, 27)

KULLANILIR = {"KESİN", "TÜRETİLMİŞ"}
KAT_KOD = {
    "ANA LİSTE": "A", "KOŞULLU ANA LİSTE": "K", "İZLEME": "I",
    "50–59 · BİLANÇO PUANI GEREKLİ": "B", "ALT": "L", "BELİRSİZ": "U",
}


def son_dolu(degerler):
    for v in reversed(degerler):
        if v is not None:
            return v
    return None


def fcf_satirlari(xlsx):
    ws = openpyxl.load_workbook(xlsx, read_only=True, data_only=True)["ANA"]
    for r in list(ws.iter_rows(values_only=True))[3:]:
        kod = r[C_KOD]
        if not kod or r[C_KAPSAM] != "STANDART":
            continue
        fcf = [r[i] if r[j] in KULLANILIR else None
               for i, j in zip(C_FCF, C_STATU)]
        son = son_dolu(fcf)
        son3 = [v for v in fcf[-3:] if v is not None]
        neg3 = int(len(son3) == 3 and all(v < 0 for v in son3))
        funnel = son_dolu([r[i] for i in C_FUNNEL])
        kat = KAT_KOD.get(son_dolu([r[i] for i in C_KAT]), "-")
        if son is None and funnel is None:
            continue
        yield (
            str(kod),
            "NULL" if son is None else f"{son:.1f}",
            neg3,
            "NULL" if funnel is None else int(funnel),
            kat,
        )


def fcf_cte(satirlar):
    parcalar = []
    for i, (k, fcf, neg3, fn, kat) in enumerate(satirlar):
        if i == 0:
            parcalar.append(
                f"SELECT '{k}' AS k, CAST({fcf} AS numeric) AS fcf, {neg3} AS neg3, "
                f"CAST({fn} AS integer) AS funnel, '{kat}' AS kat")
        else:
            parcalar.append(f"SELECT '{k}', {fcf}, {neg3}, {fn}, '{kat}'")
    return "\n  UNION ALL ".join(parcalar)


BOS_FCF = ("SELECT CAST(NULL AS text) AS k, CAST(NULL AS numeric) AS fcf, 0 AS neg3, "
           "CAST(NULL AS integer) AS funnel, '-' AS kat")

if __name__ == "__main__":
    arg = sys.argv[1:]
    if arg == ["--sadece-yayinci"]:
        fcf, sira = BOS_FCF, "yayinci"
    elif len(arg) == 1:
        satirlar = list(fcf_satirlari(arg[0]))
        fcf, sira = fcf_cte(satirlar), "puan"
        print(f"-- {len(satirlar)} şirketin FCF/Funnel verisi gömüldü", file=sys.stderr)
    else:
        sys.exit("Kullanım: python temel_tarama.py (FCF_MASTER.xlsx | --sadece-yayinci) > sorgu.sql")
    sql = SABLON.read_text(encoding="utf-8")
    sys.stdout.write(sql.replace("{{FCF}}", fcf).replace("{{SIRA}}", sira))
