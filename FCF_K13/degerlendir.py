"""Revizyon varyantlarını ORNEKLEM (örneklem içi) ve OOS-20 (örneklem dışı, belgeyle
etiketli) üzerinde karşılaştırır."""
import sys
import pandas as pd
HATA = {('MARBL','2025/12'),('EPLAS','2025/03'),('OZRDN','2025/06'),('IZFAS','2026/06'),('ASUZU','2026/03'),
        ('TTRAK','2025/06'),('PNSUT','2026/06'),('BERA','2026/06')}
TEMIZ = {('OYLUM','2025/03'),('TCKRC','2026/06'),('CATES','2025/06'),('DENGE','2026/06'),('BESTE','2025/12'),
         ('FORTE','2026/03'),('GUNDG','2026/06'),('ENSRI','2025/12'),('SANEL','2025/06'),('MEGMT','2025/09'),
         ('ARMGD','2025/09'),('YATAS','2026/03')}
oran = sys.argv[1] if len(sys.argv) > 1 else '5'
rows = []
for v in sys.argv[2:]:
    x = pd.read_pickle(f'karar_{oran}_{v}.pkl')
    K, D = x['K'], x['D']
    a = {(r.Kod, r['Dönem']) for _, r in K[K['Alarm']].iterrows()}
    vc = D['YENİ sonuç'].value_counts()
    rows.append(dict(varyant=v,
        IS_yakalandi=vc.get('YAKALANDI', 0), IS_sessiz_hata=vc.get('SESSİZ HATA', 0),
        IS_yanlis_alarm=vc.get('YANLIŞ ALARM', 0),
        OOS_dogru_alarm=len(HATA & a), OOS_kacirma=len(HATA - a),
        OOS_yanlis_alarm=len(TEMIZ & a), OOS_dogru_sessiz=len(TEMIZ - a),
        evren_degisen=int(K['Statü değişti'].sum()),
        OOS_kacirilan=','.join(sorted(k for k, _ in HATA - a)),
        OOS_yanlis=','.join(sorted(k for k, _ in TEMIZ & a))))
print(pd.DataFrame(rows).to_string(index=False))
