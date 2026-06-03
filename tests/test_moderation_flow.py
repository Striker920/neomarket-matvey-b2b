import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.main import app
from src.database import get_db
from src.models.base import Base, Product, ProductStatus, ProcessedEvent

engine = create_engine("sqlite:///./test_moderation.db", connect_args={"check_same_thread": False})
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


def _create_product(db, status=ProductStatus.ON_MODERATION, block_reason="Old reason", field_reports=None):
    p = Product(
        id="550e8400-e29b-41d4-a716-446655440000",
        seller_id="111e8400-e29b-41d4-a716-446655440000",
        title="Test Product",
        status=status,
        block_reason=block_reason,
        field_reports=field_reports
    )
    db.add(p)
    db.commit()
    return p


HEADERS = {"X-Service-Key": "test-key"}
BAD_HEADERS = {}


def test_moderated_event_clears_blocking_data():
    with TestingSessionLocal() as db:
        _create_product(db, block_reason="Bad content", field_reports=[{"field": "title", "issue": "spam"}])

    payload = {
        "idempotency_key": "evt-001",
        "product_id": "550e8400-e29b-41d4-a716-446655440000",
        "event_type": "MODERATED",
        "occurred_at": datetime.now(timezone.utc).isoformat()
    }

    response = client.post("/api/v1/moderation/events", json=payload, headers=HEADERS)
    assert response.status_code == 204

    with TestingSessionLocal() as db:
        p = db.get(Product, "550e8400-e29b-41d4-a716-446655440000")
        assert p.status == ProductStatus.MODERATED
        assert p.block_reason is None
        assert p.field_reports is None


def test_blocked_soft_saves_field_reports():
    with TestingSessionLocal() as db:
        _create_product(db)

    payload = {
        "idempotency_key": "evt-002",
        "product_id": "550e8400-e29b-41d4-a716-446655440000",
        "event_type": "BLOCKED",
        "hard_block": False,
        "moderator_comment": "Некачественные фото",
        "blocking_reason_id": "reason-uuid-001",
        "field_reports": [
            {"field_name": "image", "issue": "blurry", "severity": "high"}
        ],
        "occurred_at": datetime.now(timezone.utc).isoformat()
    }

    response = client.post("/api/v1/moderation/events", json=payload, headers=HEADERS)
    assert response.status_code == 204

    with TestingSessionLocal() as db:
        p = db.get(Product, "550e8400-e29b-41d4-a716-446655440000")
        assert p.status == ProductStatus.BLOCKED
        assert p.block_reason == "Некачественные фото"
        assert p.blocking_reason_id == "reason-uuid-001"
        assert p.field_reports == [{"field_name": "image", "issue": "blurry", "severity": "high"}]


def test_blocked_hard_sets_terminal_status():
    with TestingSessionLocal() as db:
        _create_product(db)

    payload = {
        "idempotency_key": "evt-003",
        "product_id": "550e8400-e29b-41d4-a716-446655440000",
        "event_type": "BLOCKED",
        "hard_block": True,
        "moderator_comment": "Мошенничество",
        "blocking_reason_id": "reason-uuid-002",
        "occurred_at": datetime.now(timezone.utc).isoformat()
    }

    response = client.post("/api/v1/moderation/events", json=payload, headers=HEADERS)
    assert response.status_code == 204

    with TestingSessionLocal() as db:
        p = db.get(Product, "550e8400-e29b-41d4-a716-446655440000")
        assert p.status == ProductStatus.HARD_BLOCKED
        assert p.block_reason == "Мошенничество"


def test_hard_blocked_product_rejects_seller_edits():
    with TestingSessionLocal() as db:
        _create_product(db, status=ProductStatus.HARD_BLOCKED)

    response = client.put(
        "/api/v1/products/550e8400-e29b-41d4-a716-446655440000?seller_id=111e8400-e29b-41d4-a716-446655440000"
    )
    assert response.status_code == 403
    assert "жёсткой блокировкой" in response.json()["detail"]


def test_duplicate_event_same_idempotency_key_no_side_effects():
    with TestingSessionLocal() as db:
        _create_product(db)

    payload = {
        "idempotency_key": "evt-dup",
        "product_id": "550e8400-e29b-41d4-a716-446655440000",
        "event_type": "BLOCKED",
        "hard_block": True,
        "moderator_comment": "Fraud",
        "blocking_reason_id": "reason-uuid-003",
        "occurred_at": datetime.now(timezone.utc).isoformat()
    }

    response1 = client.post("/api/v1/moderation/events", json=payload, headers=HEADERS)
    assert response1.status_code == 204

    response2 = client.post("/api/v1/moderation/events", json=payload, headers=HEADERS)
    assert response2.status_code == 204
    assert response2.headers.get("X-Idempotent-Replay") == "true"

    with TestingSessionLocal() as db:
        events = db.query(ProcessedEvent).filter(
            ProcessedEvent.idempotency_key == "evt-dup"
        ).all()
        assert len(events) == 1


def test_missing_service_key_returns_401():
    payload = {
        "idempotency_key": "evt-no-key",
        "product_id": "550e8400-e29b-41d4-a716-446655440000",
        "event_type": "MODERATED",
        "occurred_at": datetime.now(timezone.utc).isoformat()
    }

    response = client.post("/api/v1/moderation/events", json=payload, headers=BAD_HEADERS)
    assert response.status_code == 401
    assert "X-Service-Key" in response.json()["detail"]