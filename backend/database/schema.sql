-- ==========================================================================
-- Intelligent Document Processing & Business Process Automation Platform
-- Veritabanı Şeması (DDL)
--
-- Birincil hedef: PostgreSQL 14+
-- MySQL 8+ ile uyumluluk için gerekli farklar aşağıda not edilmiştir:
--   1) UUID üretimi:
--        PostgreSQL -> gen_random_uuid()  (pgcrypto eklentisi gerekir)
--        MySQL      -> UUID()  ve kolon tipi CHAR(36)
--   2) Otomatik artan tamsayı:
--        PostgreSQL -> BIGSERIAL / GENERATED ALWAYS AS IDENTITY
--        MySQL      -> BIGINT ... AUTO_INCREMENT
--   3) ENUM kısıtları taşınabilirlik için native ENUM tipi yerine
--      VARCHAR + CHECK constraint olarak modellenmiştir (her iki motorda
--      da çalışır).
--   4) "updated_at" alanının otomatik güncellenmesi PostgreSQL'de trigger,
--      MySQL'de "ON UPDATE CURRENT_TIMESTAMP" ile sağlanır (ilgili yerlerde
--      her iki seçenek de belirtilmiştir).
-- ==========================================================================

-- PostgreSQL için UUID üretim fonksiyonunu sağlayan eklenti.
-- MySQL kullanıyorsanız bu satırı kaldırın.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- --------------------------------------------------------------------------
-- Tablo: documents
-- Her belge (fatura, sözleşme, sipariş vb.) için tek bir kayıt tutulur.
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS documents (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- MySQL alternatifi: id CHAR(36) PRIMARY KEY DEFAULT (UUID()),

    filename          VARCHAR(255) NOT NULL,
    document_type     VARCHAR(20)  NOT NULL DEFAULT 'UNKNOWN'
                       CONSTRAINT chk_documents_document_type
                       CHECK (document_type IN ('INVOICE', 'CONTRACT', 'PURCHASE_ORDER', 'UNKNOWN')),

    confidence_score  NUMERIC(5, 4) NOT NULL DEFAULT 0.0000
                       CONSTRAINT chk_documents_confidence_score
                       CHECK (confidence_score >= 0 AND confidence_score <= 1),

    status            VARCHAR(20) NOT NULL DEFAULT 'PROCESSING'
                       CONSTRAINT chk_documents_status
                       CHECK (status IN ('PROCESSING', 'APPROVED', 'HUMAN_REVIEW', 'FAILED')),

    file_path         VARCHAR(500) NOT NULL,

    created_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    -- MySQL alternatifi: updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    --                    ON UPDATE CURRENT_TIMESTAMP,
);

-- documents.updated_at alanını her UPDATE'te otomatik güncelleyen trigger (PostgreSQL).
CREATE OR REPLACE FUNCTION set_updated_at_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_documents_updated_at ON documents;
CREATE TRIGGER trg_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at_timestamp();

-- Sık kullanılan filtreler için performans indeksleri.
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents (status);
CREATE INDEX IF NOT EXISTS idx_documents_document_type ON documents (document_type);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents (created_at DESC);

-- --------------------------------------------------------------------------
-- Tablo: invoices
-- "documents" tablosundaki fatura tipi belgelerin ayrıntılı alanları.
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS invoices (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- MySQL alternatifi: id CHAR(36) PRIMARY KEY DEFAULT (UUID()),

    document_id       UUID NOT NULL,
    -- MySQL alternatifi: document_id CHAR(36) NOT NULL,

    supplier_name     VARCHAR(255),
    invoice_number    VARCHAR(100),
    invoice_date      DATE,
    total_amount      NUMERIC(14, 2),
    tax_amount        NUMERIC(14, 2),
    currency          VARCHAR(3) NOT NULL DEFAULT 'TRY',

    created_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_invoices_document
        FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_invoices_document_id ON invoices (document_id);
CREATE INDEX IF NOT EXISTS idx_invoices_invoice_number ON invoices (invoice_number);

-- --------------------------------------------------------------------------
-- Tablo: automation_logs
-- RPA robotlarının her iş akışı adımında ürettiği çalışma kayıtları.
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS automation_logs (
    id                      BIGSERIAL PRIMARY KEY,
    -- MySQL alternatifi: id BIGINT AUTO_INCREMENT PRIMARY KEY,

    document_id             UUID NOT NULL,
    -- MySQL alternatifi: document_id CHAR(36) NOT NULL,

    robot_name              VARCHAR(100) NOT NULL,

    execution_stage         VARCHAR(50) NOT NULL
                             CONSTRAINT chk_automation_logs_execution_stage
                             CHECK (execution_stage IN (
                                 'MAIL_ATTACHMENT_DOWNLOAD',
                                 'AI_PREDICTION_CALL',
                                 'DATA_VALIDATION',
                                 'ERP_ENTRY'
                             )),

    status                   VARCHAR(20) NOT NULL
                             CONSTRAINT chk_automation_logs_status
                             CHECK (status IN ('SUCCESS', 'FAILED', 'RETRYING')),

    error_details            TEXT,
    execution_duration_ms   INTEGER,

    logged_at                TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_automation_logs_document
        FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_automation_logs_document_id ON automation_logs (document_id);
CREATE INDEX IF NOT EXISTS idx_automation_logs_status ON automation_logs (status);
CREATE INDEX IF NOT EXISTS idx_automation_logs_logged_at ON automation_logs (logged_at DESC);
