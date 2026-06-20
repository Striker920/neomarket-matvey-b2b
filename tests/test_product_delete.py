# tests/test_product_delete.py
import pytest
from uuid import uuid4
from unittest.mock import patch

from src.models.product import Product


class TestProductDelete:
    
    def test_delete_sets_deleted_true(self, client, db_session, valid_jwt_with_fixed_id):
        """Сценарий 1: delete_sets_deleted_true — поле deleted=true в БД"""
        token, seller_id = valid_jwt_with_fixed_id
        
        product = Product(
            id=str(uuid4()),
            seller_id=str(seller_id),
            category_id=str(uuid4()),
            title="Test Product",
            description="Test Description",
            status="MODERATED",
            deleted=False,
            images=[],
            slug="test-product"
        )
        db_session.add(product)
        db_session.commit()
        
        response = client.delete(
            f"/api/v1/products/{product.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        assert response.json() == {"ok": True}
        db_session.refresh(product)
        assert product.deleted == True
    
    def test_delete_emits_event_to_moderation(self, client, db_session, valid_jwt_with_fixed_id):
        """Сценарий 2: delete_emits_event_to_moderation — событие DELETED уходит в Moderation"""
        token, seller_id = valid_jwt_with_fixed_id
        
        product = Product(
            id=str(uuid4()),
            seller_id=str(seller_id),
            category_id=str(uuid4()),
            title="Test Product",
            description="Test Description",
            status="MODERATED",
            deleted=False,
            images=[],
            slug="test-product"
        )
        db_session.add(product)
        db_session.commit()
        
        with patch('src.services.event_service.send_deleted_event') as mock_event:
            response = client.delete(
                f"/api/v1/products/{product.id}",
                headers={"Authorization": f"Bearer {token}"}
            )
        
        assert response.status_code == 200
        mock_event.assert_called_once_with(
            product_id=product.id,
            seller_id=seller_id
        )
    
    def test_delete_emits_product_deleted_to_b2c(self, client, db_session, valid_jwt_with_fixed_id):
        """Сценарий 3: delete_emits_product_deleted_to_b2c — событие PRODUCT_DELETED уходит в B2C с sku_ids"""
        token, seller_id = valid_jwt_with_fixed_id
        
        sku_id = str(uuid4())
        product = Product(
            id=str(uuid4()),
            seller_id=str(seller_id),
            category_id=str(uuid4()),
            title="Test Product",
            description="Test Description",
            status="MODERATED",
            deleted=False,
            images=[],
            slug="test-product",
            skus=[{"id": sku_id, "sku_code": "TEST001", "price": 100}]
        )
        db_session.add(product)
        db_session.commit()
        
        with patch('src.services.event_service.send_product_deleted_to_b2c') as mock_event:
            response = client.delete(
                f"/api/v1/products/{product.id}",
                headers={"Authorization": f"Bearer {token}"}
            )
        
        assert response.status_code == 200
        mock_event.assert_called_once_with(
            product_id=product.id,
            sku_ids=[sku_id]
        )
    
    def test_delete_already_deleted_returns_400(self, client, db_session, valid_jwt_with_fixed_id):
        """Сценарий 4: delete_already_deleted_returns_400 — повторное удаление → 400"""
        token, seller_id = valid_jwt_with_fixed_id
        
        product = Product(
            id=str(uuid4()),
            seller_id=str(seller_id),
            category_id=str(uuid4()),
            title="Test Product",
            description="Test Description",
            status="MODERATED",
            deleted=True,  # уже удалён
            images=[],
            slug="test-product"
        )
        db_session.add(product)
        db_session.commit()
        
        response = client.delete(
            f"/api/v1/products/{product.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "ALREADY_DELETED"
    
    def test_delete_others_product_returns_403(self, client, db_session, valid_jwt_with_fixed_id, valid_jwt):
        """Сценарий 5: delete_others_product_returns_403 — удаление чужого товара → 403"""
        token, seller_id = valid_jwt_with_fixed_id
        other_token = valid_jwt
        
        product = Product(
            id=str(uuid4()),
            seller_id=str(seller_id),
            category_id=str(uuid4()),
            title="Someone's Product",
            description="Test",
            status="MODERATED",
            deleted=False,
            images=[],
            slug="someones-product"
        )
        db_session.add(product)
        db_session.commit()
        
        response = client.delete(
            f"/api/v1/products/{product.id}",
            headers={"Authorization": f"Bearer {other_token}"}
        )
        
        assert response.status_code == 403

    def test_deleted_product_not_in_seller_list(self, client, db_session, valid_jwt_with_fixed_id):
        """Deleted products are visible in seller list with deleted=true (canon B2B-11)"""
        token, seller_id = valid_jwt_with_fixed_id
        
        active_product = Product(
            id=str(uuid4()),
            seller_id=str(seller_id),
            category_id=str(uuid4()),
            title="Active Product",
            description="Should appear",
            status=Product.Status.MODERATED,
            deleted=False,
            images=[],
            slug="active-product"
        )
        db_session.add(active_product)
        
        deleted_product = Product(
            id=str(uuid4()),
            seller_id=str(seller_id),
            category_id=str(uuid4()),
            title="Deleted Product",
            description="Visible with deleted=true",
            status=Product.Status.MODERATED,
            deleted=True,
            images=[],
            slug="deleted-product"
        )
        db_session.add(deleted_product)
        db_session.commit()
        
        response = client.get(
            "/api/v1/products",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        products = response.json()
        product_titles = [p["title"] for p in products["items"]]
        
        assert "Active Product" in product_titles
        assert "Deleted Product" in product_titles