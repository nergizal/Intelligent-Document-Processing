import re
from typing import Dict, Any, Optional
from datetime import datetime

class RegexExtractor:
    """
    AI-005: Belge metinlerinden kural tabanlı (Regex) bilgi çıkaran motor.
    TR ve EN fatura etiketlerini destekler, None dönebilen hata korumasına sahiptir.
    """
    def __init__(self):
        # 1. Fatura / Belge No Kalıpları
        self.invoice_no_pattern = re.compile(
            r'(?i)(?:fatura\s*no|fatura\s*numaras[ı|i]|invoice\s*no|inv\s*#|belge\s*no|order\s*id|order\s*no|siparis\s*no|sipariş\s*no)\s*[:.]?\s*([a-zA-Z0-9\-_/]+)'
        )
        
        # 2. Tarih Kalıpları (DD.MM.YYYY, DD/MM/YYYY, YYYY-MM-DD, YYYY.MM.DD vb.)
        self.date_pattern = re.compile(
            r'(?i)(?:tarih|fatura\s*tarihi|date|invoice\s*date|order\s*date|siparis\s*tarihi|sipariş\s*tarihi)\s*[:.]?\s*(\d{2,4}[./-]\d{2}[./-]\d{2,4})|(\b\d{2}[./-]\d{2}[./-]\d{4}\b|\b\d{4}[./-]\d{2}[./-]\d{2}\b)'
        )
        
        # 3. Toplam Tutar Kalıpları
        self.total_pattern = re.compile(
            r'(?i)(?:genel\s*toplam|toplam\s*tutar|toplam|ödenecek\s*tutar|total\s*amount|total|grand\s*total|hizmet\s*bedeli)\s*[:.]?\s*([0-9.,]+)\s*(?:tl|₺|usd|\$|eur|€)?'
        )

        # 4. Vergi / KDV Tutarı Kalıpları
        self.tax_pattern = re.compile(
            r'(?i)(?:kdv\s*tutarı|kdv\s*toplam[ı|i]|kdv|vergi\s*tutarı|tax\s*amount|tax|vat)\s*(?:\(\s*%\s*\d+\s*\))?\s*[:.]?\s*([0-9.,]+)\s*(?:tl|₺|usd|\$|eur|€)?'
        )

    def _normalize_amount(self, amount_str: Optional[str]) -> Optional[float]:
        """
        '1.234,56' (TR) veya '1,234.56' (EN) veya '50.80' formatındaki tutarları float'a çevirir.
        """
        if not amount_str:
            return None
        clean_str = amount_str.strip()
        try:
            if ',' in clean_str and '.' in clean_str:
                if clean_str.rfind(',') > clean_str.rfind('.'):
                    # TR Formatı: 1.234,56 -> 1234.56
                    clean_str = clean_str.replace('.', '').replace(',', '.')
                else:
                    # EN Formatı: 1,234.56 -> 1234.56
                    clean_str = clean_str.replace(',', '')
            elif ',' in clean_str:
                # Sadece virgül varsa ondalık kabul edilir: 1500,50 -> 1500.50
                clean_str = clean_str.replace(',', '.')
            
            return float(clean_str)
        except (ValueError, TypeError):
            return None

    def _normalize_date(self, date_str: Optional[str]) -> Optional[str]:
        """Tarihi YYYY-MM-DD (ISO 8601) formatına standardize eder."""
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
        """Metin içerisinden tüm anahtar alanları ayıklar."""
        invoice_no = None
        date = None
        total = None
        tax = None

        if not text:
            return {
                "invoice_no": None,
                "date": None,
                "total": None,
                "tax": None
            }

        # Fatura / Belge No
        inv_match = self.invoice_no_pattern.search(text)
        if inv_match:
            invoice_no = inv_match.group(1).strip()

        # Tarih
        date_match = self.date_pattern.search(text)
        if date_match:
            raw_date = date_match.group(1) or date_match.group(2)
            date = self._normalize_date(raw_date)

        # Toplam Tutar
        total_match = self.total_pattern.search(text)
        if total_match:
            total = self._normalize_amount(total_match.group(1))

        # KDV / Vergi Tutarı
        tax_match = self.tax_pattern.search(text)
        if tax_match:
            tax = self._normalize_amount(tax_match.group(1))

        return {
            "invoice_no": invoice_no,
            "date": date,
            "total": total,
            "tax": tax
        }

if __name__ == "__main__":
    extractor = RegexExtractor()
    sample_text = """
    SATIS FATURASI
    Fatura No: FT2026-0001
    Fatura Tarihi: 12.08.2026
    KDV Tutari (%20): 300,00 TL
    Genel Toplam: 1.500,00 TL
    """
    extracted = extractor.extract_fields(sample_text)
    print("====================================")
    print("Örnek Metin:")
    print(sample_text.strip())
    print("\nÇıkarılan Alanlar (Extracted Fields):")
    print(extracted)
    print("====================================")
