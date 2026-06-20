import pytest
from uuid import uuid4

from src.models.product import Product
from src.config import settings


class TestFulfill:

    def test_fulfill_decreases_reserved_quantity(self, client, db_session):
        """fulfill decreases reserved_quantity by specified amount"""
        sku_id = str(uuid4())
        product = Product(
            id=str(uuid4()),
            seller_id=str(uuid4()),
            category_id=str(uuid4()),
            title="Fulfill Test",
            slug="fulfill-test",
            description="Description",
            status=Product.Status.MODERATED,
            deleted=False,
            blocked=False,
            images=[],
            characteristics=[],
            skus=[{
                "id": sku_id,
                "sku_code": "SKU001",
                "price": 10000,
                "active_quantity": 7,
                "reserved_quantity": 3
            }]
        )
        db_session.add(product)
        db_session.commit()

        response = client.post(
            "/api/v1/fulfill",
            json={
                "order_id": str(uuid4()),
                "items": [{"sku_id": sku_id, "quantity": 2}]
            },
            headers={"X-Service-Key": settings.B2C_SERVICE_KEY}
        )

        assert response.status_code == 200
        assert response.json() == {"ok": True}

        db_session.refresh(product)
        assert product.skus[0]["reserved_quantity"] == 1

    def test_active_quantity_unchanged(self, client, db_session):
        """active_quantity does not change after fulfill"""
        sku_id = str(uuid4())
        product = Product(
            id=str(uuid4()),
            seller_id=str(uuid4()),
            category_id=str(uuid4()),
            title="Active Unchanged",
            slug="active-unchanged",
            description="Description",
            status=Product.Status.MODERATED,
            deleted=False,
            blocked=False,
            images=[],
            characteristics=[],
            skus=[{
                "id": sku_id,
                "sku_code": "SKU002",
                "price": 10000,
                "active_quantity": 7,
                "reserved_quantity": 3
            }]
        )
        db_session.add(product)
        db_session.commit()

        client.post(
            "/api/v1/fulfill",
            json={
                "order_id": str(uuid4()),
                "items": [{"sku_id": sku_id, "quantity": 2}]
            },
            headers={"X-Service-Key": settings.B2C_SERVICE_KEY}
        )

        db_session.refresh(product)
        assert product.skus[0]["active_quantity"] == 7

    def test_idempotent_fulfill_no_double_deduction(self, client, db_session):
        """Same order_id -> 200, no double deduction"""
        sku_id = str(uuid4())
        product = Product(
            id=str(uuid4()),
            seller_id=str(uuid4()),
            category_id=str(uuid4()),
            title="Idempotent Fulfill",
            slug="idempotent-fulfill",
            description="Description",
            status=Product.Status.MODERATED,
            deleted=False,
            blocked=False,
            images=[],
            characteristics=[],
            skus=[{
                "id": sku_id,
                "sku_code": "SKU003",
                "price": 10000,
                "active_quantity": 7,
                "reserved_quantity": 5
            }]
        )
        db_session.add(product)
        db_session.commit()

        order_id = str(uuid4())

        response1 = client.post(
            "/api/v1/fulfill",
            json={
                "order_id": order_id,
                "items": [{"sku_id": sku_id, "quantity": 3}]
            },
            headers={"X-Service-Key": settings.B2C_SERVICE_KEY}
        )
        assert response1.status_code == 200

        response2 = client.post(
            "/api/v1/fulfill",
            json={
                "order_id": order_id,
                "items": [{"sku_id": sku_id, "quantity": 3}]
            },
            headers={"X-Service-Key": settings.B2C_SERVICE_KEY}
        )
        assert response2.status_code == 200
        assert response2.json() == {"ok": True}

        db_session.refresh(product)
        assert product.skus[0]["reserved_quantity"] == 2
        assert product.skus[0]["active_quantity"] == 7

    def test_missing_service_key_returns_401(self, client, db_session):
        """No X-Service-Key -> 401"""
        response = client.post(
            "/api/v1/fulfill",
            json={
                "order_id": str(uuid4()),
                "items": [{"sku_id": str(uuid4()), "quantity": 1}]
            }
        )
        assert response.status_code == 401
