from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Any
from uuid import UUID, uuid4
from datetime import datetime

class ImageSchema(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    url: str
    ordering: int

class CharacteristicSchema(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    value: str

class ProductCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1, max_length=5000)
    category_id: UUID
    slug: Optional[str] = None
    images: List[ImageSchema] = Field(..., min_length=1)
    characteristics: Optional[List[CharacteristicSchema]] = []
    
    @field_validator('images')
    @classmethod
    def images_not_empty(cls, v):
        if not v:
            raise ValueError('At least one image is required')
        return v

class ProductResponse(BaseModel):
    id: UUID
    seller_id: UUID
    title: str
    slug: str
    description: str
    status: str
    deleted: bool
    blocked: bool
    category: Optional[dict] = None
    images: List[ImageSchema]
    characteristics: List[CharacteristicSchema]
    skus: List[Any]
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class ProductUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1, max_length=5000)
    category_id: Optional[UUID] = None
    images: Optional[List[ImageSchema]] = None
    characteristics: Optional[List[CharacteristicSchema]] = None


class SKUCreateRequest(BaseModel):
    product_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    price: int = Field(..., gt=0)
    cost_price: int = Field(..., gt=0)
    discount: int = Field(default=0, ge=0)
    image: str = Field(..., min_length=1)
    characteristics: Optional[List[CharacteristicSchema]] = []


class SKUCreateResponse(BaseModel):
    id: UUID
    product_id: UUID
    name: str
    price: int
    cost_price: int
    discount: int = 0
    image: str
    active_quantity: int = 0
    reserved_quantity: int = 0
    characteristics: List[CharacteristicSchema] = []

    model_config = {"from_attributes": True}


class SKUUpdateRequest(BaseModel):
    sku_code: Optional[str] = Field(None, min_length=1, max_length=100)
    price: Optional[float] = Field(None, gt=0)
    stock_quantity: Optional[int] = Field(None, ge=0)


class SKUResponse(BaseModel):
    id: UUID
    product_id: UUID
    sku_code: str
    price: float
    stock_quantity: int
    reserved_quantity: int = 0
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class BlockingReasonSchema(BaseModel):
    id: UUID
    title: str
    description: str

class FieldReportSchema(BaseModel):
    field: str
    message: str

class SKUForSellerResponse(BaseModel):
    id: UUID
    product_id: Optional[UUID] = None
    sku_code: Optional[str] = None
    price: float
    cost_price: int = 0
    stock_quantity: int = 0
    reserved_quantity: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    model_config = {"from_attributes": True}

class ProductDetailResponse(ProductResponse):
    blocking_reason: Optional[BlockingReasonSchema] = None
    field_reports: Optional[List[FieldReportSchema]] = None
    skus: List[SKUForSellerResponse]


class SKUCatalogResponse(BaseModel):
    id: UUID
    sku_code: Optional[str] = None
    name: Optional[str] = None
    price: float
    discount: int = 0
    image: Optional[str] = None
    active_quantity: int = 0
    characteristics: List[Any] = []


class CategoryBrief(BaseModel):
    id: UUID
    name: str = "Unknown"

class ProductCatalogItem(BaseModel):
    id: UUID
    title: str
    description: str
    status: str
    category: Optional[CategoryBrief] = None
    images: List[Any] = []
    characteristics: List[Any] = []
    skus: List[SKUCatalogResponse] = []


class CatalogResponse(BaseModel):
    items: List[ProductCatalogItem] = []
    total_count: int = 0
    limit: int = 20
    offset: int = 0