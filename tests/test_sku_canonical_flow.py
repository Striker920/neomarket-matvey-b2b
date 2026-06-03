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
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def _create_product(db, status=ProductStatus.DRAFT):
    p = Product(
        id="550e8400-e29b-41d4-a716-446655440000",
        seller_id="111e8400-e29b-41d4-a716-446655440000",
        title="Test",
        status=status
    )
    db.add(p)
    db.commit()
    return p


def test_first_sku_transitions_product_to_on_moderation():
    with TestingSessionLocal() as db:
        _create_product(db, ProductStatus.DRAFT)
    payload = {
        "product_id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "V1",
        "price": 1000,
        "images": [{"url": "http://a.com/1.jpg"}]
    }
    client.post("/api/v1/skus", json=payload, headers={"X-Service-Key": "test-key"})
    with TestingSessionLocal() as db:
        p = db.get(Product, "550e8400-e29b-41d4-a716-446655440000")
        assert p.status == ProductStatus.ON_MODERATION


def test_first_sku_emits_created_event_to_moderation():
    with TestingSessionLocal() as db:
        _create_product(db, ProductStatus.DRAFT)
    payload = {
        "product_id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "V1",
        "price": 1000,
        "images": [{"url": "http://a.com/1.jpg"}]
    }
    client.post("/api/v1/skus", json=payload, headers={"X-Service-Key": "test-key"})
    with TestingSessionLocal() as db:
        event = db.query(ModerationEventOutbox).first()
        assert event is not None
        assert event.event_type == "product.created"
        assert event.idempotency_key.startswith("sku-created-")


def test_second_sku_no_state_change():
    with TestingSessionLocal() as db:
        p = _create_product(db, ProductStatus.ON_MODERATION)
        db.add(SKU(id="sku-1", product_id=p.id, name="First", price=1000))
        db.commit()
    payload = {
        "product_id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "V2",
        "price": 2000,
        "images": [{"url": "http://a.com/2.jpg"}]
    }
    client.post("/api/v1/skus", json=payload, headers={"X-Service-Key": "test-key"})
    with TestingSessionLocal() as db:
        p = db.get(Product, "550e8400-e29b-41d4-a716-446655440000")
        assert p.status == ProductStatus.ON_MODERATION
        events = db.query(ModerationEventOutbox).filter(
            ModerationEventOutbox.aggregate_id == p.id
        ).all()
        assert len(events) <= 1


def test_add_sku_to_hard_blocked_returns_403():
    with TestingSessionLocal() as db:
        _create_product(db, ProductStatus.HARD_BLOCKED)
    payload = {
        "product_id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "V1",
        "price": 1000,
        "images": [{"url": "http://a.com/1.jpg"}]
    }
    response = client.post("/api/v1/skus", json=payload, headers={"X-Service-Key": "test-key"})
    assert response.status_code == 403
    assert "жёсткой блокировкой" in response.json()["detail"]


def test_missing_image_returns_400():
    with TestingSessionLocal() as db:
        _create_product(db, ProductStatus.DRAFT)
    payload = {
        "product_id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "V1",
        "price": 1000,
        "images": []
    }
    response = client.post("/api/v1/skus", json=payload, headers={"X-Service-Key": "test-key"})
    assert response.status_code in (400, 422)
    assert "images" in str(response.json()).lower()