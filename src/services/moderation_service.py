from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from src.models.base import Product, ProductStatus, ProcessedEvent, B2CCascadeOutbox
from src.schemas.moderation import ModerationEventRequest


def apply_moderation_decision(
    db: Session,
    payload: ModerationEventRequest,
    sender_service: str = "moderation"
) -> dict:
    existing_event = db.query(ProcessedEvent).filter(
        ProcessedEvent.idempotency_key == payload.idempotency_key,
        ProcessedEvent.sender_service == sender_service
    ).first()

    if existing_event:
        return {"status": "duplicate", "idempotency_key": payload.idempotency_key}

    product = db.query(Product).filter(Product.id == payload.product_id).with_for_update().first()
    if not product:
        raise ValueError(f"Товар {payload.product_id} не найден")

    if payload.event_type == "MODERATED":
        product.status = ProductStatus.MODERATED
        product.block_reason = None
        product.blocking_reason_id = None
        product.field_reports = None

    elif payload.event_type == "BLOCKED":
        if payload.hard_block:
            product.status = ProductStatus.HARD_BLOCKED
        else:
            product.status = ProductStatus.BLOCKED

        product.block_reason = payload.moderator_comment
        product.blocking_reason_id = payload.blocking_reason_id
        product.field_reports = [fr.model_dump() for fr in payload.field_reports] if payload.field_reports else None

        _emit_b2c_cascade(db, product.id, payload)

    db.add(ProcessedEvent(
        idempotency_key=payload.idempotency_key,
        sender_service=sender_service,
        event_type=payload.event_type
    ))

    try:
        db.commit()
        db.refresh(product)
    except IntegrityError:
        db.rollback()
        return {"status": "duplicate", "idempotency_key": payload.idempotency_key}

    return {
        "status": "success",
        "product_id": product.id,
        "new_status": product.status.value
    }


def _emit_b2c_cascade(db: Session, product_id: str, payload: ModerationEventRequest):
    cascade_payload = {
        "product_id": product_id,
        "event_type": "PRODUCT_BLOCKED",
        "hard_block": payload.hard_block,
        "blocking_reason_id": payload.blocking_reason_id,
        "occurred_at": payload.occurred_at.isoformat()
    }
    import uuid
    db.add(B2CCascadeOutbox(
        id=str(uuid.uuid4()),
        event_type="PRODUCT_BLOCKED",
        product_id=product_id,
        payload=cascade_payload
    ))


def update_product_by_seller(db: Session, product_id: str, seller_id: str, update_data: dict) -> dict:
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise ValueError("Товар не найден")

    if product.status == ProductStatus.HARD_BLOCKED:
        raise PermissionError("Невозможно редактировать товар с жёсткой блокировкой")

    if product.seller_id != seller_id:
        raise PermissionError("Нет прав на редактирование")

    return {"status": "updated"}