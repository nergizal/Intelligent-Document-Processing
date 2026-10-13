import os
import time
import shutil
import requests

# Klasör yolları
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE_DIR, "data", "input_pdf")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed_pdf")
API_URL = "http://localhost:8000/api/v1/documents/process"

# Gerekli klasörleri yoksa otomatik oluştur
os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)


def process_folder():
    print("=" * 60)
    print("🤖 Python RPA Otomasyon Worker Başlatıldı!")
    print(f"📂 İzlenen Girdi Klasörü : {INPUT_DIR}")
    print(f"📦 Arşiv Klasörü         : {PROCESSED_DIR}")
    print(f"🔗 Hedef API             : {API_URL}")
    print("=" * 60)

    while True:
        try:
            # Girdi klasöründeki dosyaları tara
            files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith(".pdf")]

            for filename in files:
                file_path = os.path.join(INPUT_DIR, filename)
                print(f"\n[+] Yeni belge algılandı: {filename}")

                # API'ye multipart/form-data olarak POST et
                with open(file_path, "rb") as f:
                    response = requests.post(
                        API_URL,
                        files={"file": (filename, f, "application/pdf")}
                    )

                if response.status_code == 201:
                    data = response.json()
                    print(f"  ✓ Başarıyla İşlendi!")
                    print(f"    - ID          : {data['document_id']}")
                    print(f"    - Belge Türü  : {data['document_type']}")
                    print(f"    - Güven Skoru : {data['confidence_score']}")
                    print(f"    - Durum       : {data['status']}")
                    if data.get("extracted_data"):
                        ext = data["extracted_data"]
                        print(f"    - Fatura No   : {ext.get('invoice_no')}")
                        print(f"    - Toplam Tutar: {ext.get('total')} TRY")
                else:
                    print(f"  ✗ API Hatası ({response.status_code}): {response.text}")

                # Dosyayı processed klasörüne taşı (arşivle)
                dest_path = os.path.join(PROCESSED_DIR, filename)
                # Aynı isimde dosya varsa üzerine yazmasın diye timestamp ekleyebiliriz
                if os.path.exists(dest_path):
                    name, ext = os.path.splitext(filename)
                    dest_path = os.path.join(PROCESSED_DIR, f"{name}_{int(time.time())}{ext}")

                shutil.move(file_path, dest_path)
                print(f"  ➜ Belge arşivlendi: {os.path.basename(dest_path)}")

        except requests.exceptions.ConnectionError:
            print("[!] Uyarı: Backend API (:8000) henüz ayakta değil, bekleniyor...", end="\r")
        except Exception as e:
            print(f"[!] Beklenmeyen hata: {e}")

        time.sleep(3)  # 3 saniyede bir klasörü kontrol et


if __name__ == "__main__":
    process_folder()