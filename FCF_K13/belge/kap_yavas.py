"""KAP bildirimlerini yavaş indirir (WAF engeline karşı): öncelikli sıra, her bildirim arası bekleme,
art arda 3 'html indirilemedi' → durur. Kullanım: python3 kap_yavas.py liste.txt [bekleme_sn]"""
import json, os, sys, time
import kap_indir
OB = kap_indir.OB
liste = [l.strip() for l in open(sys.argv[1]) if l.strip()]
bek = float(sys.argv[2]) if len(sys.argv) > 2 else 6
ard = 0
for i, idx in enumerate(liste):
    p = f'{OB}/{idx}.json'
    if os.path.exists(p) and 'hata' not in json.load(open(p)): continue
    if os.path.exists(p): os.remove(p)
    kap_indir.isle(idx)
    hata = 'hata' in json.load(open(p))
    ard = ard + 1 if hata else 0
    print(i, idx, 'HATA' if hata else 'ok', flush=True)
    if ard >= 3: print('art arda 3 hata → durdu'); break
    time.sleep(bek)
