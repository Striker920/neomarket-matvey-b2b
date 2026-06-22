from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from src.models.product import Product
from src.models.fulfill_operation import FulfillOperation
from src.schemas.fulfill import FulfillRequest


class FulfillService:
    def __init__(self, db: Session):
        self.db = db

    def fulfill(self, request: FulfillRequest) -> dict:
        existing = self.db.query(FulfillOperation).filter(
            FulfillOperation.order_id == str(request.order_id)
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

            for item in request.items:
                sku_key = str(item.sku_id)
                product, sku = sku_map[sku_key]
                sku["reserved_quantity"] = sku.get("reserved_quantity", 0) - item.quantity
                flag_modified(product, "skus")

            response_data = {"ok": True}

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
