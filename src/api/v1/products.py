from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.database import get_db
from src.services.moderation_service import update_product_by_seller

router = APIRouter(prefix="/api/v1/products", tags=["B2B: Products"])

@router.put("/{product_id}")
def update_product(
    product_id: str,
    seller_id: str,
    db: Session = Depends(get_db)
):
    try:
        return update_product_by_seller(db, product_id, seller_id, {"title": "Updated"})
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))