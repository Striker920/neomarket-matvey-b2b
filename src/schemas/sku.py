from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import List, Optional

class SKUImageCreate(BaseModel):
    url: str = Field(..., max_length=512)

class SKUCharacteristicCreate(BaseModel):
    name: str = Field(..., max_length=100)
    value: str = Field(..., max_length=255)

class SKUCreateRequest(BaseModel):
    product_id: str
    name: str = Field(..., min_length=1, max_length=255)
    price: int = Field(..., ge=0)  # ИСПРАВЛЕНО: цена может быть >= 0
    stock_quantity: int = Field(default=0, ge=0)
    article: Optional[str] = Field(None, max_length=64)
    images: List[SKUImageCreate] = Field(default_factory=list)  # ИСПРАВЛЕНО: опционально
    characteristics: List[SKUCharacteristicCreate] = Field(default_factory=list)

    @field_validator("article")
    @classmethod
    def normalize_article(cls, v: Optional[str]) -> Optional[str]:
        return v.strip().upper() if v else None

class SKUResponse(BaseModel):
    id: str
    product_id: str
    name: str
    price: int
    stock_quantity: int
    article: Optional[str] = None
    status: str
    images: List[dict]
    characteristics: List[dict]
    created_at: str
    triggered_moderation: bool

    model_config = ConfigDict(from_attributes=True)