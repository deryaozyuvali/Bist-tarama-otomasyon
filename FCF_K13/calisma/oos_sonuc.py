"""Belge testi sonuç kaydı. Her kayıt: kod, dönem, kalem, sınıf, V7 hata alt sınırı (mn TL), kanıt."""
import json, sys, os
P = 'OOS_SONUCLAR.json'
def ekle(**k):
    d = json.load(open(P)) if os.path.exists(P) else []
    d = [x for x in d if not (x['kod'] == k['kod'] and x['kalem'] == k['kalem'])]
    d.append(k); json.dump(d, open(P, 'w'), ensure_ascii=False, indent=1)
if __name__ == '__main__':
    ekle(**json.loads(sys.argv[1])); print('kaydedildi', len(json.load(open(P))))
