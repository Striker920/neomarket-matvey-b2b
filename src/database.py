from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Используем SQLite для простоты тестирования (в проде будет PostgreSQL)
engine = create_engine("sqlite:///./app.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()