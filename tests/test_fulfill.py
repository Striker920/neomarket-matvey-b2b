import pytest
from uuid import uuid4
from datetime import datetime

from src.models.product import Product
from src.config import settings


class TestFulfill:

    def test_fulfill_decreases_reserved_quantity(self, client, db_session):
        """Happy path: fulfill decreases reserved_quantity, active_quantity unchanged"""
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
                "reserved_quantity": 10
            }]
        )
        db_session.add(product)
        db_session.commit()

        order_id = str(uuid4())
        response = client.post(
            "/api/v1/inventory/fulfill",
            json={
                "order_id": order_id,
                "items": [{"sku_id": sku_id, "quantity": 3}]
            },
            headers={"X-Service-Key": settings.B2C_SERVICE_KEY}
        )

        assert response.status_code == 200
        
        # <-- ИСПРАВЛЕНО: проверяем InventoryOrderResponse согласно b2b/openapi.yaml:1735-1741
        data = response.json()
        assert data["order_id"] == order_id
        assert data["status"] == "FULFILLED"
        assert "processed_at" in data
        
        # Проверяем формат ISO 8601
        processed_at = data["processed_at"]
        datetime.fromisoformat(processed_at.replace("Z", "+00:00"))

        db_session.refresh(product)
        sku = product.skus[0]
        assert sku["reserved_quantity"] == 7  # 10 - 3
        assert sku["active_quantity"] == 7  # не изменился

    def test_active_quantity_unchanged(self, client, db_session):
        """active_quantity does not change after fulfill"""
        sku_id = str(uuid4())
        product = Product(
            id=str(uuid4()),
            seller_id=str(uuid4()),
            category_id=str(uuid4()),
            title="Active Unchanged Test",
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
                "active_quantity": 5,
                "reserved_quantity": 10
            }]
        )
        db_session.add(product)
        db_session.commit()

        initial_active = product.skus[0]["active_quantity"]

        response = client.post(
            "/api/v1/inventory/fulfill",
            json={
                "order_id": str(uuid4()),
                "items": [{"sku_id": sku_id, "quantity": 5}]
            },
            headers={"X-Service-Key": settings.B2C_SERVICE_KEY}
        )

        assert response.status_code == 200
        
        # <-- ИСПРАВЛЕНО: проверяем InventoryOrderResponse
        data = response.json()
        assert data["status"] == "FULFILLED"
        assert "order_id" in data
        assert "processed_at" in data

        db_session.refresh(product)
        sku = product.skus[0]
        assert sku["active_quantity"] == initial_active  # не изменился
        assert sku["reserved_quantity"] == 5  # 10 - 5

    def test_idempotent_fulfill_no_double_deduction(self, client, db_session):
        """Same order_id -> 200 without double deduction"""
        sku_id = str(uuid4())
        product = Product(
            id=str(uuid4()),
            seller_id=str(uuid4()),
            category_id=str(uuid4()),
            title="Idempotent Fulfill Test",
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
                "active_quantity": 6,
                "reserved_quantity": 10
            }]
        )
        db_session.add(product)
        db_session.commit()

        order_id = str(uuid4())

        response1 = client.post(
            "/api/v1/inventory/fulfill",
            json={
                "order_id": order_id,
                "items": [{"sku_id": sku_id, "quantity": 4}]
            },
            headers={"X-Service-Key": settings.B2C_SERVICE_KEY}
        )
        assert response1.status_code == 200
        assert response1.json()["status"] == "FULFILLED"

        response2 = client.post(
            "/api/v1/inventory/fulfill",
            json={
                "order_id": order_id,
                "items": [{"sku_id": sku_id, "quantity": 4}]
            },
            headers={"X-Service-Key": settings.B2C_SERVICE_KEY}
        )
        assert response2.status_code == 200
        # <-- ИСПРАВЛЕНО: идемпотентный ответ должен совпадать с первым
        assert response2.json() == response1.json()
        assert response2.json()["status"] == "FULFILLED"
        assert response2.json()["order_id"] == order_id

        db_session.refresh(product)
        sku = product.skus[0]
        assert sku["reserved_quantity"] == 6  # 10 - 4 (не 10 - 4 - 4)
        assert sku["active_quantity"] == 6  # не изменился

    def test_missing_service_key_returns_401(self, client, db_session):
        """No X-Service-Key -> 401"""
        response = client.post(
            "/api/v1/inventory/fulfill",
            json={
                "order_id": str(uuid4()),
                "items": [{"sku_id": str(uuid4()), "quantity": 1}]
            }
        )
        assert response.status_code == 401

    def test_sku_not_found_returns_404(self, client, db_session):
        """Non-existent SKU -> 404"""
        response = client.post(
            "/api/v1/inventory/fulfill",
            json={
                "order_id": str(uuid4()),
                "items": [{"sku_id": str(uuid4()), "quantity": 1}]
            },
            headers={"X-Service-Key": settings.B2C_SERVICE_KEY}
        )
        assert response.status_code == 404
        data = response.json()
        assert data["code"] == "SKU_NOT_FOUND"

    def test_insufficient_reservation_returns_409(self, client, db_session):
        """Not enough reserved -> 409"""
        sku_id = str(uuid4())
        product = Product(
            id=str(uuid4()),
            seller_id=str(uuid4()),
            category_id=str(uuid4()),
            title="Insufficient Test",
            slug="insufficient-test",
            description="Description",
            status=Product.Status.MODERATED,
            deleted=False,
            blocked=False,
            images=[],
            characteristics=[],
            skus=[{
                "id": sku_id,
                "sku_code": "SKU004",
                "price": 10000,
                "active_quantity": 10,
                "reserved_quantity": 2  # мало резерва
            }]
        )
        db_session.add(product)
        db_session.commit()

        response = client.post(
            "/api/v1/inventory/fulfill",
            json={
                "order_id": str(uuid4()),
                "items": [{"sku_id": sku_id, "quantity": 5}]
            },
            headers={"X-Service-Key": settings.B2C_SERVICE_KEY}
        )
        assert response.status_code == 409
        data = response.json()
        assert data["code"] == "INSUFFICIENT_RESERVATION"