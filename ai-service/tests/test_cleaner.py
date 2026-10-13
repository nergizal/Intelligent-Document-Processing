import pytest
from src.preprocessing.cleaner import TextCleaner

def test_cleaner_noise_and_financial_protection():
    cleaner = TextCleaner()
    noisy_input = "FATURA NO: 12345*** \n\n Toplam: 1.500 TL "
    
    cleaned, tokens = cleaner.clean(noisy_input)
    
    # Doğrulamalar
    assert "1.500 tl" in cleaned
    assert "***" not in cleaned
    assert "fatura" in cleaned
    assert len(tokens) > 0

def test_turkish_character_lowercase():
    cleaner = TextCleaner()
    turkish_input = "İSTANBUL IŞIK ÇAY"
    cleaned, _ = cleaner.clean(turkish_input)
    
    assert "istanbul" in cleaned
    assert "ışık" in cleaned
    assert "çay" in cleaned
