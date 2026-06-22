from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.orm import Session
from src.config import settings
from src.database import get_db
from src.schemas.product import CatalogResponse
from src.services.product_service import ProductService
from typing import Optional

router = APIRouter(prefix="/api/v1/public", tags=["Public Catalog"])


def _require_b2c_service_key(x_service_key: Optional[str]) -> str:
    """
    US-B2B-07: Проверяет X-Service-Key для режима каталога B2C.
    Возвращает 401, если заголовок отсутствует или невалиден.
    """
    if not x_service_key:
        raise HTTPException(
            status_code=401,
            detail={"code": "UNAUTHORIZED", "message": "Missing X-Service-Key header"}
        )
    if x_service_key != settings.B2C_SERVICE_KEY:
        raise HTTPException(
            status_code=401,
            detail={"code": "UNAUTHORIZED", "message": "Invalid X-Service-Key"}
        )
    return x_service_key


@router.get("/products", response_model=CatalogResponse)
def list_public_products(
    db: Session = Depends(get_db),
    x_service_key: Optional[str] = Header(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    # ✅ ИСПРАВЛЕНО: category → category_id (по спецификации OpenAPI)
    category_id: Optional[str] = Query(None, description="Filter by category ID"),
    search: Optional[str] = None,
    sort: Optional[str] = None,
    ids: Optional[str] = None,
):
    """
    US-B2B-07: Публичный каталог для B2C (service-to-service).
    
    Фильтры видимости:
    - status = MODERATED
    - deleted = False
    - active_quantity > 0
    - Исключить HARD_BLOCKED
    
    НЕ возвращает cost_price и reserved_quantity (IDOR-защита).
    """
    # Проверяем X-Service-Key
    _require_b2c_service_key(x_service_key)

    service = ProductService(db)
    id_list = None
    if ids:
        id_list = [i.strip() for i in ids.split(",") if i.strip()]

    # ✅ Передаём category_id как category (внутреннее имя сервиса)
    products, total = service.get_catalog_products(
        limit=limit,
        offset=offset,
        category=category_id,
        search=search,
        sort=sort,
        ids=id_list
    )

    items = [service._format_for_catalog(p) for p in products]
    return CatalogResponse(items=items, total_count=total, limit=limit, offset=offset)