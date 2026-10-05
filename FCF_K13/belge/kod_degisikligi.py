"""Hisse kodu değişenler / geçersiz kodlar → kod_degisikligi.csv
Kontrol: KAP finansal rapor listesi (kap_fr.json) bu kodla hiç rapor içermiyor VE Evo'da bu kod yok (sembol_arama,
nakit akış tablosu). Yeni kodun raporları KAP'ta, Evo'da ve V7'de mevcut → eski koddaki satırlar tekrar; K13'ten çıkarılır."""
import pandas as pd
ESKI = {
    'KOZAL': ('TRALT', "KAP/Evo'da KOZAL yok; TRALT 2024/03–2026/06 tüm dönemler Evo'da, V7'de dolu"),
    'KOZAA': ('TRMET', "KAP/Evo'da KOZAA yok; TRMET tüm dönemler Evo'da, V7'de dolu"),
    'IPEKE': ('TRENJ', "KAP/Evo'da IPEKE yok; TRENJ tüm dönemler Evo'da, V7'de dolu"),
    'MARKA': ('USHOL', "KAP'ta USHOL kodlu raporların unvanı 'MARKA YATIRIM HOLDİNG A.Ş.'; Evo'da USHOL = US Yatırım "
                       "Holding, MARKA yok. V7 MARKA 2025/12 TÜRETİLMİŞ (−1,49) kaynaksız; USHOL 2025/12 KESİN (−1,76)"),
    'SNKRN': ('—', "KAP'ta rapor yok, Evo'da kod yok, Yahoo verisi yok; V7'de 6 dönem NULL, veri yok"),
}
K = pd.read_excel('../FCF_V8_aday_K13.xlsx', sheet_name='KARAR', keep_default_na=False, na_values=[''])
R = K[K.Kod.isin(list(ESKI))][['Kod', 'Dönem', 'V7 statü', 'Önerilen statü', 'CFO_TTM']].copy()
R['Yeni kod'] = R.Kod.map(lambda k: ESKI[k][0])
R['Öneri'] = 'ÇIKAR (eski/geçersiz kod)'
R['Gerekçe'] = R.Kod.map(lambda k: ESKI[k][1])
R.to_csv('kod_degisikligi.csv', index=False)
print(R.groupby('Kod').size().to_dict(), len(R))
