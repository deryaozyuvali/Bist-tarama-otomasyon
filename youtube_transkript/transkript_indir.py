#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
transkript_indir.py — YouTube oynatma listesindeki TÜM videoların
transkriptlerini (kanal üyelerine özel videolar dahil) .txt olarak indirir.

Neden hazır araçlar çalışmıyor?
    Üyelere özel videolar sadece üye olan hesabın oturumuyla açılır. Online
    "YouTube transcript" siteleri, tarayıcı eklentileri ve
    youtube-transcript-api gibi kütüphaneler senin hesabınla giriş yapmadığı
    için bu videolarda "Join this channel..." hatası alır. Bu script yt-dlp'yi
    SENİN tarayıcındaki YouTube oturumuyla (çerezlerle) çalıştırır. Bu yüzden
    kendi bilgisayarında çalıştırılmalı; çerezlerini hiçbir yere yükleme.

Ne yapar?
    1. Listedeki videoları sırayla bulur.
    2. Her video için kanalın eklediği altyazıyı, yoksa YouTube'un otomatik
       (konuşmadan üretilen) altyazısını indirir.
    3. Altyazı yoksa ve --whisper verildiyse sesi indirip bilgisayarında
       Whisper ile yazıya döker.
    4. Her video için "001 - Başlık.txt", hepsi bir arada
       "_TUM_TRANSKRIPTLER.txt" ve durum raporu "_durum.csv" yazar.
    Tekrar çalıştırıldığında kaldığı yerden devam eder: inen ham altyazılar
    "_ham" klasöründe durur ve bir daha indirilmez.

Kullanım (ayrıntılar README.md'de):
    python transkript_indir.py --tarayici firefox
    python transkript_indir.py --tarayici firefox --sadece 1-3
    python transkript_indir.py --cerez cookies.txt
    python transkript_indir.py "<başka liste ya da video linki>" --tarayici chrome
"""
import argparse
import contextlib
import csv
import functools
import importlib
import json
import random
import re
import shlex
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

VARSAYILAN_LISTE = "https://www.youtube.com/playlist?list=PLY3uBtlqxtjcBbEBlBX4ZGq0q4g6g4CCg"
YTDLP_PAKETI = "yt-dlp[default,deno,curl-cffi]"
BURASI = Path(__file__).resolve().parent

KAYNAK_ADLARI = {
    "manuel": "Kanalın eklediği altyazı",
    "otomatik": "YouTube otomatik altyazısı",
    "otomatik-ceviri": "YouTube otomatik altyazısı (makine çevirisi)",
    "whisper": "Whisper ile sesten yazıya",
}

# Hata türü -> (YouTube/yt-dlp mesajında geçen ifadeler, kullanıcıya açıklama)
IPUCLARI = {
    "uyelik": (
        ("members-only", "join this channel", "channel's members"),
        "Üyelere özel video açılamadı. Çerezler kanala üye olan hesaba ait olmalı "
        "(README > Sorun giderme).",
    ),
    "bot": (
        ("sign in to confirm", "not a bot"),
        "YouTube bot doğrulaması istedi. Giriş yapılmış tarayıcının çerezlerini kullan "
        "ve --bekleme süresini artır.",
    ),
    "hiz": (
        ("429", "too many requests", "rate-limited", "try again later"),
        "YouTube hız sınırı. ~1 saat bekleyip aynı komutu tekrar çalıştır; kaldığı yerden devam eder.",
    ),
    "pot": (
        ("po token",),
        "YouTube bu videonun altyazısı için PO token istiyor (README > Sorun giderme > PO token).",
    ),
    "ozel": (("private video",), "Özel (private) video, erişim yok."),
    "yok": (
        ("video unavailable", "has been removed", "no longer available"),
        "Video kaldırılmış ya da erişilemiyor.",
    ),
    "canli": (
        ("premieres in", "live event will begin", "is upcoming"),
        "Henüz yayınlanmamış canlı yayın ya da prömiyer.",
    ),
}

TARAYICI_IPUCU = """Tarayıcı çerezleri okunamadı. Şunları dene:
  - Firefox kullan (en sorunsuz yol): --tarayici firefox
  - Chrome/Edge/Brave kullanıyorsan tarayıcıyı TAMAMEN kapatıp tekrar dene
  - Windows'ta Chrome çerezleri çoğu zaman dışarıdan okunamıyor; cookies.txt
    dışa aktarıp --cerez cookies.txt ile çalıştır (README > Sorun giderme)"""

DOSYA_IPUCU = """cookies.txt okunamadı. Dosya Netscape biçiminde olmalı: "Get cookies.txt
LOCALLY" eklentisiyle youtube.com açıkken dışa aktar (README > Sorun giderme)."""


class TranskriptHatasi(Exception):
    pass


def _ensure(paket, modul, zorunlu=True):
    """Paket kurulu değilse pip ile kurar (gate.py'deki yöntem)."""
    try:
        return importlib.import_module(modul)
    except ImportError:
        pass
    print(f"Gerekli paket kuruluyor: {paket}")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "-U", paket])
        importlib.invalidate_caches()
        return importlib.import_module(modul)
    except (subprocess.CalledProcessError, OSError, ImportError):
        mesaj = f'"{paket}" kurulamadı. Elle kurmayı dene:\n  "{sys.executable}" -m pip install -U "{paket}"'
        if zorunlu:
            sys.exit(mesaj)
        print("UYARI: " + mesaj)
        return None


# ---------------------------------------------------------------------------
# Mesajlar ve hatalar
# ---------------------------------------------------------------------------

def temizle(mesaj):
    """yt-dlp mesajından renk kodlarını ve "ERROR: [youtube] abc123:" önekini atar."""
    mesaj = re.sub(r"\x1b\[[0-9;]*m", "", str(mesaj)).strip()
    mesaj = re.sub(r"^(ERROR|WARNING):\s*", "", mesaj)
    return re.sub(r"^\[[\w:]+\]\s*[\w-]+:\s*", "", mesaj)


def hata_turu(hata):
    kucuk = str(hata).lower()
    for tur, (ifadeler, _) in IPUCLARI.items():
        if any(i in kucuk for i in ifadeler):
            return tur
    return None


def hata_aciklamasi(hata):
    mesaj = temizle(hata)
    tur = hata_turu(hata)
    if tur is None or isinstance(hata, TranskriptHatasi):
        return mesaj[:300]
    return f"{IPUCLARI[tur][1]} [YouTube: {mesaj[:160]}]"


class Gunluk:
    """yt-dlp'nin mesajlarını toplar. Altyazı/çerez gibi önemli uyarıları gösterir,
    gerisini sadece --ayrinti ile basar."""

    ONEMLI = re.compile(r"cookie|subtitle|javascript|js runtime|impersonat|rate.?limit", re.I)

    def __init__(self, ayrinti):
        self.ayrinti = ayrinti
        self.uyarilar = []
        self._gosterilen = set()

    def debug(self, mesaj):
        if self.ayrinti:
            print(mesaj)

    info = debug

    def warning(self, mesaj):
        self.uyarilar.append(mesaj)
        if self.ayrinti or (self.ONEMLI.search(mesaj) and mesaj not in self._gosterilen):
            self._gosterilen.add(mesaj)
            print(f"   yt-dlp uyarısı: {temizle(mesaj)}")

    def error(self, mesaj):
        self.uyarilar.append(mesaj)
        if self.ayrinti:
            print(mesaj)


# ---------------------------------------------------------------------------
# yt-dlp ayarları
# ---------------------------------------------------------------------------

def js_ortami():
    """YouTube'un JavaScript sınamalarını çözmesi için yt-dlp'ye deno'yu gösterir.
    deno, pip paketi olarak geliyor; ayrıca kurmak gerekmiyor."""
    deno = _ensure("deno", "deno", zorunlu=False)
    with contextlib.suppress(Exception):
        return {"deno": {"path": str(deno.find_deno_bin())}}
    return {"deno": {}}  # PATH'te deno varsa yt-dlp kendisi bulur


def ytdlp_ayarlari(args, gunluk):
    import yt_dlp

    # Çerez seçeneklerini (ve --ytdlp ile verilenleri) yt-dlp'nin kendi komut
    # satırı ayrıştırıcısıyla çeviriyoruz; hatalı tarayıcı adı vb. orada yakalanır.
    secenekler = []
    if args.tarayici:
        secenekler += ["--cookies-from-browser", args.tarayici]
    if args.cerez:
        secenekler += ["--cookies", str(Path(args.cerez).expanduser())]
    secenekler += shlex.split(args.ytdlp)
    try:
        varsayilan = yt_dlp.parse_options([]).ydl_opts
        verilen = yt_dlp.parse_options(secenekler).ydl_opts
    except (Exception, SystemExit) as hata:  # yt-dlp hatalı seçenekte OptParseError atıyor
        neden = (str(hata).strip().splitlines() or [""])[-1].split("error: ", 1)[-1]
        sys.exit(f"--tarayici / --cerez / --ytdlp değerlerinden biri hatalı: {neden}")

    ayarlar = {
        "logger": gunluk,
        "quiet": True,
        "noprogress": True,
        "extract_flat": "in_playlist",
        "playlist_items": args.sadece,
        "skip_download": True,
        # Altyazı istediğimizi bildiriyoruz ki yt-dlp altyazıyla ilgili uyarıları
        # (ör. PO token) versin; indirmeyi altyazi_indir() kendisi yapıyor.
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": [args.dil],
        "extractor_args": {"youtube": {"skip": ["translated_subs"]}},
        # YouTube'u yormamak (ve hesabı riske atmamak) için istekler arasında bekle
        "sleep_interval_requests": 1,
        "sleep_interval_subtitles": 2,
        "retries": 5,
        "extractor_retries": 3,
        "js_runtimes": js_ortami(),
    }
    ayarlar.update({k: v for k, v in verilen.items() if varsayilan.get(k) != v})
    return ayarlar


def cerez_kontrol(ydl, args):
    if not (args.tarayici or args.cerez):
        print("UYARI: Çerez verilmedi. Üyelere özel videolar için --tarayici ya da --cerez gerekli.\n")
        return
    try:
        adlar = {c.name for c in ydl.cookiejar if c.domain.endswith("youtube.com")}
    except Exception as hata:
        sys.exit(f"HATA: {temizle(hata)}\n\n{DOSYA_IPUCU if args.cerez else TARAYICI_IPUCU}")
    if "LOGIN_INFO" in adlar and adlar & {"SAPISID", "__Secure-1PAPISID", "__Secure-3PAPISID"}:
        print("YouTube oturum çerezleri bulundu.\n")
    else:
        print("UYARI: Çerezlerde YouTube oturumu yok. O tarayıcıda (ve profilde) kanala üye olan "
              "hesapla youtube.com'a giriş yapmış olmalısın.\n")


# ---------------------------------------------------------------------------
# Liste ve altyazı
# ---------------------------------------------------------------------------

def listeyi_al(ydl, url):
    """(liste adı, [video, ...]) döndürür. Tek video linki de verilebilir."""
    sonuc = ydl.extract_info(url, download=False, process=False)
    if sonuc.get("_type") in ("url", "url_transparent"):
        sonuc = ydl.extract_info(sonuc["url"], download=False, process=False)
    if sonuc.get("_type") != "playlist":
        return sonuc.get("title") or "Video", [
            {"sira": 1, "id": sonuc["id"], "baslik": sonuc.get("title") or sonuc["id"], "url": url}]

    sonuc = ydl.process_ie_result(sonuc, download=False)
    girdiler = sonuc.get("entries") or []
    # --sadece verildiyse videoların listedeki asıl sırası requested_entries'te durur
    siralar = sonuc.get("requested_entries") or range(1, len(girdiler) + 1)
    videolar = []
    for sira, e in zip(siralar, girdiler):
        if e and e.get("id"):
            videolar.append({
                "sira": sira,
                "id": e["id"],
                "baslik": e.get("title") or e["id"],
                "url": e.get("url") or f"https://www.youtube.com/watch?v={e['id']}",
            })
    return sonuc.get("title") or "Oynatma listesi", videolar


def altyazi_sec(info, dil):
    """En uygun altyazıyı seçer: (kaynak, dil_kodu, json3_biçimi) ya da None.

    Sıra: istenen dilde kanalın altyazısı > istenen dilde otomatik altyazı >
    başka dilde kanalın altyazısı > videonun kendi dilinde otomatik altyazı >
    istenen dile makine çevirisi.
    """
    manuel = {k: v for k, v in (info.get("subtitles") or {}).items() if k != "live_chat"}
    oto = info.get("automatic_captions") or {}

    def ceviri_mi(kod):  # otomatik altyazılarda "tlang" parametresi = makine çevirisi
        return any("tlang=" in (b.get("url") or "") for b in oto[kod])

    adaylar = [("manuel", k) for k in manuel if k == dil or k.startswith(dil + "-")]
    adaylar += [("otomatik", k) for k in (f"{dil}-orig", dil) if k in oto and not ceviri_mi(k)]
    adaylar += [("manuel", k) for k in manuel]
    adaylar += [("otomatik", k) for k in oto if k.endswith("-orig")]
    if dil in oto:
        adaylar.append(("otomatik-ceviri", dil))

    for kaynak, kod in adaylar:
        bicimler = manuel[kod] if kaynak == "manuel" else oto[kod]
        json3 = next((b for b in bicimler if b.get("ext") == "json3"), None)
        if json3:
            return kaynak, kod, json3
    return None


def json3_parcalar(veri):
    """YouTube'un json3 altyazısını [(başlangıç_ms, metin), ...] listesine çevirir."""
    parcalar = []
    for olay in veri.get("events") or []:
        metin = " ".join("".join(s.get("utf8", "") for s in olay.get("segs") or []).split())
        if metin:
            parcalar.append((int(olay.get("tStartMs", 0)), metin))
    return parcalar


def altyazi_indir(ydl, bicim, hedef):
    """Seçilen altyazıyı yt-dlp'nin indiricisiyle (çerezler, bekleme, tekrar
    deneme dahil) indirir ve doğrulayıp hedef'e yazar."""
    gecici = hedef.with_name(hedef.name + ".tmp")
    artiklar = (gecici, gecici.with_name(gecici.name + ".part"))
    for yol in artiklar:
        yol.unlink(missing_ok=True)
    try:
        ydl.dl(str(gecici), dict(bicim), subtitle=True)
        veri = json.loads(gecici.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        veri = None
    except Exception as hata:
        if "did not get any data blocks" not in str(hata).lower():  # boş cevap
            raise
        veri = None
    finally:
        for yol in artiklar:
            yol.unlink(missing_ok=True)
    if not veri or not json3_parcalar(veri):
        raise TranskriptHatasi("YouTube altyazıyı boş döndürdü (genelde hız sınırı ya da PO token kaynaklı). "
                               "Bir süre sonra tekrar dene.")
    hedef.write_text(json.dumps(veri, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# Whisper (altyazısı olmayan videolar için, isteğe bağlı)
# ---------------------------------------------------------------------------

@functools.lru_cache(maxsize=None)
def whisper_modeli(ad, gpu):
    fw = _ensure("faster-whisper", "faster_whisper")
    print(f"   Whisper modeli yükleniyor: {ad} (ilk seferde indirilir, birkaç dakika sürebilir)")
    if gpu:
        return fw.WhisperModel(ad, device="cuda", compute_type="float16")
    return fw.WhisperModel(ad, device="cpu", compute_type="int8")


def whisper_ile_yaz(ses_ydl, url, args, hedef):
    """Videonun sesini indirir, Whisper ile yazıya döker, sonucu hedef'e yazar."""
    model = whisper_modeli(args.whisper_model, args.whisper_gpu)
    bilgi = ses_ydl.extract_info(url, download=True)
    ses = Path(bilgi["requested_downloads"][0]["filepath"])
    try:
        segmentler, ozet = model.transcribe(str(ses), language=args.dil, vad_filter=True)
        parcalar = []
        for s in segmentler:
            parcalar.append([int(s.start * 1000), s.text.strip()])
            print(f"\r   Whisper: {zaman(s.end * 1000)} / {zaman(ozet.duration * 1000)}", end="", flush=True)
        print()
    finally:
        ses.unlink(missing_ok=True)
    if not parcalar:
        raise TranskriptHatasi("Whisper seste konuşma bulamadı.")
    hedef.write_text(json.dumps({"model": args.whisper_model, "parcalar": parcalar}, ensure_ascii=False),
                     encoding="utf-8")


# ---------------------------------------------------------------------------
# Metin çıktısı
# ---------------------------------------------------------------------------

CUMLE_SONU = (".", "?", "!", "…")


def zaman(ms):
    sn = int(ms) // 1000
    sa, dk, sn = sn // 3600, sn % 3600 // 60, sn % 60
    return f"{sa}:{dk:02d}:{sn:02d}" if sa else f"{dk:02d}:{sn:02d}"


def paragraflar(parcalar):
    """Parçaları ~30 sn'lik paragraflara böler. Metin noktalamalıysa cümle
    sonunu bekler (en fazla 90 sn); YouTube'un Türkçe otomatik altyazısında
    noktalama olmadığı için orada doğrudan 30 sn'de böler."""
    noktalamali = sum(m.endswith(CUMLE_SONU) for _, m in parcalar) > len(parcalar) // 10
    sonuc = []
    for bas, metin in parcalar:
        if sonuc:
            p_bas, p_metin = sonuc[-1]
            sure = bas - p_bas
            bol = sure >= 90_000 or (sure >= 30_000 and (not noktalamali or p_metin.endswith(CUMLE_SONU)))
            if not bol:
                sonuc[-1] = (p_bas, f"{p_metin} {metin}")
                continue
        sonuc.append((bas, metin))
    return sonuc


def metin_olustur(meta, parcalar, zamanli=True):
    bilgi = [meta.get("kanal"), meta.get("sure") and f"Süre {zaman(meta['sure'] * 1000)}"]
    satirlar = [
        meta["baslik"],
        meta["url"],
        " | ".join(x for x in bilgi if x),
        f"Kaynak: {KAYNAK_ADLARI[meta['kaynak']]} [{meta['dil']}]",
        "",
    ]
    for bas, metin in paragraflar(parcalar):
        satirlar += [f"[{zaman(bas)}] {metin}" if zamanli else metin, ""]
    return "\n".join(satirlar)


def dosya_adi(ad):
    ad = " ".join(re.sub(r'[<>:"/\\|?*\x00-\x1f]', " ", ad).split()).strip(" .")
    return ad[:100].rstrip(" .") or "video"


def ham_oku(yol):
    veri = json.loads(yol.read_text(encoding="utf-8"))
    if "parcalar" in veri:  # Whisper çıktısı
        return [tuple(p) for p in veri["parcalar"]]
    return json3_parcalar(veri)


def json_oku(yol):
    with contextlib.suppress(OSError, ValueError):
        return json.loads(yol.read_text(encoding="utf-8"))
    return None


# ---------------------------------------------------------------------------
# Akış
# ---------------------------------------------------------------------------

def transkript_indir(ydl, ses_ydl, video, args, ham, gunluk):
    """Videonun ham transkriptini _ham klasörüne indirir, bilgilerini döndürür."""
    gunluk.uyarilar.clear()
    info = ydl.extract_info(video["url"], download=False, process=False)
    meta = {
        "id": info["id"],
        "baslik": info.get("title") or video["baslik"],
        "url": f"https://www.youtube.com/watch?v={info['id']}",
        "kanal": info.get("channel") or info.get("uploader"),
        "sure": info.get("duration"),
    }
    secim = altyazi_sec(info, args.dil) if args.whisper != "hepsi" else None
    if secim:
        kaynak, dil, bicim = secim
        dosya = f"{info['id']}.{dil}.json3"
        altyazi_indir(ydl, bicim, ham / dosya)
    elif args.whisper != "yok":
        kaynak, dil, dosya = "whisper", args.dil, f"{info['id']}.whisper.json"
        whisper_ile_yaz(ses_ydl, meta["url"], args, ham / dosya)
    elif any(hata_turu(u) == "pot" and "subtitle" in u.lower() for u in gunluk.uyarilar):
        raise TranskriptHatasi(IPUCLARI["pot"][1])
    else:
        raise TranskriptHatasi("Bu videonun altyazısı yok. --whisper yedek ile çalıştırırsan sesten yazıya dökülür.")
    meta.update(kaynak=kaynak, dil=dil, ham=dosya)
    return meta


def hiz_sinirinda_bir_daha(is_):
    try:
        return is_()
    except Exception as hata:
        if hata_turu(hata) != "hiz":
            raise
    print("   YouTube hız sınırı; 90 sn bekleyip bir kez daha deniyorum...")
    time.sleep(90)
    return is_()


def video_isle(ydl, ses_ydl, video, args, cikti, ham, gunluk):
    """Tek videoyu işler: gerekiyorsa indirir, .txt dosyasını yazar.
    (meta, metin, indirildi_mi) döndürür."""
    meta_yolu = ham / f"{video['id']}.json"
    eski = json_oku(meta_yolu) or {}
    indirildi = args.yeniden or not (ham / eski.get("ham", "")).is_file()
    if indirildi:
        meta = hiz_sinirinda_bir_daha(lambda: transkript_indir(ydl, ses_ydl, video, args, ham, gunluk))
    else:
        meta = eski

    metin = metin_olustur(meta, ham_oku(ham / meta["ham"]), zamanli=not args.zamansiz)
    txt = f"{video['sira']:03d} - {dosya_adi(meta['baslik'])}.txt"
    if eski.get("txt") and eski["txt"] != txt:  # sıra ya da başlık değiştiyse eskisini sil
        (cikti / eski["txt"]).unlink(missing_ok=True)
    (cikti / txt).write_text(metin, encoding="utf-8")
    meta["txt"] = txt
    meta_yolu.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    return meta, metin, indirildi


def ciktilari_yaz(cikti, liste_adi, rapor, metinler):
    if metinler:
        ayrac = "\n\n" + "=" * 80 + "\n\n"
        (cikti / "_TUM_TRANSKRIPTLER.txt").write_text(
            liste_adi + ayrac + ayrac.join(metinler) + "\n", encoding="utf-8")
    # Türkçe Excel'de sütunların ayrılması için ";" ve BOM'lu UTF-8
    with open(cikti / "_durum.csv", "w", encoding="utf-8-sig", newline="") as f:
        yazici = csv.writer(f, delimiter=";")
        yazici.writerow(["sira", "video_id", "baslik", "durum", "kaynak", "dosya_veya_hata"])
        yazici.writerows(rapor)


def bekle(saniye):
    if saniye > 0:
        time.sleep(random.uniform(saniye, saniye * 2))


def surum_uyarisi(surum):
    with contextlib.suppress(ValueError, TypeError):
        yas = (date.today() - date(*map(int, surum.split(".")[:3]))).days
        if yas > 60:
            print(f"UYARI: yt-dlp {yas} günlük (sürüm {surum}). Hata alırsan önce güncelle:\n"
                  f'  "{sys.executable}" -m pip install -U "{YTDLP_PAKETI}"\n')


def argumanlar():
    p = argparse.ArgumentParser(
        description="YouTube oynatma listesindeki (üyelere özel dahil) videoların transkriptlerini indirir.",
        epilog="Örnek: python transkript_indir.py --tarayici firefox   (ayrıntılar: README.md)",
    )
    p.add_argument("url", nargs="?", default=VARSAYILAN_LISTE,
                   help="Oynatma listesi ya da video linki (verilmezse kurs listesi)")
    cerez = p.add_mutually_exclusive_group()
    cerez.add_argument("--tarayici", metavar="TARAYICI",
                       help="YouTube'a giriş yaptığın tarayıcı: firefox, chrome, edge, brave, opera, safari, "
                            'vivaldi, chromium. Belirli profil için örn. "chrome:Profile 1"')
    cerez.add_argument("--cerez", metavar="DOSYA", help="Tarayıcıdan dışa aktarılmış cookies.txt dosyası")
    p.add_argument("--dil", default="tr", help="Tercih edilen altyazı dili (varsayılan: tr)")
    p.add_argument("--cikti", default=str(BURASI / "transkriptler"),
                   help="Çıktı klasörü (varsayılan: bu klasördeki transkriptler/)")
    p.add_argument("--sadece", metavar="SIRA", help="Sadece bu sıradaki videolar, örn. 1-3 ya da 1,4,7")
    p.add_argument("--bekleme", type=float, default=5,
                   help="Videolar arası bekleme, saniye (varsayılan: 5; hız sınırına takılırsan artır)")
    p.add_argument("--whisper", choices=["yok", "yedek", "hepsi"], default="yok",
                   help="yedek: altyazısı olmayan videoları sesten yazıya dök; hepsi: her video için Whisper kullan")
    p.add_argument("--whisper-model", default="large-v3-turbo",
                   help="Whisper modeli (varsayılan: large-v3-turbo; daha hızlı ama daha zayıf: small, medium)")
    p.add_argument("--whisper-gpu", action="store_true", help="Whisper'ı NVIDIA ekran kartıyla (CUDA) çalıştır")
    p.add_argument("--zamansiz", action="store_true", help="Paragraflara [dk:sn] zaman damgası ekleme")
    p.add_argument("--yeniden", action="store_true", help="Daha önce indirilenleri de baştan indir")
    p.add_argument("--ytdlp", default="", metavar="SECENEKLER",
                   help='yt-dlp\'ye aynen geçecek ek seçenekler (ileri düzey), örn. '
                        '--ytdlp="--extractor-args youtube:player_client=tv"')
    p.add_argument("--ayrinti", action="store_true", help="yt-dlp'nin tüm mesajlarını göster (hata ayıklama)")
    return p.parse_args()


def main():
    for akis in (sys.stdout, sys.stderr):
        with contextlib.suppress(AttributeError, ValueError):
            akis.reconfigure(errors="replace")
    if sys.version_info < (3, 10):
        sys.exit("Python 3.10 ya da daha yenisi gerekli: https://www.python.org/downloads/")
    args = argumanlar()
    if args.cerez and not Path(args.cerez).expanduser().is_file():
        sys.exit(f"Çerez dosyası bulunamadı: {args.cerez}")

    _ensure(YTDLP_PAKETI, "yt_dlp")
    from yt_dlp import YoutubeDL
    from yt_dlp.version import __version__ as ytdlp_surumu

    surum_uyarisi(ytdlp_surumu)
    cikti = Path(args.cikti).expanduser().resolve()
    ham = cikti / "_ham"
    ham.mkdir(parents=True, exist_ok=True)
    gunluk = Gunluk(args.ayrinti)
    ayarlar = ytdlp_ayarlari(args, gunluk)
    ses_ayarlari = {
        **ayarlar,
        "format": "bestaudio/best",
        "skip_download": False,
        "writesubtitles": False,
        "writeautomaticsub": False,
        "noplaylist": True,
        "outtmpl": {"default": str(ham / "_ses" / "%(id)s.%(ext)s")},
    }
    print(f"yt-dlp {ytdlp_surumu} | çıktı: {cikti}")

    rapor, metinler = [], []
    liste_adi = "Oynatma listesi"
    ydl = YoutubeDL(ayarlar)
    # with'e girmeden önce: çerezler okunamazsa yt-dlp kapanırken aynı hatayı
    # tekrar atıp açıklamamızı gölgelemesin
    cerez_kontrol(ydl, args)
    with contextlib.ExitStack() as yigin:
        yigin.enter_context(ydl)
        ses_ydl = yigin.enter_context(YoutubeDL(ses_ayarlari)) if args.whisper != "yok" else None
        try:
            liste_adi, videolar = listeyi_al(ydl, args.url)
        except Exception as hata:
            sys.exit(f"Liste okunamadı: {hata_aciklamasi(hata)}")
        print(f"{liste_adi}: {len(videolar)} video\n")

        uyelik_hatasi = 0
        try:
            for n, video in enumerate(videolar, 1):
                print(f"[{n}/{len(videolar)}] {video['sira']:03d} - {video['baslik']}")
                try:
                    meta, metin, indirildi = video_isle(ydl, ses_ydl, video, args, cikti, ham, gunluk)
                except Exception as hata:
                    aciklama = hata_aciklamasi(hata)
                    print(f"   HATA: {aciklama}")
                    rapor.append([video["sira"], video["id"], video["baslik"], "hata", "", aciklama])
                    if hata_turu(hata) == "hiz":
                        print("\nYouTube bu oturumu geçici olarak sınırladı. ~1 saat sonra aynı komutu "
                              "tekrar çalıştır; kaldığı yerden devam eder.")
                        break
                    if hata_turu(hata) == "uyelik" and not metinler:
                        uyelik_hatasi += 1
                        if uyelik_hatasi >= 3:
                            print("\nÜyelere özel videolar açılamıyor, sorun çerezlerde. "
                                  "README > Sorun giderme bölümüne bak.")
                            break
                    if n < len(videolar):
                        bekle(args.bekleme)
                    continue
                kaynak = f"{KAYNAK_ADLARI[meta['kaynak']]} [{meta['dil']}]"
                print(f"   {'Tamam' if indirildi else 'Daha önce inmiş'}: {kaynak}")
                rapor.append([video["sira"], video["id"], meta["baslik"], "tamam", kaynak, meta["txt"]])
                metinler.append(metin)
                if indirildi and n < len(videolar):
                    bekle(args.bekleme)
        except KeyboardInterrupt:
            print("\nDurduruldu. Aynı komutu tekrar çalıştırınca kaldığı yerden devam eder.")

    ciktilari_yaz(cikti, liste_adi, rapor, metinler)
    hatali = sum(r[3] == "hata" for r in rapor)
    print(f"\nBitti: {len(metinler)} video tamam, {hatali} hata. Çıktı klasörü: {cikti}")
    if metinler:
        print("Hepsi tek dosyada: _TUM_TRANSKRIPTLER.txt")
    if hatali:
        print("Hataların listesi _durum.csv içinde. Aynı komutu tekrar çalıştırınca sadece eksikler denenir.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("\nDurduruldu.")
