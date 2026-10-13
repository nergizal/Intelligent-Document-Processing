import os
import re
import unicodedata
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List

import joblib
import pdfplumber
import pytesseract
from PIL import Image

# Model dosyasının yolu
MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "artifacts",
    "document_classifier.joblib"
)


class OCREngine:
    """PDF metin katmanını okur, gerekiyorsa OCR fallback yapar."""
    def __init__(self, min_text_len_per_page: int = 20):
        self.min_text_len = min_text_len_per_page

    def clean_page_noise(self, text: str) -> str:
        text = re.sub(r'Sayfa\s*\d+\s*(/\s*\d+)?', '', text, flags=re.IGNORECASE)
        text = re.sub(r'Page\s*\d+\s*(of\s*\d+)?', '', text, flags=re.IGNORECASE)
        return "\n".join([line.strip() for line in text.splitlines() if line.strip()])

    def extract_text(self, pdf_path: str) -> dict:
        result = {"doc_type": "digital", "pages_text": [], "total_pages": 0}

        with pdfplumber.open(pdf_path) as pdf:
            result["total_pages"] = len(pdf.pages)
            for page in pdf.pages:
                extracted = page.extract_text() or ""
                if len(extracted.strip()) < self.min_text_len:
                    result["doc_type"] = "scanned"
                    break
                result["pages_text"].append(self.clean_page_noise(extracted))

        # Taranmış belge fallback adımı (Tesseract TR+ENG)
        if result["doc_type"] == "scanned":
            try:
                from pdf2image import convert_from_path
                result["pages_text"] = []
                images = convert_from_path(pdf_path, dpi=300)
                for img in images:
                    ocr_text = pytesseract.image_to_string(img, lang="tur+eng")
                    result["pages_text"].append(self.clean_page_noise(ocr_text))
            except Exception as e:
                # pdf2image veya poppler yoksa mevcuttaki metinle devam et
                pass

        return {
            "is_scanned": result["doc_type"] == "scanned",
            "full_text": "\n".join(result["pages_text"])
        }


class TextCleaner:
    """Türkçe uyumlu metin temizleme ve normalizasyon."""
    def __init__(self):
        self.amount_pattern = re.compile(
            r'\b\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})\s*(?:TL|₺|USD|\$|EUR|€)?\b',
            re.IGNORECASE
        )
        self.date_pattern = re.compile(
            r'\b\d{2}[./-]\d{2}[./-]\d{4}\b|\b\d{4}[./-]\d{2}[./-]\d{2}\b'
        )

    @staticmethod
    def to_turkish_lower(text: str) -> str:
        if not text:
            return ""
        translation_table = str.maketrans({"İ": "i", "I": "ı"})
        return text.translate(translation_table).lower()

    def clean(self, raw_text: str) -> Tuple[str, List[str]]:
        if not raw_text:
            return "", []

        normalized = unicodedata.normalize('NFKC', raw_text)
        placeholders: Dict[str, str] = {}

        def mask_dates(match):
            key = f"__DATE_{len(placeholders)}__"
            placeholders[key] = match.group(0)
            return key

        def mask_amounts(match):
            key = f"__AMOUNT_{len(placeholders)}__"
            placeholders[key] = match.group(0)
            return key

        masked = self.date_pattern.sub(mask_dates, normalized)
        masked = self.amount_pattern.sub(mask_amounts, masked)

        lowered = self.to_turkish_lower(masked)
        cleaned = re.sub(r'[^\w\s_.:,\-\/]', ' ', lowered)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        for placeholder, original_value in placeholders.items():
            cleaned = cleaned.replace(placeholder.lower(), self.to_turkish_lower(original_value))

        cleaned = re.sub(r'[*_#]', '', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        tokens = [token.strip() for token in cleaned.split() if token.strip()]

        return cleaned, tokens


class RegexExtractor:
    """Fatura ve siparişlerden alan çıkarma."""
    def __init__(self):
        self.invoice_no_pattern = re.compile(
            r'(?i)(?:fatura\s*no|fatura\s*numaras[ı|i]|invoice\s*no|inv\s*#|belge\s*no|order\s*id|order\s*no|siparis\s*no|sipariş\s*no)\s*[:.]?\s*([a-zA-Z0-9\-_/]+)'
        )
        self.date_pattern = re.compile(
            r'(?i)(?:tarih|fatura\s*tarihi|date|invoice\s*date|order\s*date|siparis\s*tarihi|sipariş\s*tarihi)\s*[:.]?\s*(\d{2,4}[./-]\d{2}[./-]\d{2,4})|(\b\d{2}[./-]\d{2}[./-]\d{4}\b|\b\d{4}[./-]\d{2}[./-]\d{2}\b)'
        )
        self.total_pattern = re.compile(
            r'(?i)(?:genel\s*toplam|toplam\s*tutar|toplam|ödenecek\s*tutar|total\s*amount|total|grand\s*total|hizmet\s*bedeli)\s*[:.]?\s*([0-9.,]+)\s*(?:tl|₺|usd|\$|eur|€)?'
        )
        self.tax_pattern = re.compile(
            r'(?i)(?:kdv\s*tutarı|kdv\s*toplam[ı|i]|kdv|vergi\s*tutarı|tax\s*amount|tax|vat)\s*(?:\(\s*%\s*\d+\s*\))?\s*[:.]?\s*([0-9.,]+)\s*(?:tl|₺|usd|\$|eur|€)?'
        )

    def _normalize_amount(self, amount_str: Optional[str]) -> Optional[float]:
        if not amount_str:
            return None
        clean_str = amount_str.strip()
        try:
            if ',' in clean_str and '.' in clean_str:
                if clean_str.rfind(',') > clean_str.rfind('.'):
                    clean_str = clean_str.replace('.', '').replace(',', '.')
                else:
                    clean_str = clean_str.replace(',', '')
            elif ',' in clean_str:
                clean_str = clean_str.replace(',', '.')
            return float(clean_str)
        except (ValueError, TypeError):
            return None

    def _normalize_date(self, date_str: Optional[str]) -> Optional[str]:
        if not date_str:
            return None
        date_str = date_str.strip().replace('/', '.').replace('-', '.')
        formats = ["%d.%m.%Y", "%Y.%m.%d", "%d.%m.%y", "%y.%m.%d"]
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
        return None

    def extract_fields(self, text: str) -> Dict[str, Any]:
        invoice_no, date, total, tax = None, None, None, None
        if not text:
            return {"invoice_no": None, "date": None, "total": None, "tax": None}

        inv_match = self.invoice_no_pattern.search(text)
        if inv_match:
            invoice_no = inv_match.group(1).strip()

        date_match = self.date_pattern.search(text)
        if date_match:
            raw_date = date_match.group(1) or date_match.group(2)
            date = self._normalize_date(raw_date)

        total_match = self.total_pattern.search(text)
        if total_match:
            total = self._normalize_amount(total_match.group(1))

        tax_match = self.tax_pattern.search(text)
        if tax_match:
            tax = self._normalize_amount(tax_match.group(1))

        return {"invoice_no": invoice_no, "date": date, "total": total, "tax": tax}


class DocumentPipeline:
    """Tüm adımları tek elden yöneten ana servis."""
    def __init__(self):
        self.ocr_engine = OCREngine()
        self.cleaner = TextCleaner()
        self.extractor = RegexExtractor()
        self.model = None

        if os.path.exists(MODEL_PATH):
            try:
                self.model = joblib.load(MODEL_PATH)
            except Exception:
                self.model = None

    def run(self, pdf_path: str) -> Dict[str, Any]:
        # 1. OCR / Metin Çıkarımı
        ocr_res = self.ocr_engine.extract_text(pdf_path)
        raw_text = ocr_res.get("full_text", "")

        # 2. Temizleme
        cleaned_text, tokens = self.cleaner.clean(raw_text)

        # 3. Sınıflandırma ve Güven Skoru
        doc_type = "UNKNOWN"
        confidence_score = 0.0

        if self.model and cleaned_text:
            try:
                proba = self.model.predict_proba([cleaned_text])[0]
                max_idx = proba.argmax()
                predicted_label = self.model.classes_[max_idx].upper()

                # Şema kısıtlarına eşleme: INVOICE, CONTRACT, PURCHASE_ORDER, UNKNOWN
                if "INVOICE" in predicted_label:
                    doc_type = "INVOICE"
                elif "CONTRACT" in predicted_label:
                    doc_type = "CONTRACT"
                elif "ORDER" in predicted_label:
                    doc_type = "PURCHASE_ORDER"
                else:
                    doc_type = "UNKNOWN"

                confidence_score = round(float(proba[max_idx]), 4)
            except Exception:
                doc_type = "UNKNOWN"
                confidence_score = 0.0

        # 4. Alan Çıkarımı
        extracted_data = self.extractor.extract_fields(raw_text)

        return {
            "raw_text": raw_text,
            "cleaned_text": cleaned_text,
            "document_type": doc_type,
            "confidence_score": confidence_score,
            "is_scanned": ocr_res.get("is_scanned", False),
            "extracted_data": extracted_data
        }