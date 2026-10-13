import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# PostgreSQL yerine doğrudan sorunsuz SQLite dosyası kullan
DATABASE_URL = "sqlite:///./idp_platform.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def is_database_reachable() -> bool:
    """Health check için veritabanı testi"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False