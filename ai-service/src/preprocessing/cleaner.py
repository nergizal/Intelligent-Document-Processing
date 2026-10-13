import re
import unicodedata
from typing import Tuple, List, Dict

class TextCleaner:
    """
    OCR ve Metin Ön İşleme / Temizleme Hattı.
    OOP prensiplerine uygun, yeni kural eklenebilir genişletilebilir yapı.
    """
    def __init__(self):
        # Finansal veri koruyucu Regex kalıpları
        self.amount_pattern = re.compile(r'\b\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})\s*(?:TL|₺|USD|\$|EUR|€)?\b', re.IGNORECASE)
        self.date_pattern = re.compile(r'\b\d{2}[./-]\d{2}[./-]\d{4}\b|\b\d{4}[./-]\d{2}[./-]\d{2}\b')

    @staticmethod
    def to_turkish_lower(text: str) -> str:
        """Python'ın default .lower() metodunun bozduğu büyük İ/I harflerini düzeltir."""
        if not text:
            return ""
        translation_table = str.maketrans({"İ": "i", "I": "ı"})
        return text.translate(translation_table).lower()

    def clean(self, raw_text: str) -> Tuple[str, List[str]]:
        """
        Metni temizler, gürültüyü siler, para/tarihleri korur.
        Dönüş: (temizlenmiş_metin, token_listesi)
        """
        if not raw_text:
            return "", []

        # 1. Adım: Unicode normalizasyonu (NFKC)
        normalized = unicodedata.normalize('NFKC', raw_text)
        
        # 2. Adım: Placeholder ile Tutar ve Tarihleri Maskeleme
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

        # 3. Adım: Türkçe Uyumlu Küçük Harfe Dönüştürme
        lowered = self.to_turkish_lower(masked)

        # 4. Adım: Gürültü ve İstenmeyen Özel Karakterleri Temizleme
        cleaned = re.sub(r'[^\w\s_.:,\-\/]', ' ', lowered)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        # 5. Adım: Maskeleri Geri Yükleme
        for placeholder, original_value in placeholders.items():
            cleaned = cleaned.replace(placeholder.lower(), self.to_turkish_lower(original_value))

        # 6. Adım: Ekstra boşluk temizliği ve gereksiz sembolleri ayırma
        cleaned = re.sub(r'[*_#]', '', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        # 7. Adım: Tokenization (Kelime bazlı ayırma)
        tokens = [token.strip() for token in cleaned.split() if token.strip()]

        return cleaned, tokens

if __name__ == "__main__":
    cleaner = TextCleaner()
    test_noisy_text = "FATURA NO: 12345*** \n\n Toplam: 1.500 TL \n Tarih: 12.08.2026"
    cleaned_text, tokens = cleaner.clean(test_noisy_text)
    print("====================================")
    print("Ham Gürültülü Metin:")
    print(repr(test_noisy_text))
    print("\nTemizlenmiş Metin:")
    print(repr(cleaned_text))
    print("\nToken Listesi:")
    print(tokens)
    print("====================================")
