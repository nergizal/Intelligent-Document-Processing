# API Sözleşmesi (API Contract)

Bu doküman; **AI Servisi**, **RPA Log Servisi** ve **Backend API** arasında değiş
tokuş edilen JSON veri yapılarını tanımlar. Tüm servisler bu sözleşmeye uymakla
yükümlüdür; alan adı veya tip değişikliği bu dokümanın güncellenmesini ve tüm
tarafların onayını gerektirir.

## 1. AI Servisi → Backend: `POST /predict`

RPA robotu veya backend, indirilen bir belgeyi sınıflandırma ve alan çıkarımı için
AI servisine gönderir.

### İstek (Request)
`multipart/form-data`

| Alan       | Tip    | Zorunlu | Açıklama                          |
|------------|--------|---------|------------------------------------|
| `file`     | binary | Evet    | PDF belgesi                        |
| `filename` | string | Hayır   | Orijinal dosya adı (verilmezse `file.filename` kullanılır) |

### Yanıt (Response) — `200 OK`
```json
{
  "document_id": "3f1c9e3a-8b2e-4b0a-9a3d-2b6a9c9e0a11",
  "document_type": "INVOICE",
  "confidence_score": 0.94,
  "extracted_data": {
    "invoice_number": "INV-2026-000482",
    "invoice_date": "2026-08-10",
    "supplier_name": "Acme Tedarik A.Ş.",
    "total_amount": 15420.50,
    "tax_amount": 2350.25,
    "currency": "TRY"
  },
  "processing_time_ms": 842
}
```

### Alan Tanımları

| Alan                  | Tip     | Açıklama                                                                 |
|-----------------------|---------|----------------------------------------------------------------------------|
| `document_id`         | UUID    | Bu işlem için üretilen benzersiz belge kimliği                             |
| `document_type`       | string  | `INVOICE` \| `CONTRACT` \| `PURCHASE_ORDER` \| `UNKNOWN`                    |
| `confidence_score`    | float   | 0.0–1.0 arası sınıflandırma güven skoru                                    |
| `extracted_data`      | object  | Belge türüne göre değişen, regex/model ile çıkarılan alanlar               |
| `processing_time_ms`  | integer | Sunucu tarafında işlemin toplam süresi (milisaniye)                        |

> **Not:** `confidence_score < 0.75` olduğunda backend, belgeyi otomatik olarak
> `HUMAN_REVIEW` statüsüne alır (bkz. [schema.sql](../backend/database/schema.sql)).

### Hata Yanıtı — `422 Unprocessable Entity`
```json
{
  "document_id": null,
  "document_type": "UNKNOWN",
  "confidence_score": 0.0,
  "extracted_data": {},
  "processing_time_ms": 120,
  "error": "PDF içeriği okunamadı veya desteklenmeyen format."
}
```

---

## 2. RPA → Backend: `POST /api/v1/logs`

RPA robotu, her iş akışı adımının sonucunu (başarı/hata) backend'e loglar.

### İstek (Request)
```json
{
  "document_id": "3f1c9e3a-8b2e-4b0a-9a3d-2b6a9c9e0a11",
  "robot_name": "InvoiceIngestionBot",
  "execution_stage": "MAIL_ATTACHMENT_DOWNLOAD",
  "status": "SUCCESS",
  "error_details": null,
  "execution_duration_ms": 1350
}
```

### Alan Tanımları

| Alan                     | Tip     | Açıklama                                                                 |
|--------------------------|---------|----------------------------------------------------------------------------|
| `document_id`            | UUID    | İlgili belgenin kimliği (`documents.id`)                                    |
| `robot_name`              | string  | Çalışan UiPath robotunun adı                                               |
| `execution_stage`        | string  | `MAIL_ATTACHMENT_DOWNLOAD` \| `AI_PREDICTION_CALL` \| `DATA_VALIDATION` \| `ERP_ENTRY` |
| `status`                  | string  | `SUCCESS` \| `FAILED` \| `RETRYING`                                        |
| `error_details`           | string \| null | Hata oluştuysa stack trace / açıklama, yoksa `null`                  |
| `execution_duration_ms`  | integer | Bu aşamanın süresi (milisaniye)                                            |

### Yanıt (Response) — `201 Created`
```json
{
  "id": 10245,
  "logged_at": "2026-08-16T09:12:33Z"
}
```

---

## 3. Backend: `GET /api/v1/health`

Servisin ve veritabanı bağlantısının durumunu kontrol eder.

### Yanıt (Response) — `200 OK`
```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2026-08-16T09:12:33Z"
}
```

### Yanıt (Response) — `503 Service Unavailable`
```json
{
  "status": "unhealthy",
  "database": "disconnected",
  "timestamp": "2026-08-16T09:12:33Z"
}
```

---

## Ortak Enum Değerleri

| Enum              | Değerler                                                        |
|--------------------|------------------------------------------------------------------|
| `document_type`   | `INVOICE`, `CONTRACT`, `PURCHASE_ORDER`, `UNKNOWN`                |
| `status` (belge)  | `PROCESSING`, `APPROVED`, `HUMAN_REVIEW`, `FAILED`                |
| `status` (log)    | `SUCCESS`, `FAILED`, `RETRYING`                                   |
