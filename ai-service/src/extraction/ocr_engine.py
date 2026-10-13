import os
import re
from typing import Dict, Any, List
import pdfplumber
import pytesseract
from pdf2image import convert_from_path
from PIL import Image

class OCREngine:
    """
    Hibrit Metin Cikarim Motoru:
    - Dijital PDF'ler icin pdfplumber (<500ms, dusuk CPU)
    - Taranmis / Gorsel PDF'ler icin 300 DPI Tesseract OCR (tur+eng)
    """
    def __init__(self, min_char_threshold: int = 20, tesseract_cmd: str = None):
        self.min_char_threshold = min_char_threshold
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        elif os.getenv("TESSERACT_CMD"):
            pytesseract.pytesseract.tesseract_cmd = os.getenv("TESSERACT_CMD")

    def _clean_page_artifacts(self, text: str) -> str:
        """Sayfa altligi, ustlugu ve gereksiz tireleme gurultulerini temizler."""
        if not text:
            return ""
        text = re.sub(r'(?i)\b(?:sayfa|page)\s*\d+\s*(?:[/|-]\s*\d+)?\b', '', text)
        text = re.sub(r'(\w+)-\n(\w+)', r'\1\2', text)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines)

    def extract_text(self, pdf_path: str) -> Dict[str, Any]:
        """PDF dosyasini analiz eder, metin katmanini veya OCR ciktisini doner."""
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF dosyasi bulunamadi: {pdf_path}")

        is_scanned = False
        extracted_pages: List[str] = []

        # 1. Asama: Hizli Dijital Katman Kontrolu
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            for page in pdf.pages:
                raw_text = page.extract_text() or ""
                cleaned = self._clean_page_artifacts(raw_text)
                if len(cleaned.strip()) < self.min_char_threshold:
                    is_scanned = True
                    break
                extracted_pages.append(cleaned)

        # 2. Asama: Taranmis Belge Fallback (Tesseract OCR)
        if is_scanned:
            extracted_pages = []
            images: List[Image.Image] = convert_from_path(pdf_path, dpi=300)
            for img in images:
                ocr_text = pytesseract.image_to_string(img, lang="tur+eng")
                cleaned_ocr = self._clean_page_artifacts(ocr_text)
                extracted_pages.append(cleaned_ocr)

        full_text = "\n\n".join(extracted_pages).strip()
        
        return {
            "is_scanned": is_scanned,
            "total_pages": total_pages if not is_scanned else len(extracted_pages),
            "raw_text": full_text
        }

if __name__ == "__main__":
    import glob
    # Test: raw/invoices altindaki ilk dosyayi okutalim
    sample_files = glob.glob("data/raw/invoices/*")
    if sample_files:
        sample_pdf = sample_files[0]
        engine = OCREngine()
        result = engine.extract_text(sample_pdf)
        print("====================================")
        print(f"Test Edilen Dosya : {sample_pdf}")
        print(f"Taranmis mi (OCR)? : {result['is_scanned']}")
        print(f"Sayfa Sayisi      : {result['total_pages']}")
        print("--- Cikarilan Metin Onizleme ---")
        print(result['raw_text'][:300])
        print("====================================")
    else:
        print("data/raw/invoices altinda test edilecek dosya bulunamadi.")
