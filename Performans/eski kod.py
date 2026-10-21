import random
import time

# Hocanın PDF'te verdiği yavaş çalışan başlangıç fonksiyonu
def bul(l):
    r = []
    for i in range(len(l)):
        for j in range(i + 1, len(l)):
            if l[i] == l[j] and l[i] not in r:
                r.append(l[i])
    return r

random.seed(42)  # Her çalıştırmada aynı test verisi

# 5000 satırlık hastane muayene kaydı (10001 - 11000 arası Hasta ID'leri)
veriler = [random.randint(10001, 11000) for _ in range(5000)]

baslangic = time.perf_counter()
sonuc_eski = bul(veriler)
eski_sure = time.perf_counter() - baslangic

print("=== AŞAMA 01: ESKİ KOD İLK ÖLÇÜM SONUCU ===")
print(f"Veri sayısı (Hastane Kaydı): {len(veriler)}")
print(f"Tespit edilen mükerrer hasta sayısı: {len(sonuc_eski)}")
print(f"Eski kodun çalışma süresi: {eski_sure:.6f} saniye")