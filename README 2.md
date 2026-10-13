# Intelligent Document Processing & Business Process Automation Platform

Fatura, sözleşme ve sipariş gibi yarı yapılandırılmış belgeleri e-posta kutusundan
otomatik olarak toplayan, OCR/NLP ile sınıflandırıp veri çıkarımı yapan ve sonuçları
insan onayı gerektiren durumlar hariç uçtan uca otomatik işleyen bir
**Belge İşleme + İş Süreci Otomasyonu (IDP + RPA)** platformudur.

## 🎯 Projenin Amacı

Manuel olarak yapılan "e-postadan fatura indir → oku → sisteme gir" sürecini ortadan
kaldırmak için üç bileşen birlikte çalışır:

1. **RPA Robotu (UiPath)** e-posta kutusunu izler, ekleri indirir ve AI servisine gönderir.
2. **AI Servisi (Python/FastAPI)** belgenin türünü sınıflandırır (Fatura / Sözleşme / Sipariş),
   OCR ile metni çıkarır ve kural tabanlı + istatistiksel modellerle alanları
   (fatura no, tarih, tutar vb.) ayıklar.
3. **Backend API (FastAPI)** sonuçları veritabanına yazar, güven skoru düşük olan
   belgeleri "insan incelemesi" kuyruğuna alır ve dış sistemlere/raporlamaya API sağlar.

## 🏗️ Mimari Şema

```
                                   ┌────────────────────────────┐
                                   │        E-posta Kutusu       │
                                   │   (IMAP / Outlook / M365)    │
                                   └──────────────┬───────────────┘
                                                  │ yeni e-posta + PDF ek
                                                  ▼
                       ┌──────────────────────────────────────────────┐
                       │                RPA MODÜLÜ (UiPath)             │
                       │  ┌────────────┐  ┌────────────────────────┐   │
                       │  │ Mail Okuma │─▶│ PDF Attachment Download │   │
                       │  └────────────┘  └────────────┬───────────┘   │
                       │                                │               │
                       │                     ┌──────────▼───────────┐   │
                       │                     │   JSON Parser /       │   │
                       │                     │   AI API Çağrısı      │   │
                       │                     └──────────┬───────────┘   │
                       └────────────────────────────────┼───────────────┘
                                                         │ POST /predict (multipart PDF)
                                                         ▼
                       ┌──────────────────────────────────────────────┐
                       │              AI SERVICE (FastAPI :8500)         │
                       │                                                │
                       │   ┌───────────┐  ┌───────────┐  ┌───────────┐  │
                       │   │  OCR /    │─▶│  Metin     │─▶│ Sınıflandır│  │
                       │   │  Extraction│  │  Temizleme │  │ + Regex    │  │
                       │   │(pdfplumber/│  │ (cleaner)  │  │ Çıkarım    │  │
                       │   │ Tesseract) │  │            │  │(TF-IDF+LR) │  │
                       │   └───────────┘  └───────────┘  └───────────┘  │
                       └────────────────────────────────┬───────────────┘
                                                         │ JSON (document_type,
                                                         │ confidence_score,
                                                         │ extracted_data)
                                                         ▼
                       ┌──────────────────────────────────────────────┐
                       │             BACKEND API (FastAPI :8000)         │
                       │                                                │
                       │   ┌───────────┐   ┌───────────┐  ┌──────────┐  │
                       │   │  API      │──▶│  Servis   │─▶│   ORM /   │  │
                       │   │  Router   │   │  Katmanı  │  │ Repository│  │
                       │   │ (v1)      │   │           │  │  (SQLAlchemy)│
                       │   └───────────┘   └───────────┘  └─────┬─────┘  │
                       └───────────────────────────────────────┼─────────┘
                                                                ▼
                                                  ┌───────────────────────┐
                                                  │  PostgreSQL / MySQL    │
                                                  │  documents             │
                                                  │  invoices               │
                                                  │  automation_logs        │
                                                  └───────────────────────┘
```

## 📦 Modül Açıklamaları

| Modül         | Teknoloji                                              | Sorumluluk                                                                 |
|---------------|---------------------------------------------------------|-----------------------------------------------------------------------------|
| `ai-service/` | Python 3.10+, FastAPI, pdfplumber, PyTesseract, scikit-learn, joblib | PDF'den metin çıkarımı, temizleme, belge sınıflandırma ve alan çıkarımı        |
| `backend/`    | Python 3.10+, FastAPI, SQLAlchemy, Pydantic v2, PostgreSQL/MySQL | İş verisinin kalıcı hale getirilmesi, iş kuralları, dış sistemlere API sağlama |
| `rpa/`        | UiPath Studio                                            | E-posta izleme, ek indirme, AI servisiyle entegrasyon ve loglama              |
| `docs/`       | Markdown                                                 | Mimari kararlar ve servisler arası API sözleşmeleri                          |

## 📁 Depo Yapısı

```
intelligent-document-processing-platform/
├── .gitignore
├── .env.example
├── README.md
├── docs/
│   └── API_CONTRACT.md
├── backend/
│   ├── requirements.txt
│   ├── main.py
│   ├── app/
│   │   ├── core/config.py
│   │   ├── db/session.py
│   │   ├── schemas/health.py
│   │   └── api/v1/...
│   └── database/
│       ├── schema.sql
│       └── seed.py
├── ai-service/
│   ├── requirements.txt
│   └── src/
│       ├── main.py
│       ├── extraction/{ocr_engine.py, regex_extractor.py}
│       ├── preprocessing/cleaner.py
│       └── models/train_baseline.py
└── rpa/
    ├── Data/{Input,Output}/
    ├── Workflows/
    ├── Config.csv
    └── mock_ai_response.json
```

## 🚀 Yerel Kurulum

### Ön Koşullar
- Python 3.10 veya üzeri
- PostgreSQL 14+ (veya MySQL 8+)
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) (taranmış PDF'ler için)
- UiPath Studio (RPA modülünü çalıştırmak için, opsiyonel)

### 1. Ortam değişkenlerini oluşturun
```bash
cp .env.example .env
# .env dosyasını kendi veritabanı bilgilerinizle güncelleyin
```

### 2. Backend servisini çalıştırın
```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Veritabanı şemasını oluşturun
psql -U idp_user -d idp_platform -f database/schema.sql

# Mock verileri yükleyin (idempotent)
python database/seed.py

# Servisi başlatın
uvicorn main:app --reload --port 8000
```
Sağlık kontrolü: `GET http://localhost:8000/api/v1/health`

### 3. AI servisini çalıştırın
```bash
cd ai-service
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Baseline sınıflandırma modelini eğitin
python src/models/train_baseline.py

# Servisi başlatın
uvicorn src.main:app --reload --port 8500
```

### 4. RPA modülünü açın
`rpa/` klasörünü UiPath Studio ile açın, `Config.csv` içindeki değerleri kendi
ortamınıza göre güncelleyip bir `Config.xlsx` olarak kaydedin
(bkz. [rpa/Config.csv](rpa/Config.csv)).

## 🔗 Servisler Arası Sözleşme

AI servisi, RPA loglama servisi ve backend arasındaki JSON kontratı için
[docs/API_CONTRACT.md](docs/API_CONTRACT.md) dosyasına bakınız.

## 🗺️ Sprint 1 Kapsamı

- [x] Depo iskeleti ve konfigürasyon dosyaları
- [x] Veritabanı şeması (`documents`, `invoices`, `automation_logs`)
- [x] Backend health-check ve katmanlı FastAPI altyapısı
- [x] AI servisi için OCR, temizleme, regex çıkarım ve baseline sınıflandırma taslağı
- [x] RPA klasör iskeleti ve mock AI yanıtı
