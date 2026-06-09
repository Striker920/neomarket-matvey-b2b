import uuid
from sqlalchemy.orm import Session
from sqlalchemy import func
from src.models.base import Product, SKU, SKUImage, SKUCharacteristic, ProductStatus, SKUStatus, ModerationEventOutbox
from src.schemas.sku import SKUCreateRequest
from src.core.exceptions import AppError

def create_sku(db: Session, data: SKUCreateRequest, seller_id: str) -> dict:
    # 1. Проверка существования товара (404)
    product = db.query(Product).filter(Product.id == data.product_id).with_for_update().first()
    if not product:
        raise AppError("PRODUCT_NOT_FOUND", "Товар не найден", 404)
    
    # 2. Проверка владельца (403)
    if product.seller_id != seller_id:
        raise AppError("FORBIDDEN", "Нет прав на управление этим товаром", 403)

    # 3. Проверка на жесткую блокировку (403)
    if product.status == ProductStatus.HARD_BLOCKED:
        raise AppError("HARD_BLOCKED", "Невозможно добавить SKU к товару с жёсткой блокировкой", 403)
    
    if product.status in (ProductStatus.BLOCKED, ProductStatus.ARCHIVED):
        raise AppError("INVALID_STATUS", f"Невозможно добавить SKU к товару в статусе {product.status}", 400)

    # 4. Создание SKU
    sku_id = str(uuid.uuid4())
    sku = SKU(
        id=sku_id,
        product_id=data.product_id,
        name=data.name,
        price=data.price,
        stock_quantity=data.stock_quantity,
        article=data.article,
        status=SKUStatus.ACTIVE
    )
    db.add(sku)
    db.flush()

    for img in data.images:
        db.add(SKUImage(id=str(uuid.uuid4()), sku_id=sku.id, url=img.url))
    
    for char in data.characteristics:
        db.add(SKUCharacteristic(id=str(uuid.uuid4()), sku_id=sku.id, name=char.name, value=char.value))

    # 5. Логика перехода в модерацию
    sku_count = db.query(func.count(SKU.id)).filter(SKU.product_id == data.product_id).scalar()
    triggered_moderation = False

    if sku_count == 1 and product.status == ProductStatus.DRAFT:
        product.status = ProductStatus.ON_MODERATION
        triggered_moderation = True
        
        event_payload = {
            "event_type": "product.created",
            "product_id": product.id,
            "seller_id": product.seller_id,
            "title": product.title,
            "first_sku": {"sku_id": sku.id, "name": sku.name, "price": sku.price},
            "images": [img.url for img in sku.images]
        }
        db.add(ModerationEventOutbox(
            id=str(uuid.uuid4()),
            event_type="product.created",
            aggregate_id=product.id,
            payload=event_payload,
            idempotency_key=f"sku-created-{sku.id}"
        ))

    db.commit()
    db.refresh(sku)
    
    return {
        "sku": sku,
        "triggered_moderation": triggered_moderation
    }