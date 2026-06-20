from pydantic import BaseModel, Field
from typing import List, Optional, Any
from uuid import UUID
from datetime import datetime


class SellerProductItem(BaseModel):
    id: UUID
    title: str
    status: str
    category: Optional[dict] = None
    images: List[Any] = []
    skus_count: int = 0
    total_active_quantity: int = 0
    created_at: Optional[datetime] = None


class SellerProductsResponse(BaseModel):
    items: List[SellerProductItem] = []
    total_count: int = 0
    limit: int = 20
    offset: int = 0
