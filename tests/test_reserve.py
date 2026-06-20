import pytest
from uuid import uuid4
from unittest.mock import patch

from src.models.product import Product
from src.config import settings


class TestReserve:

    def test_reserve_all_skus_succeeds(self, client, db_session):
        """Happy path: reserve succeeds, active_quantity decreases, reserved_quantity increases"""
        sku_id = str(uuid4())
        product = Product(
            id=str(uuid4()),
            seller_id=str(uuid4()),
            category_id=str(uuid4()),
            title="Reserve Test",
            slug="reserve-test",
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
                "active_quantity": 10,
                "reserved_quantity": 0
            }]
        )
        db_session.add(product)
        db_session.commit()

        response = client.post(
            "/api/v1/inventory/reserve",
            json={
                "idempotency_key": str(uuid4()),
                "order_id": str(uuid4()),
                "items": [{"sku_id": sku_id, "quantity": 3}]
            },
            headers={"X-Service-Key": settings.B2C_SERVICE_KEY}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["reserved"] is True
        assert len(data["items"]) == 1
        assert data["items"][0]["reserved_quantity"] == 3
        assert data["items"][0]["remaining_stock"] == 7

        db_session.refresh(product)
        sku = product.skus[0]
        assert sku["active_quantity"] == 7
        assert sku["reserved_quantity"] == 3

    def test_partial_insufficient_stock_returns_409_all_rollback(self, client, db_session):
        """One SKU insufficient -> 409, nothing reserved"""
        sku_id = str(uuid4())
        product = Product(
            id=str(uuid4()),
            seller_id=str(uuid4()),
            category_id=str(uuid4()),
            title="Insufficient Test",
            slug="insufficient",
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
                "active_quantity": 2,
                "reserved_quantity": 0
            }]
        )
        db_session.add(product)
        db_session.commit()

        response = client.post(
            "/api/v1/inventory/reserve",
            json={
                "idempotency_key": str(uuid4()),
                "order_id": str(uuid4()),
                "items": [{"sku_id": sku_id, "quantity": 5}]
            },
            headers={"X-Service-Key": settings.B2C_SERVICE_KEY}
        )

        assert response.status_code == 409
        data = response.json()
        assert data["code"] == "PARTIAL_INSUFFICIENT_STOCK"

        db_session.refresh(product)
        assert product.skus[0]["active_quantity"] == 2
        assert product.skus[0]["reserved_quantity"] == 0

    def test_idempotent_reserve_returns_200_without_double_deduction(self, client, db_session):
        """Same idempotency_key -> 200 without double deduction"""
        sku_id = str(uuid4())
        product = Product(
            id=str(uuid4()),
            seller_id=str(uuid4()),
            category_id=str(uuid4()),
            title="Idempotent Test",
            slug="idempotent",
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
                "active_quantity": 10,
                "reserved_quantity": 0
            }]
        )
        db_session.add(product)
        db_session.commit()

        idempotency_key = str(uuid4())

        response1 = client.post(
            "/api/v1/inventory/reserve",
            json={
                "idempotency_key": idempotency_key,
                "order_id": str(uuid4()),
                "items": [{"sku_id": sku_id, "quantity": 3}]
            },
            headers={"X-Service-Key": settings.B2C_SERVICE_KEY}
        )
        assert response1.status_code == 200

        response2 = client.post(
            "/api/v1/inventory/reserve",
            json={
                "idempotency_key": idempotency_key,
                "order_id": str(uuid4()),
                "items": [{"sku_id": sku_id, "quantity": 3}]
            },
            headers={"X-Service-Key": settings.B2C_SERVICE_KEY}
        )
        assert response2.status_code == 200
        assert response2.json() == response1.json()

        db_session.refresh(product)
        assert product.skus[0]["active_quantity"] == 7
        assert product.skus[0]["reserved_quantity"] == 3

    def test_sku_out_of_stock_event_emitted(self, client, db_session):
        """active_quantity becomes 0 -> SKU_OUT_OF_STOCK event emitted"""
        sku_id = str(uuid4())
        product = Product(
            id=str(uuid4()),
            seller_id=str(uuid4()),
            category_id=str(uuid4()),
            title="OutOfStock Test",
            slug="out-of-stock",
            description="Description",
            status=Product.Status.MODERATED,
            deleted=False,
            blocked=False,
            images=[],
            characteristics=[],
            skus=[{
                "id": sku_id,
                "sku_code": "SKU005",
                "price": 10000,
                "active_quantity": 3,
                "reserved_quantity": 0
            }]
        )
        db_session.add(product)
        db_session.commit()

        with patch('src.services.reserve_service.ReserveService._emit_out_of_stock_event') as mock_event:
            response = client.post(
                "/api/v1/inventory/reserve",
                json={
                    "idempotency_key": str(uuid4()),
                    "order_id": str(uuid4()),
                    "items": [{"sku_id": sku_id, "quantity": 3}]
                },
                headers={"X-Service-Key": settings.B2C_SERVICE_KEY}
            )

        assert response.status_code == 200
        mock_event.assert_called_once()

        db_session.refresh(product)
        assert product.skus[0]["active_quantity"] == 0
        assert product.skus[0]["reserved_quantity"] == 3

    def test_unreserve_restores_quantities(self, client, db_session):
        """Unreserve correctly restores active and reserved quantities"""
        sku_id = str(uuid4())
        product = Product(
            id=str(uuid4()),
            seller_id=str(uuid4()),
            category_id=str(uuid4()),
            title="Unreserve Test",
            slug="unreserve",
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
                "reserved_quantity": 0
            }]
        )
        db_session.add(product)
        db_session.commit()

        client.post(
            "/api/v1/inventory/reserve",
            json={
                "idempotency_key": str(uuid4()),
                "order_id": str(uuid4()),
                "items": [{"sku_id": sku_id, "quantity": 3}]
            },
            headers={"X-Service-Key": settings.B2C_SERVICE_KEY}
        )

        response = client.post(
            "/api/v1/inventory/unreserve",
            json={
                "order_id": str(uuid4()),
                "items": [{"sku_id": sku_id, "quantity": 2}]
            },
            headers={"X-Service-Key": settings.B2C_SERVICE_KEY}
        )

        assert response.status_code == 200
        assert response.json() == {"ok": True}

        db_session.refresh(product)
        assert product.skus[0]["active_quantity"] == 9
        assert product.skus[0]["reserved_quantity"] == 1

    def test_missing_service_key_returns_401(self, client, db_session):
        """No X-Service-Key -> 401"""
        response = client.post(
            "/api/v1/inventory/reserve",
            json={
                "idempotency_key": str(uuid4()),
                "order_id": str(uuid4()),
                "items": [{"sku_id": str(uuid4()), "quantity": 1}]
            }
        )
        assert response.status_code == 401
