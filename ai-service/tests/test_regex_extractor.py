import pytest
from src.extraction.regex_extractor import RegexExtractor

def test_extract_turkish_invoice():
    extractor = RegexExtractor()
    text = "Fatura No: FT2026-001 \n Tarih: 12.08.2026 \n KDV: 300,00 TL \n Genel Toplam: 1.500,00 TL"
    res = extractor.extract_fields(text)
    
    assert res["invoice_no"] == "FT2026-001"
    assert res["date"] == "2026-08-12"
    assert res["total"] == 1500.00
    assert res["tax"] == 300.00

def test_extract_english_invoice():
    extractor = RegexExtractor()
    text = "Invoice No: INV-9876 \n Order Date: 2026-07-04 \n Total: 2,450.50 USD"
    res = extractor.extract_fields(text)
    
    assert res["invoice_no"] == "INV-9876"
    assert res["date"] == "2026-07-04"
    assert res["total"] == 2450.50
    assert res["tax"] is None  # Bulunamayan alan None dönmeli

def test_graceful_degradation_on_empty():
    extractor = RegexExtractor()
    res = extractor.extract_fields("")
    
    assert res["invoice_no"] is None
    assert res["date"] is None
    assert res["total"] is None
    assert res["tax"] is None
