import httpx
import structlog
import uuid
from src.config import settings
from datetime import datetime

logger = structlog.get_logger(__name__)


def send_edited_event(product_id: str, seller_id: str, changes: dict, old_data: dict = None):
    """Событие PRODUCT_EDITED → Moderation Service"""
    try:
        with httpx.Client() as client:
            response = client.post(
                f"{settings.MODERATION_SERVICE_URL}/api/v1/b2b/events",
                json={
                    "event_type": "PRODUCT_EDITED",
                    "idempotency_key": str(uuid.uuid4()),
                    "occurred_at": datetime.utcnow().isoformat(),
                    "payload": {
                        "product_id": str(product_id),
                        "seller_id": str(seller_id),
                        "json_before": old_data or {},
                        "json_after": changes
                    }
                },
                timeout=5.0
            )
            response.raise_for_status()
            logger.info("product_edited_event_sent", product_id=product_id)
    except Exception as e:
        logger.error("failed_to_send_edited_event", product_id=product_id, error=str(e))


def send_deleted_event(product_id: str, seller_id: str) -> None:
    """Событие PRODUCT_DELETED → Moderation Service (при удалении товара)"""
    try:
        with httpx.Client() as client:
            response = client.post(
                f"{settings.MODERATION_SERVICE_URL}/api/v1/b2b/events",  # ✅ исправлено
                json={
                    "event_type": "PRODUCT_DELETED",  # ✅ исправлено
                    "idempotency_key": str(uuid.uuid4()),  # ✅ добавлено
                    "occurred_at": datetime.utcnow().isoformat(),  # ✅ добавлено
                    "payload": {  # ✅ обёрнуто в payload
                        "product_id": str(product_id)
                    }
                },
                timeout=5.0
            )
            response.raise_for_status()
            logger.info("product_deleted_event_sent", product_id=product_id)
    except Exception as e:
        logger.error("failed_to_send_deleted_event", product_id=product_id, error=str(e))


def send_product_deleted_to_b2c(product_id: str, sku_ids: list) -> None:
    """Событие PRODUCT_DELETED → B2C сервис (для очистки корзин)"""
    try:
        with httpx.Client() as client:
            response = client.post(
                f"{settings.B2C_SERVICE_URL}/api/v1/b2b/events",  # ✅ исправлен путь
                json={
                    "event_type": "PRODUCT_DELETED",  # ✅ добавлен event_type
                    "idempotency_key": str(uuid.uuid4()),  # ✅ добавлено
                    "occurred_at": datetime.utcnow().isoformat(),  # ✅ добавлено
                    "payload": {  # ✅ обёрнуто в payload
                        "product_id": str(product_id),
                        "sku_ids": sku_ids
                    }
                },
                timeout=5.0
            )
            response.raise_for_status()
            logger.info("product_deleted_b2c_event_sent", product_id=product_id, sku_count=len(sku_ids))
    except Exception as e:
        logger.error("failed_to_send_b2c_event", product_id=product_id, error=str(e))


def send_created_event(product_id: str, seller_id: str, sku: dict) -> None:
    """Событие CREATED → Moderation Service (при первом SKU)"""
    try:
        with httpx.Client() as client:
            response = client.post(
                f"{settings.MODERATION_SERVICE_URL}/api/v1/b2b/events",
                json={
                    "event_type": "CREATED",
                    "idempotency_key": str(uuid.uuid4()),
                    "occurred_at": datetime.utcnow().isoformat(),
                    "payload": {
                        "product_id": str(product_id),
                        "seller_id": str(seller_id),
                        "sku": sku
                    }
                },
                timeout=5.0
            )
            response.raise_for_status()
            logger.info("product_created_event_sent", product_id=product_id, sku_code=sku.get("sku_code"))
    except Exception as e:
        logger.error("failed_to_send_created_event", product_id=product_id, error=str(e))


def send_event_to_b2c(event_type: str, payload: dict) -> None:
    """Generic event sender to B2C service"""
    try:
        with httpx.Client() as client:
            response = client.post(
                f"{settings.B2C_SERVICE_URL}/api/v1/events",
                json={
                    "event_type": event_type,
                    "idempotency_key": str(uuid.uuid4()),
                    "occurred_at": datetime.utcnow().isoformat(),
                    "payload": payload
                },
                timeout=5.0
            )
            response.raise_for_status()
            logger.info("event_sent_to_b2c", event_type=event_type)
    except Exception as e:
        logger.error("failed_to_send_event_to_b2c", event_type=event_type, error=str(e))