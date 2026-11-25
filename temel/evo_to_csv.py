"""EVO (Fintables MCP) veri_sorgula çıktısını (JSON, markdown tablo) CSV'ye çevirir."""
import json, sys, csv

def convert(src, dst):
    raw = open(src, encoding="utf-8").read()
    try:
        d = json.loads(raw)
    except json.JSONDecodeError:
        d = json.loads(json.loads(raw)[0]["text"]) if raw.startswith("[") else None
    if isinstance(d, list):
        d = json.loads(d[0]["text"])
    lines = [l for l in d["table"].split("\n") if l.strip()]
    rows = []
    for i, l in enumerate(lines):
        if i == 1:
            continue  # ayraç satırı
        rows.append([c.strip() for c in l.strip().strip("|").split("|")])
    with open(dst, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)
    print(dst, "satır:", len(rows) - 1, "| row_count:", d.get("row_count"), "| notes:", d.get("notes"))

if __name__ == "__main__":
    convert(sys.argv[1], sys.argv[2])


def from_transcript(jsonl, header_marker, dst):
    """Satır içi dönen (dosyaya kaydedilmeyen) sorgu sonuçlarını oturum kaydından toplar."""
    rows, hdr = {}, None
    for line in open(jsonl, encoding="utf-8"):
        if header_marker not in line:
            continue
        o = json.loads(line)
        c = o.get("message", {}).get("content")
        if not isinstance(c, list):
            continue
        for part in c:
            if part.get("type") != "tool_result":
                continue
            cc = part["content"]
            txt = cc if isinstance(cc, str) else "".join(x.get("text", "") for x in cc)
            if header_marker not in txt or not txt.startswith("{"):
                continue
            d = json.loads(txt)
            L = [l for l in d["table"].split("\n") if l.strip()]
            hdr = [x.strip() for x in L[0].strip("|").split("|")]
            for l in L[2:]:
                r = [x.strip() for x in l.strip().strip("|").split("|")]
                rows.setdefault(r[0], r)
    with open(dst, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(hdr); w.writerows(rows.values())
    print(dst, "satır:", len(rows))
