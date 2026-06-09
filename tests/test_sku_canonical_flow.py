import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.main import app
from src.database import get_db
from src.models.base import Base, Product, SKU, ProductStatus, ModerationEventOutbox

engine = create_engine("sqlite:///./test_canon.db", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine)
client = TestClient(app)

def override_get_db():
    db = TestingSessionLocal()
    try: yield db
    finally: db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def _create_product(db, status=ProductStatus.DRAFT, seller_id="seller-001"):
    p = Product(id="550e8400-e29b-41d4-a716-446655440000", seller_id=seller_id, title="Test", status=status)
    db.add(p); db.commit(); return p

HEADERS = {"X-Seller-Id": "seller-001"}
WRONG_OWNER_HEADERS = {"X-Seller-Id": "seller-999"}

def test_first_sku_transitions_product_to_on_moderation():
    with TestingSessionLocal() as db: _create_product(db, ProductStatus.DRAFT)
    # Проверяем, что price=0 допустим, а images не обязательны
    payload = {"product_id": "550e8400-e29b-41d4-a716-446655440000", "name": "V1", "price": 0}
    response = client.post("/api/v1/skus", json=payload, headers=HEADERS)
    assert response.status_code == 201
    data = response.json()
    # Проверка полного ответа
    assert "stock_quantity" in data
    assert "images" in data
    assert "characteristics" in data
    assert "created_at" in data
    
    with TestingSessionLocal() as db:
        p = db.get(Product, "550e8400-e29b-41d4-a716-446655440000")
        assert p.status == ProductStatus.ON_MODERATION

def test_first_sku_emits_created_event_to_moderation():
    with TestingSessionLocal() as db: _create_product(db, ProductStatus.DRAFT)
    payload = {"product_id": "550e8400-e29b-41d4-a716-446655440000", "name": "V1", "price": 1000, "images": [{"url": "http://a.com/1.jpg"}]}
    client.post("/api/v1/skus", json=payload, headers=HEADERS)
    with TestingSessionLocal() as db:
        event = db.query(ModerationEventOutbox).first()
        assert event is not None and event.event_type == "product.created"

def test_second_sku_no_state_change():
    with TestingSessionLocal() as db:
        p = _create_product(db, ProductStatus.ON_MODERATION)
        db.add(SKU(id="sku-1", product_id=p.id, name="First", price=1000))
        db.commit()
    payload = {"product_id": "550e8400-e29b-41d4-a716-446655440000", "name": "V2", "price": 2000}
    client.post("/api/v1/skus", json=payload, headers=HEADERS)
    with TestingSessionLocal() as db:
        p = db.get(Product, "550e8400-e29b-41d4-a716-446655440000")
        assert p.status == ProductStatus.ON_MODERATION

def test_add_sku_to_hard_blocked_returns_403():
    with TestingSessionLocal() as db: _create_product(db, ProductStatus.HARD_BLOCKED)
    payload = {"product_id": "550e8400-e29b-41d4-a716-446655440000", "name": "V1", "price": 1000}
    response = client.post("/api/v1/skus", json=payload, headers=HEADERS)
    assert response.status_code == 403
    assert response.json()["code"] == "HARD_BLOCKED"

def test_missing_owner_returns_403():
    with TestingSessionLocal() as db: _create_product(db, ProductStatus.DRAFT, seller_id="owner-123")
    payload = {"product_id": "550e8400-e29b-41d4-a716-446655440000", "name": "V1", "price": 1000}
    response = client.post("/api/v1/skus", json=payload, headers=WRONG_OWNER_HEADERS)
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"

def test_product_not_found_returns_404():
    payload = {"product_id": "non-existent-id", "name": "V1", "price": 1000}
    response = client.post("/api/v1/skus", json=payload, headers=HEADERS)
    assert response.status_code == 404
    assert response.json()["code"] == "PRODUCT_NOT_FOUND"