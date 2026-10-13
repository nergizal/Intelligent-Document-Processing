# 📄 Intelligent Document Processing (IDP) & Process Automation Platform
<img width="1373" height="717" alt="Ekran Resmi 2026-10-13 17 25 13" src="https://github.com/user-attachments/assets/3cd887d4-8e1f-4b54-b61f-0faad918bcd1" />


Yarı yapılandırılmış belgeleri (Fatura, Sözleşme, Sipariş Formu vb.) Hibrit OCR, Makine Öğrenmesi (NLP/Sınıflandırma) ve Düzenli İfadeler (Regex) kullanarak milisaniyeler seviyesinde işleyen, **Human-in-the-Loop** prensibine dayalı uçtan uca Akıllı Belge İşleme ve Süreç Otomasyonu Platformu.

---



## 📐 Sistem Mimarisi & Akış Şeması

```text
[ İstemci / Web Dashboard / worker.py ]
                   │
                   ▼ (PDF Upload)
        [ FastAPI: /documents/process ]
                   │
                   ▼
       [ DocumentPipeline (AI/NLP) ]
      ├── 1. OCR (pdfplumber / Tesseract Fallback)
      ├── 2. Cleaner (Metin Normalizasyonu & Türkçe Karakter Temizliği)
      ├── 3. ML Model (Document Classifier - Scikit-Learn TF-IDF) ──► confidence_score
      └── 4. Regex Extractor (Fatura No, Tarih, Tutar Ayrıştırma)
                   │
         ┌─────────┴─────────┐
         │ Score >= 0.75 ?   │
         └────┬─────────┬────┘
           Evet       Hayır
           │           │
           ▼           ▼
      [APPROVED]   [HUMAN_REVIEW]
           │           │
           │           └─► [Operatör Paneli (/app)] ─► (PATCH /approve) ─┐
           │                                                            │
           └───────────────────────────┬────────────────────────────────┘
                                       ▼
                       [ SQLite Database: idp_platform.db ]
                       ├── documents         (Belge üst verisi)
                       ├── invoices          (Ayrıştırılan fatura detayları)
                       └── automation_logs   (Milisaniye bazlı işlem logları)
```

---

## 📋 Yazılım Gereksinim Bildirimi (Software Requirements Specification - SRS)

### 1. İşlevsel Gereksinimler (Functional Requirements - FR)

| Kod | Gereksinim | Açıklama |
|-----|------------|----------|
| **FR-1** | Hibrit OCR Çıkarımı | Dijital PDF'lerden `pdfplumber` ile doğrudan metin okuma; görsel veya taranmış belgelerde `pytesseract` (Tesseract OCR) katmanına otomatik geçiş yapılarak metin ayıklanması. |
| **FR-2** | Metin Normalizasyonu & Temizleme | Türkçe karakterlerin standartlaştırılması (`İ` → `i`, `I` → `ı`), gürültülü özel sembollerin ayıklanması ve finansal/sayısal veriler korunarak metnin işlenmesi. |
| **FR-3** | ML Tabanlı Sınıflandırma ve Güven Skoru | Eğitilmiş TF-IDF + Scikit-Learn modelinin belge türünü (`INVOICE`, `CONTRACT`, `PURCHASE_ORDER`, `UNKNOWN`) ve tahminsel güven skorunu (0.0 – 1.0) üretmesi. |
| **FR-4** | Eşik Değer & İş Kuralları Engine | Güven skoru ≥ 0.75 olan belgelerin doğrudan `APPROVED` statüsüne alınması, < 0.75 olanların risk almamak adına `HUMAN_REVIEW` durumuna yönlendirilmesi. |
| **FR-5** | Kural Tabanlı Veri Çıkarımı (Regex) | Fatura türündeki belgelerden Fatura Numarası, Fatura Tarihi, Toplam Tutar ve Vergi verilerinin düzenli ifadeler (Regex) kullanılarak ayıklanması. |
| **FR-6** | Human-in-the-Loop Operatör Arayüzü | Operatörün güven skoru düşük belgeleri listeleyebilmesi, eksik veya hatalı alanları web paneli üzerinden güncelleyip manuel olarak onaylayabilmesi. |
| **FR-7** | Süreç Otomasyonu - Watcher Worker | Belirlenen ortak klasöre düşen PDF dosyalarını otomatik algılayıp API hattına gönderen ve arşivleyen arka plan servisi (`worker.py`). |

### 2. İşlevsel Olmayan Gereksinimler (Non-Functional Requirements - NFR)

| Kod | Gereksinim | Açıklama |
|-----|------------|----------|
| **NFR-1** | Yüksek Performans & Düşük Gecikme | OCR, ML sınıflandırma ve Regex ayıklama adımlarının tek bir belge için ortalama 30-50 ms aralığında tamamlanması. |
| **NFR-2** | Tam Denetlenebilirlik (Audit Trail) | Tüm adımların robot adı, aşama, durum ve milisaniye bazlı çalışma süresi verileriyle veritabanına (`automation_logs`) loglanması. |
| **NFR-3** | Çevrimdışı / Yerel Çalışabilirlik | Harici veya ücretli bir Cloud API'ye (OpenAI, Gemini vb.) ihtiyaç duymadan %100 yerel ve çevrimdışı (offline) çalışması. |
| **NFR-4** | Modülerlik & Katmanlı Mimari | Veri erişim (ORM), iş mantığı (Pipeline) ve sunum (API/Web) katmanlarının birbirinden bağımsız ve sürdürülebilir modüller halinde tasarlanması. |

---

##  Kullanım Senaryoları (Use Cases)

### Use Case 1: Otomatik Belge Analizi ve Onay

- **Aktör:** Kullanıcı / Otomasyon Servisi (`worker.py`)
- **Ön Koşul:** FastAPI servisinin aktif olması (`http://127.0.0.1:8000`)
- **Ana Akış:**
  1. PDF belgesi `POST /api/v1/documents/process` servisine gönderilir.
  2. OCR motoru metni çıkarır, metin temizleyici gürültüyü siler.
  3. ML modeli belge türünü (`INVOICE`) ve güven skorunu (`0.767`) hesaplar.
  4. Regex motoru Fatura No (`10250`) ve Tarih (`2016-07-08`) verilerini çeker.
  5. Güven skoru ≥ 0.75 olduğu için sistem belge statüsünü `APPROVED` yapar ve veritabanına kaydeder.

### Use Case 2: İnceleme Kuyruğu ve Manuel Operatör Onayı (Human-in-the-Loop)

- **Aktör:** Human Operator
- **Ön Koşul:** Sistemde `HUMAN_REVIEW` durumunda en az bir belgenin bulunması.
- **Ana Akış:**
  1. Operatör `/app` veya `GET /api/v1/documents/review-queue` üzerinden inceleme bekleyen belgeleri görüntüler.
  2. Düşük skora sahip belgeyi seçip düzenleme modalını açar.
  3. Eksik veya hatalı alanları (Tedarikçi adı, tutar vb.) elle düzeltir.
  4. "Onayla & Kaydet" butonuna basarak `PATCH /api/v1/documents/{id}/approve` isteği atar.
  5. Belge statüsü `APPROVED` olarak güncellenir ve işlem `HumanOperator` ismiyle loglanır.

---

##  Detaylı Dosya & Kod Yapısı (Source Code Breakdown)

```text
backend/
├── app/
│   ├── api/v1/
│   │   ├── documents.py      # API Uç Noktaları & İş Kuralları Controller
│   │   └── router.py         # Router Kayıt Modülü
│   ├── db/
│   │   ├── models.py         # SQLAlchemy ORM Veri Modelleri
│   │   └── session.py        # Veritabanı Oturumu & Health Check
│   └── services/
│       └── pipeline.py       # AI, OCR & NLP Boru Hattı (Business Logic)
├── main.py                   # FastAPI Uygulama Giriş Noktası & Gömülü Web Paneli
└── worker.py                 # Klasör İzleyici Otomasyon Servisi
```


##  Kurulum ve Çalıştırma

### 1. Gereksinimler

- Python 3.11+
- Tesseract OCR Engine (`brew install tesseract` veya Windows binary)

### 2. Sanal Ortam ve Bağımlılıklar

```bash
# Proje dizinine geçin
cd backend

# Sanal ortam oluşturun ve aktif edin
python -m venv venv
source venv/bin/activate  # Windows için: venv\Scripts\activate

# Bağımlılıkları yükleyin
pip install -r requirements.txt
```

### 3. Sunucuyu Başlatma

```bash
# FastAPI backend ve entegre web panelini çalıştırın
uvicorn main:app --reload --port 8000
```

### 4. Erişilebilir Adresler

| Servis | Adres |
|--------|-------|
| Yönetim & Operatör Paneli | <http://127.0.0.1:8000/app> |
| Interactive Swagger API Docs | <http://127.0.0.1:8000/docs> |
| Health Check Uç Noktası | <http://127.0.0.1:8000/api/v1/health> |

---

##  Arka Plan Otomasyon İzleyicisini Çalıştırma (RPA Worker)

Projede harici RPA lisansı gerektirmeden dosya izleme otomasyonu sağlayan `worker.py` script'i mevcuttur:

```bash
# Ayrı bir terminalde klasör izleyiciyi başlatın
python worker.py
```

`watch_folder/` klasörüne kopyalanan tüm PDF dosyaları otomatik olarak tespit edilir, API'ye gönderilir ve işlem bittiğinde `processed/` klasörüne taşınır.

---

##  Teknolojik Mimari

- **Backend:** FastAPI, Python 3.11, Pydantic
- **Database & ORM:** SQLite, SQLAlchemy ORM
- **AI & Machine Learning:** Scikit-Learn (TF-IDF Vectorizer + Classifier), Joblib
- **OCR & Document Processing:** pdfplumber, pytesseract (Tesseract)
- **Frontend:** Bootstrap 5, Bootstrap Icons, Vanilla JavaScript (Fetch API)
