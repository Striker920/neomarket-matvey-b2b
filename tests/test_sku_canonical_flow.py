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

HEADERS = {"Authorization": "Bearer mock-token"}
WRONG_OWNER_HEADERS = {"Authorization": "Bearer wrong-seller-token"}

def test_first_sku_transitions_product_to_on_moderation():
    with TestingSessionLocal() as db: _create_product(db, ProductStatus.DRAFT)
    payload = {"product_id": "550e8400-e29b-41d4-a716-446655440000", "name": "V1", "price": 0}
    response = client.post("/api/v1/skus", json=payload, headers=HEADERS)
    assert response.status_code == 201
    data = response.json()
    assert "active_quantity" in data
    assert "reserved_quantity" in data
    assert "discount" in data
    assert "updated_at" in data
    assert data["images"] == []
    assert data["characteristics"] == []
    
    with TestingSessionLocal() as db:
        p = db.get(Product, "550e8400-e29b-41d4-a716-446655440000")
        assert p.status == ProductStatus.ON_MODERATION

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

def test_add_sku_to_blocked_triggers_re_moderation():
    with TestingSessionLocal() as db: _create_product(db, ProductStatus.BLOCKED)
    payload = {"product_id": "550e8400-e29b-41d4-a716-446655440000", "name": "V1", "price": 1000}
    response = client.post("/api/v1/skus", json=payload, headers=HEADERS)
    assert response.status_code == 201
    
    with TestingSessionLocal() as db:
        p = db.get(Product, "550e8400-e29b-41d4-a716-446655440000")
        assert p.status == ProductStatus.ON_MODERATION
        event = db.query(ModerationEventOutbox).filter(ModerationEventOutbox.aggregate_id == p.id).first()
        assert event is not None
        assert event.event_type == "PRODUCT_EDITED"

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

def test_duplicate_article_returns_409():
    with TestingSessionLocal() as db: 
        p = _create_product(db, ProductStatus.DRAFT)
        db.add(SKU(id="sku-1", product_id=p.id, name="First", price=1000, article="ART-001"))
        db.commit()
    
    payload = {"product_id": "550e8400-e29b-41d4-a716-446655440000", "name": "V2", "price": 2000, "article": "ART-001"}
    response = client.post("/api/v1/skus", json=payload, headers=HEADERS)
    assert response.status_code == 409
    assert response.json()["code"] == "ARTICLE_ALREADY_EXISTS"