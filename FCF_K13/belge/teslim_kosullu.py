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
    ('Sonuç: KESİN_ONERI_YAKIN', 'Bileşenler V7 ile en fazla %3 farklı — TMS 29 yeniden ifadesinin Evo’daki uygulama ayrıntısı '
               'düzeyinde; belge V7’yi esasen doğruluyor, KESİN önerilir.'),
    ('Sonuç: BELGE_DEGERI', 'Belge değerleri güvenilir ve en az bir bileşen V7’den farklı → belge değeri önerilir. '
               'Fark nedeni EVO_NOMINAL: V7, belgenin TMS 29 çevrimsiz (nominal) haliyle tutuyor — Evo bu şirkette dönemleri '
               'kendi raporundaki haliyle saklayıp TTM’i karışık kurmuş. FARKLI: Evo’da başka bir değer (ör. OBAMS 2025/06 CFO '
               'Evo 1.618,7 mn, belge 296,3 mn; SASA/KRDM/EKOS kira Evo’da yok).'),
    ('Yedek kaynak', 'Bir rapor yoksa aynı dönemin değeri başka raporun sütunundan alınır: dönem değeri bir yıl sonraki '
               'aynı dönem raporunun karşılaştırmalı sütunundan, önceki yıl sonu cari yıl sonu raporunun karşılaştırmalı '
               'sütunundan (TMS 29 çevrimi kaynak raporun tarihiyle). Kanıtta "yedek:" olarak yazılır.'),
    ('Sonuç: YEDEK_FARKLI', 'Belge V7’den farklı, ama farklı bileşen yedek sütundan kuruldu. Şirket o dönemi sonraki '
               'raporda yeniden düzenlemiş olabilir (ör. BVSAN 2024 CFO) → orijinal rapor görülmeden belge değeri önerilmez.'),
    ('Sonuç: ELLE', 'Belge değerlerinden en az biri düşük güvenli/okunamadı ve V7 ile tam örtüşme yok.'),
    ('Sonuç: BELGE_YOK', 'Gereken rapor(lar) KAP’tan indirilemedi (erişim engeli) ve Evo havuzunda yok — KAP açılınca tamamlanacak.'),
    ('Tutarlar', 'mn TL, Haziran 2026 satın alma gücü (TMS 29 uygulayanlar); bileşen işaretleri belgedeki gibi.'),
], columns=['Başlık', 'Açıklama'])
# elle kalan satırların gerekçesi (belgeden incelendi)
ACIKLAMA = {
    'ODAS': 'ODAS nakit akış tabloları güvenilmez: MDV alımları bazı raporlarda pozitif (giriş gibi), aynı dönem farklı '
            'raporlarda farklı işaretle; A+B+C(+D) basılı net değişimle tutmuyor (2025/03: 3 mn, 2025/06: 4,5 mn fark). '
            'CFO başlık toplamları açık etiketli olsa da CAPEX/kira belgeden güvenle kurulamıyor.',
    'GSDHO': 'GSDHO 2025/09: A başlık değeri (1.764.997 bin TL) ile alt toplamlar ve dönem sonu − başı nakit değişimi '
             'birbiriyle tutmuyor; CFO belgeden tek değere bağlanamadı.',
}
R['Açıklama'] = [ACIKLAMA.get(k, '') if s == 'ELLE' else '' for k, s in zip(R.Kod, R['Sonuç'])]
ozet = R['Sonuç'].value_counts().rename_axis('Sonuç').reset_index(name='Satır')
kolon = ['Kod', 'Tip', 'Dönem', 'Sonuç', 'Fark özeti', 'Açıklama', 'Satır statü',
         'CFO TTM', 'V7 CFO_TTM (Evo)', 'CFO TTM nominal', 'CAPEX_STD (belge)', 'V7 CAPEX_STD (Evo)',
         '|Kira| (belge)', 'V7 |Kira| (Evo)', 'FCF_STD (belge)',
         'CFO statü', 'CFO bileşen', 'CFO kanıt', 'MDV+MODV statü', 'MDV+MODV bileşen', 'MDV+MODV kanıt',
         'YAGM statü', 'YAGM bileşen', 'YAGM kanıt', 'KIRA statü', 'KIRA bileşen', 'KIRA kanıt', 'K6 dışlanan (belge)']
with pd.ExcelWriter('KOSULLU_belge_kontrol.xlsx') as w:
    okubeni.to_excel(w, sheet_name='OKUBENI', index=False)
    ozet.to_excel(w, sheet_name='OZET', index=False)
    for s in ('BELGE_DEGERI', 'KESİN_ONERI', 'KESİN_ONERI_YAKIN', 'YEDEK_FARKLI', 'ELLE', 'BELGE_YOK'):
        R[R['Sonuç'] == s][[k for k in kolon if k in R]].to_excel(w, sheet_name=s[:31], index=False)
    R[[k for k in kolon if k in R]].to_excel(w, sheet_name='TUMU', index=False)
print(ozet.to_string(index=False))
