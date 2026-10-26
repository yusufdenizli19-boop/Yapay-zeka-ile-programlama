import json
import os
import re

DOSYA_ADI = "sorgular.json"
RAPOR_DOSYASI = "analiz_sonucu.txt"
MODEL_ADI = "gemini-3.5-flash-lite"
GEREKLI_ALANLAR = ("sql_sorgusu", "aciklama")


# ----------------------------------------------------------------------
# 1) GEMINI API
# ----------------------------------------------------------------------
def sql_uretim_api_simulasyonu(veritabani_Semasi, urun_talebi):
    """Gemini'ye istek atar, yanıtı JSON olarak ayrıştırıp dict döndürür.
    Hata durumunda exception fırlatır; çağıran fonksiyon yakalar."""

    api_anahtari = ""
    if not api_anahtari:
        raise RuntimeError("API anahtarı tanımlı değil.")   

    try:
        from google import genai
    except ModuleNotFoundError as e:
        raise RuntimeError(
            "Google Gen AI SDK çözümlenemedi. Uygulamanın kullandığı Python "
            "ortamına 'python -m pip install google-genai' komutuyla yükleyin."
        ) from e

    client = genai.Client(api_key=api_anahtari)

    sistem_mesaji = f"""
    Sen kurumsal bir veri tabanı asistanısın.
    Aşağıdaki veri tabanı şemesını kullanarak kullanıcının doğal dildeki talebini 
    uygun SQL sorgusuna çevirmelisin. Yanıtı SADECE JSON formatında vermelisin.

    Veritabanı Şeması:
    {veritabani_Semasi}

    JSON nesnesi kesinlikle şu anahtarları içermelidir:

    {{
        "sql_sorgusu": "Üretilen SQL sorgusu",
        "aciklama": "Sorgunun ne yaptığına dair kısa bir açıklama"
    }}

    JSON dışında hiçbir açıklama yazma.
    """

    interaction = client.interactions.create(
        model=MODEL_ADI,
        input=f"{sistem_mesaji}\n\nKullanıcının talebi:\n{urun_talebi}",
    )
    ham_yanit = interaction.output_text

    return yaniti_ayristir(ham_yanit), ham_yanit


def yaniti_ayristir(ham_yanit):
    """Ham metni dict'e çevirir ve zorunlu alanları doğrular."""
    if not ham_yanit or not ham_yanit.strip():
        raise ValueError("API boş yanıt döndürdü.")

    metin = ham_yanit.strip()
    metin = re.sub(r"^```(?:json)?\s*|\s*```$", "", metin, flags=re.IGNORECASE)

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


def analiz_raporu_yaz(talep, ham_yanit):
    """Sonucu analiz_sonucu.txt dosyasına yazar."""
    try:
        with open(RAPOR_DOSYASI, "w", encoding="utf-8") as dosya:
            dosya.write("=" * 70 + "\n")
            dosya.write("YAPAY ZEKA DESTEKLİ DOĞAL DİLDEN SQL ÜRETİCİ - RAPOR\n")
            dosya.write("=" * 70 + "\n\n")
            dosya.write("[KULLANICI TALEBİ]\n" + talep.strip() + "\n\n")
            dosya.write("[GEMINI JSON ÇIKTISI]\n" + ham_yanit)
    except OSError as e:
        print(f"[UYARI] Rapor dosyası yazılamadı: {e}")


# ----------------------------------------------------------------------
# 2) DOSYA İŞLEMLERİ
# ----------------------------------------------------------------------
def sorgulari_yukle():
    """sorgular.json dosyasını okur. Yoksa/bozuksa boş liste döndürür."""
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
            print(f"[BİLGİ] Bozuk dosya '{yedek}' olarak yedeklendi.")
        except OSError:
            pass
        return []
    except OSError as e:
        print(f"[HATA] Dosya okunamadı: {e}")
        return []


def sorgulari_kaydet(sorgular):
    """Sorgu listesini JSON dosyasına yazar."""
    try:
        with open(DOSYA_ADI, "w", encoding="utf-8") as dosya:
            json.dump(sorgular, dosya, ensure_ascii=False, indent=2)
        return True
    except OSError as e:
        print(f"[HATA] Dosyaya yazılamadı: {e}")
        return False


# ----------------------------------------------------------------------
# 3) YARDIMCI FONKSİYONLAR
# ----------------------------------------------------------------------
def yeni_sorgu_kodu(sorgular):
    """SRG-0001, SRG-0002 ... biçiminde benzersiz kod üretir."""
    en_buyuk = 0
    for s in sorgular:
        eslesme = re.fullmatch(r"SRG-(\d+)", str(s.get("sorgu_kodu", "")))
        if eslesme:
            en_buyuk = max(en_buyuk, int(eslesme.group(1)))
    return f"SRG-{en_buyuk + 1:04d}"


def sorgu_ozeti_yazdir(sorgu):
    print(f"Sorgu Kodu : {sorgu['sorgu_kodu']}")
    print(f"Talep      : {sorgu['talep']}")
    print(f"SQL Sorgusu:\n{sorgu['sql_sorgusu']}")
    print(f"Açıklama   : {sorgu['aciklama']}")


# ----------------------------------------------------------------------
# 4) MENÜ İŞLEMLERİ
# ----------------------------------------------------------------------
def menu_goster():
    print("\n========== DOĞAL DİLDEN SQL ÜRETİCİ PANELİ ==========")
    print("1 - Doğal Dilden SQL Üret")
    print("2 - Kayıtlı Sorguları Listele")
    print("3 - Çıkış")


def sql_uret_islem(sorgular):
    sema = (
        "1. Musteriler Tablosu: musteri_id, ad_soyad, eposta, sehir\n"
        "2. Siparisler Tablosu: siparis_id, musteri_id, tutar, siparis_tarihi"
    )
    print("\n[ŞEMA BİLGİSİ]")
    print(sema)

    talep = input("\nDoğal dilde talebinizi girin: ").strip()
    if not talep:
        print("[HATA] Talep boş olamaz.")
        return

    print("\n[AŞAMA 2] SQL Çevirisi için Gemini'ye bağlanılıyor...")
    try:
        veri, ham_yanit = sql_uretim_api_simulasyonu(sema, talep)
    except ValueError as e:
        print(f"[HATA] Gemini yanıtı işlenemedi: {e}")
        return
    except Exception as e:
        print(f"[SİSTEM HATASI] Beklenmeyen hata: {e}")
        return

    sorgu_kaydi = {
        "sorgu_kodu": yeni_sorgu_kodu(sorgular),
        "talep": talep,
        "sql_sorgusu": veri["sql_sorgusu"],
        "aciklama": veri["aciklama"],
    }
    sorgular.append(sorgu_kaydi)

    if sorgulari_kaydet(sorgular):
        analiz_raporu_yaz(talep, ham_yanit)
        print("\n[BAŞARILI] ÜRETİLEN SQL SORGUSU:")
        print("-" * 50)
        print(veri["sql_sorgusu"])
        print("-" * 50)
        print(f"Açıklama: {veri['aciklama']}")
    else:
        sorgular.pop()


def sorgulari_listele(sorgular):
    if not sorgular:
        print("[UYARI] Kayıtlı sorgu bulunmuyor.")
        return
    print(f"\n{'Kod':<10}{'Talep':<40}")
    print("-" * 50)
    for s in sorgular:
        print(f"{s['sorgu_kodu']:<10}{s['talep'][:38]:<40}")


# ----------------------------------------------------------------------
# 5) ANA PROGRAM
# ----------------------------------------------------------------------
def main():
    sorgular = sorgulari_yukle()

    while True:
        menu_goster()
        secim = input("Seçiminiz: ").strip()

        if secim == "1":
            sql_uret_islem(sorgular)
        elif secim == "2":
            sorgulari_listele(sorgular)
        elif secim == "3":
            print("Çıkış yapılıyor. Görüşmek üzere!")
            break
        else:
            print("[HATA] Geçersiz seçim. Lütfen 1-3 arasında bir sayı girin.")


if __name__ == "__main__":
    main()