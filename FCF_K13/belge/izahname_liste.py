"""KAP'tan SPK onaylı izahname bildirimlerini toplar (halka arz öncesi finansallar için) → kap_izahname.json"""
import json, subprocess, datetime as dt, sys
U = "https://www.kap.org.tr/tr/api/disclosure/members/byCriteria"
def q(a, b, cls):
    body = {"fromDate": a, "toDate": b, "memberType": "IGS", "mkkMemberOidList": [], "disclosureClass": cls,
            "subjectList": [], "isLate": "", "mainSector": "", "sector": "", "subSector": "", "marketOidList": [],
            "index": "", "bdkReview": "", "bdkMemberOidList": [], "year": "", "term": "", "ruleType": "", "period": "",
            "fromSrc": False, "srcCategory": "", "discIndex": []}
    for _ in range(3):
        r = subprocess.run(["curl", "-sS", "--max-time", "120", "-X", "POST", "-H", "Content-Type: application/json", U,
                            "-d", json.dumps(body)], capture_output=True, text=True)
        try: return json.loads(r.stdout)
        except Exception: pass
    print('hata', a, cls, file=sys.stderr); return []
out = {}
d = dt.date(2024, 6, 1)
while d < dt.date(2026, 10, 5):
    e = d + dt.timedelta(days=14)
    for cls in ("ODA", "DG"):
        for x in q(d.isoformat(), e.isoformat(), cls):
            if (x.get('subject') or '').startswith('İzahname') and 'Onaylanan' in x['subject']:
                out[x['disclosureIndex']] = x
    d = e + dt.timedelta(days=1)
json.dump(list(out.values()), open('kap_izahname.json', 'w'), ensure_ascii=False)
print(len(out))
