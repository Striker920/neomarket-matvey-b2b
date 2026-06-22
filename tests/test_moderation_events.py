import pytest
from uuid import uuid4
from datetime import datetime, timezone
from unittest.mock import patch

from src.models.product import Product
from src.config import settings


class TestModerationEvents:

    def test_moderated_event_clears_blocking_data(self, client, db_session):
        """MODERATED event: status=MODERATED, blocking data cleared"""
        product = Product(
            id=str(uuid4()),
            seller_id=str(uuid4()),
            category_id=str(uuid4()),
            title="Blocked Product",
            slug="blocked",
            description="Description",
            status=Product.Status.BLOCKED,
            deleted=False,
            blocked=True,
            blocking_reason_id=str(uuid4()),
            moderator_comment="Bad content",
            images=[],
            characteristics=[],
            skus=[]
        )
        db_session.add(product)
        db_session.commit()

        response = client.post(
            "/api/v1/moderation/events",
            json={
                "idempotency_key": str(uuid4()),
                "product_id": str(product.id),
                "event_type": "MODERATED",
                "occurred_at": datetime.now(timezone.utc).isoformat()
            },
            headers={"X-Service-Key": settings.MODERATION_SERVICE_KEY}
        )

        assert response.status_code == 204
        db_session.refresh(product)
        assert product.status == Product.Status.MODERATED
        assert product.blocked is False
        assert product.moderator_comment == ""

    def test_blocked_soft_saves_field_reports(self, client, db_session):
        """BLOCKED soft: status=BLOCKED, B2C cascade"""
        product = Product(
            id=str(uuid4()),
            seller_id=str(uuid4()),
            category_id=str(uuid4()),
            title="Soft Block Test",
            slug="soft-block",
            description="Description",
            status=Product.Status.MODERATED,
            deleted=False,
            blocked=False,
            images=[],
            characteristics=[],
            skus=[]
        )
        db_session.add(product)
        db_session.commit()

        response = client.post(
            "/api/v1/moderation/events",
            json={
                "idempotency_key": str(uuid4()),
                "product_id": str(product.id),
                "event_type": "BLOCKED",
                "hard_block": False,
                "moderator_comment": "Некачественные фото",
                "blocking_reason_id": "reason-uuid-001",
                "field_reports": [
                    {"field_name": "image", "comment": "blurry"}
                ],
                "occurred_at": datetime.now(timezone.utc).isoformat()
            },
            headers={"X-Service-Key": settings.MODERATION_SERVICE_KEY}
        )

        assert response.status_code == 204
        db_session.refresh(product)
        assert product.status == Product.Status.BLOCKED
        assert product.blocked is True
        assert product.moderator_comment == "Некачественные фото"

    def test_blocked_hard_sets_terminal_status(self, client, db_session):
        """BLOCKED hard: HARD_BLOCKED, B2C cascade outbox event"""
        from src.models.b2c_cascade_outbox import B2CCascadeOutbox

        product = Product(
            id=str(uuid4()),
            seller_id=str(uuid4()),
            category_id=str(uuid4()),
            title="Hard Block Test",
            slug="hard-block",
            description="Description",
            status=Product.Status.MODERATED,
            deleted=False,
            blocked=False,
            images=[],
            characteristics=[],
            skus=[]
        )
        db_session.add(product)
        db_session.commit()

        response = client.post(
            "/api/v1/moderation/events",
            json={
                "idempotency_key": str(uuid4()),
                "product_id": str(product.id),
                "event_type": "BLOCKED",
                "hard_block": True,
                "moderator_comment": "Мошенничество",
                "blocking_reason_id": "reason-uuid-002",
                "occurred_at": datetime.now(timezone.utc).isoformat()
            },
            headers={"X-Service-Key": settings.MODERATION_SERVICE_KEY}
        )

        assert response.status_code == 204
        db_session.refresh(product)
        assert product.status == Product.Status.HARD_BLOCKED
        assert product.moderator_comment == "Мошенничество"

        outbox_event = db_session.query(B2CCascadeOutbox).filter(
            B2CCascadeOutbox.product_id == product.id
        ).first()
        assert outbox_event is not None
        assert outbox_event.status == "pending"

    def test_hard_blocked_product_rejects_seller_edits(self, client, db_session, valid_jwt_with_fixed_id):
        """PUT/DELETE from seller on HARD_BLOCKED -> 403"""
        token, seller_id = valid_jwt_with_fixed_id

        product = Product(
            id=str(uuid4()),
            seller_id=seller_id,
            category_id=str(uuid4()),
            title="Hard Blocked Edit",
            slug="hard-blocked-edit",
            description="Description",
            status=Product.Status.HARD_BLOCKED,
            deleted=False,
            blocked=True,
            images=[],
            characteristics=[],
            skus=[]
        )
        db_session.add(product)
        db_session.commit()

        response = client.patch(
            f"/api/v1/products/{product.id}",
            json={"title": "Try to edit"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403

    def test_duplicate_event_same_idempotency_key_no_side_effects(self, client, db_session):
        """Duplicate event with same idempotency_key -> no changes"""
        product = Product(
            id=str(uuid4()),
            seller_id=str(uuid4()),
            category_id=str(uuid4()),
            title="Duplicate Test",
            slug="duplicate",
            description="Description",
            status=Product.Status.MODERATED,
            deleted=False,
            blocked=False,
            images=[],
            characteristics=[],
            skus=[]
        )
        db_session.add(product)
        db_session.commit()

        idempotency_key = str(uuid4())

        response1 = client.post(
            "/api/v1/moderation/events",
            json={
                "idempotency_key": idempotency_key,
                "product_id": str(product.id),
                "event_type": "BLOCKED",
                "hard_block": True,
                "moderator_comment": "Fraud",
                "blocking_reason_id": "reason-uuid-003",
                "occurred_at": datetime.now(timezone.utc).isoformat()
            },
            headers={"X-Service-Key": settings.MODERATION_SERVICE_KEY}
        )
        assert response1.status_code == 204

        response2 = client.post(
            "/api/v1/moderation/events",
            json={
                "idempotency_key": idempotency_key,
                "product_id": str(product.id),
                "event_type": "MODERATED",
                "occurred_at": datetime.now(timezone.utc).isoformat()
            },
            headers={"X-Service-Key": settings.MODERATION_SERVICE_KEY}
        )
        assert response2.status_code == 204
        assert response2.headers.get("X-Idempotent-Replay") == "true"

        db_session.refresh(product)
        assert product.status == Product.Status.HARD_BLOCKED

    def test_missing_service_key_returns_401(self, client, db_session):
        """No X-Service-Key -> 401"""
        response = client.post(
            "/api/v1/moderation/events",
            json={
                "idempotency_key": str(uuid4()),
                "product_id": str(uuid4()),
                "event_type": "MODERATED",
                "occurred_at": datetime.now(timezone.utc).isoformat()
            }
        )
        assert response.status_code == 401
