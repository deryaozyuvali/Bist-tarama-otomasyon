"""Teslim dosyası: FCF_V8_aday_K13.xlsx"""
import pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment

import json, os
SFX = os.environ.get('K13_SFX', '')
d = pd.read_pickle(f'karar_5{SFX}.pkl')
K, R, D, OZ, SK = d['K'], d['R'], d['D'], d['OZ'], d['SK']
d3, d10 = pd.read_pickle(f'karar_3{SFX}.pkl'), pd.read_pickle(f'karar_10{SFX}.pkl')

okubeni = pd.DataFrame([
    ('Ne', 'V7 nihai üzerinde PARALEL çalıştırılan Kontrol 13 (seri tutarlılığı) + Kontrol 6 v2 sonucu. V7 dosyası ve hiçbir FCF rakamı değiştirilmedi; yalnız statü önerildi.'),
    ('Kural metni', 'GEM_K6v2_K13_onerisi.txt — GEM\'e eklenecek metin, doğrulama vakaları ve elenen testlerle.'),
    ('Veri', "V7 Bileşenler sayfasındaki Evo köprü noktaları (6.995 nokta, 2024/03–2026/06; V7'nin FCF'te kullandığı aynı vintage). Evo yalnız örneklem dışı belge doğrulaması için kullanıldı."),
    ('Karar', 'Eşik = MAX(1 mn; %5 × |FCF|). Köprü noktası şüpheli ve etki ≥ eşik → KOŞULLU. Net davranış ve maks pozitif YTD ≥ eşik → KOŞULLU. Diğer → statü korunur + not.'),
    ('KARAR', 'Tüm 3.048 şirket-dönem: V7 statü → önerilen statü, gerekçe, teşhis, etki alt sınırı, en az düzeltilmiş FCF (TEŞHİS — FCF DEĞİLDİR).'),
    ('FARK', f"Statüsü değişen {int(K['Statü değişti'].sum())} satır (diff-set). Kademe-2 kuralı gereği yalnız bunlar incelenir."),
    ('Kod değişikliği', "KOZAL→TRALT, KOZAA→TRMET, IPEKE→TRENJ, MARKA→USHOL (KAP'ta USHOL bildirimlerinin unvanı Marka Yatırım Holding) "
                        "ve hiçbir kaynakta olmayan SNKRN: 30 satır Önerilen statü = ÇIKAR (aynı şirketin yeni kodlu satırlarının tekrarı). "
                        "MARKA 2025/12 TÜRETİLMİŞ (−1,49) kaynaksız; aynı dönem USHOL'da KESİN. Diğer K13 ölçümleri bu satırlardan etkilenmez."),
    ('Sürüm', 'K13 rev2 = K13 + R2 (pencere dışı TEK pozitif nokta net bayrağını tetiklemez) + R4 (yıl içi dolu noktadan sonra gelen 0, önceki FY o noktadan küçük değilse veri sayılır). R1 (zayıf ölçüsünü daraltma) holdout testinde yanlışlandı ve ALINMADI.'),
    ('OOS_TEST', 'Bağımsız belge testi: ön kayıtlı 20 ASIL satır + revizyon sonrası dondurulmuş YEDEK satırlar; her satırda belge, bulgu, K13 kararı ve doğru/yanlış.'),
    ('KALEM', 'Kalem düzeyinde ayrıntı: şüpheli köprü noktası (kesin/olası), zayıf atama, S1, net davranış, etki, V7 kaynak.'),
    ('DOGRULAMA', "DiffSet ORNEKLEM 125 belgeli satır: P0/P1/P2 ile yan yana. ⚠️ Örneklem içi (kural tasarımında da kullanıldı)."),
    ('ORNEKLEM_DISI', 'Tasarımda kullanılmayan şirketlerde belgeyle doğrulama (ADEL, EREGL).'),
    ('DUYARLILIK', 'Eşik %3 / %5 / %10 karşılaştırması.'),
    ('Sınırlar', 'KOPOL tipi gömülü kira (seri yok), CFO sunum değişikliği (K11 a–c), PDF kaynaklı bileşenler kapsam dışı. "En az düzeltilmiş FCF" bir alt sınırdır, doğru FCF değildir.'),
], columns=['Başlık', 'Açıklama'])

karar_cols = ['Kod', 'Tip', 'Sektör', 'Dönem', 'V7 statü', 'Önerilen statü', 'Statü değişti', 'Gerekçe',
              'V7 FCF (mn TL)', 'En az düzeltilmiş FCF (TEŞHİS — FCF DEĞİLDİR)', 'Toplam etki alt sınır (mn TL)',
              'Toplam karar ölçüsü (mn TL)', 'Eşik (mn TL)', 'Alarm kalemleri', 'Teşhis', 'CFO_TTM', 'CAPEX_STD', '|Kira anapara|', 'FCF türü',
              'K6 dışlanan satır', 'KOŞULLU nedeni']
KARAR = K[karar_cols].sort_values(['Kod', 'Dönem'])
# Kodu değişen / geçersiz hisseler (belge/kod_degisikligi.py ile doğrulandı): KAP finansal rapor listesinde bu kodla rapor yok,
# Evo'da kod yok; yeni kodun satırları V7'de mevcut → eski kodun satırları tekrar, ÇIKAR önerilir. K13 ölçümlerine (DUYARLILIK,
# DOGRULAMA, OOS) dokunmaz; yalnız KARAR/FARK'ta statü önerisi.
ESKI_KOD = {'KOZAL': 'TRALT', 'KOZAA': 'TRMET', 'IPEKE': 'TRENJ', 'MARKA': 'USHOL', 'SNKRN': None}
_e = KARAR.Kod.isin(list(ESKI_KOD))
KARAR.loc[_e, 'Önerilen statü'] = 'ÇIKAR'
KARAR.loc[_e, 'Statü değişti'] = KARAR.loc[_e, 'V7 statü'] != 'ÇIKAR'
KARAR.loc[_e, 'Gerekçe'] = [f"Eski kod → {ESKI_KOD[k]} (KAP'ta bu kodla rapor yok, Evo'da kod yok; şirketin satırları {ESKI_KOD[k]} altında)"
                            if ESKI_KOD[k] else "Geçersiz kod: KAP'ta rapor, Evo'da kod, Yahoo'da fiyat yok; V7'de veri yok"
                            for k in KARAR.loc[_e, 'Kod']]
okubeni.loc[okubeni['Başlık'] == 'FARK', 'Açıklama'] = (
    f"Statüsü değişen {int(KARAR['Statü değişti'].sum())} satır (diff-set; {int(K['Statü değişti'].sum())} K13 + {int(_e.sum())} kod değişikliği). "
    "Kademe-2 kuralı gereği yalnız bunlar incelenir.")
FARK = KARAR[KARAR['Statü değişti']].copy()
FARK['Karar ölçüsü / |FCF|'] = FARK['Toplam karar ölçüsü (mn TL)'] / FARK['V7 FCF (mn TL)'].abs()
FARK = FARK.sort_values('Toplam karar ölçüsü (mn TL)', ascending=False)

kalem_cols = ['Kod', 'Dönem', 'Kalem', 'V7 statü', 'V7 FCF', 'CFO_TTM', 'V7 TTM (işaretli)', 'V7 kullanılan',
              'V7 K6 dışladı', 'Şüpheli köprü noktası (kesin)', 'Şüpheli köprü noktası (olası)', 'Zayıf atama',
              'S1 cari pozitif', 'A3 net davranış (maks pozitif YTD)', 'Etki alt sınır (mn TL)', 'Karar ölçüsü (mn TL)',
              'En az düzeltilmiş kalem (mn TL)', 'Eşik (mn TL)', 'Alarm', 'Teşhis', 'Kaynak (V7)']
KALEM = R[kalem_cols].sort_values(['Kod', 'Kalem', 'Dönem'])

dog_cols = ['Aşama', 'Kod', 'Kalem', 'Dönem', 'V7 FCF statü', 'Gerçek durum', 'Kanıt düzeyi', 'Mekanizma / kanıt özeti',
            'Etki alt sınır (mn TL)', 'Karar ölçüsü (mn TL)', 'Zayıf atama', 'A3 net davranış (maks pozitif YTD)', 'Teşhis', 'Alarm',
            'P0 sonuç (formül)', 'P1 sonuç (formül)', 'P2 sonuç (formül)', 'YENİ sonuç']
DOG = D[dog_cols]

DIS = pd.DataFrame([
    dict(Kod='ADEL', Kalem='Kira anapara', Dönem='2025/09', **{
        'K13 ataması': '2024/09 noktası (kesin)', 'V7 FCF': 36.421, 'Etki alt sınır': 37.99,
        'Belge': 'ADEL 2025/09 Finansal Tablo ve Dipnotlar, s.8 (Evo chunk 55896)',
        'Bulgu': "Karşılaştırmalı 9A'24 kira ödemesi (6.069) bin TL = Evo −7,46 mn (TMS 29). Aynı yılın H1'24 değeri −49,4, FY'24 −93,3 mn. 9A tutarı şirketin kendi raporunda H1'in altında → nokta tutarsız, TTM köprüsüne giriyor.",
        'Sonuç': 'ATAMA DOĞRU — KOŞULLU yerinde (FCF işareti belirsiz)'}),
    dict(Kod='EREGL', Kalem='MDV+MODV alımı', Dönem='2025/03', **{
        'K13 ataması': '2025/03 noktası (kesin)', 'V7 FCF': 6345.172, 'Etki alt sınır': 3544.99,
        'Belge': 'EREGL 2025/03 s.8 (chunk 154038) · 2025/06 s.9 (103170) · 2026/03 s.8 (2122849)',
        'Bulgu': "Q1'25 raporu alım (11.233.376) bin TL; Q1'26 karşılaştırmalısı (11.233.069). H1'25 raporu (7.688.384) bin TL. Q1'25 alım satırı (11,23 mlr) aynı raporun yatırım bölümü toplamından (5,10 mlr) büyük. Kümülatif alım şirketin kendi raporlarında Q1→H1 arası geriliyor.",
        'Sonuç': 'ATAMA DOĞRU — KOŞULLU yerinde (etki ≥ %56 |FCF|); belge hangi değerin doğru olduğunu söylemiyor → KOŞULLU kalır'}),
])

def ozet_tablo(dd, ad):
    k = dd['K']; oz = dd['OZ']['YENİ sonuç']
    return {'Eşik': ad, 'Yakalandı': oz.get('YAKALANDI', 0), 'Sessiz hata': oz.get('SESSİZ HATA', 0),
            'Yanlış alarm': oz.get('YANLIŞ ALARM', 0),
            'Evren: KOŞULLU\'ya geçen': int(k['Statü değişti'].sum()),
            'Şirket': int(k.loc[k['Statü değişti'], 'Kod'].nunique()),
            'KOŞULLU oranı': (k['Önerilen statü'] == 'KOŞULLU').mean()}

DUY = pd.DataFrame([ozet_tablo(d3, 'max(1 mn; %3|FCF|)'), ozet_tablo(d, 'max(1 mn; %5|FCF|) ← seçilen'),
                    ozet_tablo(d10, 'max(1 mn; %10|FCF|)')])
ref = pd.DataFrame([{'Eşik': f'Referans {p}', 'Yakalandı': D[c].eq('YAKALANDI').sum(), 'Sessiz hata': D[c].eq('SESSİZ HATA').sum(),
                     'Yanlış alarm': D[c].eq('YANLIŞ ALARM').sum()} for p, c in
                    [('P0 (V7)', 'P0 sonuç (formül)'), ('P1', 'P1 sonuç (formül)'), ('P2', 'P2 sonuç (formül)')]])
DUY = pd.concat([ref, DUY], ignore_index=True)

OOS = pd.DataFrame(json.load(open('OOS_SONUCLAR.json')))
OOS.insert(0, 'Set', 'ASIL-20 (ön kayıt a34b8ca)')
YED = pd.DataFrame(json.load(open('YEDEK_SONUCLAR.json')))
YED.insert(0, 'Set', 'YEDEK (ön kayıt d00975b, revizyon sonrası)')
OOST = pd.concat([OOS, YED], ignore_index=True).astype(str)
OUT = 'FCF_V8_aday_K13.xlsx'
with pd.ExcelWriter(OUT, engine='openpyxl') as w:
    for name, df in [('OKUBENI', okubeni), ('KARAR', KARAR), ('FARK', FARK), ('KALEM', KALEM),
                     ('DOGRULAMA', DOG), ('OOS_TEST', OOST), ('ORNEKLEM_DISI', DIS), ('DUYARLILIK', DUY)]:
        df.to_excel(w, sheet_name=name, index=False)
        ws = w.sheets[name]
        for c in ws[1]:
            c.font = Font(bold=True, color='FFFFFF')
            c.fill = PatternFill('solid', fgColor='1F4E78')
            c.alignment = Alignment(wrap_text=True, vertical='top')
        ws.freeze_panes = 'A2'
        for col in ws.columns:
            L = max(len(str(c.value)) if c.value is not None else 0 for c in list(col)[:200])
            ws.column_dimensions[col[0].column_letter].width = min(max(10, L * 0.9), 60)
    ws = w.sheets['OKUBENI']
    ws.column_dimensions['B'].width = 140
    for row in ws.iter_rows(min_row=2):
        row[1].alignment = Alignment(wrap_text=True, vertical='top')
print('yazıldı', OUT, len(KARAR), len(FARK), len(KALEM))
print(DUY.to_string())
