from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.database import get_db
from src.schemas.category import CategoryTreeResponse, CategoryDetailResponse
from src.services.category_service import CategoryService

router = APIRouter(prefix="/api/v1/categories", tags=["Categories"])


@router.get("/", response_model=CategoryTreeResponse)
def get_category_tree(db: Session = Depends(get_db)):
    service = CategoryService(db)
    items = service.get_category_tree()
    return CategoryTreeResponse(items=items)


@router.get("/{category_id}", response_model=CategoryDetailResponse)
def get_category_detail(category_id: str, db: Session = Depends(get_db)):
    service = CategoryService(db)
    result = service.get_category_by_id(category_id)

    if not result:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "Category not found"}
        )

    return result
