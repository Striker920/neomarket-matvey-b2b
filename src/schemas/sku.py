from pydantic import BaseModel, Field, field_validator
from typing import List, Optional


class SKUImageCreate(BaseModel):
    url: str = Field(..., max_length=512)


class SKUCreateRequest(BaseModel):
    product_id: str = Field(..., description="ID товара")
    name: str = Field(..., min_length=1, max_length=255)
    price: int = Field(..., gt=0, description="Цена в копейках")
    stock_quantity: int = Field(default=0, ge=0)
    article: Optional[str] = Field(None, max_length=64)
    images: List[SKUImageCreate] = Field(..., min_length=1, max_length=10)

    @field_validator("article")
    @classmethod
    def normalize_article(cls, v: Optional[str]) -> Optional[str]:
        return v.strip().upper() if v else None