import pytest
from uuid import uuid4
from datetime import datetime

from src.models.product import Product
from src.config import settings


class TestB2CCatalog:

    def test_catalog_returns_moderated_in_stock_products(self, client, db_session):
        """MODERATED + deleted=false + active_quantity>0 → visible in catalog"""
        product = Product(
            id=str(uuid4()),
            seller_id=str(uuid4()),
            category_id=str(uuid4()),
            title="iPhone 15",
            slug="iphone-15",
            description="Smartphone",
            status=Product.Status.MODERATED,
            deleted=False,
            blocked=False,
            images=[{"url": "/s3/front.jpg", "ordering": 0}],
            characteristics=[{"name": "Brand", "value": "Apple"}],
            skus=[{
                "id": str(uuid4()),
                "sku_code": "SKU001",
                "price": 100000,
                "active_quantity": 5,
                "reserved_quantity": 2
            }]
        )
        db_session.add(product)
        db_session.commit()

        response = client.get(
            "/api/v1/products",
            headers={"X-Service-Key": settings.B2C_SERVICE_KEY}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) >= 1
        titles = [p["title"] for p in data["items"]]
        assert "iPhone 15" in titles

    def test_catalog_excludes_hard_blocked(self, client, db_session):
        """HARD_BLOCKED product → not in catalog"""
        product = Product(
            id=str(uuid4()),
            seller_id=str(uuid4()),
            category_id=str(uuid4()),
            title="Banned Product",
            slug="banned-product",
            description="Bad",
            status=Product.Status.HARD_BLOCKED,
            deleted=False,
            blocked=True,
            images=[{"url": "/s3/banned.jpg", "ordering": 0}],
            characteristics=[],
            skus=[{
                "id": str(uuid4()),
                "sku_code": "SKU002",
                "price": 10000,
                "active_quantity": 10
            }]
        )
        db_session.add(product)
        db_session.commit()

        response = client.get(
            "/api/v1/products",
            headers={"X-Service-Key": settings.B2C_SERVICE_KEY}
        )

        assert response.status_code == 200
        data = response.json()
        titles = [p["title"] for p in data["items"]]
        assert "Banned Product" not in titles

    def test_catalog_missing_service_key_returns_401(self, client, db_session):
        """No X-Service-Key → 401"""
        response = client.get("/api/v1/products")

        assert response.status_code == 401

    def test_catalog_response_has_no_cost_price(self, client, db_session):
        """B2C response must NOT contain cost_price or reserved_quantity"""
        product = Product(
            id=str(uuid4()),
            seller_id=str(uuid4()),
            category_id=str(uuid4()),
            title="Secret Product",
            slug="secret-product",
            description="Has secrets",
            status=Product.Status.MODERATED,
            deleted=False,
            blocked=False,
            images=[{"url": "/s3/secret.jpg", "ordering": 0}],
            characteristics=[],
            skus=[{
                "id": str(uuid4()),
                "sku_code": "SKU003",
                "price": 50000,
                "cost_price": 25000,
                "active_quantity": 3,
                "reserved_quantity": 7
            }]
        )
        db_session.add(product)
        db_session.commit()

        response = client.get(
            "/api/v1/products",
            headers={"X-Service-Key": settings.B2C_SERVICE_KEY}
        )

        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            if item["title"] == "Secret Product":
                for sku in item["skus"]:
                    assert "cost_price" not in sku
                    assert "reserved_quantity" not in sku
                break

    def test_batch_ids_returns_visible_subset(self, client, db_session):
        """?ids= returns only visible products, no 404 for hidden ones"""
        seller_id = str(uuid4())
        cat_id = str(uuid4())

        visible_product = Product(
            id=str(uuid4()),
            seller_id=seller_id,
            category_id=cat_id,
            title="Visible Product",
            slug="visible",
            description="Visible",
            status=Product.Status.MODERATED,
            deleted=False,
            blocked=False,
            images=[{"url": "/s3/vis.jpg", "ordering": 0}],
            characteristics=[],
            skus=[{
                "id": str(uuid4()),
                "sku_code": "SKU004",
                "price": 10000,
                "active_quantity": 1
            }]
        )
        hidden_product = Product(
            id=str(uuid4()),
            seller_id=seller_id,
            category_id=cat_id,
            title="Hidden Product",
            slug="hidden",
            description="Hidden",
            status=Product.Status.CREATED,
            deleted=False,
            blocked=False,
            images=[{"url": "/s3/hid.jpg", "ordering": 0}],
            characteristics=[],
            skus=[{
                "id": str(uuid4()),
                "sku_code": "SKU005",
                "price": 20000,
                "active_quantity": 1
            }]
        )
        deleted_product = Product(
            id=str(uuid4()),
            seller_id=seller_id,
            category_id=cat_id,
            title="Deleted Product",
            slug="deleted",
            description="Deleted",
            status=Product.Status.MODERATED,
            deleted=True,
            blocked=False,
            images=[],
            characteristics=[],
            skus=[]
        )
        db_session.add_all([visible_product, hidden_product, deleted_product])
        db_session.commit()

        ids_param = f"{visible_product.id},{hidden_product.id},{deleted_product.id}"
        response = client.get(
            f"/api/v1/products?ids={ids_param}",
            headers={"X-Service-Key": settings.B2C_SERVICE_KEY}
        )

        assert response.status_code == 200
        data = response.json()
        returned_ids = [item["id"] for item in data["items"]]
        assert str(visible_product.id) in returned_ids
        assert str(hidden_product.id) not in returned_ids
        assert str(deleted_product.id) not in returned_ids
