import os
import shutil
import time
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime

from app.db.models import AutomationLog, Document, Invoice
from app.db.session import get_db
from app.services.pipeline import DocumentPipeline

router = APIRouter(prefix="/documents", tags=["Documents"])
pipeline = DocumentPipeline()

CONFIDENCE_THRESHOLD = 0.75
UPLOAD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    "data",
    "uploads"
)
os.makedirs(UPLOAD_DIR, exist_ok=True)


class DocumentApproveRequest(BaseModel):
    supplier_name: Optional[str] = None
    invoice_number: Optional[str] = None
    total_amount: Optional[float] = None
    tax_amount: Optional[float] = None
    currency: Optional[str] = "TRY"


@router.post("/process", status_code=status.HTTP_201_CREATED)
async def process_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    PDF yükler, AI analizini (OCR + Sınıflandırma + Extraction) çalıştırır.
    Güven skoru >= 0.75 ise APPROVED, < 0.75 ise HUMAN_REVIEW durumuna alır.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Yalnızca PDF formatındaki belgeler desteklenmektedir.")

    start_time = time.time()
    file_id = str(uuid.uuid4())
    saved_filename = f"{file_id}_{file.filename}"
    saved_path = os.path.join(UPLOAD_DIR, saved_filename)

    # 1. Dosyayı diske kaydet
    with open(saved_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # 2. AI Boru Hattını Çalıştır
        result = pipeline.run(saved_path)
        doc_type = result["document_type"]
        confidence = result["confidence_score"]
        extracted = result["extracted_data"]

        # 3. Eşik Değeri Mantığı (Threshold Rule)
        if doc_type == "UNKNOWN":
            doc_status = "FAILED"
        elif confidence >= CONFIDENCE_THRESHOLD:
            doc_status = "APPROVED"
        else:
            doc_status = "HUMAN_REVIEW"

        # 4. Document Kaydını Oluştur
        document = Document(
            filename=file.filename,
            document_type=doc_type,
            confidence_score=confidence,
            status=doc_status,
            file_path=saved_path
        )
        db.add(document)
        db.flush()

# 5. Belge Fatura ise Invoice tablosuna yaz
        if doc_type == "INVOICE":
            raw_date_str = extracted.get("date")
            parsed_date = None
            if raw_date_str:
                try:
                    parsed_date = datetime.strptime(raw_date_str, "%Y-%m-%d").date()
                except ValueError:
                    parsed_date = None

            invoice = Invoice(
                document_id=document.id,
                supplier_name=None,
                invoice_number=extracted.get("invoice_no"),
                invoice_date=parsed_date,
                total_amount=extracted.get("total"),
                tax_amount=extracted.get("tax"),
                currency="TRY"
            )
            db.add(invoice)

        # 6. İşlem Logunu Yaz (automation_logs)
        duration_ms = int((time.time() - start_time) * 1000)
        log = AutomationLog(
            document_id=document.id,
            robot_name="IntegratedAIWorker",
            execution_stage="DATA_VALIDATION" if doc_status == "HUMAN_REVIEW" else "AI_PREDICTION_CALL",
            status="SUCCESS" if doc_status in ["APPROVED", "HUMAN_REVIEW"] else "FAILED",
            error_details="Güven skoru 0.75 eşiğinin altında kaldı, operatör incelemesi gerekiyor." if doc_status == "HUMAN_REVIEW" else None,
            execution_duration_ms=duration_ms
        )
        db.add(log)
        db.commit()
        db.refresh(document)

        return {
            "document_id": str(document.id),
            "filename": document.filename,
            "document_type": document.document_type,
            "confidence_score": float(document.confidence_score),
            "status": document.status,
            "is_scanned": result.get("is_scanned", False),
            "extracted_data": extracted,
            "execution_duration_ms": duration_ms
        }

    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"İşlem sırasında hata oluştu: {str(exc)}")


@router.get("/review-queue")
def get_review_queue(db: Session = Depends(get_db)):
    """Operatör incelemesi bekleyen (HUMAN_REVIEW) belgeleri listeler."""
    docs = db.query(Document).filter(Document.status == "HUMAN_REVIEW").order_by(Document.created_at.desc()).all()
    return [
        {
            "id": str(d.id),
            "filename": d.filename,
            "document_type": d.document_type,
            "confidence_score": float(d.confidence_score),
            "status": d.status,
            "created_at": d.created_at.isoformat()
        }
        for d in docs
    ]

@router.patch("/{document_id}/approve")
def approve_document(
    document_id: str,
    payload: DocumentApproveRequest,
    db: Session = Depends(get_db)
):
    """Operatörün inceleyip düzelttiği/onayladığı faturayı APPROVED statüsüne geçirir."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Belge bulunamadı.")

    doc.status = "APPROVED"

    inv = db.query(Invoice).filter(Invoice.document_id == document_id).first()
    if not inv:
        inv = Invoice(document_id=doc.id)
        db.add(inv)

    if payload.supplier_name is not None:
        inv.supplier_name = payload.supplier_name
    if payload.invoice_number is not None:
        inv.invoice_number = payload.invoice_number
    if payload.total_amount is not None:
        inv.total_amount = payload.total_amount
    if payload.tax_amount is not None:
        inv.tax_amount = payload.tax_amount
    if payload.currency is not None:
        inv.currency = payload.currency

    log = AutomationLog(
        document_id=doc.id,
        robot_name="HumanOperator",
        execution_stage="ERP_ENTRY",
        status="SUCCESS",
        error_details="Belge operatör tarafından manuel olarak doğrulandı ve onaylandı.",
        execution_duration_ms=0
    )
    db.add(log)
    db.commit()

    return {"message": "Belge başarıyla onaylandı.", "document_id": str(doc.id), "status": doc.status}