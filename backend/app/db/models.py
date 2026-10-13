import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Float, DateTime, ForeignKey, Integer, Text
)
from sqlalchemy.orm import declarative_base, relationship

# İŞTE BURASI: main.py doğrudan bu Base nesnesini arıyor:
Base = declarative_base()


class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String(255), nullable=False)
    document_type = Column(String(20), nullable=False, default="UNKNOWN")
    confidence_score = Column(Float, nullable=False, default=0.0)
    status = Column(String(20), nullable=False, default="PROCESSING")
    file_path = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    invoice = relationship("Invoice", back_populates="document", uselist=False, cascade="all, delete-orphan")
    logs = relationship("AutomationLog", back_populates="document", cascade="all, delete-orphan")


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    supplier_name = Column(String(255), nullable=True)
    invoice_number = Column(String(100), nullable=True)
    invoice_date = Column(DateTime, nullable=True)
    total_amount = Column(Float, nullable=True)
    tax_amount = Column(Float, nullable=True)
    currency = Column(String(3), default="TRY", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    document = relationship("Document", back_populates="invoice")


class AutomationLog(Base):
    __tablename__ = "automation_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    robot_name = Column(String(100), nullable=False, default="IntegratedAutomationWorker")
    execution_stage = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False)
    error_details = Column(Text, nullable=True)
    execution_duration_ms = Column(Integer, nullable=True)
    logged_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    document = relationship("Document", back_populates="logs")