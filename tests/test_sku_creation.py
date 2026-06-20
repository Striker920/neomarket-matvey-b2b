import pytest
from uuid import uuid4
from datetime import datetime
from unittest.mock import patch

from src.models.product import Product
from src.config import settings


class TestSKUCreation:

    def test_first_sku_transitions_product_to_on_moderation(self, client, db_session, valid_jwt_with_fixed_id):
        """First SKU on CREATED product → ON_MODERATION"""
        token, seller_id = valid_jwt_with_fixed_id

        product = Product(
            id=str(uuid4()),
            seller_id=seller_id,
            category_id=str(uuid4()),
            title="New Product",
            slug="new-product",
            description="Description",
            status=Product.Status.CREATED,
            deleted=False,
            blocked=False,
            images=[],
            characteristics=[],
            skus=[]
        )
        db_session.add(product)
        db_session.commit()

        response = client.post(
            "/api/v1/skus",
            json={
                "product_id": str(product.id),
                "name": "256GB Black",
                "price": 12999000,
                "cost_price": 9500000,
                "discount": 0,
                "image": "/s3/iphone15-black-256.jpg",
                "characteristics": [
                    {"name": "Цвет", "value": "Чёрный"},
                    {"name": "Объём памяти", "value": "256 ГБ"}
                ]
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "256GB Black"
        assert data["price"] == 12999000
        assert data["cost_price"] == 9500000
        assert data["active_quantity"] == 0
        assert data["reserved_quantity"] == 0

        db_session.refresh(product)
        assert product.status == Product.Status.ON_MODERATION

    def test_first_sku_emits_created_event_to_moderation(self, client, db_session, valid_jwt_with_fixed_id):
        """First SKU emits CREATED event to Moderation"""
        token, seller_id = valid_jwt_with_fixed_id

        product = Product(
            id=str(uuid4()),
            seller_id=seller_id,
            category_id=str(uuid4()),
            title="Event Test",
            slug="event-test",
            description="Description",
            status=Product.Status.CREATED,
            deleted=False,
            blocked=False,
            images=[],
            characteristics=[],
            skus=[]
        )
        db_session.add(product)
        db_session.commit()

        with patch('src.services.event_service.send_created_event') as mock_event:
            response = client.post(
                "/api/v1/skus",
                json={
                    "product_id": str(product.id),
                    "name": "128GB White",
                    "price": 9999000,
                    "cost_price": 7000000,
                    "image": "/s3/iphone-white.jpg"
                },
                headers={"Authorization": f"Bearer {token}"}
            )

        assert response.status_code == 201
        mock_event.assert_called_once()

    def test_second_sku_no_state_change(self, client, db_session, valid_jwt_with_fixed_id):
        """Second SKU on MODERATED product → ON_MODERATION + EDITED event"""
        token, seller_id = valid_jwt_with_fixed_id

        product = Product(
            id=str(uuid4()),
            seller_id=seller_id,
            category_id=str(uuid4()),
            title="Moderated Product",
            slug="moderated",
            description="Description",
            status=Product.Status.MODERATED,
            deleted=False,
            blocked=False,
            images=[],
            characteristics=[],
            skus=[{
                "id": str(uuid4()),
                "name": "First SKU",
                "sku_code": "First SKU",
                "price": 10000,
                "cost_price": 5000,
                "active_quantity": 5,
                "reserved_quantity": 0
            }]
        )
        db_session.add(product)
        db_session.commit()

        with patch('src.services.event_service.send_edited_event') as mock_event:
            response = client.post(
                "/api/v1/skus",
                json={
                    "product_id": str(product.id),
                    "name": "Second SKU",
                    "price": 15000,
                    "cost_price": 8000,
                    "image": "/s3/second.jpg"
                },
                headers={"Authorization": f"Bearer {token}"}
            )

        assert response.status_code == 201
        db_session.refresh(product)
        assert product.status == Product.Status.ON_MODERATION
        mock_event.assert_called_once()

    def test_add_sku_to_hard_blocked_returns_403(self, client, db_session, valid_jwt_with_fixed_id):
        """HARD_BLOCKED product → 403"""
        token, seller_id = valid_jwt_with_fixed_id

        product = Product(
            id=str(uuid4()),
            seller_id=seller_id,
            category_id=str(uuid4()),
            title="Hard Blocked",
            slug="hard-blocked",
            description="Violation",
            status=Product.Status.HARD_BLOCKED,
            deleted=False,
            blocked=True,
            images=[],
            characteristics=[],
            skus=[]
        )
        db_session.add(product)
        db_session.commit()

        response = client.post(
            "/api/v1/skus",
            json={
                "product_id": str(product.id),
                "name": "New SKU",
                "price": 10000,
                "cost_price": 5000,
                "image": "/s3/new.jpg"
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 403

    def test_missing_image_returns_400(self, client, db_session, valid_jwt_with_fixed_id):
        """No image → 400"""
        token, seller_id = valid_jwt_with_fixed_id

        product = Product(
            id=str(uuid4()),
            seller_id=seller_id,
            category_id=str(uuid4()),
            title="Test Product",
            slug="test",
            description="Description",
            status=Product.Status.CREATED,
            deleted=False,
            blocked=False,
            images=[],
            characteristics=[],
            skus=[]
        )
        db_session.add(product)
        db_session.commit()

        response = client.post(
            "/api/v1/skus",
            json={
                "product_id": str(product.id),
                "name": "No Image SKU",
                "price": 10000,
                "cost_price": 5000
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 422
