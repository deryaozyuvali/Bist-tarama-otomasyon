"""KAP'tan finansal rapor (FR) bildirimlerini tarih penceresi bazında çeker → kap_fr.json"""
import json, subprocess, datetime as dt, sys, time
U = "https://www.kap.org.tr/tr/api/disclosure/members/byCriteria"
def q(a, b):
    body = {"fromDate": a, "toDate": b, "memberType": "IGS", "mkkMemberOidList": [], "disclosureClass": "FR",
            "subjectList": [], "isLate": "", "mainSector": "", "sector": "", "subSector": "", "marketOidList": [],
            "index": "", "bdkReview": "", "bdkMemberOidList": [], "year": "", "term": "", "ruleType": "", "period": "",
            "fromSrc": False, "srcCategory": "", "discIndex": []}
    for i in range(4):
        r = subprocess.run(["curl", "-sS", "--max-time", "90", "-X", "POST", "-H", "Content-Type: application/json",
                            U, "-d", json.dumps(body)], capture_output=True, text=True)
        try: return json.loads(r.stdout)
        except Exception: time.sleep(2 ** i)
    raise SystemExit(f"başarısız {a} {b}: {r.stdout[:200]} {r.stderr[:200]}")
out = {}
d = dt.date(2025, 1, 15)
while d < dt.date(2026, 10, 5):
    e = d + dt.timedelta(days=6)
    rs = q(d.isoformat(), e.isoformat())
    for x in rs: out[x['disclosureIndex']] = x
    print(d, len(rs), file=sys.stderr)
    d = e + dt.timedelta(days=1)
json.dump(list(out.values()), open('kap_fr.json', 'w'), ensure_ascii=False)
print(len(out))
