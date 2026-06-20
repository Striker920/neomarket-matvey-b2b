import pytest
from uuid import uuid4
from unittest.mock import patch

from src.models.product import Product


class TestProductEdit:
    
    def test_edit_moderated_product_returns_to_on_moderation(self, client, db_session, valid_jwt_with_fixed_id):
        token, seller_id = valid_jwt_with_fixed_id
        
        product = Product(
            id=str(uuid4()),
            seller_id=str(seller_id),
            category_id=str(uuid4()),
            title="Original Title",
            description="Original Description",
            status=Product.Status.MODERATED,
            images=[],
            slug="original-slug"
        )
        db_session.add(product)
        db_session.commit()
        
        with patch('src.services.event_service.send_edited_event') as mock_event:
            response = client.patch(
                f"/api/v1/products/{product.id}",
                json={
                    "title": "Updated Title",
                    "description": "Updated Description"
                },
                headers={"Authorization": f"Bearer {token}"}
            )
        
        assert response.status_code == 200
        db_session.refresh(product)
        assert product.status == Product.Status.ON_MODERATION
        assert product.title == "Updated Title"
        mock_event.assert_called_once()
    
    def test_edit_blocked_product_returns_to_on_moderation(self, client, db_session, valid_jwt_with_fixed_id):
        token, seller_id = valid_jwt_with_fixed_id
        
        product = Product(
            id=str(uuid4()),
            seller_id=str(seller_id),
            category_id=str(uuid4()),
            title="Blocked Product",
            description="Bad description",
            status=Product.Status.BLOCKED,
            blocked=True,
            moderator_comment="Bad photo quality",
            images=[],
            slug="blocked-product"
        )
        db_session.add(product)
        db_session.commit()
        
        with patch('src.services.event_service.send_edited_event') as mock_event:
            response = client.patch(
                f"/api/v1/products/{product.id}",
                json={
                    "title": "Fixed Title",
                    "description": "Fixed description"
                },
                headers={"Authorization": f"Bearer {token}"}
            )
        
        assert response.status_code == 200
        db_session.refresh(product)
        assert product.status == Product.Status.ON_MODERATION
        mock_event.assert_called_once()
    
    def test_edit_hard_blocked_returns_403(self, client, db_session, valid_jwt_with_fixed_id):
        token, seller_id = valid_jwt_with_fixed_id
        
        product = Product(
            id=str(uuid4()),
            seller_id=str(seller_id),
            category_id=str(uuid4()),
            title="Hard Blocked Product",
            description="Violation of terms",
            status=Product.Status.HARD_BLOCKED,
            blocked=True,
            images=[],
            slug="hard-blocked"
        )
        db_session.add(product)
        db_session.commit()
        
        response = client.patch(
            f"/api/v1/products/{product.id}",
            json={"title": "Try to edit"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403
    
    def test_edit_others_product_returns_403(self, client, db_session, valid_jwt_with_fixed_id, valid_jwt):
        token, seller_id = valid_jwt_with_fixed_id
        other_token = valid_jwt
        
        product = Product(
            id=str(uuid4()),
            seller_id=str(seller_id),
            category_id=str(uuid4()),
            title="Someone's Product",
            description="Original description",
            status=Product.Status.MODERATED,
            images=[],
            slug="someones-product"
        )
        db_session.add(product)
        db_session.commit()
        
        response = client.patch(
            f"/api/v1/products/{product.id}",
            json={"title": "Hijack Attempt"},
            headers={"Authorization": f"Bearer {other_token}"}
        )
        
        assert response.status_code == 403
    
    def test_edit_created_product_does_not_change_status(self, client, db_session, valid_jwt_with_fixed_id):
        token, seller_id = valid_jwt_with_fixed_id
        
        product = Product(
            id=str(uuid4()),
            seller_id=str(seller_id),
            category_id=str(uuid4()),
            title="Created Product",
            description="New product",
            status=Product.Status.CREATED,
            images=[],
            slug="created-product"
        )
        db_session.add(product)
        db_session.commit()
        
        response = client.patch(
            f"/api/v1/products/{product.id}",
            json={"description": "Updated description"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        db_session.refresh(product)
        assert product.status == Product.Status.CREATED