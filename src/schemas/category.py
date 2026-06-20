from pydantic import BaseModel
from typing import List, Optional, Any


class CategoryCreateRequest(BaseModel):
    name: str
    slug: Optional[str] = None
    parent_id: Optional[str] = None
    description: Optional[str] = None


class CategoryResponse(BaseModel):
    id: str
    name: str
    slug: Optional[str] = None
    parent_id: Optional[str] = None
    children: List[Any] = []


class CategoryDetailResponse(BaseModel):
    id: str
    name: str
    slug: Optional[str] = None
    parent_id: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True


class CategoryTreeResponse(BaseModel):
    items: List[CategoryResponse] = []
