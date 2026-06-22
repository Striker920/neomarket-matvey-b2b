from sqlalchemy.orm import Session
from app.models.product import Product, SKU, ProductImage, ProductCharacteristic, BlockingReason, FieldReport
from app.models.category import Category  # ✅ Category в отдельном файле
from app.schemas.product import (
    ProductResponse, SKUResponse, ImageResponse, SKUImageResponse,
    CharacteristicValue, BlockingReasonResponse, FieldReportResponse
)


class ProductService:
    
    @staticmethod
    def build_seller_response(product: Product, db: Session) -> dict:
        """Построение ответа для продавца (с cost_price и reserved_quantity)"""
        return ProductService._build_response(product, db, include_sensitive=True)
    
    @staticmethod
    def build_service_response(product: Product, db: Session) -> dict:
        """Построение ответа для межсервисных вызовов (без sensitive полей)"""
        return ProductService._build_response(product, db, include_sensitive=False)
    
    @staticmethod
    def _build_response(product: Product, db: Session, include_sensitive: bool) -> dict:
        """Общая логика построения ответа"""
        
        # ✅ Изображения товара с id
        images = [
            ImageResponse(
                id=str(img.id),  # ✅ Добавлено
                url=img.url,
                ordering=img.ordering
            )
            for img in sorted(product.images, key=lambda x: x.ordering)
        ]

        # ✅ Характеристики товара с id
        characteristics = [
            CharacteristicValue(
                id=str(char.id),  # ✅ Добавлено
                name=char.name,
                value=char.value
            )
            for char in product.characteristics
        ]

        # ✅ SKU с полными полями
        skus = []
        for sku in product.skus:
            # Изображения SKU
            sku_images = []
            if hasattr(sku, 'images') and sku.images:
                sku_images = [
                    SKUImageResponse(
                        id=str(img.id),  # ✅ Добавлено
                        url=img.url,
                        ordering=img.ordering
                    )
                    for img in sku.images
                ]
            
            # Характеристики SKU
            sku_chars = [
                CharacteristicValue(
                    id=str(char.id),  # ✅ Добавлено
                    name=char.name,
                    value=char.value
                )
                for char in sku.characteristics
            ]

            sku_data = SKUResponse(
                id=str(sku.id),
                product_id=str(sku.product_id),  # ✅ Добавлено
                name=sku.name,
                price=sku.price,
                discount=sku.discount,
                cost_price=sku.cost_price if include_sensitive else None,  # Только seller
                stock_quantity=sku.stock_quantity if hasattr(sku, 'stock_quantity') else 0,  # ✅ Добавлено
                active_quantity=sku.active_quantity,
                reserved_quantity=sku.reserved_quantity if include_sensitive else 0,  # Только seller
                article=sku.article if hasattr(sku, 'article') else None,  # ✅ Добавлено
                images=sku_images,  # ✅ Заменено на images
                characteristics=sku_chars,
                created_at=sku.created_at.isoformat() if hasattr(sku, 'created_at') and sku.created_at else "",  # ✅ Добавлено
                updated_at=sku.updated_at.isoformat() if hasattr(sku, 'updated_at') and sku.updated_at else ""  # ✅ Добавлено
            )
            skus.append(sku_data)

        # ✅ Blocking reason и field_reports — только при BLOCKED
        blocking_reason = None
        field_reports = []
        
        if product.status == "BLOCKED" and product.blocking_reason:
            blocking_reason = BlockingReasonResponse(
                id=str(product.blocking_reason.id),
                title=product.blocking_reason.title,
                comment=product.blocking_reason.comment
            )
            
            # Загружаем field_reports для этого товара
            reports = db.query(FieldReport).filter(
                FieldReport.product_id == product.id
            ).all()
            
            field_reports = [
                FieldReportResponse(
                    field_name=report.field_name,
                    sku_id=str(report.sku_id) if report.sku_id else None,
                    comment=report.comment
                )
                for report in reports
            ]

        return {
            "id": str(product.id),
            "seller_id": str(product.seller_id),  # ✅ Добавлено
            "category_id": str(product.category_id),  # ✅ Добавлено (flat UUID)
            "title": product.title,
            "slug": product.slug if hasattr(product, 'slug') and product.slug else "",  # ✅ Добавлено
            "description": product.description,
            "status": product.status,
            "deleted": product.deleted,
            "blocked": product.status == "BLOCKED",
            "blocking_reason": blocking_reason,
            "field_reports": field_reports,
            "moderator_comment": product.moderator_comment if hasattr(product, 'moderator_comment') else None,
            "images": images,
            "characteristics": characteristics,
            "skus": skus,
            "created_at": product.created_at.isoformat() if hasattr(product, 'created_at') and product.created_at else "",  # ✅ Добавлено
            "updated_at": product.updated_at.isoformat() if hasattr(product, 'updated_at') and product.updated_at else ""  # ✅ Добавлено
        }