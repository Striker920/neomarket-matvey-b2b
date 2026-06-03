from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from src.database import get_db
from src.schemas.sku import SKUCreateRequest
from src.services.sku_service import create_sku
from src.core.config import settings

router = APIRouter(prefix="/api/v1", tags=["B2B: SKU"])

@router.post("/skus", status_code=status.HTTP_201_CREATED)
def create_sku_endpoint(
    payload: SKUCreateRequest,
    db: Session = Depends(get_db),
    x_service_key: str | None = Header(None, alias="X-Service-Key")
):
    if settings.REQUIRE_SERVICE_KEY and x_service_key != settings.INTERNAL_SERVICE_KEY:
        raise HTTPException(status_code=403, detail="Invalid X-Service-Key")

    try:
        result = create_sku(db, payload)
        return {
            "id": result["sku"].id,
            "product_id": result["sku"].product_id,
            "name": result["sku"].name,
            "price": result["sku"].price,
            "triggered_moderation": result["triggered_moderation"]
        }
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))