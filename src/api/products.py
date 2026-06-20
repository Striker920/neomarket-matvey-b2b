from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request
from sqlalchemy.orm import Session
from uuid import UUID
from src.config import settings
from src.database import get_db
from src.schemas.product import (
    ProductCreateRequest,
    ProductResponse,
    ProductUpdateRequest,
    ProductDetailResponse,
    CatalogResponse,
    ProductCatalogItem,
)
from src.schemas.seller_products import SellerProductsResponse, SellerProductItem
from src.services.product_service import ProductService
from src.dependencies.auth import get_current_seller_id
from typing import List, Optional

router = APIRouter(prefix="/api/v1/products", tags=["Products"])


@router.post("/", response_model=ProductResponse, status_code=201)
def create_product(
    product_data: ProductCreateRequest,
    seller_id: UUID = Depends(get_current_seller_id),
    db: Session = Depends(get_db)
):
    if not product_data.images:
        raise HTTPException(400, {"code": "INVALID_REQUEST", "message": "At least one image is required"})

    service = ProductService(db)
    product = service.create_product(str(seller_id), product_data)
    return product


@router.patch("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: UUID,
    product_data: ProductUpdateRequest,
    seller_id: UUID = Depends(get_current_seller_id),
    db: Session = Depends(get_db)
):
    service = ProductService(db)

    updated_product = service.update_product(
        product_id=str(product_id),
        seller_id=str(seller_id),
        update_data=product_data.model_dump(exclude_unset=True)
    )

    from src.services.event_service import send_edited_event
    send_edited_event(
        product_id=updated_product["id"],
        seller_id=str(seller_id),
        changes=product_data.model_dump(exclude_unset=True)
    )

    return updated_product


@router.delete("/{product_id}")
def delete_product(
    product_id: UUID,
    seller_id: UUID = Depends(get_current_seller_id),
    db: Session = Depends(get_db)
):
    service = ProductService(db)
    service.delete_product(product_id=str(product_id), seller_id=str(seller_id))
    return {"ok": True}


@router.get("/")
def get_products(
    request: Request,
    db: Session = Depends(get_db),
    x_service_key: Optional[str] = Header(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    category: Optional[str] = None,
    search: Optional[str] = None,
    sort: Optional[str] = None,
    ids: Optional[str] = None,
    status: Optional[str] = None,
):
    is_b2c_mode = x_service_key == settings.B2C_SERVICE_KEY if x_service_key else False

    if is_b2c_mode:
        service = ProductService(db)
        id_list = None
        if ids:
            id_list = [i.strip() for i in ids.split(",") if i.strip()]

        products, total = service.get_catalog_products(
            limit=limit,
            offset=offset,
            category=category,
            search=search,
            sort=sort,
            ids=id_list
        )

        items = [service._format_for_catalog(p) for p in products]
        return CatalogResponse(items=items, total_count=total, limit=limit, offset=offset)

    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        from jose import jwt as jose_jwt
        token = auth_header.split(" ")[1]
        try:
            payload = jose_jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            seller_id_str = payload.get("sub")
            if seller_id_str:
                service = ProductService(db)
                items, total = service.get_seller_products_list(
                    seller_id=seller_id_str,
                    limit=limit,
                    offset=offset,
                    status=status,
                    search=search
                )
                return SellerProductsResponse(
                    items=items,
                    total_count=total,
                    limit=limit,
                    offset=offset
                )
        except Exception:
            pass

    raise HTTPException(
        status_code=401,
        detail={"code": "UNAUTHORIZED", "message": "Missing or invalid authorization"}
    )


@router.get("/{product_id}", response_model=ProductDetailResponse)
def get_product(
    product_id: UUID,
    seller_id: UUID = Depends(get_current_seller_id),
    db: Session = Depends(get_db),
    x_service_key: Optional[str] = Header(None)
):
    service = ProductService(db)

    is_b2c_mode = x_service_key == settings.B2C_SERVICE_KEY if x_service_key else False

    product = service.get_product_by_id(
        str(product_id),
        str(seller_id),
        is_b2c_mode=is_b2c_mode
    )

    if not product:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "Product not found"}
        )

    return product
