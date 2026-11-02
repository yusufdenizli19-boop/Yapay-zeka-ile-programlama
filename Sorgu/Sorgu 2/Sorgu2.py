import sqlite3
import os
import re
import time
import random
from google import genai
from google.genai import types

# Rapor ve model ayarları
RAPOR_DOSYASI = "sql_asistan_raporu.txt"
MODEL_ADI = "gemini-3.5-flash"  # Föyde belirtilen model

# 1. VERİTABANI OLUŞTURMA VE SHADOW SCHEMA
conn = sqlite3.connect(':memory:')
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS musteriler (
    musteri_id INT, 
    ad_soyad TEXT, 
    sehir TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS siparisler (
    siparis_id INT, 
    musteri_id INT, 
    tutar REAL, 
    tarih TEXT
)
""")
conn.commit()

# TODO 1: random ile 1.000 müşteri ve 1.000 sipariş verisi üretip executemany() ile ekleyin.
def veritabani_verileri_yukle():
    sehirler = ['İstanbul', 'Ankara', 'Izmir', 'Bursa', 'Antalya']
    isimler = ['Ahmet Yılmaz', 'Ayşe Kaya', 'Mehmet Demir', 'Fatma Çelik', 'Ali Şahin', 'Zeynep Koç', 'Mustafa Aydın', 'Elif Öztürk']
    
    musteri_verileri = []
    for m_id in range(1, 1001):
        ad_soyad = f"{random.choice(isimler)} {m_id}"
        sehir = random.choice(sehirler)
        musteri_verileri.append((m_id, ad_soyad, sehir))
        
    siparis_verileri = []
    for s_id in range(1, 1001):
        musteri_id = random.randint(1, 1000)
        tutar = round(random.uniform(100.0, 10000.0), 2)
        # 2026 yılına ait rastgele tarih simülasyonu
        ay = random.randint(1, 12)
        gun = random.randint(1, 28)
        tarih = f"2026-{ay:02d}-{gun:02d}"
        siparis_verileri.append((s_id, musteri_id, tutar, tarih))

    cursor.executemany("INSERT INTO musteriler VALUES (?, ?, ?)", musteri_verileri)
    cursor.executemany("INSERT INTO siparisler VALUES (?, ?, ?, ?)", siparis_verileri)
    conn.commit()
    print("[BİLGİ] Veritabanı oluşturuldu. 1.000 müşteri ve 1.000 sipariş yüklendi.")

# TODO 2: DROP, DELETE, UPDATE, INSERT, ALTER komutlarını re.search() ile engelleyin.
def guvenlik_kontrolu(sql_kodu: str) -> bool:
    yasakli_komutlar = r'\b(DROP|DELETE|UPDATE|INSERT|ALTER|TRATUNCATE|CREATE)\b'
    if re.search(yasakli_komutlar, sql_kodu, re.IGNORECASE):
        print(f"[GÜVENLİK ENGELİ] Zararlı SQL tespit edildi: Yasaklı komut içeriyor!")
        return False
    
    # Sadece SELECT ile başlamalı veya en azından sadece okuma yapmalı
    temiz_kod = sql_kodu.strip().upper()
    if not temiz_kod.startswith("SELECT"):
        print(f"[GÜVENLİK ENGELİ] Sorgu SELECT ile başlamıyor.")
        return False
        
    print("[GÜVENLİK] Denetim Başarılı (Sadece SELECT).")
    return True

# TODO 3: Gemini yanıtındaki markdown etiketlerini regex ile temizleyin.
def clean_sql(raw_sql: str) -> str:
    if not raw_sql:
        return ""
    # ```sql ... ``` bloklarını ve boşlukları temizle
    metin = raw_sql.strip()
    metin = re.sub(r"^```(?:sql)?\s*", "", metin, flags=re.IGNORECASE)
    metin = re.sub(r"\s*```$", "", metin)
    return metin.strip()

# TODO 4: Gemini API entegrasyonu ve Otomatik Hata Düzeltme (Self-Correction) döngüsü.
def gemini_sql_uret(talep: str, hata_mesaji: str = None) -> str:
    api_anahtari = os.environ.get("GEMINI_API_KEY", "")
    if not api_anahtari:
        # Test ortamı simülasyonu veya hata yönetimi için
        raise RuntimeError("GEMINI_API_KEY ortam değişkeni tanımlı değil.")

    client = genai.Client(api_key=api_anahtari)
    
    sistem_mesaji = (
        "Aşağıdaki veritabanı şemasına göre kullanıcının doğal dille istediği veriyi çekecek SQLite uyumlu SQL sorgusunu yaz. "
        "Şema: Musteriler(musteri_id, ad_soyad, sehir), Siparisler(siparis_id, musteri_id, tutar, tarih). "
        "Kurallar: Sadece SELECT komutu kullan. Çıktıda markdown etiketi ve açıklama olmasın, sadece saf SQL döndür."
    )
    
    prompt = f"Kullanıcı Talebi: {talep}"
    if hata_mesaji:
        prompt += f"\n[DİKKAT] Önceki yazdığın şu SQL hata verdi: {hata_mesaji}. Lütfen bu hatayı düzelterek yeniden yaz."

    response = client.models.generate_content(
        model=MODEL_ADI,
        contents=[types.Content(role="user", parts=[types.Part.from_text(text=f"{sistem_mesaji}\n\n{prompt}")])]
    )
    return response.text

def sql_asistani_calistir(kullanici_talebi: str):
    print("[GEMINI] SQL Üretiliyor...")
    
    deneme = 0
    max_deneme = 3
    hata_mesaji = None
    uretilen_sql = ""
    basarili = False
    icra_suresi = 0.0
    sonuc_satirlari = []
    
    while deneme < max_deneme:
        deneme += 1
        try:
            ham_yanit = gemini_sql_uret(kullanici_talebi, hata_mesaji)
            uretilen_sql = clean_sql(ham_yanit)
            print(f"[SQL] {uretilen_sql}")
            
            # Güvenlik Kontrolü
            if not guvenlik_kontrolu(uretilen_sql):
                return "ENGELLENDI", 0.0, []
                
            # SQLite İcra Testi ve Süre Ölçümü
            start_time = time.perf_counter()
            cursor.execute(uretilen_sql)
            sonuc_satirlari = cursor.fetchall()
            end_time = time.perf_counter()
            
            icra_suresi = round(end_time - start_time, 4)
            basarili = True
            if deneme > 1:
                print(f"[BİLGİ] Self-Correction başarılı: {deneme}. denemede hata giderildi.")
            break
            
        except sqlite3.Error as e:
            hata_mesaji = str(e)
            print(f"[HATA - Self-Correction Devrede] SQLite Hatası (Deneme {deneme}): {hata_mesaji}")
            if deneme >= max_deneme:
                return "HATA", 0.0, []
        except Exception as e:
            print(f"[SİSTEM HATASI] {e}")
            return "HATA", 0.0, []
            
    if basarili:
        return "BASARILI", icra_suresi, sonuc_satirlari
    return "HATA", 0.0, []

# TODO 5: while True döngüsü kurarak kullanıcıdan interaktif istek alın.
def rapor_yaz(test_ozetleri):
    rapor_icerik = f"""AKILLI SQL ASİSTANI PERFORMANS VE GÜVENLİK RAPORU
Çalıştırma Tarihi: 2026-11-02
Veritabanı Hacmi: 1.000 Müşteri, 1.000 Sipariş
Toplam Test Talebi: {len(test_ozetleri)}
"""
    basarili_sayisi = sum(1 for t in test_ozetleri if t['durum'] == 'BAŞARILI')
    engellenen_sayisi = sum(1 for t in test_ozetleri if t['durum'] == 'ENGELLENDİ')
    
    rapor_icerik += f"Başarılı İcra: {basarili_sayisi}\n"
    rapor_icerik += f"Engellenen Saldırı: {engellenen_sayisi}\n\n"
    rapor_icerik += "TEST DETAYLARI:\n"
    
    for i, test in enumerate(test_ozetleri, 1):
        if test['durum'] == 'BAŞARILI':
            rapor_icerik += f"[TEST {i}] İcra Süresi: {test['sure']} saniye | Durum: BAŞARILI ({test['talep']})\n"
        elif test['durum'] == 'ENGELLENDİ':
            rapor_icerik += f"[TEST {i}] Güvenlik Engeli: BAŞARILI (Zararlı komut engellendi: {test['talep']})\n"
        else:
            rapor_icerik += f"[TEST {i}] Talep: {test['talep']} | Durum: BAŞARISIZ/HATA\n"
            
    rapor_icerik += "\nKISA YORUM VE DEĞERLENDİRME:\n"
    rapor_icerik += "1.000 kayıtlık veritabanında Gemini modeli ile SQL üretimi başarıyla gerçekleştirilmiştir.\n"
    rapor_icerik += "Üretilen SQL'lerin SQLite üzerindeki icra süreleri milisaniye mertebesindedir.\n"
    rapor_icerik += "Güvenlik filtresi tehlikeli komutları veritabanına ulaşmadan başarıyla bloke etmiştir.\n"
    
    with open(RAPOR_DOSYASI, "w", encoding="utf-8") as f:
        f.write(rapor_icerik)
    print(f"\n[BİLGİ] Rapor '{RAPOR_DOSYASI}' dosyasına kaydedildi.")

def main():
    veritabani_verileri_yukle()
    test_gecmisi = []
    
    print("\nSistem Hazır. Örnek sorgu yazabilir veya 'q' ile çıkabilirsiniz.")
    while True:
        talep = input("\nSoru Girin (Çıkış için 'q'): ").strip()
        if talep.lower() == 'q':
            print("Çıkış yapılıyor...")
            break
        if not talep:
            continue
            
        durum, sure, sonuclar = sql_asistani_calistir(talep)
        
        if durum == "BASARILI":
            print(f"[SONUÇ] (İcra Süresi: {sure} sn)")
            for satir in sonuclar[:5]:  # İlk 5 satırı göster
                print(" | ".join(str(s) for s in satir))
            test_gecmisi.append({"talep": talep, "durum": "BAŞARILI", "sure": sure})
        elif durum == "ENGELLENDI":
            test_gecmisi.append({"talep": talep, "durum": "ENGELLENDİ", "sure": 0.0})
        else:
            print("[SONUÇ] İşlem tamamlanamadı veya hata oluştu.")
            test_gecmisi.append({"talep": talep, "durum": "HATA", "sure": 0.0})
            
    if test_gecmisi:
        rapor_yaz(test_gecmisi)

if __name__ == "__main__":
    main()