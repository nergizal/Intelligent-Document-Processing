import os
import shutil
import random
from pathlib import Path

def split_data(raw_dir="data/raw", split_dir="data/split", train_ratio=0.8):
    categories = ["invoices", "contracts", "order_forms"]
    
    for category in categories:
        src_cat_dir = Path(raw_dir) / category
        if not src_cat_dir.exists():
            print(f"Hata: {src_cat_dir} dizini bulunamadı!")
            continue
            
        # Gizli dosyaları (.DS_Store vb.) hariç tut
        files = [f for f in os.listdir(src_cat_dir) if not f.startswith('.')]
        
        if len(files) == 0:
            print(f"Uyarı: {category} klasörünün içi boş! Lütfen dosya ekleyin.")
            continue

        random.seed(42)
        random.shuffle(files)
        
        split_idx = int(len(files) * train_ratio)
        train_files = files[:split_idx]
        test_files = files[split_idx:]
        
        # Train ve Test klasörlerine kopyala
        for split_name, file_list in [("train", train_files), ("test", test_files)]:
            dest_dir = Path(split_dir) / split_name / category
            dest_dir.mkdir(parents=True, exist_ok=True)
            
            for file_name in file_list:
                src_path = src_cat_dir / file_name
                dest_path = dest_dir / file_name
                shutil.copy2(src_path, dest_path)
                
        print(f"[{category}] Toplam: {len(files)} Belge -> Train: {len(train_files)}, Test: {len(test_files)}")

if __name__ == "__main__":
    split_data()
