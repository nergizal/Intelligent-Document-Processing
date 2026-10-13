"""
AI servisi giriş noktası.

Pipeline (bkz. docs/API_CONTRACT.md -> POST /predict):
    1. OCREngine       -> PDF'den ham metin çıkarımı (dijital veya OCR)
    2. TextCleaner     -> Gürültü temizleme (tarih/tutar korunarak)
    3. Sınıflandırma   -> TF-IDF + Lojistik Regresyon baseline modeli
    4. RegexExtractor  -> Fatura no / tarih / tutar alanlarının çıkarımı

Çalıştırma:
    uvicorn src.main:app --reload --port 8500
"""

from __future__ import annotations

import logging
import os
import tempfile
import time
import uuid
from pathlib import Path

import joblib
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from src.extraction.ocr_engine import OCREngine
from src.extraction.regex_extractor import RegexExtractor
from src.preprocessing.cleaner import TextCleaner

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

MODEL_ARTIFACT_PATH = Path(
    os.getenv("MODEL_ARTIFACT_PATH", "src/models/trained/document_classifier.joblib")
)
CONFIDENCE_HUMAN_REVIEW_THRESHOLD = 0.75

app = FastAPI(
    title="Intelligent Document Processing - AI Service",
    description="Belge sınıflandırma, OCR ve alan çıkarımı servisi.",
    version="1.0.0",
)

ocr_engine = OCREngine(tesseract_cmd=os.getenv("TESSERACT_CMD") or None)
text_cleaner = TextCleaner()
regex_extractor = RegexExtractor()

_classifier_pipeline = None
if MODEL_ARTIFACT_PATH.exists():
    _classifier_pipeline = joblib.load(MODEL_ARTIFACT_PATH)
    logger.info("Sınıflandırma modeli yüklendi: %s", MODEL_ARTIFACT_PATH)
else:
    logger.warning(
        "Sınıflandırma modeli bulunamadı (%s). Önce train_baseline.py çalıştırın.",
        MODEL_ARTIFACT_PATH,
    )


def _classify(cleaned_text: str) -> tuple[str, float]:
    """Temizlenmiş metni sınıflandırır; model yoksa UNKNOWN döner."""
    if _classifier_pipeline is None or not cleaned_text.strip():
        return "UNKNOWN", 0.0

    predicted_label = _classifier_pipeline.predict([cleaned_text])[0]
    probabilities = _classifier_pipeline.predict_proba([cleaned_text])[0]
    confidence = float(max(probabilities))
    return predicted_label, round(confidence, 4)


@app.get("/", include_in_schema=False)
def root() -> dict:
    return {"service": "idp-ai-service", "docs": "/docs"}


@app.post("/predict", summary="Belgeyi sınıflandırır ve alan çıkarımı yapar")
async def predict(file: UploadFile = File(...)) -> JSONResponse:
    start_time = time.perf_counter()

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=422, detail="Yalnızca PDF dosyaları desteklenmektedir.")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
        tmp_file.write(await file.read())
        tmp_path = Path(tmp_file.name)

    try:
        extraction_result = ocr_engine.extract_text(tmp_path)
        cleaned_text = text_cleaner.clean(extraction_result.full_text)

        document_type, confidence_score = _classify(cleaned_text)
        extracted_fields = regex_extractor.extract_all(cleaned_text)

        processing_time_ms = round((time.perf_counter() - start_time) * 1000)

        payload = {
            "document_id": str(uuid.uuid4()),
            "document_type": document_type,
            "confidence_score": confidence_score,
            "extracted_data": {
                "invoice_number": extracted_fields.invoice_number,
                "invoice_date": extracted_fields.invoice_date,
                "total_amount": extracted_fields.total_amount,
                "tax_amount": extracted_fields.tax_amount,
                "currency": extracted_fields.currency,
            },
            "processing_time_ms": processing_time_ms,
        }
        return JSONResponse(status_code=200, content=payload)

    except Exception as exc:  # noqa: BLE001
        logger.exception("Belge işlenirken hata oluştu: %s", file.filename)
        processing_time_ms = round((time.perf_counter() - start_time) * 1000)
        error_payload = {
            "document_id": None,
            "document_type": "UNKNOWN",
            "confidence_score": 0.0,
            "extracted_data": {},
            "processing_time_ms": processing_time_ms,
            "error": f"PDF içeriği okunamadı veya desteklenmeyen format: {exc}",
        }
        return JSONResponse(status_code=422, content=error_payload)

    finally:
        tmp_path.unlink(missing_ok=True)
