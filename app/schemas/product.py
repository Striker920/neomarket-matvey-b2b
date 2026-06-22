from pydantic import BaseModel, UUID4
from typing import Optional, List
from datetime import datetime
from enum import Enum


class ProductStatus(str, Enum):
    CREATED = "CREATED"
    ON_MODERATION = "ON_MODERATION"
    MODERATED = "MODERATED"
    BLOCKED = "BLOCKED"
    HARD_BLOCKED = "HARD_BLOCKED"


# ============================================================
# Images
# ============================================================
class ImageResponse(BaseModel):
    """Изображение товара (по спецификации b2b/openapi.yaml:1259-1265)."""
    id: str  # ✅ Добавлено
    url: str
    ordering: int


class SKUImageResponse(BaseModel):
    """Изображение SKU."""
    id: str  # ✅ Добавлено
    url: str
    ordering: int


# ============================================================
# Characteristics
# ============================================================
class CharacteristicValue(BaseModel):
    """Значение характеристики (по спецификации b2b/openapi.yaml:1240-1246)."""
    id: str  # ✅ Добавлено
    name: str
    value: str


# ============================================================
# Blocking & Field Reports
# ============================================================
class BlockingReasonResponse(BaseModel):
    """Причина блокировки."""
    id: str
    title: str
    comment: Optional[str] = None


class FieldReportResponse(BaseModel):
    """Замечание по полю товара."""
    field_name: str
    sku_id: Optional[str] = None
    comment: str


# ============================================================
# SKU
# ============================================================
class SKUResponse(BaseModel):
    """SKU товара (по спецификации b2b/openapi.yaml:1488-1534)."""
    id: str
    product_id: str  # ✅ Добавлено
    name: str
    price: int
    discount: int = 0
    cost_price: Optional[int] = None  # Только в seller-режиме
    stock_quantity: int  # ✅ Добавлено
    active_quantity: int  # ✅ Добавлено
    reserved_quantity: int  # ✅ Добавлено (только в seller-режиме)
    article: Optional[str] = None  # ✅ Добавлено
    images: List[SKUImageResponse] = []  # ✅ Заменено на images (вместо image)
    characteristics: List[CharacteristicValue] = []
    created_at: str  # ✅ Добавлено
    updated_at: str  # ✅ Добавлено


# ============================================================
# Product
# ============================================================
class ProductResponse(BaseModel):
    """Товар (по спецификации b2b/openapi.yaml:1799-1815)."""
    id: str
    seller_id: str  # ✅ Добавлено
    category_id: str  # ✅ Добавлено (flat UUID, не объект)
    title: str
    slug: str  # ✅ Добавлено
    description: Optional[str] = None
    status: str
    deleted: bool
    blocked: bool
    blocking_reason: Optional[BlockingReasonResponse] = None  # Только при BLOCKED
    field_reports: List[FieldReportResponse] = []  # Только при BLOCKED
    moderator_comment: Optional[str] = None
    images: List[ImageResponse] = []
    characteristics: List[CharacteristicValue] = []
    skus: List[SKUResponse] = []
    created_at: str  # ✅ Добавлено
    updated_at: str  # ✅ Добавлено