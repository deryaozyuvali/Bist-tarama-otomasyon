"""Bu oturumdaki Evo pivot sorgu sonuçlarını (HASAT_GELIR / HASAT_NAKIT / HASAT_BORC) oturum kaydından toplar → evo_3yil.csv"""
import json, glob, re, sys
import pandas as pd
J = '/root/.claude/projects/-home-user-Bist-tarama-otomasyon/31baba60-340d-5df9-b796-839f2b1597f2.jsonl'
TR = '/root/.claude/projects/-home-user-Bist-tarama-otomasyon/31baba60-340d-5df9-b796-839f2b1597f2/tool-results/'
metinler = []
def ekle(t):
    if isinstance(t, str) and '"row_count"' in t and '| kod |' in t: metinler.append(t)
for l in open(J):
    try: o = json.loads(l)
    except Exception: continue
    c = o.get('message', {}).get('content')
    if not isinstance(c, list): continue
    for x in c:
        if x.get('type') == 'tool_result':
            cc = x.get('content')
            if isinstance(cc, list):
                for y in cc: ekle(y.get('text'))
            else: ekle(cc)
for f in glob.glob(TR + 'mcp-EVO-veri_sorgula-17913056*.txt') + glob.glob(TR + 'mcp-EVO-veri_sorgula-17913057*.txt'):
    s = open(f).read()
    try:
        d = json.loads(s)
        if isinstance(d, list): [ekle(y.get('text')) for y in d]
        else: ekle(s)
    except Exception: ekle(s)
tablolar = {}
for t in metinler:
    try: tab = json.loads(t)['table']
    except Exception:
        try: tab = json.loads(json.loads(t)[0]['text'])['table']
        except Exception: continue
    sat = tab.split('\n'); bas = [h.strip() for h in sat[0].strip('|').split('|')]
    if 'kod' not in bas: continue
    anahtar = 'gelir' if 's23' in bas else 'nakit' if 'cfo23' in bas else 'borc' if 'nb23' in bas else 'gyo' if 'gcfo25' in bas else 'gyooz' if 'goz26' in bas else None
    if not anahtar: continue
    for r in sat[2:]:
        v = [x.strip() for x in r.strip('|').split('|')]
        if len(v) != len(bas): continue
        d = dict(zip(bas, v)); tablolar.setdefault(anahtar, {})[d['kod']] = d
dfs = [pd.DataFrame(v.values()).set_index('kod') for k, v in tablolar.items()]
print({k: len(v) for k, v in tablolar.items()})
D = pd.concat(dfs, axis=1).apply(pd.to_numeric, errors='coerce')
D.index.name = 'Kod'
D.to_csv('/home/user/Bist-tarama-otomasyon/FCF_K13/hasat/evo_3yil.csv')
print(D.shape)
