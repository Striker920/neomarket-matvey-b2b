from sqlalchemy.orm import Session
from fastapi import HTTPException
from src.models.product import Product
from src.models.category import Category
from src.schemas.product import ProductCreateRequest
from datetime import datetime
from sqlalchemy.orm.attributes import flag_modified
import uuid


class ProductService:
    def __init__(self, db: Session):
        self.db = db

    def _get_category_name(self, category_id: str) -> str:
        cat = self.db.query(Category).filter(Category.id == category_id).first()
        return cat.name if cat else "Unknown"

    def _format_category(self, product) -> dict:
        return {"id": product.category_id, "name": self._get_category_name(product.category_id)}
    
    def create_product(self, seller_id: str, product_data: ProductCreateRequest) -> Product:
        slug = product_data.slug or product_data.title.lower().replace(" ", "-")[:255]
        
        category_id_str = str(product_data.category_id)

        images_json = []
        for img in product_data.images:
            images_json.append({
                "id": str(img.id),
                "url": img.url,
                "ordering": img.ordering
            })
        
        characteristics_json = []
        if product_data.characteristics:
            for char in product_data.characteristics:
                characteristics_json.append({
                    "id": str(char.id),
                    "name": char.name,
                    "value": char.value
                })
        
        product = Product(
            seller_id=seller_id,
            category_id=category_id_str,
            title=product_data.title,
            slug=slug,
            description=product_data.description,
            status="CREATED",
            deleted=False,
            blocked=False,
            moderator_comment="",
            images=images_json,
            characteristics=characteristics_json,
            skus=[]
        )
        
        self.db.add(product)
        
        try:
            self.db.commit()
        except Exception as e:
            raise
        
        self.db.refresh(product)
        return {
            "id": product.id,
            "seller_id": product.seller_id,
            "title": product.title,
            "slug": product.slug,
            "description": product.description,
            "status": product.status,
            "deleted": product.deleted,
            "blocked": product.blocked,
            "category": self._format_category(product),
            "images": product.images,
            "characteristics": product.characteristics,
            "skus": [],
            "created_at": product.created_at,
            "updated_at": product.updated_at
        }
    
    def create_sku(self, seller_id: str, sku_data) -> dict:
        """Создание SKU для товара. Первый SKU переводит CREATED → ON_MODERATION."""
        from src.services.event_service import send_created_event, send_edited_event

        product = self.db.query(Product).filter(
            Product.id == str(sku_data.product_id)
        ).first()

        if not product:
            raise HTTPException(
                status_code=404,
                detail={"code": "NOT_FOUND", "message": "Product not found"}
            )

        if product.seller_id != seller_id:
            raise HTTPException(
                status_code=403,
                detail={"code": "FORBIDDEN", "message": "Not your product"}
            )

        if product.status == Product.Status.HARD_BLOCKED:
            raise HTTPException(
                status_code=403,
                detail={"code": "FORBIDDEN", "message": "Cannot add SKU to hard-blocked product"}
            )

        now_str = datetime.utcnow().isoformat()
        characteristics = []
        if sku_data.characteristics:
            for ch in sku_data.characteristics:
                characteristics.append({"name": ch.name, "value": ch.value})

        new_sku = {
            "id": str(uuid.uuid4()),
            "product_id": str(product.id),
            "name": sku_data.name,
            "price": sku_data.price,
            "cost_price": sku_data.cost_price,
            "discount": sku_data.discount,
            "image": sku_data.image,
            "active_quantity": 0,
            "reserved_quantity": 0,
            "sku_code": sku_data.name,
            "characteristics": characteristics,
            "created_at": now_str,
            "updated_at": now_str
        }

        if product.skus is None:
            product.skus = []

        existing_skus_count = len(product.skus)
        product.skus.append(new_sku)
        flag_modified(product, "skus")

        is_first_sku = existing_skus_count == 0 and product.status == Product.Status.CREATED
        is_post_moderated = product.status in [Product.Status.MODERATED, Product.Status.BLOCKED]

        if is_first_sku or is_post_moderated:
            product.status = Product.Status.ON_MODERATION
            product.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(product)

        if is_first_sku:
            send_created_event(
                product_id=str(product.id),
                seller_id=seller_id,
                sku=new_sku
            )
        elif is_post_moderated:
            send_edited_event(
                product_id=str(product.id),
                seller_id=seller_id,
                changes={"sku_added": new_sku["id"]}
            )

        return new_sku

    def update_product(self, product_id: str, seller_id: str, update_data: dict) -> Product:
        product = self.db.query(Product).filter(
            Product.id == product_id
        ).first()

        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        if product.seller_id != seller_id:
            raise HTTPException(status_code=403, detail="Access denied: you are not the owner of this product")

        if product.status == "HARD_BLOCKED":
            raise HTTPException(status_code=403, detail="Hard blocked product cannot be edited")

        old_status = product.status

        for key, value in update_data.items():
            if hasattr(product, key) and value is not None:
                if key == "category_id" and value:
                    value = str(value)
                elif key == "images" and value:
                    value = [{"id": str(img.id), "url": img.url, "ordering": img.ordering} for img in value]
                elif key == "characteristics" and value:
                    value = [{"id": str(char.id), "name": char.name, "value": char.value} for char in value]
                setattr(product, key, value)

        if old_status in ["MODERATED", "BLOCKED"]:
            product.status = "ON_MODERATION"

        product.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(product)
        
        return {
            "id": product.id,
            "seller_id": product.seller_id,
            "title": product.title,
            "slug": product.slug,
            "description": product.description,
            "status": product.status,
            "deleted": product.deleted,
            "blocked": product.blocked,
            "category": self._format_category(product),
            "images": product.images,
            "characteristics": product.characteristics,
            "skus": product.skus or [],
            "created_at": product.created_at,
            "updated_at": product.updated_at
        }
    
    def update_sku(self, sku_id: str, seller_id: str, update_data: dict) -> dict:
        from src.services.event_service import send_edited_event
        
        products = self.db.query(Product).filter(
            Product.seller_id == seller_id
        ).all()
        
        found_product = None
        sku_index = None
        original_reserved = None
        
        for prod in products:
            for i, sku in enumerate(prod.skus):
                if sku.get("id") == sku_id:
                    found_product = prod
                    sku_index = i
                    original_reserved = sku.get("reserved_quantity", 0)
                    break
            if found_product:
                break
        
        if not found_product:
            raise HTTPException(
                status_code=404,
                detail={"code": "SKU_NOT_FOUND", "message": "SKU not found"}
            )
        
        if found_product.status == "HARD_BLOCKED":
            raise HTTPException(
                status_code=403,
                detail={"code": "HARD_BLOCKED", "message": "Product is hard blocked"}
            )
        
        sku_to_update = found_product.skus[sku_index]
        
        if "sku_code" in update_data:
            sku_to_update["sku_code"] = update_data["sku_code"]
        if "price" in update_data:
            sku_to_update["price"] = update_data["price"]
        if "stock_quantity" in update_data:
            sku_to_update["stock_quantity"] = update_data["stock_quantity"]
        
        sku_to_update["reserved_quantity"] = original_reserved
        sku_to_update["updated_at"] = datetime.utcnow().isoformat()
        
        if "created_at" not in sku_to_update:
            sku_to_update["created_at"] = datetime.utcnow().isoformat()
        
        flag_modified(found_product, "skus")
        
        old_status = found_product.status
        if old_status in ["MODERATED", "BLOCKED"]:
            found_product.status = "ON_MODERATION"
            found_product.updated_at = datetime.utcnow()
        
        self.db.commit()
        
        result_sku = found_product.skus[sku_index].copy()
        result_sku["product_id"] = str(found_product.id)
        
        send_edited_event(
            product_id=str(found_product.id),
            seller_id=seller_id,
            changes=update_data
        )
        
        return result_sku
    
    def delete_product(self, product_id: str, seller_id: str) -> None:
        from src.services.event_service import send_deleted_event, send_product_deleted_to_b2c
        
        product = self.db.query(Product).filter(
            Product.id == product_id
        ).first()
        
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        if product.seller_id != seller_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        if product.deleted:
            raise HTTPException(
                status_code=400,
                detail={"code": "ALREADY_DELETED", "message": "Product already deleted"}
            )
        
        product.deleted = True
        self.db.commit()
        
        sku_ids = [sku.get("id") for sku in product.skus if sku.get("id")]
        
        send_deleted_event(product_id=product.id, seller_id=seller_id)
        send_product_deleted_to_b2c(product_id=product.id, sku_ids=sku_ids)

    def delete_sku(self, sku_id: str, seller_id: str) -> dict:
        """Delete SKU with guardrails: HARD_BLOCKED check, reserved_quantity check, side effects."""
        from src.services.event_service import send_deleted_event, send_event_to_b2c

        products = self.db.query(Product).filter(
            Product.deleted == False
        ).all()

        found_product = None
        sku_index = None

        for product in products:
            for i, sku in enumerate(product.skus or []):
                if str(sku.get("id")) == sku_id:
                    found_product = product
                    sku_index = i
                    break
            if found_product:
                break

        if not found_product:
            return {"code": "NOT_FOUND", "message": "SKU not found"}

        if found_product.seller_id != seller_id:
            return {"code": "NOT_OWNER", "message": "SKU does not belong to the authenticated seller"}

        if found_product.status == Product.Status.HARD_BLOCKED:
            return {"code": "FORBIDDEN", "message": "Cannot delete SKU of hard-blocked product"}

        sku = found_product.skus[sku_index]
        if sku.get("reserved_quantity", 0) > 0:
            return {"code": "CONFLICT", "message": "Cannot delete SKU with active reserves"}

        active_qty = sku.get("active_quantity", 0)
        product_was_on_moderation = found_product.status == Product.Status.ON_MODERATION
        product_is_moderated = found_product.status == Product.Status.MODERATED

        found_product.skus.pop(sku_index)
        flag_modified(found_product, "skus")

        if len(found_product.skus) == 0 and product_was_on_moderation:
            found_product.status = Product.Status.CREATED
            found_product.updated_at = datetime.utcnow()
            send_deleted_event(product_id=found_product.id, seller_id=seller_id)

        if active_qty > 0 and product_is_moderated:
            send_event_to_b2c(
                event_type="SKU_OUT_OF_STOCK",
                payload={
                    "sku_id": sku_id,
                    "product_id": str(found_product.id),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

        self.db.commit()
        return {"ok": True}

    def get_seller_products(self, seller_id: str, skip: int = 0, limit: int = 100) -> list[Product]:
        return self.db.query(Product).filter(
            Product.seller_id == seller_id,
            Product.deleted == False
        ).offset(skip).limit(limit).all()

    def get_seller_products_list(
        self,
        seller_id: str,
        limit: int = 20,
        offset: int = 0,
        status: str = None,
        search: str = None
    ) -> tuple[list[dict], int]:
        """Seller cabinet: all statuses, including deleted, with skus_count and total_active_quantity"""
        query = self.db.query(Product).filter(
            Product.seller_id == seller_id
        )

        if status:
            query = query.filter(Product.status == status)

        if search:
            search_filter = f"%{search}%"
            query = query.filter(Product.title.ilike(search_filter))

        total = query.count()
        products = query.order_by(Product.created_at.desc()).offset(offset).limit(limit).all()

        items = []
        for p in products:
            skus = p.skus or []
            items.append({
                "id": p.id,
                "title": p.title,
                "status": p.status,
                "category": self._format_category(p),
                "images": p.images,
                "characteristics": p.characteristics,
                "skus_count": len(skus),
                "total_active_quantity": sum(sku.get("active_quantity", 0) for sku in skus),
                "created_at": p.created_at
            })

        return items, total
    
    def get_product_by_id(self, product_id: str, seller_id: str, is_b2c_mode: bool = False) -> dict | None:
        """Получить товар с учётом режима доступа"""
        product = self.db.query(Product).filter(Product.id == product_id).first()
        
        if not product:
            return None
        
        # B2C режим: только опубликованные товары, без cost_price
        if is_b2c_mode:
            if product.status != Product.Status.MODERATED or product.deleted:
                return None
            return self._format_for_b2c(product)
        
        # Seller режим: проверяем владельца
        if product.seller_id != seller_id:
            return None
        
        return self._format_for_seller(product)

    def _format_for_seller(self, product: Product) -> dict:
        """Формат для продавца — полные данные + blocking_reason"""
        result = {
            "id": product.id,
            "seller_id": product.seller_id,
            "category_id": product.category_id,
            "title": product.title,
            "slug": product.slug,
            "description": product.description,
            "status": product.status,
            "deleted": product.deleted,
            "blocked": product.blocked,
            "blocking_reason_id": product.blocking_reason_id,
            "moderator_comment": product.moderator_comment,
            "images": product.images,
            "characteristics": product.characteristics,
            "skus": self._enrich_skus_for_seller(product.skus),
            "created_at": product.created_at,
            "updated_at": product.updated_at
        }
        
        # Добавляем причину блокировки, если статус BLOCKED
        if product.status == Product.Status.BLOCKED and product.blocked:
            blocking_info = self._get_blocking_info(product.id)
            if blocking_info:
                result["blocking_reason"] = blocking_info["reason"]
                result["field_reports"] = blocking_info["field_reports"]
        else:
            result["blocking_reason"] = None
            result["field_reports"] = None
        
        return result

    def _format_for_b2c(self, product: Product) -> dict:
        """Формат для B2C — только публичные поля"""
        public_skus = []
        for sku in product.skus:
            public_skus.append({
                "id": sku.get("id"),
                "sku_code": sku.get("sku_code"),
                "price": sku.get("price"),
                "stock_quantity": sku.get("stock_quantity", 0)
            })
        
        return {
            "id": product.id,
            "title": product.title,
            "slug": product.slug,
            "description": product.description,
            "images": product.images,
            "characteristics": product.characteristics,
            "skus": public_skus,
            "status": product.status
        }

    def _enrich_skus_for_seller(self, skus: list) -> list:
        """Добавляем cost_price и reserved_quantity для продавца"""
        enriched = []
        for sku in skus:
            enriched_sku = dict(sku)  # копируем
            enriched_sku["cost_price"] = sku.get("cost_price", 0)
            enriched_sku["reserved_quantity"] = sku.get("reserved_quantity", 0)
            enriched.append(enriched_sku)
        return enriched

    def get_catalog_products(
        self,
        limit: int = 20,
        offset: int = 0,
        category: str = None,
        search: str = None,
        sort: str = None,
        ids: list[str] = None
    ) -> tuple[list[dict], int]:
        """B2C catalog: only MODERATED, not deleted, at least one SKU with active_quantity > 0"""
        query = self.db.query(Product).filter(
            Product.status == Product.Status.MODERATED,
            Product.deleted == False
        )

        if ids:
            query = query.filter(Product.id.in_(ids))

        if category:
            query = query.filter(Product.category_id == category)

        if search:
            search_filter = f"%{search}%"
            query = query.filter(
                (Product.title.ilike(search_filter)) |
                (Product.description.ilike(search_filter))
            )

        all_products = query.all()

        visible = [p for p in all_products if self._has_active_sku(p)]

        if sort == "price_asc":
            visible.sort(key=lambda p: self._min_sku_price(p))
        elif sort == "price_desc":
            visible.sort(key=lambda p: self._min_sku_price(p), reverse=True)
        elif sort == "date_desc":
            visible.sort(key=lambda p: p.created_at or "", reverse=True)

        total = len(visible)
        paginated = visible[offset:offset + limit]

        return paginated, total

    def _min_sku_price(self, product: Product) -> float:
        """Get minimum price from active SKUs"""
        prices = [s.get("price", 0) for s in (product.skus or []) if s.get("active_quantity", 0) > 0]
        return min(prices) if prices else 0

    def _has_active_sku(self, product: Product) -> bool:
        """Check if at least one SKU has active_quantity > 0"""
        if not product.skus:
            return False
        return any(sku.get("active_quantity", 0) > 0 for sku in product.skus)

    def _format_for_catalog(self, product: Product) -> dict:
        """Format product for B2C catalog — no cost_price, no reserved_quantity"""
        public_skus = []
        for sku in product.skus:
            if sku.get("active_quantity", 0) > 0:
                public_skus.append({
                    "id": sku.get("id"),
                    "sku_code": sku.get("sku_code"),
                    "name": sku.get("name"),
                    "price": sku.get("price"),
                    "discount": sku.get("discount", 0),
                    "image": sku.get("image"),
                    "active_quantity": sku.get("active_quantity", 0),
                    "characteristics": sku.get("characteristics", [])
                })

        return {
            "id": product.id,
            "title": product.title,
            "description": product.description,
            "status": product.status,
            "category": self._format_category(product),
            "images": product.images,
            "characteristics": product.characteristics,
            "skus": public_skus
        }

    def _get_blocking_info(self, product_id: str) -> dict | None:
        """Получить информацию о блокировке товара"""
        from src.models.blocking import ProductBlocking, BlockingReason
        
        product_blocking = self.db.query(ProductBlocking).filter(
            ProductBlocking.product_id == product_id
        ).first()
        
        if not product_blocking:
            return None
        
        reason = self.db.query(BlockingReason).filter(
            BlockingReason.id == product_blocking.blocking_reason_id
        ).first()
        
        if not reason:
            return None
        
        return {
            "reason": {
                "id": reason.id,
                "title": reason.title,
                "description": reason.description
            },
            "field_reports": product_blocking.field_reports or []
        }