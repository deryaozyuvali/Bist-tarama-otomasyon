"""KOŞULLU satırların belge kontrolü teslim dosyası → KOSULLU_belge_kontrol.xlsx"""
import pandas as pd

R = pd.read_csv('kosullu_sonuc.csv')
okubeni = pd.DataFrame([
    ('Kapsam', 'K13 önerisinde KOŞULLU olan 405 satır (V7 KOŞULLU 172 + KESİN→KOŞULLU 200 + TÜRETİLMİŞ→KOŞULLU 33).'),
    ('Yöntem', 'Her satır için şirketin kendi raporlarından TTM = YTD_cari + FY_önceki − YTD_önceki (NULL çalışmasıyla aynı '
               'hesap, aynı TMS 29 çevrimi: değer × F(rapor) / F(şirketin son raporu)). Bileşenler V7 ile kıyaslanır.'),
    ('Kaynak', 'KAP bildirimi (XBRL + imzalı PDF) — KAP erişimi kesildiğinde Evo belge havuzundaki orijinal PDF '
               '(storage.fintables.com; KAP ekinin aynısı). Evo havuzu raporların yaklaşık %45’ini kapsıyor.'),
    ('XBRL’siz PDF okuma güvenilirliği', 'XBRL ile teyitli ~1.000 rapora karşı test: özdeşlikle (A+B+C(+etki) = nakit değişimi) '
               'okunan CFO 1.037/1.042 doğru; tek adaylı CFO 70/92 (yalnız V7 ile örtüşürse kabul); MDV+MODV satırı %99 doğru; '
               '"MDV satırı yok → 0" güvenilmez (elle). Türetilmiş CFO (net − B − C) testte başarısız olduğu için kullanılmıyor.'),
    ('Sonuç: KESİN_ONERI', 'CFO, CAPEX_STD ve |Kira| belgeyle V7 aynı (%0,5 + 0,05 mn) → V7 değeri belgeyle teyitli; KESİN önerilir.'),
    ('Sonuç: BELGE_DEGERI', 'Belge değerleri güvenilir ve en az bir bileşen V7’den farklı → belge değeri önerilir. '
               'Fark nedeni EVO_NOMINAL: V7, belgenin TMS 29 çevrimsiz (nominal) haliyle tutuyor — Evo bu şirkette dönemleri '
               'kendi raporundaki haliyle saklayıp TTM’i karışık kurmuş. FARKLI: Evo’da başka bir değer (ör. OBAMS 2025/06 CFO '
               'Evo 1.618,7 mn, belge 296,3 mn; SASA/KRDM/EKOS kira Evo’da yok).'),
    ('Sonuç: ELLE', 'Belge değerlerinden en az biri düşük güvenli/okunamadı ve V7 ile tam örtüşme yok.'),
    ('Sonuç: BELGE_YOK', 'Gereken rapor(lar) KAP’tan indirilemedi (erişim engeli) ve Evo havuzunda yok — KAP açılınca tamamlanacak.'),
    ('Tutarlar', 'mn TL, Haziran 2026 satın alma gücü (TMS 29 uygulayanlar); bileşen işaretleri belgedeki gibi.'),
], columns=['Başlık', 'Açıklama'])
ozet = R['Sonuç'].value_counts().rename_axis('Sonuç').reset_index(name='Satır')
kolon = ['Kod', 'Tip', 'Dönem', 'Sonuç', 'Fark özeti', 'Satır statü',
         'CFO TTM', 'V7 CFO_TTM (Evo)', 'CFO TTM nominal', 'CAPEX_STD (belge)', 'V7 CAPEX_STD (Evo)',
         '|Kira| (belge)', 'V7 |Kira| (Evo)', 'FCF_STD (belge)',
         'CFO statü', 'CFO bileşen', 'CFO kanıt', 'MDV+MODV statü', 'MDV+MODV bileşen', 'MDV+MODV kanıt',
         'YAGM statü', 'YAGM bileşen', 'YAGM kanıt', 'KIRA statü', 'KIRA bileşen', 'KIRA kanıt', 'K6 dışlanan (belge)']
with pd.ExcelWriter('KOSULLU_belge_kontrol.xlsx') as w:
    okubeni.to_excel(w, 'OKUBENI', index=False)
    ozet.to_excel(w, 'OZET', index=False)
    for s in ('BELGE_DEGERI', 'KESİN_ONERI', 'ELLE', 'BELGE_YOK'):
        R[R['Sonuç'] == s][[k for k in kolon if k in R]].to_excel(w, s[:31], index=False)
    R[[k for k in kolon if k in R]].to_excel(w, 'TUMU', index=False)
print(ozet.to_string(index=False))
