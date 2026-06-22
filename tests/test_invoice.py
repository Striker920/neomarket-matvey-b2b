# tests/test_invoice.py
import pytest
from uuid import uuid4
from datetime import datetime
from src.models.product import Product
from src.models.invoice import Invoice, InvoiceStatus


class TestInvoiceCreate:
    
    def test_create_invoice_with_moderated_sku_returns_201(self, client, db_session, valid_jwt_with_fixed_id):
        token, seller_id = valid_jwt_with_fixed_id
        
        sku_id = str(uuid4())
        product = Product(
            id=str(uuid4()),
            seller_id=seller_id,
            category_id=str(uuid4()),
            title="Test Product",
            slug="test-product",
            description="Test",
            status=Product.Status.MODERATED,
            images=[],
            characteristics=[],
            skus=[{
                "id": sku_id,
                "sku_code": "SKU001",
                "price": 10000,
                "stock_quantity": 10
            }]
        )
        db_session.add(product)
        db_session.commit()
        
        response = client.post(
            "/api/v1/invoices",
            json={
                "items": [
                    {"sku_id": sku_id, "quantity": 5}
                ]
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "PENDING"
        assert len(data["items"]) == 1
        assert data["items"][0]["sku_id"] == sku_id
        assert data["items"][0]["quantity"] == 5
        assert data["items"][0]["accepted_quantity"] is None
        
        invoice = db_session.query(Invoice).filter(Invoice.id == data["id"]).first()
        assert invoice is not None
        assert invoice.seller_id == seller_id
        assert invoice.status == InvoiceStatus.PENDING
    
    def test_empty_items_returns_400(self, client, valid_jwt_with_fixed_id):
        """Empty items → 400"""
        token, _ = valid_jwt_with_fixed_id
        
        response = client.post(
            "/api/v1/invoices",
            json={"items": []},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 422
    
    def test_non_moderated_sku_returns_400(self, client, db_session, valid_jwt_with_fixed_id):
        """SKU не-MODERATED товара → 400"""
        token, seller_id = valid_jwt_with_fixed_id
        
        sku_id = str(uuid4())
        product = Product(
            id=str(uuid4()),
            seller_id=seller_id,
            category_id=str(uuid4()),
            title="Test Product",
            slug="test-product",
            description="Test",
            status=Product.Status.CREATED,
            images=[],
            characteristics=[],
            skus=[{
                "id": sku_id,
                "sku_code": "SKU001",
                "price": 10000,
                "stock_quantity": 10
            }]
        )
        db_session.add(product)
        db_session.commit()
        
        response = client.post(
            "/api/v1/invoices",
            json={
                "items": [
                    {"sku_id": sku_id, "quantity": 5}
                ]
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "INVALID_REQUEST"
        assert "not MODERATED" in data["message"]
    
    def test_others_sku_returns_403(self, client, db_session, valid_jwt_with_fixed_id, valid_jwt):
        """SKU чужого продавца → 403"""
        token, owner_id = valid_jwt_with_fixed_id
        other_token = valid_jwt
        
        sku_id = str(uuid4())
        product = Product(
            id=str(uuid4()),
            seller_id=owner_id,
            category_id=str(uuid4()),
            title="Test Product",
            slug="test-product",
            description="Test",
            status=Product.Status.MODERATED,
            images=[],
            characteristics=[],
            skus=[{
                "id": sku_id,
                "sku_code": "SKU001",
                "price": 10000,
                "stock_quantity": 10
            }]
        )
        db_session.add(product)
        db_session.commit()
        
        response = client.post(
            "/api/v1/invoices",
            json={
                "items": [
                    {"sku_id": sku_id, "quantity": 5}
                ]
            },
            headers={"Authorization": f"Bearer {other_token}"}
        )
        
        assert response.status_code == 403
        data = response.json()
        assert data["code"] == "FORBIDDEN"
        assert "belongs to another seller" in data["message"]