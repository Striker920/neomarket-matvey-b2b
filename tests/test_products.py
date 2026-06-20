import pytest
from fastapi.testclient import TestClient
from uuid import uuid4

from src.main import app


def test_create_product_returns_201_with_created_status(client, valid_jwt):
    response = client.post(
        "/api/v1/products",
        json={
            "title": "iPhone 15 Pro Max",
            "description": "Флагманский смартфон",
            "category_id": str(uuid4()),
            "images": [
                {"url": "/s3/front.jpg", "ordering": 0},
                {"url": "/s3/back.jpg", "ordering": 1}
            ],
            "characteristics": [
                {"name": "Бренд", "value": "Apple"}
            ]
        },
        headers={"Authorization": f"Bearer {valid_jwt}"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "CREATED"
    assert data["skus"] == []


def test_seller_id_taken_from_jwt(client, valid_jwt_with_fixed_id):
    token, expected_seller_id = valid_jwt_with_fixed_id
    
    response = client.post(
        "/api/v1/products",
        json={
            "title": "Test Product",
            "description": "Test Description",
            "category_id": str(uuid4()),
            "images": [{"url": "/s3/test.jpg", "ordering": 0}]
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 201
    assert response.json()["seller_id"] == expected_seller_id


def test_missing_images_returns_400(client, valid_jwt):
    response = client.post(
        "/api/v1/products",
        json={
            "title": "Test",
            "description": "Test",
            "category_id": str(uuid4())
        },
        headers={"Authorization": f"Bearer {valid_jwt}"}
    )
    
    assert response.status_code == 422


def test_missing_category_returns_400(client, valid_jwt):
    response = client.post(
        "/api/v1/products",
        json={
            "title": "Test",
            "description": "Test",
            "images": [{"url": "/s3/test.jpg", "ordering": 0}]
        },
        headers={"Authorization": f"Bearer {valid_jwt}"}
    )
    
    assert response.status_code == 422


def test_invalid_category_id_returns_400(client, valid_jwt):
    response = client.post(
        "/api/v1/products",
        json={
            "title": "Test",
            "description": "Test",
            "category_id": "not-a-uuid",
            "images": [{"url": "/s3/test.jpg", "ordering": 0}]
        },
        headers={"Authorization": f"Bearer {valid_jwt}"}
    )
    
    assert response.status_code == 422


def test_missing_auth_returns_401(client):
    response = client.post(
        "/api/v1/products",
        json={
            "title": "Test",
            "description": "Test",
            "category_id": str(uuid4()),
            "images": [{"url": "/s3/test.jpg", "ordering": 0}]
        }
    )
    
    assert response.status_code == 401