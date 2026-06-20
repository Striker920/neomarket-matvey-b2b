import sys
from pathlib import Path

root_path = str(Path(__file__).parent.parent)
if root_path not in sys.path:
    sys.path.insert(0, root_path)

import pytest
from jose import jwt
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from src.database import Base, get_db
from src.main import app

from src.models.product import Product


TEST_DATABASE_URL = "sqlite:///./test.db"


@pytest.fixture(scope="session")
def engine():
    """Создаём engine один раз для всей сессии"""
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(engine):
    """Создаёт сессию тестовой БД"""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture
def client(db_session):
    """Клиент, который использует ту же БД, что и фикстура"""
    
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def valid_jwt():
    payload = {"sub": str(uuid4())}
    return jwt.encode(payload, "your-secret-key-change-in-production", algorithm="HS256")


@pytest.fixture
def valid_jwt_with_fixed_id():
    expected_seller_id = "123e4567-e89b-12d3-a456-426614174000"
    payload = {"sub": expected_seller_id}
    token = jwt.encode(payload, "your-secret-key-change-in-production", algorithm="HS256")
    return token, expected_seller_id