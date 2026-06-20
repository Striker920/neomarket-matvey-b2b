from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime


class ReserveItem(BaseModel):
    sku_id: UUID
    quantity: int = Field(..., gt=0)


class ReserveRequest(BaseModel):
    idempotency_key: UUID
    order_id: UUID
    items: List[ReserveItem]


class ReserveSuccessResponse(BaseModel):
    order_id: UUID
    status: str = "RESERVED"
    reserved_at: datetime


class ReserveFailedItem(BaseModel):
    sku_id: UUID
    requested: int
    available: int
    reason: str


class UnreserveItem(BaseModel):
    sku_id: UUID
    quantity: int = Field(..., gt=0)


class UnreserveRequest(BaseModel):
    order_id: UUID
    items: List[UnreserveItem]


class UnreserveResponse(BaseModel):
    order_id: UUID
    status: str = "UNRESERVED"
    processed_at: datetime


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
