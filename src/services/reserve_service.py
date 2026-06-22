from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from datetime import datetime
from src.models.product import Product
from src.models.reserve_operation import ReserveOperation
from src.models.unreserve_operation import UnreserveOperation
from src.schemas.reserve import ReserveRequest, UnreserveRequest


class ReserveService:
    def __init__(self, db: Session):
        self.db = db

    def reserve(self, request: ReserveRequest) -> dict:
        existing = self.db.query(ReserveOperation).filter(
            ReserveOperation.idempotency_key == str(request.idempotency_key)
        ).first()

        if existing:
            return existing.result

        try:
            sku_ids = [str(item.sku_id) for item in request.items]

            products = self.db.query(Product).filter(
                Product.deleted == False
            ).all()

            sku_map = {}
            for product in products:
                for sku in (product.skus or []):
                    if str(sku.get("id")) in sku_ids:
                        sku_map[str(sku["id"])] = (product, sku)

            missing_ids = set(sku_ids) - set(sku_map.keys())
            if missing_ids:
                self.db.rollback()
                return {
                    "code": "SKU_NOT_FOUND",
                    "message": f"SKU not found: {missing_ids}"
                }

            failed_items = []
            for item in request.items:
                sku_key = str(item.sku_id)
                product, sku = sku_map[sku_key]
                active = sku.get("active_quantity", 0)
                if active < item.quantity:
                    failed_items.append({
                        "sku_id": sku_key,
                        "requested": item.quantity,
                        "available": active,
                        "reason": "INSUFFICIENT_STOCK"
                    })

            if failed_items:
                self.db.rollback()
                return {
                    "code": "PARTIAL_INSUFFICIENT_STOCK",
                    "message": "Some SKUs have insufficient stock",
                    "details": {"failed_items": failed_items}
                }

            for item in request.items:
                sku_key = str(item.sku_id)
                product, sku = sku_map[sku_key]
                sku["active_quantity"] = sku.get("active_quantity", 0) - item.quantity
                sku["reserved_quantity"] = sku.get("reserved_quantity", 0) + item.quantity
                flag_modified(product, "skus")

                if sku["active_quantity"] == 0:
                    self._emit_out_of_stock_event(sku)

            response_data = {
                "reserved": True,
                "items": [{
                    "sku_id": str(item.sku_id),
                    "reserved_quantity": item.quantity,
                    "remaining_stock": sku_map[str(item.sku_id)][1]["active_quantity"]
                } for item in request.items]
            }

            op = ReserveOperation(
                idempotency_key=str(request.idempotency_key),
                result=response_data
            )
            self.db.add(op)
            self.db.commit()
            return response_data

        except Exception as e:
            self.db.rollback()
            raise e

    def unreserve(self, request: UnreserveRequest) -> dict:
        existing = self.db.query(UnreserveOperation).filter(
            UnreserveOperation.order_id == str(request.order_id)
        ).first()

        if existing:
            return existing.result

        try:
            sku_ids = [str(item.sku_id) for item in request.items]

            products = self.db.query(Product).filter(
                Product.deleted == False
            ).all()

            sku_map = {}
            for product in products:
                for sku in (product.skus or []):
                    if str(sku.get("id")) in sku_ids:
                        sku_map[str(sku["id"])] = (product, sku)

            for item in request.items:
                sku_key = str(item.sku_id)
                if sku_key not in sku_map:
                    self.db.rollback()
                    return {
                        "code": "SKU_NOT_FOUND",
                        "message": f"SKU {sku_key} not found"
                    }
                _, sku = sku_map[sku_key]
                if sku.get("reserved_quantity", 0) < item.quantity:
                    self.db.rollback()
                    return {
                        "code": "INSUFFICIENT_RESERVATION",
                        "message": f"Cannot unreserve {item.quantity}, only {sku.get('reserved_quantity', 0)} reserved"
                    }

            for item in request.items:
                sku_key = str(item.sku_id)
                product, sku = sku_map[sku_key]
                sku["active_quantity"] = sku.get("active_quantity", 0) + item.quantity
                sku["reserved_quantity"] = sku.get("reserved_quantity", 0) - item.quantity
                flag_modified(product, "skus")

            response_data = {
                "ok": True
            }

            op = UnreserveOperation(
                order_id=str(request.order_id),
                result=response_data
            )
            self.db.add(op)
            self.db.commit()
            return response_data

        except Exception as e:
            self.db.rollback()
            raise e

    def _emit_out_of_stock_event(self, sku):
        from src.models.outbox_event import OutboxEvent

        event = OutboxEvent(
            event_type="SKU_OUT_OF_STOCK",
            aggregate_id=str(sku.get("id")),
            payload={
                "sku_id": str(sku.get("id")),
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        self.db.add(event)
