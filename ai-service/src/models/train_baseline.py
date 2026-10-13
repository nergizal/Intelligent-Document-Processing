import os
import joblib
from pathlib import Path
from typing import Dict, Any, List, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, accuracy_score

from src.extraction.ocr_engine import OCREngine
from src.preprocessing.cleaner import TextCleaner

class BaselineModelTrainer:
    """
    AI-004: TF-IDF (1,2 n-gram) + Logistic Regression Belge Sınıflandırıcı.
    """
    def __init__(self, artifacts_dir: str = "artifacts"):
        self.artifacts_dir = artifacts_dir
        self.model_path = os.path.join(self.artifacts_dir, "document_classifier.joblib")
        os.makedirs(self.artifacts_dir, exist_ok=True)
        
        self.pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(ngram_range=(1, 2), max_features=5000)),
            ('clf', LogisticRegression(class_weight='balanced', random_state=42))
        ])
        self.ocr = OCREngine()
        self.cleaner = TextCleaner()

    def _load_dataset_from_split(self, split_dir: str) -> Tuple[List[str], List[str]]:
        """Klasör yapısından PDF'leri okur, OCR ve Temizleme uygulayarak döner."""
        categories = ["invoices", "contracts", "order_forms"]
        texts = []
        labels = []

        print(f"--> '{split_dir}' altındaki belgeler işleniyor...")
        for cat in categories:
            cat_path = Path(split_dir) / cat
            if not cat_path.exists():
                continue
            
            for file_path in cat_path.glob("*"):
                if file_path.is_file() and not file_path.name.startswith("."):
                    try:
                        extracted = self.ocr.extract_text(str(file_path))
                        clean_text, _ = self.cleaner.clean(extracted["raw_text"])
                        if clean_text:
                            texts.append(clean_text)
                            labels.append(cat)
                    except Exception as e:
                        print(f"Hata ({file_path.name}): {e}")

        return texts, labels

    def train_from_split(self, base_data_dir: str = "data/split") -> float:
        """data/split altındaki train ve test klasörlerini kullanarak modeli eğitir."""
        train_dir = os.path.join(base_data_dir, "train")
        test_dir = os.path.join(base_data_dir, "test")

        x_train, y_train = self._load_dataset_from_split(train_dir)
        x_test, y_test = self._load_dataset_from_split(test_dir)

        if not x_train or not x_test:
            raise ValueError("Eğitim veya test için geçerli veri bulunamadı!")

        print(f"\nToplam Eğitim Verisi: {len(x_train)} | Test Verisi: {len(x_test)}")
        
        # Model Eğitimi
        self.pipeline.fit(x_train, y_train)
        
        # Test Seti Değerlendirmesi
        preds = self.pipeline.predict(x_test)
        acc = accuracy_score(y_test, preds)
        
        print(f"\n================ Model Başarım Raporu ================")
        print(f"Test Accuracy: {acc:.4f} (Hedef: >= 0.75)")
        print(classification_report(y_test, preds, zero_division=0))
        print("=======================================================")

        # Modeli Kaydet
        joblib.dump(self.pipeline, self.model_path)
        print(f"✅ Model başarıyla kaydedildi: {self.model_path}")
        return acc

    def predict(self, raw_or_clean_text: str) -> Dict[str, Any]:
        """Tekil metin için sınıf ve güven skoru (confidence) üretir."""
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model dosyası bulunamadı: {self.model_path}")

        # Eğer ham metin geldiyse temizle
        clean_text, _ = self.cleaner.clean(raw_or_clean_text)
        
        model: Pipeline = joblib.load(self.model_path)
        probabilities = model.predict_proba([clean_text])[0]
        max_idx = probabilities.argmax()
        label = model.classes_[max_idx]
        confidence = float(probabilities[max_idx])

        return {
            "label": label,
            "confidence": round(confidence, 2)
        }

if __name__ == "__main__":
    trainer = BaselineModelTrainer()
    trainer.train_from_split()
