from pydantic import BaseModel, Field
from typing import List


class FulfillItem(BaseModel):
    sku_id: str
    quantity: int = Field(..., gt=0)


class FulfillRequest(BaseModel):
    order_id: str
    items: List[FulfillItem]
