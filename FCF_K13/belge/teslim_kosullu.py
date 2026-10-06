"""KOŞULLU satırların belge kontrolü teslim dosyası → KOSULLU_belge_kontrol.xlsx"""
import pandas as pd

R = pd.read_csv('kosullu_sonuc.csv')
okubeni = pd.DataFrame([
    ('Kapsam', 'K13 önerisinde KOŞULLU olan 405 satır (V7 KOŞULLU 172 + KESİN→KOŞULLU 200 + TÜRETİLMİŞ→KOŞULLU 33).'),
    ('Yöntem', 'Her satır için şirketin kendi raporlarından TTM = YTD_cari + FY_önceki − YTD_önceki (NULL çalışmasıyla aynı '
               'hesap, aynı TMS 29 çevrimi: değer × F(rapor) / F(şirketin son raporu)). Bileşenler V7 ile kıyaslanır.'),
    ('Kaynak', 'KAP bildirimi (XBRL + imzalı PDF) — KAP erişimi kesildiğinde Evo belge havuzundaki orijinal PDF '
               '(storage.fintables.com; KAP ekinin aynısı). Evo havuzu raporların yaklaşık %45’ini kapsıyor. İkisinde de yoksa '
               'şirketin kendi sitesindeki finansal rapor PDF’i (belge/site/: adres Evo kurumsal bilgi kartından, tarama + dönem '
               'eşleme + aynı okuyucu; metinde dönem sonu tarihi ve CFO özdeşliği zorunlu). Kanıtta “Şirket sitesi <url>”.'),
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
    ('Holding', 'V7’de FCF türü FCF_HLD olan satırlarda dördüncü bileşen: yatırım bölümündeki alınan temettüler. FCF_HLD = CFO + '
                'temettü − CAPEX_STD − |Kira| (V7 Notlar ②). Temettü XBRL yatırım elemanından (PDF’te teyit) ya da PDF yatırım '
                'bölümü satırından; işletme bölümündeki “Alınan temettüler” eklenmez (V7 çifte sayım kilidi).'),
    ('Tutarlar', 'mn TL, Haziran 2026 satın alma gücü (TMS 29 uygulayanlar); bileşen işaretleri belgedeki gibi.'),
], columns=['Başlık', 'Açıklama'])
# elle kalan satırların gerekçesi (belgeden incelendi)
ACIKLAMA = {
    'ODAS': 'ODAS nakit akış tabloları güvenilmez: MDV alımları bazı raporlarda pozitif (giriş gibi), aynı dönem farklı '
            'raporlarda farklı işaretle; A+B+C(+D) basılı net değişimle tutmuyor (2025/03: 3 mn, 2025/06: 4,5 mn fark). '
            'CFO başlık toplamları açık etiketli olsa da CAPEX/kira belgeden güvenle kurulamıyor.',
    'GOKNR': 'GOKNR 2025/06 ve 2025/09 (şirket sitesi raporları): MDV alım ve satışı tek net satırda, her bölümde ayrı '
             '"enflasyon etkisi" satırı var; bu sunumda işletme nakit akışının tanımı Evo’dan farklı (belge 693,7 / V7 605,0) ve '
             'CAPEX net satırdan ayrıştırılamıyor → belgeden tek değere bağlanamadı.',
    'CANTE': 'CANTE (ODAS bağlı ortaklığı) nakit akış tabloları raporlar arası tutarsız: aynı dönem MDV alımı farklı raporlarda '
             'farklı tutar/işaretle (2025/06 kendi raporunda +233,6 mn, 2026/06 karşılaştırmalısında +308,6 mn), kira için 3 ayrı '
             'satır her raporda farklı. CFO tüm dönemlerde V7 ile aynı; CAPEX/kira belgeden güvenle kurulamıyor.',
    'KATMR': 'KATMR 2024 işletme nakit akışı orijinal 31.12.2024 raporunda +2.506,4 mn, 31.12.2025 raporunun karşılaştırmalısında '
             '999,0 mn (yeniden düzenleme). V7 düzenlenmiş esasla birebir tutuyor; 2024 ara dönem orijinal raporları bulunamadığından '
             'hangi esasın 2025 ara dönem raporlarıyla tutarlı olduğu belgeyle gösterilemedi.',
    'GSDHO': 'GSDHO 2025/09: A başlık değeri (1.764.997 bin TL) ile alt toplamlar ve dönem sonu − başı nakit değişimi '
             'birbiriyle tutmuyor; CFO belgeden tek değere bağlanamadı.',
}
# belge değeri olan satırlarda özel inceleme notları (Kod|Dönem)
NOT = {'PLTUR|2025/12': 'PLTUR (araç kiralama): filo alımları işletme bölümünde. GEM: CFO nakit akış tablosundaki satır olduğu gibi alınır → PDF \'İşletme Faaliyetlerinden Sağlanan/(Kullanılan) Net Nakit\' (filo alımları düşülmüş). XBRL/Evo CFO bu satırla uyuşmuyor ve XBRL MDV filo alımlarını da içeriyor → MDV = yatırım bölümündeki \'Maddi ve Maddi Olmayan Duran Varlık Alımları\' satırı (çift sayım yok). Kira satırı yok → 0. 2026/06: 1.405,6 − 63,7 − 24,4 = 1.317,6 mn TL (Evo 2.147,8).', 'PLTUR|2026/03': 'PLTUR (araç kiralama): filo alımları işletme bölümünde. GEM: CFO nakit akış tablosundaki satır olduğu gibi alınır → PDF \'İşletme Faaliyetlerinden Sağlanan/(Kullanılan) Net Nakit\' (filo alımları düşülmüş). XBRL/Evo CFO bu satırla uyuşmuyor ve XBRL MDV filo alımlarını da içeriyor → MDV = yatırım bölümündeki \'Maddi ve Maddi Olmayan Duran Varlık Alımları\' satırı (çift sayım yok). Kira satırı yok → 0. 2026/06: 1.405,6 − 63,7 − 24,4 = 1.317,6 mn TL (Evo 2.147,8).', 'PLTUR|2026/06': 'PLTUR (araç kiralama): filo alımları işletme bölümünde. GEM: CFO nakit akış tablosundaki satır olduğu gibi alınır → PDF \'İşletme Faaliyetlerinden Sağlanan/(Kullanılan) Net Nakit\' (filo alımları düşülmüş). XBRL/Evo CFO bu satırla uyuşmuyor ve XBRL MDV filo alımlarını da içeriyor → MDV = yatırım bölümündeki \'Maddi ve Maddi Olmayan Duran Varlık Alımları\' satırı (çift sayım yok). Kira satırı yok → 0. 2026/06: 1.405,6 − 63,7 − 24,4 = 1.317,6 mn TL (Evo 2.147,8).', 'DGNMO|2025/06': 'DGNMO 2025/06 şirket sitesi konsolide raporu: A 524.522.345, A+B+C(+etki) = net değişim ✓. Evo 2024/06 '
                        've 2024/12 değerleri belgelerle birebir; yalnız Evo 2025/06 CFO (−1.404,8 mn) belgeyle uyuşmuyor → Evo hatası.',
       **{f'SAHOL|{d}': 'SAHOL 2024 nakit akışını 31.12.2025 raporunda işletme↔yatırım arasında yeniden sınıflamış (2024 işletme: '
                         'orijinal (90,8) mlr, düzenlenmiş +153,2 mlr; net değişim aynı). 2025/03–09 raporlarının karşılaştırmalı sütunları '
                         'eski esasta (Evo 2024/03-06-09 bunlarla aynı) → tutarlı TTM orijinal 2024 raporuyla kurulur. Evo 2024/12’yi yeni '
                         'esastan (+180,4 mlr) almış; V7 TTM iki esası karıştırıyor.' for d in ('2025/03', '2025/06', '2025/09')},
       'KTSKR|2026/03': 'KTSKR 2026/03: MDV alımı 24.122.658 pozitif basılmış; özdeşlik ancak çıkış işaretiyle tutuyor → (24.122.658). '
                        'V7/Evo basılı işareti kullanmış.'}
R['Açıklama'] = [ACIKLAMA.get(k, '') if s == 'ELLE' else NOT.get(f'{k}|{d}', '') for k, s, d in zip(R.Kod, R['Sonuç'], R['Dönem'])]
ozet = R['Sonuç'].value_counts().rename_axis('Sonuç').reset_index(name='Satır')
kolon = ['Kod', 'Tip', 'Dönem', 'Sonuç', 'Fark özeti', 'Açıklama', 'Satır statü',
         'CFO TTM', 'V7 CFO_TTM (Evo)', 'CFO TTM nominal', 'CAPEX_STD (belge)', 'V7 CAPEX_STD (Evo)',
         '|Kira| (belge)', 'V7 |Kira| (Evo)', 'FCF_STD (belge)', 'V7 FCF türü', 'TEMETTU (belge)', 'V7 temettü',
         'FCF_HLD (belge)', 'V7 FCF_HLD (Evo)', 'TEMETTU kıyas', 'TEMETTU statü', 'TEMETTU bileşen', 'TEMETTU kanıt',
         'CFO statü', 'CFO bileşen', 'CFO kanıt', 'MDV+MODV statü', 'MDV+MODV bileşen', 'MDV+MODV kanıt',
         'YAGM statü', 'YAGM bileşen', 'YAGM kanıt', 'KIRA statü', 'KIRA bileşen', 'KIRA kanıt', 'K6 dışlanan (belge)']
with pd.ExcelWriter('KOSULLU_belge_kontrol.xlsx') as w:
    okubeni.to_excel(w, sheet_name='OKUBENI', index=False)
    ozet.to_excel(w, sheet_name='OZET', index=False)
    for s in ('BELGE_DEGERI', 'KESİN_ONERI', 'KESİN_ONERI_YAKIN', 'YEDEK_FARKLI', 'ELLE', 'BELGE_YOK'):
        R[R['Sonuç'] == s][[k for k in kolon if k in R]].to_excel(w, sheet_name=s[:31], index=False)
    R[[k for k in kolon if k in R]].to_excel(w, sheet_name='TUMU', index=False)
print(ozet.to_string(index=False))
