"""Evo belge chunk dosyasından anahtar satırların sütun=değer çiftlerini çıkarır.
Kullanım: python3 oku.py <dosya> <anahtar1> [<anahtar2> ...]
Her chunk için: id, ilk 120 karakter (birim/tarih başlığı), sonra her anahtar
eşleşmesinde 'etiket, sütun = değer' parçaları."""
import json
import re
import sys

path, keys = sys.argv[1], sys.argv[2:]
raw = open(path).read()
try:
    d = json.loads(raw)
    items = d if isinstance(d, list) else json.loads(d[0]['text'])
except Exception:
    items = [{'id': '?', 'content': raw}]
for it in items:
    c = it['content'].replace('\n', ' ')
    print(f"=== chunk {it['id']} ({len(c)} kr) :: {c[:160]}")
    for k in keys:
        for m in re.finditer(re.escape(k), c, flags=re.I):
            # etiket için geriye 120 kr, değer için ileriye kadar ilk '= ...' ifadesi
            s = c[max(0, m.start() - 60): m.start() + 420]
            vals = re.findall(r'([^=.]{0,90})= ([\(\)\d\.\,\- ]+)', s)
            vv = ' | '.join(f"{a.strip()[-60:]} = {b.strip()}" for a, b in vals[:4])
            print(f"  [{k}] {vv}")
