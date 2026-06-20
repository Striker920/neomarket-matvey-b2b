from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from enum import Enum

class InvoiceItemRequest(BaseModel):
    sku_id: UUID
    quantity: int = Field(..., gt=0, description="Количество в накладной")
    
    @field_validator('quantity')
    @classmethod
    def quantity_positive(cls, v):
        if v <= 0:
            raise ValueError('Quantity must be positive')
        return v

class InvoiceCreateRequest(BaseModel):
    items: List[InvoiceItemRequest] = Field(..., min_length=1)
    
    @field_validator('items')
    @classmethod
    def items_not_empty(cls, v):
        if not v:
            raise ValueError('At least one item is required')
        return v

class InvoiceStatusEnum(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"

class InvoiceItemResponse(BaseModel):
    sku_id: UUID
    quantity: int
    accepted_quantity: Optional[int] = None

class InvoiceResponse(BaseModel):
    id: UUID
    seller_id: UUID
    status: InvoiceStatusEnum
    items: List[InvoiceItemResponse]
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}