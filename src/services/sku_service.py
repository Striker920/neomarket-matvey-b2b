from sqlalchemy.orm import Session
from sqlalchemy import func
from src.models.base import Product, SKU, SKUImage, ProductStatus, ModerationEventOutbox
from src.schemas.sku import SKUCreateRequest
import uuid

def create_sku(db: Session, data: SKUCreateRequest) -> dict:
    # 1. Проверка товара
    product = db.query(Product).filter(Product.id == data.product_id).with_for_update().first()
    if not product:
        raise ValueError("Товар не найден")
    
    # DoD: add_sku_to_hard_blocked_returns_403
    if product.status == ProductStatus.HARD_BLOCKED:
        raise PermissionError("Невозможно добавить SKU к товару с жёсткой блокировкой")
    
    if product.status in (ProductStatus.BLOCKED, ProductStatus.ARCHIVED):
        raise ValueError(f"Товар в статусе {product.status}")

    # 2. Создание SKU
    sku_id = str(uuid.uuid4())
    sku = SKU(
        id=sku_id,
        product_id=data.product_id,
        name=data.name,
        price=data.price,
        stock_quantity=data.stock_quantity,
        article=data.article
    )
    db.add(sku)
    db.flush()

    for img in data.images:
        db.add(SKUImage(id=str(uuid.uuid4()), sku_id=sku.id, url=img.url))

    # 3. Канонический flow: Это первый SKU?
    sku_count = db.query(func.count(SKU.id)).filter(SKU.product_id == data.product_id).scalar()
    triggered_moderation = False

    if sku_count == 1 and product.status == ProductStatus.DRAFT:
        product.status = ProductStatus.ON_MODERATION
        triggered_moderation = True
        
        # Outbox pattern (ADR)
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
    
    return {"sku": sku, "triggered_moderation": triggered_moderation}