import json
import os
import re

from google import genai
from google.genai import errors

DOSYA_ADI = "urunler.json"
RAPOR_DOSYASI = "analiz_sonucu.txt"
MODEL_ADI = "gemini-2.5-flash-lite"  # geçen hafta çalışan model adı
GEREKLI_ALANLAR = ("urun_adi", "kategori", "seo_etiketleri", "satis_aciklamasi")


# ----------------------------------------------------------------------
# 1) GEMINI API
# ----------------------------------------------------------------------
def e_ticaret_api_simulasyonu(urun_talebi):
    """Gemini'ye istek atar, yanıtı JSON olarak ayrıştırıp dict döndürür.
    Hata durumunda exception fırlatır; çağıran fonksiyon yakalar."""

    # API anahtarını koda yazmak yerine ortam değişkeninden okuyoruz.
    api_anahtari = os.environ.get("")
    if not api_anahtari:
        raise RuntimeError("GEMINI_API_KEY ortam değişkeni tanımlı değil.")

    client = genai.Client(api_key=api_anahtari)

    sistem_mesaji = """
    Sen kurumsal bir e-ticaret sisteminin arka planında çalışan
    bir veri yapılandırma asistanısın.

    Kullanıcının girdiği ham ürün bilgilerini analiz edip,
    veritabanına kaydedilebilmesi için SADECE JSON formatında
    yanıt vermelisin.

    JSON nesnesi kesinlikle şu anahtarları içermelidir:

    {
        "urun_adi": "Kısa ve optimize edilmiş ürün adı",
        "kategori": "Uygun e-ticaret kategorisi",
        "seo_etiketleri": "3 adet virgülle ayrılmış SEO etiketi",
        "satis_aciklamasi": "Müşteriyi ikna edecek profesyonel 2 cümle"
    }

    JSON dışında hiçbir açıklama yazma.
    """

    interaction = client.interactions.create(
        model=MODEL_ADI,
        input=f"{sistem_mesaji}\n\nKullanıcının ürün talebi:\n{urun_talebi}",
    )
    ham_yanit = interaction.output_text

    return yaniti_ayristir(ham_yanit), ham_yanit


def yaniti_ayristir(ham_yanit):
    """Ham metni dict'e çevirir ve zorunlu alanları doğrular."""
    if not ham_yanit or not ham_yanit.strip():
        raise ValueError("API boş yanıt döndürdü.")

    metin = ham_yanit.strip()
    # ```json ... ``` bloğu geldiyse temizle
    metin = re.sub(r"^```(?:json)?\s*|\s*```$", "", metin, flags=re.IGNORECASE)

    # Yine de başında/sonunda fazlalık varsa ilk { ile son } arasını al
    bas, son = metin.find("{"), metin.rfind("}")
    if bas == -1 or son == -1:
        raise ValueError("Yanıtta JSON nesnesi bulunamadı.")

    try:
        veri = json.loads(metin[bas : son + 1])
    except json.JSONDecodeError as e:
        raise ValueError(f"Yanıt geçerli JSON değil: {e}")

    if not isinstance(veri, dict):
        raise ValueError("JSON bir nesne (dict) değil.")

    for alan in GEREKLI_ALANLAR:
        deger = veri.get(alan)
        if not isinstance(deger, str) or not deger.strip():
            raise ValueError(f"Zorunlu alan eksik veya boş: '{alan}'")
        veri[alan] = deger.strip()

    return veri


def analiz_raporu_yaz(urun_talebi, ham_yanit):
    """Geçen haftaki gibi ham sonucu analiz_sonucu.txt dosyasına yazar."""
    try:
        with open(RAPOR_DOSYASI, "w", encoding="utf-8") as dosya:
            dosya.write("=" * 70 + "\n")
            dosya.write("B2C E-TİCARET SİSTEMİ - GEMINI ANALİZ RAPORU\n")
            dosya.write("=" * 70 + "\n\n")
            dosya.write("[KULLANICI TALEBİ]\n" + urun_talebi.strip() + "\n\n")
            dosya.write("[GEMINI JSON ÇIKTISI]\n" + ham_yanit)
    except OSError as e:
        print(f"[UYARI] Rapor dosyası yazılamadı: {e}")


# ----------------------------------------------------------------------
# 2) DOSYA İŞLEMLERİ
# ----------------------------------------------------------------------
def urunleri_yukle():
    """urunler.json dosyasını okur. Yoksa/bozuksa boş liste döndürür."""
    if not os.path.exists(DOSYA_ADI):
        return []

    try:
        with open(DOSYA_ADI, "r", encoding="utf-8") as dosya:
            icerik = dosya.read().strip()
            if not icerik:
                return []
            veri = json.loads(icerik)
        if not isinstance(veri, list):
            raise ValueError("Dosya bir liste içermiyor.")
        return veri
    except (json.JSONDecodeError, ValueError) as e:
        yedek = DOSYA_ADI + ".bozuk"
        print(f"[UYARI] {DOSYA_ADI} okunamadı ({e}).")
        try:
            os.replace(DOSYA_ADI, yedek)
            print(f"[BİLGİ] Bozuk dosya '{yedek}' olarak yedeklendi, boş liste ile devam ediliyor.")
        except OSError:
            pass
        return []
    except OSError as e:
        print(f"[HATA] Dosya okunamadı: {e}")
        return []


def urunleri_kaydet(urunler):
    """Ürün listesini JSON dosyasına yazar. Başarılıysa True döner."""
    try:
        with open(DOSYA_ADI, "w", encoding="utf-8") as dosya:
            json.dump(urunler, dosya, ensure_ascii=False, indent=2)
        return True
    except OSError as e:
        print(f"[HATA] Dosyaya yazılamadı: {e}")
        return False


# ----------------------------------------------------------------------
# 3) YARDIMCI FONKSİYONLAR
# ----------------------------------------------------------------------
def yeni_urun_kodu(urunler):
    """URN-0001, URN-0002 ... biçiminde benzersiz kod üretir."""
    en_buyuk = 0
    for urun in urunler:
        eslesme = re.fullmatch(r"URN-(\d+)", str(urun.get("urun_kodu", "")))
        if eslesme:
            en_buyuk = max(en_buyuk, int(eslesme.group(1)))
    return f"URN-{en_buyuk + 1:04d}"


def sayi_al(mesaj, tur=int):
    """Negatif olmayan sayı alır; geçersiz girişte tekrar sorar."""
    while True:
        giris = input(mesaj).strip().replace(",", ".")
        try:
            deger = tur(giris)
        except ValueError:
            print("[HATA] Lütfen geçerli bir sayı girin.")
            continue
        if deger < 0:
            print("[HATA] Negatif değer girilemez.")
            continue
        return deger


def fiyat_al(mesaj):
    """Fiyat alır (0'dan büyük olmalı). 2499 -> int, 99.9 -> float."""
    while True:
        fiyat = sayi_al(mesaj, float)
        if fiyat == 0:
            print("[HATA] Fiyat 0 olamaz.")
            continue
        return int(fiyat) if fiyat.is_integer() else fiyat


def turkce_kucult(metin):
    """İ/I sorununu çözerek küçük harfe çevirir (büyük/küçük harf duyarsız arama için)."""
    return metin.replace("İ", "i").replace("I", "ı").lower()


def stok_uyarisi_yazdir(stok):
    if stok == 0:
        print("[UYARI] STOKTA YOK!")
    elif 1 <= stok <= 4:
        print(f"[UYARI] KRİTİK STOK! Yalnızca {stok} adet kaldı.")


def urun_ozeti_yazdir(urun):
    print(f"Ürün Kodu : {urun['urun_kodu']}")
    print(f"Ürün Adı  : {urun['urun_adi']}")
    print(f"Kategori  : {urun['kategori']}")
    print(f"Fiyat     : {urun['fiyat']} TL")
    print(f"Stok      : {urun['stok']}")
    print(f"SEO       : {urun['seo_etiketleri']}")


# ----------------------------------------------------------------------
# 4) MENÜ İŞLEMLERİ
# ----------------------------------------------------------------------
def menu_goster():
    print("\n========== E-TİCARET YÖNETİM PANELİ ==========")
    print("1 - Yeni Ürün Ekle")
    print("2 - Ürünleri Listele")
    print("3 - Ürün Ara")
    print("4 - Stok Güncelle")
    print("5 - Çıkış")


def urun_ekle(urunler):
    aciklama = input("Ürün açıklaması: ").strip()
    if not aciklama:
        print("[HATA] Ürün açıklaması boş olamaz.")
        return
    fiyat = fiyat_al("Ürün fiyatı: ")
    stok = sayi_al("Stok miktarı: ", int)

    print("\n[API] Ürün bilgileri oluşturuluyor...")
    try:
        # Fiyatı prompta eklemiyoruz; Gemini'ye zaten kullanıcı verdi.
        talep = f"{aciklama}\n(Fiyat ve stok bilgisi sisteme ayrıca girilecek, bunları yazma.)"
        veri, ham_yanit = e_ticaret_api_simulasyonu(talep)
    except errors.APIError as e:
        print(f"[API HATASI] {e}")
        print("[BİLGİ] Ürün kaydedilmedi.")
        return
    except ValueError as e:
        print(f"[HATA] Gemini yanıtı işlenemedi: {e}")
        print("[BİLGİ] Ürün kaydedilmedi.")
        return
    except Exception as e:
        print(f"[SİSTEM HATASI] Beklenmeyen bir hata oluştu: {e}")
        print("[BİLGİ] Ürün kaydedilmedi.")
        return

    urun = {
        "urun_kodu": yeni_urun_kodu(urunler),
        "urun_adi": veri["urun_adi"],
        "kategori": veri["kategori"],
        "seo_etiketleri": veri["seo_etiketleri"],
        "satis_aciklamasi": veri["satis_aciklamasi"],
        "fiyat": fiyat,
        "stok": stok,
    }
    urunler.append(urun)

    if urunleri_kaydet(urunler):
        analiz_raporu_yaz(aciklama, ham_yanit)
        print("[BAŞARILI] Ürün kaydedildi.")
        urun_ozeti_yazdir(urun)
        stok_uyarisi_yazdir(stok)
    else:
        urunler.pop()  # kaydedilemediyse bellekten de çıkar


def urunleri_listele(urunler):
    if not urunler:
        print("[UYARI] Kayıtlı ürün bulunmuyor.")
        return
    print(f"\n{'Kod':<10}{'Ürün Adı':<32}{'Kategori':<20}{'Fiyat':>10}{'Stok':>6}")
    print("-" * 78)
    for u in urunler:
        durum = ""
        if u["stok"] == 0:
            durum = "  STOKTA YOK"
        elif u["stok"] <= 4:
            durum = "  KRİTİK STOK"
        print(
            f"{u['urun_kodu']:<10}{u['urun_adi'][:30]:<32}{u['kategori'][:18]:<20}"
            f"{str(u['fiyat']) + ' TL':>10}{u['stok']:>6}{durum}"
        )


def urun_ara(urunler):
    aranan = input("Aranacak ürün: ").strip()
    if not aranan:
        print("[HATA] Arama metni boş olamaz.")
        return
    anahtar = turkce_kucult(aranan)
    bulunanlar = [
        u
        for u in urunler
        if anahtar in turkce_kucult(u["urun_adi"])
        or anahtar in turkce_kucult(u["urun_kodu"])
    ]
    if not bulunanlar:
        print("[SONUÇ] Eşleşen ürün bulunamadı.")
        return
    kodlar = ", ".join(u["urun_kodu"] for u in bulunanlar)
    print(f"[SONUÇ] {len(bulunanlar)} ürün bulundu: {kodlar}")
    for u in bulunanlar:
        print()
        urun_ozeti_yazdir(u)


def stok_guncelle(urunler):
    kod = input("Ürün kodu: ").strip().upper()
    urun = next((u for u in urunler if u["urun_kodu"] == kod), None)
    if urun is None:
        print("[HATA] Bu koda sahip ürün bulunamadı.")
        return
    yeni_stok = sayi_al("Yeni stok miktarı: ", int)
    eski_stok = urun["stok"]
    urun["stok"] = yeni_stok
    if urunleri_kaydet(urunler):
        print(f"[BAŞARILI] Stok {eski_stok} -> {yeni_stok} olarak güncellendi.")
        stok_uyarisi_yazdir(yeni_stok)
    else:
        urun["stok"] = eski_stok


# ----------------------------------------------------------------------
# 5) ANA PROGRAM
# ----------------------------------------------------------------------
def main():
    urunler = urunleri_yukle()

    while True:
        menu_goster()
        secim = input("Seçiminiz: ").strip()

        if secim == "1":
            urun_ekle(urunler)
        elif secim == "2":
            urunleri_listele(urunler)
        elif secim == "3":
            urun_ara(urunler)
        elif secim == "4":
            stok_guncelle(urunler)
        elif secim == "5":
            print("Çıkış yapılıyor. Görüşmek üzere!")
            break
        else:
            print("[HATA] Geçersiz seçim. Lütfen 1-5 arasında bir sayı girin.")


if __name__ == "__main__":
    main()