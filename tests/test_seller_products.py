import pytest
from uuid import uuid4

from src.models.product import Product
from src.config import settings


class TestSellerProductsList:

    def test_list_returns_only_own_products(self, client, db_session, valid_jwt_with_fixed_id):
        """Only products with seller_id from JWT are returned"""
        token, seller_id = valid_jwt_with_fixed_id
        other_seller_id = str(uuid4())

        own_product = Product(
            id=str(uuid4()),
            seller_id=seller_id,
            category_id=str(uuid4()),
            title="Own Product",
            slug="own-product",
            description="My product",
            status=Product.Status.MODERATED,
            deleted=False,
            blocked=False,
            images=[],
            characteristics=[],
            skus=[{"id": str(uuid4()), "sku_code": "SKU001", "price": 10000, "active_quantity": 5}]
        )
        other_product = Product(
            id=str(uuid4()),
            seller_id=other_seller_id,
            category_id=str(uuid4()),
            title="Other Product",
            slug="other-product",
            description="Not mine",
            status=Product.Status.MODERATED,
            deleted=False,
            blocked=False,
            images=[],
            characteristics=[],
            skus=[]
        )
        db_session.add_all([own_product, other_product])
        db_session.commit()

        response = client.get(
            "/api/v1/products",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        titles = [item["title"] for item in data["items"]]
        assert "Own Product" in titles
        assert "Other Product" not in titles

    def test_idor_query_param_seller_id_ignored(self, client, db_session, valid_jwt_with_fixed_id):
        """?seller_id= in query does not change selection"""
        token, seller_id = valid_jwt_with_fixed_id
        other_seller_id = str(uuid4())

        own_product = Product(
            id=str(uuid4()),
            seller_id=seller_id,
            category_id=str(uuid4()),
            title="My Product",
            slug="my-product",
            description="Mine",
            status=Product.Status.MODERATED,
            deleted=False,
            blocked=False,
            images=[],
            characteristics=[],
            skus=[]
        )
        other_product = Product(
            id=str(uuid4()),
            seller_id=other_seller_id,
            category_id=str(uuid4()),
            title="Their Product",
            slug="their-product",
            description="Theirs",
            status=Product.Status.MODERATED,
            deleted=False,
            blocked=False,
            images=[],
            characteristics=[],
            skus=[]
        )
        db_session.add_all([own_product, other_product])
        db_session.commit()

        response = client.get(
            f"/api/v1/products?seller_id={other_seller_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        titles = [item["title"] for item in data["items"]]
        assert "My Product" in titles
        assert "Their Product" not in titles

    def test_deleted_products_visible_with_deleted_flag(self, client, db_session, valid_jwt_with_fixed_id):
        """Deleted products are visible with deleted=true"""
        token, seller_id = valid_jwt_with_fixed_id

        active_product = Product(
            id=str(uuid4()),
            seller_id=seller_id,
            category_id=str(uuid4()),
            title="Active Product",
            slug="active",
            description="Active",
            status=Product.Status.MODERATED,
            deleted=False,
            blocked=False,
            images=[],
            characteristics=[],
            skus=[]
        )
        deleted_product = Product(
            id=str(uuid4()),
            seller_id=seller_id,
            category_id=str(uuid4()),
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
        db_session.add_all([active_product, deleted_product])
        db_session.commit()

        response = client.get(
            "/api/v1/products",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        titles = [item["title"] for item in data["items"]]
        assert "Active Product" in titles
        assert "Deleted Product" in titles

    def test_status_filter_works_correctly(self, client, db_session, valid_jwt_with_fixed_id):
        """?status=BLOCKED returns only BLOCKED products"""
        token, seller_id = valid_jwt_with_fixed_id

        moderated_product = Product(
            id=str(uuid4()),
            seller_id=seller_id,
            category_id=str(uuid4()),
            title="Moderated Product",
            slug="moderated",
            description="Moderated",
            status=Product.Status.MODERATED,
            deleted=False,
            blocked=False,
            images=[],
            characteristics=[],
            skus=[]
        )
        blocked_product = Product(
            id=str(uuid4()),
            seller_id=seller_id,
            category_id=str(uuid4()),
            title="Blocked Product",
            slug="blocked",
            description="Blocked",
            status=Product.Status.BLOCKED,
            deleted=False,
            blocked=True,
            images=[],
            characteristics=[],
            skus=[]
        )
        db_session.add_all([moderated_product, blocked_product])
        db_session.commit()

        response = client.get(
            "/api/v1/products?status=BLOCKED",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        titles = [item["title"] for item in data["items"]]
        assert "Blocked Product" in titles
        assert "Moderated Product" not in titles

    def test_search_by_title_case_insensitive(self, client, db_session, valid_jwt_with_fixed_id):
        """Search by title is case insensitive"""
        token, seller_id = valid_jwt_with_fixed_id

        product = Product(
            id=str(uuid4()),
            seller_id=seller_id,
            category_id=str(uuid4()),
            title="iPhone 15 Pro",
            slug="iphone-15-pro",
            description="Smartphone",
            status=Product.Status.MODERATED,
            deleted=False,
            blocked=False,
            images=[],
            characteristics=[],
            skus=[]
        )
        db_session.add(product)
        db_session.commit()

        response = client.get(
            "/api/v1/products?search=iphone",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) >= 1
        assert data["items"][0]["title"] == "iPhone 15 Pro"

    def test_response_includes_skus_count_and_total_active_quantity(self, client, db_session, valid_jwt_with_fixed_id):
        """Response includes skus_count and total_active_quantity"""
        token, seller_id = valid_jwt_with_fixed_id

        sku_id_1 = str(uuid4())
        sku_id_2 = str(uuid4())
        product_id = str(uuid4())

        product = Product(
            id=product_id,
            seller_id=seller_id,
            category_id=str(uuid4()),
            title="Product with SKUs",
            slug="with-skus",
            description="Has SKUs",
            status=Product.Status.MODERATED,
            deleted=False,
            blocked=False,
            images=[],
            characteristics=[],
            skus=[
                {"id": sku_id_1, "sku_code": "SKU001", "price": 10000, "active_quantity": 10},
                {"id": sku_id_2, "sku_code": "SKU002", "price": 20000, "active_quantity": 5}
            ]
        )
        db_session.add(product)
        db_session.commit()

        response = client.get(
            "/api/v1/products",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()

        target_item = None
        for item in data["items"]:
            if item["id"] == product_id:
                target_item = item
                break

        assert target_item is not None
        assert target_item["skus_count"] == 2
        assert target_item["total_active_quantity"] == 15
