import random
import time
import csv
from collections import Counter
from typing import List, Dict, Any


# 1. ADIM: 5000 SATIRLIK HASTANE VERİSİ ÜRETİMİ

def hastane_verisi_uret(satir_sayisi: int = 5000, dosya_adi: str = "hastane_verisi_5000.csv") -> List[int]:
    """
    5000 satırlık gerçekçi hastane muayene kaydı üretir, CSV'ye kaydeder
    ve performans testinde kullanılmak üzere Hasta_ID listesini döndürür.
    """
    random.seed(42)  # Her çalıştırmada aynı test verisi (PDF kuralı)
    
    poliklinikler = [
        "Acil Servis", "Kardiyoloji", "Dahiliye", "Ortopedi", 
        "Nöroloji", "Göz Hastalıkları", "Kulak Burun Boğaz", "Göğüs Hastalıkları"
    ]
    kan_gruplari = ["A Rh+", "A Rh-", "B Rh+", "B Rh-", "AB Rh+", "AB Rh-", "0 Rh+", "0 Rh-"]
    triyaj_kodlari = ["Yeşil Alan", "Sarı Alan", "Kırmızı Alan"]
    
    kayitlar: List[Dict[str, Any]] = []
    hasta_id_listesi: List[int] = []
    
    # 1000 farklı hasta havuzu (10001 - 11000 arası Hasta ID)
    # 5000 muayene kaydı içinde tekrar eden hastaları bulacağız.
    for kayit_no in range(1, satir_sayisi + 1):
        hasta_id = random.randint(10001, 11000)
        hasta_id_listesi.append(hasta_id)
        
        kayitlar.append({
            "Kayit_No": kayit_no,
            "Hasta_ID": hasta_id,
            "Yas": random.randint(1, 90),
            "Kan_Grubu": random.choice(kan_gruplari),
            "Poliklinik": random.choice(poliklinikler),
            "Triyaj_Durumu": random.choice(triyaj_kodlari),
            "Yatis_Suresi_Gun": random.randint(0, 15)
        })
        
    # Veriyi görmek veya göstermek istersen diye CSV olarak da kaydediyoruz
    with open(dosya_adi, mode="w", newline="", encoding="utf-8") as f:
        yazici = csv.DictWriter(f, fieldnames=kayitlar[0].keys())
        yazici.writeheader()
        yazici.writerows(kayitlar)
        
    return hasta_id_listesi


# 2. ADIM: ESKİ FONKSİYON VE OPTİMİZE EDİLMİŞ FONKSİYON

def bul(l):
    """PDF'te verilen başlangıçtaki yavaş fonksiyon - O(n^2) karmaşıklık."""
    r = []
    for i in range(len(l)):
        for j in range(i + 1, len(l)):
            if l[i] == l[j] and l[i] not in r:
                r.append(l[i])
    return r


def bul_optimize(veri_listesi: List[Any]) -> List[Any]:
    """
    TODO 1: Gemini yardımıyla optimize edilmiş fonksiyon - O(n) karmaşıklık.
    Listedeki tekrar eden elemanları, ilk görülme sırasını koruyarak döndürür.
    """
    frekanslar = Counter(veri_listesi)
    gorulenler = set()
    tekrar_edenler: List[Any] = []
    
    for eleman in veri_listesi:
        if frekanslar[eleman] > 1 and eleman not in gorulenler:
            tekrar_edenler.append(eleman)
            gorulenler.add(eleman)
            
    return tekrar_edenler


# 3. ADIM: DOĞRULUK TESTLERİ (PDF Sayfa 3'teki Tablo)

def dogruluk_testlerini_calistir() -> bool:
    test_senaryolari = [
        ("Boş liste", []),
        ("Tek eleman", [7]),
        ("Tekrar yok", [1, 2, 3]),
        ("Tekrar var", [3, 1, 3, 2, 1]),
        ("Tekrar sırası önemli", [4, 2, 2, 4, 3, 3])
    ]
    
    try:
        for test_adi, girdi in test_senaryolari:
            eski_sonuc = bul(girdi)
            yeni_sonuc = bul_optimize(girdi)
            assert eski_sonuc == yeni_sonuc, f"HATA ({test_adi}): {eski_sonuc} != {yeni_sonuc}"
        return True
    except AssertionError as e:
        print(e)
        return False


# 4. ADIM: PERFORMANS ÖLÇÜMÜ VE RAPORLAMA

def main():
    print("1) 5.000 satırlık hastane verisi üretiliyor...")
    veriler = hastane_verisi_uret(5000, "hastane_verisi_5000.csv")
    print("   -> 'hastane_verisi_5000.csv' başarıyla oluşturuldu.")
    
    # Deney Planı: En az 3 kez ölçüm yapıp ortalamasını alıyoruz
    tekrar_sayisi = 3
    eski_sureler = []
    yeni_sureler = []
    
    print(f"2) Performans testi ({tekrar_sayisi} tekrarlı) çalıştırılıyor...")
    for _ in range(tekrar_sayisi):
        # Eski fonksiyon ölçümü
        baslangic = time.perf_counter()
        sonuc_eski = bul(veriler)
        eski_sureler.append(time.perf_counter() - baslangic)
        
        # TODO 2: bul_optimize fonksiyonunun süresini ölç
        baslangic_opt = time.perf_counter()
        sonuc_yeni = bul_optimize(veriler)
        yeni_sureler.append(time.perf_counter() - baslangic_opt)

    eski_sure_ort = sum(eski_sureler) / tekrar_sayisi
    yeni_sure_ort = sum(yeni_sureler) / tekrar_sayisi

    # TODO 3: Sonuçlar aynı mı kontrol et (assert)
    birim_testler_gecti = dogruluk_testlerini_calistir()
    ana_veri_esit = (sonuc_eski == sonuc_yeni)
    assert ana_veri_esit, "5000 satırlık hastane verisinde sonuçlar uyuşmadı!"
    
    dogruluk_durumu = "BASARILI" if (birim_testler_gecti and ana_veri_esit) else "BASARISIZ"

    # TODO 4: Hızlanma katsayısını hesapla (Sıfıra bölme korumalı)
    if yeni_sure_ort > 0:
        hizlanma_katsayisi = eski_sure_ort / yeni_sure_ort
    else:
        hizlanma_katsayisi = float('inf')

    # TODO 5: Raporu .txt dosyasına yaz
    rapor_icerigi = f"""KOD PERFORMANS RAPORU
Veri sayisi: {len(veriler)} (Hastane Muayene Kaydi - Mükerrer Hasta ID Analizi)
Eski kod suresi: {eski_sure_ort:.6f} saniye
Optimize kod suresi: {yeni_sure_ort:.6f} saniye
Hizlanma: {hizlanma_katsayisi:.2f} kat
Dogruluk testi: {dogruluk_durumu}
Kisa yorum: Eski fonksiyon (bul), 5000 satırlık hastane verisinde birden fazla kez muayene olan hastaları (Hasta_ID) bulmak için iç içe iki döngü ve doğrusal liste araması (not in) kullandığından O(n^2) zaman karmaşıklığıyla çok yavaş çalışmıştır. Gemini ile optimize edilen yeni fonksiyonda (bul_optimize) Counter (hash tablosu) ve küme (set) veri yapıları kullanılarak zaman karmaşıklığı O(n) seviyesine indirilmiştir. İlk görülme sırası korunarak {len(sonuc_yeni)} adet mükerrer hasta kaydı birebir aynı sırada tespit edilmiş ve yaklaşık {hizlanma_katsayisi:.0f} kat hızlanma sağlanmıştır.
"""

    with open("performans_raporu.txt", mode="w", encoding="utf-8") as f:
        f.write(rapor_icerigi)

    print("\n" + "=" * 50)
    print(rapor_icerigi.strip())
    print("=" * 50)
    print("\n3) 'performans_raporu.txt' dosyası başarıyla kaydedildi.")

if __name__ == "__main__":
    main()