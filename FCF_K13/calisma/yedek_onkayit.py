import json, pandas as pd
Y=[('HOROZ','2025/03'),('AVTUR','2026/06'),('GEREL','2025/03'),('BIENY','2025/12'),('OTTO','2025/12'),('KRPLS','2025/12'),
   ('EGSER','2025/12'),('SILVR','2025/12'),('BYDNR','2025/12'),('QUAGR','2025/03'),('BLUME','2025/06'),('BEYAZ','2026/06'),('BASGZ','2025/09'),('ERBOS','2026/03')]
on=json.load(open('ONKAYIT_K13_tahminler.json'))
lst=on if isinstance(on,list) else on.get('satirlar',[])
O={(r['kod'],r['donem']):r for r in lst if isinstance(r,dict)}
out=[]
for v in ['base','rev']:
    x=pd.read_pickle(f'karar_5_{v}.pkl'); K,R=x['K'],x['R']
    for k,d in Y:
        kk=K[(K.Kod==k)&(K['Dönem']==d)]
        rr=R[(R.Kod==k)&(R['Dönem']==d)]
        out.append(dict(varyant=v,kod=k,donem=d,tabaka=O.get((k,d),{}).get('tabaka'),
          v7_statu=kk['V7 statü'].iloc[0] if len(kk) else None,
          onerilen=kk['Önerilen statü'].iloc[0] if len(kk) else '(K13 kapsamı dışı — değişmez)',
          alarm=bool(kk['Alarm'].iloc[0]) if len(kk) else False,
          kalemler=[dict(kalem=q.Kalem,kesin=q['Şüpheli köprü noktası (kesin)'],olasi=q['Şüpheli köprü noktası (olası)'],
                 karar=round(float(q['Karar ölçüsü (mn TL)']),3),esik=round(float(q['Eşik (mn TL)']),3),
                 net=round(float(q['A3 net davranış (maks pozitif YTD)']),3),alarm=bool(q['Alarm'])) for _,q in rr.iterrows()]))
ACK=("K13 revizyonu rev: ZAYIF=2 (R1'), R2 (pencere disi yalitilmis tek pozitif nokta haric), "
     "R4 (sifir=veri, FY_onceki >= yil ici dolu nokta). YEDEK orneklem tahminleri, BELGE OKUNMADAN donduruldu. "
     "base = revizyon oncesi K13.")
json.dump(dict(aciklama=ACK,satirlar=out),open('ONKAYIT_REV_yedek.json','w'),ensure_ascii=False,indent=1)
for r in out:
    if r['varyant']=='rev': print(r['kod'],r['donem'],r['tabaka'],r['v7_statu'],'->',r['onerilen'],[(q['kalem'][:4],q['kesin'],q['olasi'],q['karar'],q['esik'],q['net']) for q in r['kalemler']])
b={(r['kod'],r['donem']):r['alarm'] for r in out if r['varyant']=='base'}
print('base!=rev:',[(r['kod'],b[(r['kod'],r['donem'])],r['alarm']) for r in out if r['varyant']=='rev' and b[(r['kod'],r['donem'])]!=r['alarm']])
