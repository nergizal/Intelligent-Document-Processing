"""
seed.py
-------
Veritabanına dört farklı statüde (APPROVED, HUMAN_REVIEW, FAILED, PROCESSING)
gerçekçi mock veri basan idempotent script.

Idempotentlik stratejisi:
    Her mock kayıt için sabit (deterministik) bir UUID kullanılır. Script
    tekrar çalıştırıldığında ilgili id zaten varsa o kayıt atlanır; bu sayede
    script defalarca çalıştırılsa bile veritabanında tekrar oluşmaz.

Kullanım:
    python database/seed.py
"""

import os
import sys
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://idp_user:change_me@localhost:5432/idp_platform",
)

engine = create_engine(DATABASE_URL, future=True)

# Sabit (deterministik) UUID'ler -- rerun'larda çakışmayı önlemek için.
DOCUMENT_IDS = {
    "APPROVED": "11111111-1111-4111-8111-111111111111",
    "HUMAN_REVIEW": "22222222-2222-4222-8222-222222222222",
    "FAILED": "33333333-3333-4333-8333-333333333333",
    "PROCESSING": "44444444-4444-4444-8444-444444444444",
}

INVOICE_IDS = {
    "APPROVED": "aaaaaaaa-1111-4111-8111-111111111111",
    "HUMAN_REVIEW": "aaaaaaaa-2222-4222-8222-222222222222",
}


def _now_minus(minutes: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(minutes=minutes)


def document_exists(conn, document_id: str) -> bool:
    result = conn.execute(
        text("SELECT 1 FROM documents WHERE id = :id"), {"id": document_id}
    ).fetchone()
    return result is not None


def seed_document(conn, document_id: str, filename: str, document_type: str,
                   confidence_score: float, status: str, file_path: str) -> None:
    if document_exists(conn, document_id):
        print(f"  [atlandı] documents.{status} zaten mevcut ({document_id})")
        return

    conn.execute(
        text(
            """
            INSERT INTO documents
                (id, filename, document_type, confidence_score, status, file_path, created_at)
            VALUES
                (:id, :filename, :document_type, :confidence_score, :status, :file_path, :created_at)
            """
        ),
        {
            "id": document_id,
            "filename": filename,
            "document_type": document_type,
            "confidence_score": confidence_score,
            "status": status,
            "file_path": file_path,
            "created_at": _now_minus(60),
        },
    )
    print(f"  [eklendi] documents.{status} ({document_id})")


def seed_invoice(conn, invoice_id: str, document_id: str, supplier_name: str,
                  invoice_number: str, invoice_date: str, total_amount: float,
                  tax_amount: float, currency: str = "TRY") -> None:
    existing = conn.execute(
        text("SELECT 1 FROM invoices WHERE id = :id"), {"id": invoice_id}
    ).fetchone()
    if existing is not None:
        print(f"  [atlandı] invoices {invoice_number} zaten mevcut")
        return

    conn.execute(
        text(
            """
            INSERT INTO invoices
                (id, document_id, supplier_name, invoice_number, invoice_date,
                 total_amount, tax_amount, currency)
            VALUES
                (:id, :document_id, :supplier_name, :invoice_number, :invoice_date,
                 :total_amount, :tax_amount, :currency)
            """
        ),
        {
            "id": invoice_id,
            "document_id": document_id,
            "supplier_name": supplier_name,
            "invoice_number": invoice_number,
            "invoice_date": invoice_date,
            "total_amount": total_amount,
            "tax_amount": tax_amount,
            "currency": currency,
        },
    )
    print(f"  [eklendi] invoices {invoice_number}")


def seed_automation_log(conn, document_id: str, robot_name: str, execution_stage: str,
                         status: str, error_details: str | None, duration_ms: int) -> None:
    existing = conn.execute(
        text(
            """
            SELECT 1 FROM automation_logs
            WHERE document_id = :document_id AND execution_stage = :execution_stage
            """
        ),
        {"document_id": document_id, "execution_stage": execution_stage},
    ).fetchone()
    if existing is not None:
        print(f"  [atlandı] automation_logs {execution_stage} zaten mevcut")
        return

    conn.execute(
        text(
            """
            INSERT INTO automation_logs
                (document_id, robot_name, execution_stage, status, error_details,
                 execution_duration_ms, logged_at)
            VALUES
                (:document_id, :robot_name, :execution_stage, :status, :error_details,
                 :duration_ms, :logged_at)
            """
        ),
        {
            "document_id": document_id,
            "robot_name": robot_name,
            "execution_stage": execution_stage,
            "status": status,
            "error_details": error_details,
            "duration_ms": duration_ms,
            "logged_at": _now_minus(45),
        },
    )
    print(f"  [eklendi] automation_logs {execution_stage} ({status})")


def run() -> None:
    print(f"Veritabanına bağlanılıyor: {DATABASE_URL.split('@')[-1]}")

    with engine.begin() as conn:
        print("\n1) APPROVED belge (fatura, başarıyla işlendi)")
        seed_document(
            conn, DOCUMENT_IDS["APPROVED"],
            filename="acme_tedarik_fatura_000482.pdf",
            document_type="INVOICE",
            confidence_score=0.9750,
            status="APPROVED",
            file_path="/data/documents/acme_tedarik_fatura_000482.pdf",
        )
        seed_invoice(
            conn, INVOICE_IDS["APPROVED"], DOCUMENT_IDS["APPROVED"],
            supplier_name="Acme Tedarik A.Ş.",
            invoice_number="INV-2026-000482",
            invoice_date="2026-08-10",
            total_amount=15420.50,
            tax_amount=2350.25,
        )
        seed_automation_log(
            conn, DOCUMENT_IDS["APPROVED"], "InvoiceIngestionBot",
            "ERP_ENTRY", "SUCCESS", None, 980,
        )

        print("\n2) HUMAN_REVIEW belge (düşük güven skoru, manuel onay bekliyor)")
        seed_document(
            conn, DOCUMENT_IDS["HUMAN_REVIEW"],
            filename="belirsiz_tedarikci_fatura_009911.pdf",
            document_type="INVOICE",
            confidence_score=0.6120,
            status="HUMAN_REVIEW",
            file_path="/data/documents/belirsiz_tedarikci_fatura_009911.pdf",
        )
        seed_invoice(
            conn, INVOICE_IDS["HUMAN_REVIEW"], DOCUMENT_IDS["HUMAN_REVIEW"],
            supplier_name="Yıldız Lojistik Ltd. Şti.",
            invoice_number="INV-2026-009911",
            invoice_date="2026-08-14",
            total_amount=8760.00,
            tax_amount=1350.00,
        )
        seed_automation_log(
            conn, DOCUMENT_IDS["HUMAN_REVIEW"], "InvoiceIngestionBot",
            "DATA_VALIDATION", "RETRYING",
            "Güven skoru eşik değerinin (0.75) altında, manuel inceleme gerekiyor.",
            410,
        )

        print("\n3) FAILED belge (OCR/parse hatası)")
        seed_document(
            conn, DOCUMENT_IDS["FAILED"],
            filename="hasarli_taranmis_belge.pdf",
            document_type="UNKNOWN",
            confidence_score=0.0000,
            status="FAILED",
            file_path="/data/documents/hasarli_taranmis_belge.pdf",
        )
        seed_automation_log(
            conn, DOCUMENT_IDS["FAILED"], "InvoiceIngestionBot",
            "AI_PREDICTION_CALL", "FAILED",
            "OCR motoru metni okuyamadı: taranmış görüntü çözünürlüğü çok düşük.",
            1520,
        )

        print("\n4) PROCESSING belge (henüz işleniyor)")
        seed_document(
            conn, DOCUMENT_IDS["PROCESSING"],
            filename="siparis_formu_2026_0231.pdf",
            document_type="PURCHASE_ORDER",
            confidence_score=0.0000,
            status="PROCESSING",
            file_path="/data/documents/siparis_formu_2026_0231.pdf",
        )
        seed_automation_log(
            conn, DOCUMENT_IDS["PROCESSING"], "InvoiceIngestionBot",
            "MAIL_ATTACHMENT_DOWNLOAD", "SUCCESS", None, 640,
        )

    print("\nSeed işlemi tamamlandı.")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:  # noqa: BLE001
        print(f"Seed işlemi başarısız oldu: {exc}", file=sys.stderr)
        sys.exit(1)
