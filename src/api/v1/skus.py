from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session
from src.database import get_db
from src.schemas.sku import SKUCreateRequest, SKUResponse
from src.services.sku_service import create_sku

router = APIRouter(prefix="/api/v1", tags=["B2B: SKU"])

@router.post("/skus", status_code=201)
def create_sku_endpoint(
    payload: SKUCreateRequest,
    db: Session = Depends(get_db),
    x_seller_id: str = Header(..., alias="X-Seller-Id")
):
    result = create_sku(db, payload, seller_id=x_seller_id)
    sku = result["sku"]
    
    return SKUResponse(
        id=sku.id,
        product_id=sku.product_id,
        name=sku.name,
        price=sku.price,
        stock_quantity=sku.stock_quantity,
        article=sku.article,
        status=sku.status.value if hasattr(sku.status, 'value') else str(sku.status),
        images=[{"url": img.url} for img in sku.images],
        characteristics=[{"name": c.name, "value": c.value} for c in sku.characteristics],
        created_at=sku.created_at.isoformat() if sku.created_at else "",
        triggered_moderation=result["triggered_moderation"]
    )