"""Artifact sayfası: k13_sayfa_sablon.html + rev2 sonuçları → fcf_k13_paketi.html"""
import html, json
import pandas as pd
GH = 'https://github.com/deryaozyuvali/Bist-tarama-otomasyon/blob/fcf-k13-paket/FCF_K13'
TREE = 'https://github.com/deryaozyuvali/Bist-tarama-otomasyon/tree/fcf-k13-paket/FCF_K13'
d = pd.read_pickle('karar_5_rev2.pkl'); K = d['K']; OZ = d['OZ']['YENİ sonuç']
F = K[K['Statü değişti']].copy()
F['oran'] = F['Toplam karar ölçüsü (mn TL)'] / F['V7 FCF (mn TL)'].abs() * 100
F = F.sort_values('Toplam karar ölçüsü (mn TL)', ascending=False)
def neden(r):
    return 'Seri+Net' if r['Seri alarmı'] and r['Net alarmı'] else ('Seri' if r['Seri alarmı'] else 'Net')
def num(x, n=1):
    return None if pd.isna(x) else round(float(x), n)
ROWS = [[r.Kod, r['Dönem'], r['V7 statü'], num(r['V7 FCF (mn TL)']), num(r['Toplam karar ölçüsü (mn TL)']),
         num(r['Eşik (mn TL)']), num(r['oran']), r['Alarm kalemleri'], neden(r),
         num(r['En az düzeltilmiş FCF (TEŞHİS — FCF DEĞİLDİR)'])] for _, r in F.iterrows()]
n, ns = len(F), F.Kod.nunique()
oran = (K['Önerilen statü'] == 'KOŞULLU').mean() * 100
s = open('k13_sayfa_sablon.html').read()
s = s.replace('__GH__', GH).replace('__TREE__', TREE)
s = s.replace('__GEM__', html.escape(open('GEM_K6v2_K13_onerisi.txt').read()))
s = s.replace('__ROWS__', json.dumps(ROWS, ensure_ascii=False))
s = s.replace('<tr class="us"><td>K13</td><td class="n">31</td><td class="n">4</td><td class="n">13</td></tr>',
              f'<tr class="us"><td>K13 rev2</td><td class="n">{OZ.get("YAKALANDI",0)}</td><td class="n">{OZ.get("SESSİZ HATA",0)}</td><td class="n">{OZ.get("YANLIŞ ALARM",0)}</td></tr>')
s = s.replace('<strong>255</strong><span>FCF satırı KOŞULLU\'ya geçer (99 şirket)</span>',
              f'<strong>{n}</strong><span>FCF satırı KOŞULLU\'ya geçer ({ns} şirket)</span>')
s = s.replace('<strong>%5,6 → %14,0</strong>', f'<strong>%5,6 → %{oran:.1f}</strong>'.replace('.', ','))
s = s.replace('<h2>Statüsü değişen 255 satır</h2>', f'<h2>Statüsü değişen {n} satır</h2>')
TEST = '''<section>
  <h2>Bağımsız belge testi</h2>
  <p>Satırlar belge okunmadan önce seçildi, K13'ün tahminleri donduruldu ve commit edildi. Belgeler ondan sonra okundu. Kural revize edildikten sonra yeni tahminler yeniden donduruldu ve yedek satırlarda ikinci kez sınandı.</p>
  <div class="scroll"><table>
    <thead><tr><th>Set</th><th class="n">Hata yakalandı</th><th class="n">Hata kaçtı</th><th class="n">Yanlış alarm</th></tr></thead>
    <tbody>
      <tr><td>20 satır · eski K13</td><td class="n">7 / 8</td><td class="n">1</td><td class="n">4 / 12</td></tr>
      <tr class="us"><td>20 satır · K13 rev2</td><td class="n">8 / 8</td><td class="n">0</td><td class="n">3 / 12</td></tr>
      <tr><td>Yedek, kuralların ayrıştığı 4 satır · eski K13</td><td class="n">2 / 2</td><td class="n">0</td><td class="n">2 / 2</td></tr>
      <tr class="us"><td>Yedek, kuralların ayrıştığı 4 satır · K13 rev2</td><td class="n">2 / 2</td><td class="n">0</td><td class="n">1 / 2</td></tr>
    </tbody>
  </table></div>
  <ul class="cases">
    <li><div><code>BERA 2026/06</code><span class="tag k">rev2 yakalar</span></div><p>Şirket alım ve satışı tek net satırda veriyor; Evo yarıyıl alımını 0 saklamış. Dipnotta brüt alım ≈72, eşik 19,8. Eski K13 sıfırı "kayıt yok" saydığı için kaçırıyordu.</p></li>
    <li><div><code>CATES · EGSER</code><span class="tag ok">rev2 susar</span></div><p>Pencere dışında tek bir pozitif nokta (eşleme hatası) net bayrağını tetikliyordu. Belgeyle ikisi de temiz.</p></li>
    <li><div><code>BIENY · KRPLS</code><span class="tag k">KOŞULLU kalır</span></div><p>Zayıf atama ölçüsünü daraltma denemesi bu iki gerçek hatayı kaçırdı. Deneme geri alındı; ölçü olduğu gibi kaldı.</p></li>
    <li><div><code>DENGE · OYLUM · TCKRC · OTTO</code><span class="tag">yanlış alarm</span></div><p>Bozuk nokta köprü dışında ya da alım satırına yatırım toplamı yazılmış. Maliyeti gereksiz bir dipnot okuması.</p></li>
  </ul>
  <p class="note">Bağımsız toplam: 10 gerçek hatanın 10'u yakalandı, 14 temiz satırın 4'ünde yanlış alarm. Örneklem küçük; "hiç kaçırmaz" diye okunmamalı. Eşik: %3 ek bir şey yakalamıyor, %10 TTRAK'ı kaçırıyor; %5 kanıtla desteklenen seçenek.</p>
</section>

<section>
  <h2>Statüsü değişen'''
s = s.replace('<section>\n  <h2>Statüsü değişen', TEST, 1)
assert '__' not in s.replace('__proto__', ''), 'yer tutucu kaldı'
open('fcf_k13_paketi.html', 'w').write(s)
print('sayfa yazıldı', n, ns, round(oran, 1))
