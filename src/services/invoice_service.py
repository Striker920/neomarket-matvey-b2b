# src/services/invoice_service.py
from sqlalchemy.orm import Session
from fastapi import HTTPException
from src.models.invoice import Invoice, InvoiceStatus
from src.models.product import Product
from uuid import uuid4
from datetime import datetime, timezone

class InvoiceService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_invoice(self, seller_id: str, items: list) -> Invoice:
        """
        Создание накладной с валидацией:
        1. Каждый SKU существует
        2. SKU принадлежит seller_id
        3. Товар SKU имеет статус MODERATED
        """
        if not items:
            raise ValueError("Items list cannot be empty")
        
        validated_items = []
        
        for item in items:
            sku_id = str(item.sku_id)
            quantity = item.quantity
            
            # Находим товар, содержащий этот SKU
            product = self._find_product_by_sku_id(sku_id)
            
            if not product:
                raise ValueError(f"SKU {sku_id} not found")
            
            # Проверка владельца
            if product.seller_id != seller_id:
                raise PermissionError(f"SKU {sku_id} belongs to another seller")
            
            # Проверка статуса товара
            if product.status != Product.Status.MODERATED:
                raise ValueError(f"Product for SKU {sku_id} is not MODERATED (status: {product.status})")
            
            # Проверяем, что SKU действительно существует в товаре
            sku_exists = False
            for sku in product.skus:
                if sku.get("id") == sku_id:
                    sku_exists = True
                    break
            
            if not sku_exists:
                raise ValueError(f"SKU {sku_id} not found in product {product.id}")
            
            validated_items.append({
                "sku_id": sku_id,
                "quantity": quantity,
                "accepted_quantity": None
            })
        
        now = datetime.now(timezone.utc)

        # Создаём накладную
        invoice = Invoice(
            id=str(uuid4()),
            seller_id=seller_id,
            status=InvoiceStatus.PENDING,
            items=validated_items,
            created_at=now,
            updated_at=now
        )
        
        self.db.add(invoice)
        self.db.commit()
        self.db.refresh(invoice)
        
        return invoice
    
    def _find_product_by_sku_id(self, sku_id: str) -> Product | None:
        """Ищет товар, содержащий SKU с указанным ID"""
        # Получаем все товары (в production добавить фильтр по seller_id для оптимизации)
        products = self.db.query(Product).all()
        for product in products:
            for sku in product.skus:
                if sku.get("id") == sku_id:
                    return product
        return None