import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uuid
from datetime import datetime

from app.main import app
from app.core.database import Base, SessionLocal, get_db
from app.core.security import create_access_token
from app.models.product import Product, SKU, ProductImage, ProductCharacteristic, BlockingReason, FieldReport
from app.models.category import Category

# Тестовая БД
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# ✅ ИСПРАВЛЕНО: используем get_db вместо SessionLocal
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def seller_id():
    return str(uuid.uuid4())

@pytest.fixture
def auth_token(seller_id):
    return create_access_token(seller_id)

@pytest.fixture
def category_id():
    return str(uuid.uuid4())

@pytest.fixture
def blocking_reason_id():
    return str(uuid.uuid4())

def create_test_product(db, seller_id, category_id, status="MODERATED", blocked=False):
    # ✅ ИСПРАВЛЕНО: добавляем slug
    product = Product(
        id=uuid.uuid4(),
        seller_id=uuid.UUID(seller_id),
        category_id=uuid.UUID(category_id),
        title="Test Product",
        slug=f"test-product-{uuid.uuid4().hex[:8]}",  # ✅ Добавлено
        description="Test Description",
        status=status,
        deleted=False
    )
    db.add(product)
    db.flush()
    
    # SKU
    sku = SKU(
        id=uuid.uuid4(),
        product_id=product.id,
        name="Test SKU",
        price=10000,
        cost_price=5000,
        stock_quantity=10,  # ✅ Добавлено
        active_quantity=10,
        reserved_quantity=2
    )
    db.add(sku)
    db.flush()
    
    # Image
    image = ProductImage(
        id=uuid.uuid4(),
        product_id=product.id,
        url="/s3/test.jpg",
        ordering=0
    )
    db.add(image)
    
    # Characteristic
    char = ProductCharacteristic(
        id=uuid.uuid4(),
        product_id=product.id,
        name="Color",
        value="Black"
    )
    db.add(char)
    
    db.commit()
    return product, sku

def create_blocked_product_with_reports(db, seller_id, category_id, blocking_reason_id):
    # Создаем причину блокировки
    reason = BlockingReason(
        id=uuid.UUID(blocking_reason_id),
        title="Description mismatch",
        comment="Description doesn't match photos"
    )
    db.add(reason)
    db.flush()
    
    # ✅ ИСПРАВЛЕНО: добавляем slug
    product = Product(
        id=uuid.uuid4(),
        seller_id=uuid.UUID(seller_id),
        category_id=uuid.UUID(category_id),
        title="Blocked Product",
        slug=f"blocked-product-{uuid.uuid4().hex[:8]}",  # ✅ Добавлено
        description="Test Description",
        status="BLOCKED",
        deleted=False,
        blocking_reason_id=reason.id
    )
    db.add(product)
    db.flush()
    
    # SKU
    sku = SKU(
        id=uuid.uuid4(),
        product_id=product.id,
        name="Test SKU",
        price=10000,
        cost_price=5000,
        stock_quantity=0,  # ✅ Добавлено
        active_quantity=0,
        reserved_quantity=0
    )
    db.add(sku)
    db.flush()
    
    # Field reports
    report1 = FieldReport(
        id=uuid.uuid4(),
        product_id=product.id,
        field_name="description",
        sku_id=None,
        comment="Material mismatch: leather vs synthetic"
    )
    db.add(report1)
    
    report2 = FieldReport(
        id=uuid.uuid4(),
        product_id=product.id,
        field_name="sku_image",
        sku_id=sku.id,
        comment="SKU photo doesn't match color"
    )
    db.add(report2)
    
    db.commit()
    return product, sku, reason

def test_get_moderated_product_returns_full_payload(setup_db, seller_id, auth_token, category_id):
    """Тест сценария: MODERATED - полный ответ с полями"""
    db = next(override_get_db())
    
    # Создаем категорию
    category = Category(id=uuid.UUID(category_id), name="Test Category")
    db.add(category)
    db.commit()
    
    # Создаем товар
    product, sku = create_test_product(db, seller_id, category_id, "MODERATED")
    
    response = client.get(
        f"/api/v1/products/{product.id}",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Проверяем основные поля
    assert data["id"] == str(product.id)
    assert data["title"] == "Test Product"
    assert data["status"] == "MODERATED"
    assert data["blocked"] == False
    assert data["blocking_reason"] == None
    assert data["field_reports"] == []
    
    # Проверяем SKU с sensitive полями
    assert len(data["skus"]) == 1
    sku_data = data["skus"][0]
    assert sku_data["cost_price"] == 5000
    assert sku_data["reserved_quantity"] == 2
    assert sku_data["active_quantity"] == 10
    
    # Проверяем изображения и характеристики
    assert len(data["images"]) == 1
    assert data["images"][0]["url"] == "/s3/test.jpg"
    assert len(data["characteristics"]) == 1
    assert data["characteristics"][0]["name"] == "Color"
    
    # ✅ Проверяем новые обязательные поля
    assert data["seller_id"] == seller_id
    assert data["category_id"] == category_id
    assert "slug" in data
    assert "created_at" in data
    assert "updated_at" in data
    
    # ✅ Проверяем SKU с новыми полями
    assert sku_data["product_id"] == str(product.id)
    assert "stock_quantity" in sku_data
    assert "images" in sku_data
    assert "created_at" in sku_data
    assert "updated_at" in sku_data

def test_get_blocked_product_returns_blocking_reason_and_field_reports(setup_db, seller_id, auth_token, category_id, blocking_reason_id):
    """Тест сценария: BLOCKED - возвращает причину блокировки и замечания"""
    db = next(override_get_db())
    
    # Создаем категорию
    category = Category(id=uuid.UUID(category_id), name="Test Category")
    db.add(category)
    db.commit()
    
    # Создаем заблокированный товар
    product, sku, reason = create_blocked_product_with_reports(db, seller_id, category_id, blocking_reason_id)
    
    response = client.get(
        f"/api/v1/products/{product.id}",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Проверяем статус
    assert data["status"] == "BLOCKED"
    assert data["blocked"] == True
    
    # Проверяем причину блокировки
    assert data["blocking_reason"] is not None
    assert data["blocking_reason"]["id"] == blocking_reason_id
    assert data["blocking_reason"]["title"] == "Description mismatch"
    assert data["blocking_reason"]["comment"] == "Description doesn't match photos"
    
    # Проверяем замечания по полям
    assert len(data["field_reports"]) == 2
    assert data["field_reports"][0]["field_name"] == "description"
    assert data["field_reports"][0]["sku_id"] is None
    assert data["field_reports"][0]["comment"] == "Material mismatch: leather vs synthetic"
    
    assert data["field_reports"][1]["field_name"] == "sku_image"
    assert data["field_reports"][1]["sku_id"] == str(sku.id)
    assert data["field_reports"][1]["comment"] == "SKU photo doesn't match color"

def test_get_others_product_returns_404(setup_db, seller_id, auth_token, category_id):
    """Тест сценария: чужой товар → 404"""
    db = next(override_get_db())
    
    # Создаем другого продавца
    other_seller_id = str(uuid.uuid4())
    
    # Создаем категорию
    category = Category(id=uuid.UUID(category_id), name="Test Category")
    db.add(category)
    db.commit()
    
    # Создаем товар другого продавца
    product, sku = create_test_product(db, other_seller_id, category_id, "MODERATED")
    
    response = client.get(
        f"/api/v1/products/{product.id}",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 404
    data = response.json()
    # ✅ После добавления exception handler — плоский формат
    assert data["code"] == "NOT_FOUND"
    assert "Product not found" in data["message"]

def test_get_nonexistent_returns_404(setup_db, seller_id, auth_token):
    """Тест сценария: несуществующий ID → 404"""
    nonexistent_id = str(uuid.uuid4())
    
    response = client.get(
        f"/api/v1/products/{nonexistent_id}",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 404
    data = response.json()
    # ✅ После добавления exception handler — плоский формат
    assert data["code"] == "NOT_FOUND"
    assert "Product not found" in data["message"]

def test_invalid_uuid_returns_400(setup_db, seller_id, auth_token):
    """Тест: невалидный UUID → 400"""
    response = client.get(
        "/api/v1/products/invalid-uuid",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 400
    data = response.json()
    assert data["code"] == "INVALID_REQUEST"

def test_service_call_with_x_service_key(setup_db, seller_id, category_id):
    """Тест: межсервисный вызов с X-Service-Key"""
    db = next(override_get_db())
    
    # Создаем категорию
    category = Category(id=uuid.UUID(category_id), name="Test Category")
    db.add(category)
    db.commit()
    
    # Создаем товар
    product, sku = create_test_product(db, seller_id, category_id, "MODERATED")
    
    response = client.get(
        f"/api/v1/products/{product.id}",
        headers={"X-Service-Key": "moderation-service-secret-key"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Проверяем, что sensitive поля отсутствуют
    assert len(data["skus"]) == 1
    sku_data = data["skus"][0]
    assert "cost_price" not in sku_data or sku_data["cost_price"] is None
    assert sku_data["reserved_quantity"] == 0  # В service-режиме reserved_quantity = 0