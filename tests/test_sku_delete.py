import pytest
from uuid import uuid4
from unittest.mock import patch

from src.models.product import Product
from src.config import settings


class TestDeleteSKU:

    def test_delete_sku_succeeds(self, client, db_session, valid_jwt_with_fixed_id):
        """Happy path: SKU deleted successfully"""
        token, seller_id = valid_jwt_with_fixed_id
        sku_id = str(uuid4())

        product = Product(
            id=str(uuid4()),
            seller_id=seller_id,
            category_id=str(uuid4()),
            title="Delete SKU Test",
            slug="delete-sku",
            description="Description",
            status=Product.Status.MODERATED,
            deleted=False,
            blocked=False,
            images=[],
            characteristics=[],
            skus=[
                {"id": sku_id, "sku_code": "SKU001", "price": 10000, "active_quantity": 5, "reserved_quantity": 0},
                {"id": str(uuid4()), "sku_code": "SKU002", "price": 20000, "active_quantity": 3, "reserved_quantity": 0}
            ]
        )
        db_session.add(product)
        db_session.commit()

        response = client.delete(
            f"/api/v1/skus/{sku_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert response.json() == {"ok": True}

        db_session.refresh(product)
        assert len(product.skus) == 1
        assert product.skus[0]["sku_code"] == "SKU002"

    def test_delete_sku_with_active_reserves_returns_409(self, client, db_session, valid_jwt_with_fixed_id):
        """reserved_quantity > 0 → 409"""
        token, seller_id = valid_jwt_with_fixed_id
        sku_id = str(uuid4())

        product = Product(
            id=str(uuid4()),
            seller_id=seller_id,
            category_id=str(uuid4()),
            title="Reserved SKU",
            slug="reserved",
            description="Description",
            status=Product.Status.MODERATED,
            deleted=False,
            blocked=False,
            images=[],
            characteristics=[],
            skus=[
                {"id": sku_id, "sku_code": "SKU001", "price": 10000, "active_quantity": 5, "reserved_quantity": 3}
            ]
        )
        db_session.add(product)
        db_session.commit()

        response = client.delete(
            f"/api/v1/skus/{sku_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 409
        assert response.json()["code"] == "CONFLICT"

    def test_last_sku_on_moderation_transitions_product_to_created(self, client, db_session, valid_jwt_with_fixed_id):
        """Last SKU removed + product ON_MODERATION → CREATED + DELETED event"""
        token, seller_id = valid_jwt_with_fixed_id
        sku_id = str(uuid4())

        product = Product(
            id=str(uuid4()),
            seller_id=seller_id,
            category_id=str(uuid4()),
            title="Last SKU",
            slug="last-sku",
            description="Description",
            status=Product.Status.ON_MODERATION,
            deleted=False,
            blocked=False,
            images=[],
            characteristics=[],
            skus=[
                {"id": sku_id, "sku_code": "SKU001", "price": 10000, "active_quantity": 0, "reserved_quantity": 0}
            ]
        )
        db_session.add(product)
        db_session.commit()

        with patch('src.services.event_service.send_deleted_event') as mock_event:
            response = client.delete(
                f"/api/v1/skus/{sku_id}",
                headers={"Authorization": f"Bearer {token}"}
            )

        assert response.status_code == 200
        db_session.refresh(product)
        assert product.status == Product.Status.CREATED
        assert len(product.skus) == 0
        mock_event.assert_called_once()

    def test_delete_sku_hard_blocked_product_returns_403(self, client, db_session, valid_jwt_with_fixed_id):
        """HARD_BLOCKED product → 403"""
        token, seller_id = valid_jwt_with_fixed_id
        sku_id = str(uuid4())

        product = Product(
            id=str(uuid4()),
            seller_id=seller_id,
            category_id=str(uuid4()),
            title="Hard Blocked",
            slug="hard-blocked",
            description="Description",
            status=Product.Status.HARD_BLOCKED,
            deleted=False,
            blocked=True,
            images=[],
            characteristics=[],
            skus=[
                {"id": sku_id, "sku_code": "SKU001", "price": 10000, "active_quantity": 5, "reserved_quantity": 0}
            ]
        )
        db_session.add(product)
        db_session.commit()

        response = client.delete(
            f"/api/v1/skus/{sku_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 403
        assert response.json()["code"] == "FORBIDDEN"

    def test_sku_out_of_stock_event_on_moderated_product(self, client, db_session, valid_jwt_with_fixed_id):
        """active_quantity > 0 + MODERATED → SKU_OUT_OF_STOCK event to B2C"""
        token, seller_id = valid_jwt_with_fixed_id
        sku_id = str(uuid4())

        product = Product(
            id=str(uuid4()),
            seller_id=seller_id,
            category_id=str(uuid4()),
            title="OutOfStock Test",
            slug="out-of-stock",
            description="Description",
            status=Product.Status.MODERATED,
            deleted=False,
            blocked=False,
            images=[],
            characteristics=[],
            skus=[
                {"id": sku_id, "sku_code": "SKU001", "price": 10000, "active_quantity": 5, "reserved_quantity": 0},
                {"id": str(uuid4()), "sku_code": "SKU002", "price": 20000, "active_quantity": 3, "reserved_quantity": 0}
            ]
        )
        db_session.add(product)
        db_session.commit()

        with patch('src.services.event_service.send_event_to_b2c') as mock_b2c:
            response = client.delete(
                f"/api/v1/skus/{sku_id}",
                headers={"Authorization": f"Bearer {token}"}
            )

        assert response.status_code == 200
        mock_b2c.assert_called_once()
        call_args = mock_b2c.call_args
        assert call_args[1]["event_type"] == "SKU_OUT_OF_STOCK"

    def test_delete_others_sku_returns_403(self, client, db_session, valid_jwt_with_fixed_id):
        """SKU belongs to another seller → 403"""
        token, seller_id = valid_jwt_with_fixed_id
        sku_id = str(uuid4())

        product = Product(
            id=str(uuid4()),
            seller_id=str(uuid4()),
            category_id=str(uuid4()),
            title="Others SKU",
            slug="others",
            description="Description",
            status=Product.Status.MODERATED,
            deleted=False,
            blocked=False,
            images=[],
            characteristics=[],
            skus=[
                {"id": sku_id, "sku_code": "SKU001", "price": 10000, "active_quantity": 5, "reserved_quantity": 0}
            ]
        )
        db_session.add(product)
        db_session.commit()

        response = client.delete(
            f"/api/v1/skus/{sku_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 403
        assert response.json()["code"] == "NOT_OWNER"

    def test_delete_nonexistent_sku_returns_404(self, client, db_session, valid_jwt_with_fixed_id):
        """SKU not found → 404"""
        token, _ = valid_jwt_with_fixed_id

        response = client.delete(
            f"/api/v1/skus/{str(uuid4())}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 404
        assert response.json()["code"] == "NOT_FOUND"
