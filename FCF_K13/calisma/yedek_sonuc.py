import json,sys,os
f='YEDEK_SONUCLAR.json'; d=json.load(open(f)) if os.path.exists(f) else []
r=json.loads(sys.argv[1]); d=[x for x in d if not (x['kod']==r['kod'] and x['donem']==r['donem'])]+[r]
json.dump(d,open(f,'w'),ensure_ascii=False,indent=1); print('kaydedildi',len(d))
