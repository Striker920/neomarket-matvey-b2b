import uuid
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from src.models.product import Product
from src.models.processed_event import ProcessedEvent
from src.models.b2c_cascade_outbox import B2CCascadeOutbox
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

    product = db.query(Product).filter(Product.id == payload.product_id).first()
    if not product:
        raise ValueError(f"Товар {payload.product_id} не найден")

    if payload.event_type == "MODERATED":
        product.status = Product.Status.MODERATED
        product.blocked = False
        product.blocking_reason_id = ""
        product.moderator_comment = ""

    elif payload.event_type == "BLOCKED":
        if payload.hard_block:
            product.status = Product.Status.HARD_BLOCKED
        else:
            product.status = Product.Status.BLOCKED

        product.blocked = True
        product.moderator_comment = payload.moderator_comment or ""
        product.blocking_reason_id = payload.blocking_reason_id or ""

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
        "new_status": product.status
    }


def _emit_b2c_cascade(db: Session, product_id: str, payload: ModerationEventRequest):
    cascade_payload = {
        "product_id": product_id,
        "event_type": "PRODUCT_BLOCKED",
        "hard_block": payload.hard_block,
        "blocking_reason_id": payload.blocking_reason_id,
        "occurred_at": payload.occurred_at.isoformat()
    }
    db.add(B2CCascadeOutbox(
        id=str(uuid.uuid4()),
        event_type="PRODUCT_BLOCKED",
        product_id=product_id,
        payload=cascade_payload,
        status="pending"
    ))
