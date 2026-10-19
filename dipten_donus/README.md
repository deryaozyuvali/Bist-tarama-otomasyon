# Dipten Dönüş v3.3 — pilot tarama kodu

Kural metni: `docs/dipten-donus-v3.3.md`.

- `tarama_v33.py`: Sayısal ön tarama (dip tespiti, erken sinyal, ön puan, kuyruklar, sınırdaki adaylar).
- `rapor_v33.py`: Sonuçtan Markdown rapor ve CSV üretir.

Girdi verileri (Evo çekimi, FCF_MASTER, master kapsam listesi) lisanslı veya kişisel olduğu için
bu repoya konmaz; yerel dosya yolları argüman olarak verilir.

```
python tarama_v33.py --evo evo.csv --master master_fcf.csv --evren evren.csv --sektor sektor.csv --cikti cikti/
python rapor_v33.py --sonuc cikti/sonuc.json --referans efk113.csv --cikti cikti/
```
