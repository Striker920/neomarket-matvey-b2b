import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from src.models.base import Product, SKU, SKUImage, SKUCharacteristic, ProductStatus, ModerationEventOutbox
from src.schemas.sku import SKUCreateRequest
from src.core.exceptions import AppError

def _get_product_snapshot(product: Product, sku_count: int) -> dict:
    """Снимок состояния товара для outbox payload"""
    return {
        "product_id": product.id,
        "seller_id": product.seller_id,
        "title": product.title,
        "status": product.status.value,
        "skus_count": sku_count
    }

def create_sku(db: Session, data: SKUCreateRequest, seller_id: str) -> dict:
    product = db.query(Product).filter(Product.id == data.product_id).with_for_update().first()
    if not product:
        raise AppError("PRODUCT_NOT_FOUND", "Товар не найден", 404)
    
    if product.seller_id != seller_id:
        raise AppError("FORBIDDEN", "Нет прав на управление этим товаром", 403)

    if product.status == ProductStatus.HARD_BLOCKED:
        raise AppError("HARD_BLOCKED", "Невозможно добавить SKU к товару с жёсткой блокировкой", 403)

    # Снимок ДО изменений (для PRODUCT_EDITED)
    sku_count_before = db.query(func.count(SKU.id)).filter(SKU.product_id == data.product_id).scalar()
    json_before = _get_product_snapshot(product, sku_count_before)

    sku_id = str(uuid.uuid4())
    sku = SKU(
        id=sku_id,
        product_id=data.product_id,
        name=data.name,
        price=data.price,
        stock_quantity=data.stock_quantity,
        article=data.article,
        discount=data.discount,
        cost_price=data.cost_price,
        reserved_quantity=0
    )
    db.add(sku)

    for idx, img in enumerate(data.images):
        db.add(SKUImage(id=str(uuid.uuid4()), sku_id=sku.id, url=img.url, ordering=img.ordering or idx))
    
    for char in data.characteristics:
        db.add(SKUCharacteristic(id=str(uuid.uuid4()), sku_id=sku.id, name=char.name, value=char.value))

    try:
        # ИСПРАВЛЕНО: используем sku_count_before + 1 вместо повторного COUNT
        sku_count_after = sku_count_before + 1
        
        triggered_moderation = False
        event_type = None
        json_after = None

        # Первый SKU: CREATED → ON_MODERATION + PRODUCT_CREATED
        if sku_count_after == 1 and product.status == ProductStatus.CREATED:
            product.status = ProductStatus.ON_MODERATION
            triggered_moderation = True
            event_type = "PRODUCT_CREATED"
            json_after = _get_product_snapshot(product, sku_count_after)
        
        # Re-moderation: MODERATED/BLOCKED → ON_MODERATION + PRODUCT_EDITED
        elif product.status in (ProductStatus.MODERATED, ProductStatus.BLOCKED):
            product.status = ProductStatus.ON_MODERATION
            triggered_moderation = True
            event_type = "PRODUCT_EDITED"
            json_after = _get_product_snapshot(product, sku_count_after)

        if event_type:
            payload = {
                "product_id": product.id,
                "seller_id": product.seller_id,
                "json_after": json_after
            }
            # ИСПРАВЛЕНО: правильный отступ — json_before только для PRODUCT_EDITED
            if event_type == "PRODUCT_EDITED":
                payload["json_before"] = json_before
            
            # ИСПРАВЛЕНО: детерминированный idempotency_key
            idempotency_key = f"sku-{sku_id}-{product.id}-{event_type}"
            
            db.add(ModerationEventOutbox(
                id=str(uuid.uuid4()),
                event_type=event_type,
                aggregate_id=product.id,
                payload=payload,
                idempotency_key=idempotency_key,
                occurred_at=datetime.utcnow()
            ))

        db.flush()
        db.refresh(sku)
    except IntegrityError:
        db.rollback()
        raise AppError("ARTICLE_ALREADY_EXISTS", "Товар с таким артикулом уже существует", 409)
    
    # Явный commit для сохранения изменений статуса товара и outbox-событий
    db.commit()
    
    return {
        "sku": sku,
        "triggered_moderation": triggered_moderation
    }