from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import List, Optional

class SKUImageCreate(BaseModel):
    url: str = Field(..., max_length=512)
    ordering: int = Field(default=0)

class SKUCharacteristicCreate(BaseModel):
    name: str = Field(..., max_length=100)
    value: str = Field(..., max_length=255)

class SKUCreateRequest(BaseModel):
    product_id: str
    name: str = Field(..., min_length=1, max_length=255)
    price: int = Field(..., ge=0)
    stock_quantity: int = Field(default=0, ge=0)
    article: Optional[str] = Field(None, max_length=64)
    discount: int = Field(default=0, ge=0)
    cost_price: Optional[int] = Field(None, ge=0)
    images: List[SKUImageCreate] = Field(default_factory=list)
    characteristics: List[SKUCharacteristicCreate] = Field(default_factory=list)

    @field_validator("article")
    @classmethod
    def normalize_article(cls, v: Optional[str]) -> Optional[str]:
        return v.strip().upper() if v else None

class SKUImageResponse(BaseModel):
    id: str
    url: str
    ordering: int

class CharacteristicResponse(BaseModel):
    id: str
    name: str
    value: str

class SKUResponse(BaseModel):
    id: str
    product_id: str
    name: str
    price: int
    stock_quantity: int
    article: Optional[str] = None
    discount: int
    cost_price: Optional[int]
    active_quantity: int
    reserved_quantity: int
    status: str
    images: List[SKUImageResponse]
    characteristics: List[CharacteristicResponse]
    created_at: str
    updated_at: str
    triggered_moderation: bool

    model_config = ConfigDict(from_attributes=True)