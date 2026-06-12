from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session
from src.database import get_db
from src.schemas.sku import SKUCreateRequest, SKUResponse
from src.services.sku_service import create_sku
from src.core.exceptions import AppError

router = APIRouter(prefix="/api/v1", tags=["B2B: SKU"])

def get_current_seller(authorization: str = Header(..., alias="Authorization")) -> str:
    if not authorization.startswith("Bearer "):
        raise AppError("UNAUTHORIZED", "Требуется Bearer токен", 401)
    # В реальной системе здесь был бы парсинг JWT. Для тестов возвращаем мок.
    return "seller-001"

@router.post("/skus", status_code=201)
def create_sku_endpoint(
    payload: SKUCreateRequest,
    db: Session = Depends(get_db),
    seller_id: str = Depends(get_current_seller)
):
    result = create_sku(db, payload, seller_id=seller_id)
    sku = result["sku"]
    
    return SKUResponse(
        id=sku.id,
        product_id=sku.product_id,
        name=sku.name,
        price=sku.price,
        stock_quantity=sku.stock_quantity,
        article=sku.article,
        discount=sku.discount,
        cost_price=sku.cost_price,
        active_quantity=sku.stock_quantity - sku.reserved_quantity,
        reserved_quantity=sku.reserved_quantity,
        status=sku.status.value if hasattr(sku.status, 'value') else str(sku.status),
        images=[{"id": img.id, "url": img.url, "ordering": img.ordering} for img in sku.images],
        characteristics=[{"id": c.id, "name": c.name, "value": c.value} for c in sku.characteristics],
        created_at=sku.created_at.isoformat() if sku.created_at else "",
        updated_at=sku.updated_at.isoformat() if sku.updated_at else "",
        triggered_moderation=result["triggered_moderation"]
    )