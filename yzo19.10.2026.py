import os
from google import genai
from google.genai import errors, types

import sys
sys.stdout.reconfigure(encoding="utf-8")


def kod_optimize_et(spagetti_kod: str) -> None:
    os.system("cls" if os.name == "nt" else "clear")

    print("=" * 75)
    print(" YAPAY ZEKA DESTEKLİ KOD İYİLEŞTİRME VE OPTİMİZASYON ".center(75))
    print("=" * 75)

    # API anahtarını ortam değişkeninden al
    api_anahtari = "Api"

    if not api_anahtari:
        print("\n[HATA] GEMINI_API_KEY tanımlanmamış!")
        return

    sistem_mesaji = """
    Sen kıdemli bir Yazılım Mimarı ve Performans Uzmanısın.

    Kullanıcının gönderdiği kötü yazılmış (spagetti)
    Python kodunu analiz et.

    1. Değişken isimlerini anlamlı hale getir (Clean Code).
    2. Algoritmanın çalışma hızını iyileştir.
       Örneğin O(n^2) yerine mümkünse O(n) kullan.
    3. Type Hint (Tip belirteçleri) ekle.
    4. Kodun mevcut işlevselliğini koru.
    5. Gereksiz döngüleri ortadan kaldır.

    Çıktın KESİNLİKLE sadece düzeltilmiş Python kodu olmalıdır.
    Ek açıklama veya Markdown yazma.
    """

    print("\n[AŞAMA 1] OPTİMİZE EDİLECEK SPAGETTİ KOD SİSTEME ALINDI...")
    print("\n[AŞAMA 2] REFACTORING İÇİN YAPAY ZEKAYA BAĞLANILIYOR...\n")

    try:
        # Gemini istemcisini oluştur
        client = genai.Client(api_key=api_anahtari)

        # Gemini API isteğini gönder
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=spagetti_kod,
            config=types.GenerateContentConfig(
                system_instruction=sistem_mesaji,
                temperature=0.2,
            ),
        )

        print("-" * 75)
        print("OPTİMİZE EDİLEN KOD (ÇIKIŞ):")
        print("-" * 75)
        print(response.text)

    except errors.APIError as e:
        print(f"\n[HATA] API İletişim Hatası: {e}")
    except Exception as e:
        print(f"\n[HATA] Beklenmeyen Durum: {e}")


kotu_kod = """
def bul(l):
    r = []
    for i in range(len(l)):
        for j in range(i+1, len(l)):
            if l[i] == l[j] and l[i] not in r:
                r.append(l[i])
    return r
"""

if __name__ == "__main__":
    kod_optimize_et(kotu_kod)


"Eren ÇELİK"
