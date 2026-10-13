# Intelligent Document Processing & RPA Platform — Architecture Document

Bu doküman, sistem bileşenlerini, servisler arası uçtan uca iletişim akışını ve Yapay Zeka (AI/ML) servisinin iç veri işleme boru hattını (pipeline) tanımlar.

---

## 1. Servisler Arası Sorumluluk ve Bileşen Mimarisi (Component Diagram)

```mermaid
classDiagram
    direction LR

    class RPA_Module["rpa/ (Burcu - UiPath)"] {
        +Mail_Watcher (IMAP)
        +PDF_Downloader
        +Config_Parser (Config.csv)
        +Trigger_AI_Pipeline()
        +Route_To_Backend()
    }

    class AI_Service["ai-service/ (Sen - ML & OCR)"] {
        +OCREngine (pdfplumber + Tesseract)
        +TextCleaner (TR Unicode + Placeholders)
        +BaselineTrainer (TF-IDF + LogReg)
        +RegexExtractor (Fields Normalizer)
        +POST /predict(PDF) JSON
    }

    class Backend_Service["backend/ (Kemal - API & DB)"] {
        +DB_Session (SQLAlchemy)
        +Threshold_Validator (score >= 0.75)
        +POST /api/v1/invoices
        +POST /api/v1/logs
        +GET /api/v1/health
    }

    class PostgreSQL_Database["PostgreSQL Database"] {
        +documents table
        +invoices table
        +automation_logs table
    }

    RPA_Module ..> AI_Service : HTTP POST /predict (Multipart PDF)
    RPA_Module ..> Backend_Service : HTTP POST /invoices & /logs
    Backend_Service --> PostgreSQL_Database : SQL / ORM Persist
```

---

## 2. Uçtan Uca Sıralama ve Hata Yönetimi Şeması (Sequence Diagram)

```mermaid
sequenceDiagram
    autonumber
    actor Mail as E-Posta Sunucusu (IMAP)
    participant RPA as UiPath Robot (Burcu)
    participant AI as AI Service :8500 (Sen)
    participant BE as Backend API :8000 (Kemal)
    participant DB as PostgreSQL

    Note over Mail,RPA: 1. Tetiklenme ve Indirme
    Mail->>RPA: Yeni e-posta ve PDF eki
    RPA->>RPA: PDF dosyasini rpa/Data/Input/ altina yaz

    Note over RPA,AI: 2. AI Analiz ve Cikarim
    RPA->>AI: POST /predict (multipart/form-data: file.pdf)
    activate AI
    
    alt Gecersiz Dosya Formati (Non-PDF)
        AI-->>RPA: 400 Bad Request
        RPA->>BE: POST /api/v1/logs (status: FAILED)
    else Gecerli PDF Isleme
        AI->>AI: ocr_engine: Katman analizi (Digital / Scanned)
        AI->>AI: cleaner: Turkce normalizasyon
        AI->>AI: train_baseline: Siniflandirma + Confidence
        AI->>AI: regex_extractor: Fatura No, Tarih, Tutar
        AI-->>RPA: 200 OK: JSON {type, confidence_score, data}
    end
    deactivate AI

    Note over RPA,BE: 3. Karar ve Veritabani Kaydi
    alt confidence_score >= 0.75 (Basarili)
        RPA->>BE: POST /api/v1/invoices (status: COMPLETED)
        BE->>DB: INSERT into documents & invoices
        BE-->>RPA: 201 Created
    else confidence_score < 0.75 (Insan Onayi Gerekli)
        RPA->>BE: POST /api/v1/invoices (status: HUMAN_REVIEW)
        BE->>DB: INSERT into documents
        BE-->>RPA: 201 Created
    end

    RPA->>BE: POST /api/v1/logs (execution_time_ms, status)
    BE->>DB: INSERT into automation_logs
    BE-->>RPA: 200 OK
```

---

## 3. AI & OCR Servisi Veri İşleme Boru Hattı (Pipeline Activity Diagram)

```mermaid
flowchart TD
    Start(["Girdi: Multipart PDF Dosyasi"]) --> TmpFile["Gecici Dosyaya Kaydet (/tmp)"]

    subgraph S1["1. Metin Cikarimi & Hibrit OCR (AI-002)"]
        TmpFile --> PlumberScan["pdfplumber ile Metin Katmanini Oku"]
        PlumberScan --> CheckLen{"Karakter Sayisi / Sayfa >= 20 ?"}
        CheckLen -- Evet: Dijital Belge --> ExtractPlumber["Metin Katmanini Al (pdfplumber)"]
        CheckLen -- Hayir: Taranmis Belge --> ConvertImg["pdf2image (300 DPI Rendering)"]
        ConvertImg --> TesseractEngine["Tesseract OCR (lang=tur+eng)"]
        ExtractPlumber --> RawText["Ham Metin (Raw String)"]
        TesseractEngine --> RawText
        RawText --> HeaderFooterClean["Sayfa Numarasi / Header-Footer Filtreleme"]
    end

    subgraph S2["2. On Isleme & Temizleme (AI-003)"]
        HeaderFooterClean --> TRNormalize["Turkce Harf Normalizasyonu"]
        TRNormalize --> Masking["Tarih & Tutar Maskeleme"]
        Masking --> NoiseRegex["Gurultu & Ozel Karakter Temizligi"]
        NoiseRegex --> Unmasking["Placeholder Maskelerini Geri Ac"]
        Unmasking --> CleanOutputs["Temiz Metin & Token Listesi"]
    end

    CleanOutputs --> SplitFork{Pipeline Ayrilimi}

    subgraph S3["3. Siniflandirma Modeli (AI-004)"]
        SplitFork --> TFIDF["TF-IDF Vectorizer (ngram 1-2)"]
        TFIDF --> LRClassifier["Logistic Regression Modeli"]
        LRClassifier --> ProbScore["confidence_score (0.0 - 1.0)"]
        LRClassifier --> ClassLabel["label (invoice | contract | order)"]
    end

    subgraph S4["4. Anahtar Bilgi Cikarimi (AI-005)"]
        SplitFork --> RegexInvoice["Fatura / Belge No Regex"]
        SplitFork --> RegexDate["Tarih Regex (YYYY-MM-DD)"]
        SplitFork --> RegexAmount["Tutar Regex -> Float"]
        RegexInvoice --> ExtractedDict["extracted_data Sozlugu"]
        RegexDate --> ExtractedDict
        RegexAmount --> ExtractedDict
    end

    ClassLabel --> Consolidate["JSON Yanitini Birlestir"]
    ProbScore --> Consolidate
    ExtractedDict --> Consolidate

    Consolidate --> DeleteTmp["Gecici Dosyayi Sil"]
    DeleteTmp --> Output(["Cikti: 200 OK JSON Payload"])
```