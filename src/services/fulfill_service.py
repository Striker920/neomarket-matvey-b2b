from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from datetime import datetime
from src.models.product import Product
from src.models.fulfill_operation import FulfillOperation
from src.schemas.fulfill import FulfillRequest


class FulfillService:
    def __init__(self, db: Session):
        self.db = db

    def fulfill(self, request: FulfillRequest) -> dict:
        # 1. Проверка идемпотентности
        existing = self.db.query(FulfillOperation).filter(
            FulfillOperation.order_id == str(request.order_id)
        ).first()

        if existing:
            # Повторный запрос — возвращаем сохранённый результат
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

            # 2. Проверка наличия всех SKU
            missing_ids = set(sku_ids) - set(sku_map.keys())
            if missing_ids:
                self.db.rollback()
                return {
                    "code": "SKU_NOT_FOUND",
                    "message": f"SKU not found: {missing_ids}"
                }

            # 3. Проверка достаточности резерва
            for item in request.items:
                sku_key = str(item.sku_id)
                product, sku = sku_map[sku_key]
                reserved = sku.get("reserved_quantity", 0)
                if reserved < item.quantity:
                    self.db.rollback()
                    return {
                        "code": "INSUFFICIENT_RESERVATION",
                        "message": f"Cannot fulfill {item.quantity}, only {reserved} reserved"
                    }

            # 4. Списание резерва (active_quantity НЕ трогается)
            for item in request.items:
                sku_key = str(item.sku_id)
                product, sku = sku_map[sku_key]
                sku["reserved_quantity"] = sku.get("reserved_quantity", 0) - item.quantity
                flag_modified(product, "skus")

            # 5. Формируем ответ согласно b2b/openapi.yaml:1735-1741
            # <-- ИСПРАВЛЕНО: InventoryOrderResponse вместо {"ok": True}
            processed_at = datetime.utcnow().isoformat() + "Z"
            response_data = {
                "order_id": str(request.order_id),
                "status": "FULFILLED",
                "processed_at": processed_at
            }

            # 6. Записываем операцию идемпотентности с НОВОЙ формой ответа
            op = FulfillOperation(
                order_id=str(request.order_id),
                result=response_data
            )
            self.db.add(op)
            self.db.commit()
            return response_data

        except Exception as e:
            self.db.rollback()
            raise e