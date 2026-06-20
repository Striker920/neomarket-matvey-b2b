# tests/test_sku_edit.py
import pytest
from uuid import uuid4
from unittest.mock import patch
from datetime import datetime

from src.models.product import Product


class TestSKUEdit:
    
    def test_reserves_preserved_after_sku_edit(self, client, db_session, valid_jwt_with_fixed_id):
        token, seller_id = valid_jwt_with_fixed_id
        
        sku_id = str(uuid4())
        now = datetime.utcnow().isoformat()
        
        product = Product(
            id=str(uuid4()),
            seller_id=str(seller_id),
            category_id=str(uuid4()),
            title="Test Product",
            description="Test Description",
            status=Product.Status.MODERATED,
            deleted=False,
            images=[],
            slug="test-product",
            skus=[{
                "id": sku_id,
                "sku_code": "TEST001",
                "price": 100.0,
                "stock_quantity": 10,
                "reserved_quantity": 5,
                "created_at": now,
                "updated_at": now
            }]
        )
        db_session.add(product)
        db_session.commit()
        
        response = client.patch(
            f"/api/v1/skus/{sku_id}",
            json={
                "price": 150.0,
                "stock_quantity": 20
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        db_session.refresh(product)
        
        updated_sku = None
        for sku in product.skus:
            if sku["id"] == sku_id:
                updated_sku = sku
                break
        
        assert updated_sku is not None
        assert updated_sku["reserved_quantity"] == 5
        assert updated_sku["price"] == 150.0
        assert updated_sku["stock_quantity"] == 20
    
    def test_sku_edit_returns_product_to_moderation(self, client, db_session, valid_jwt_with_fixed_id):
        token, seller_id = valid_jwt_with_fixed_id
        
        sku_id = str(uuid4())
        now = datetime.utcnow().isoformat()  # ✅ текущая дата
        
        product = Product(
            id=str(uuid4()),
            seller_id=str(seller_id),
            category_id=str(uuid4()),
            title="Test Product",
            description="Test",
            status=Product.Status.MODERATED,
            deleted=False,
            images=[],
            slug="test",
            skus=[{
                "id": sku_id,
                "sku_code": "TEST002",
                "price": 100.0,
                "stock_quantity": 10,
                "reserved_quantity": 0,
                "created_at": now,
                "updated_at": now
            }]
        )
        db_session.add(product)
        db_session.commit()
        
        with patch('src.services.event_service.send_edited_event') as mock_event:
            response = client.patch(
                f"/api/v1/skus/{sku_id}",
                json={"price": 120.0},
                headers={"Authorization": f"Bearer {token}"}
            )
        
        assert response.status_code == 200
        db_session.refresh(product)
        assert product.status == Product.Status.ON_MODERATION
        mock_event.assert_called_once()