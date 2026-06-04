import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from src.models.order import Order, OrderItem, OrderStatus
from src.schemas.order import OrderCreateRequest
from src.services.b2b_client import b2b_client, B2BUnavailableError, ReserveFailedError

class CartValidationError(Exception): pass

def process_checkout(db: Session, payload: OrderCreateRequest, idempotency_key: str, buyer_id: str) -> dict:
    existing_order = db.query(Order).filter(Order.idempotency_key == idempotency_key).first()
    if existing_order:
        return {"status": "idempotent", "order": existing_order}

    cart_items = _get_buyer_cart(buyer_id)
    if not cart_items:
        raise ValueError("Корзина пуста")

    if payload.items_snapshot:
        if not _validate_snapshot(cart_items, payload.items_snapshot):
            raise CartValidationError("Снапшот не соответствует текущей корзине")

    items_data = [{"sku_id": item["sku_id"], "quantity": item["quantity"]} for item in cart_items]
    
    try:
        reserve_result = b2b_client.reserve_skus(items_data, idempotency_key)
    except (B2BUnavailableError, ReserveFailedError):
        raise

    address = _get_address(payload.address_id, buyer_id)
    payment_method = _get_payment_method(payload.payment_method_id, buyer_id)

    subtotal = 0
    order_items_data = []
    
    for reserved_item in reserve_result["reserved_items"]:
        line_total = reserved_item["unit_price"] * reserved_item["quantity"]
        subtotal += line_total
        order_items_data.append({
            "sku_id": reserved_item["sku_id"],
            "product_id": reserved_item["product_id"],
            "name": f"{reserved_item['product_title']} - {reserved_item['sku_name']}",
            "sku_code": reserved_item.get("sku_code"),
            "quantity": reserved_item["quantity"],
            "unit_price": reserved_item["unit_price"],
            "line_total": line_total,
            "image_url": reserved_item.get("image_url")
        })

    delivery_cost = 0
    total = subtotal + delivery_cost
    order_id = str(uuid.uuid4())
    order_number = f"NM-2026-{order_id[:8].upper()}"
    now = datetime.utcnow().isoformat()
    
    order = Order(
        id=order_id, number=order_number, buyer_id=buyer_id, status=OrderStatus.PAID,
        idempotency_key=idempotency_key, address_snapshot=address, payment_method_snapshot=payment_method,
        subtotal=subtotal, delivery_cost=delivery_cost, total=total, comment=payload.comment,
        status_history=[
            {"status": OrderStatus.CREATED.value, "changed_at": now, "reason": None},
            {"status": OrderStatus.PAID.value, "changed_at": now, "reason": "Мок-оплата"}
        ],
        paid_at=datetime.utcnow()
    )
    db.add(order)
    db.flush()

    for item_data in order_items_data:
        db.add(OrderItem(id=str(uuid.uuid4()), order_id=order_id, **item_data))

    try:
        db.commit()
        db.refresh(order)
    except IntegrityError:
        db.rollback()
        existing_order = db.query(Order).filter(Order.idempotency_key == idempotency_key).first()
        if existing_order:
            return {"status": "idempotent", "order": existing_order}
        raise

    return {"status": "created", "order": order}

def _get_buyer_cart(buyer_id: str) -> list:
    return [{"sku_id": "sku-001", "quantity": 2, "unit_price": 299900}]

def _validate_snapshot(cart_items: list, snapshot: list) -> bool:
    if len(cart_items) != len(snapshot): return False
    cart_dict = {item["sku_id"]: item for item in cart_items}
    for snap_item in snapshot:
        cart_item = cart_dict.get(snap_item.sku_id)
        if not cart_item or cart_item["quantity"] != snap_item.quantity or cart_item["unit_price"] != snap_item.unit_price:
            return False
    return True

def _get_address(address_id: str, buyer_id: str) -> dict:
    return {"id": address_id, "country": "Россия", "city": "Москва", "street": "ул. Тестовая", "building": "1", "apartment": "10", "postal_code": "101000", "recipient_name": "Иван Иванов", "recipient_phone": "+79991234567", "created_at": datetime.utcnow().isoformat()}

def _get_payment_method(method_id: str, buyer_id: str) -> dict:
    return {"id": method_id, "type": "CARD", "card_last4": "1234", "card_brand": "VISA", "is_default": True, "created_at": datetime.utcnow().isoformat()}