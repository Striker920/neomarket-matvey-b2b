from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from typing import Optional
import uuid

from app.core.database import SessionLocal, get_db
from app.core.security import get_seller_id_from_request, check_x_service_key
from app.schemas.product import ProductResponse
from app.services.product_service import ProductService
from app.models.product import Product
from app.errors import ApiError

router = APIRouter()


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    request: Request,
    product_id: str,
    db: Session = Depends(get_db)
):
    """
    Получение карточки товара.
    
    Два режима:
    1. Seller cabinet (Bearer JWT) - проверка ownership
    2. X-Service-Key - межсервисный вызов (без проверки ownership)
    """
    # Проверка валидности UUID
    try:
        product_uuid = uuid.UUID(product_id)
    except ValueError:
        raise ApiError(
            status_code=400,
            code="INVALID_REQUEST",
            message="id must be a valid UUID"
        )
    
    x_service_key = request.headers.get("X-Service-Key")
    auth_header = request.headers.get("Authorization")
    
    # ✅ Используем функцию из security вместо хардкода
    is_service_call = check_x_service_key(x_service_key)
    is_seller_call = auth_header and auth_header.startswith("Bearer ")
    
    if not is_service_call and not is_seller_call:
        raise ApiError(
            status_code=401,
            code="UNAUTHORIZED",
            message="Authentication required"
        )
    
    product = db.query(Product).filter(
        Product.id == product_uuid,
        Product.deleted == False
    ).first()
    
    if not product:
        raise ApiError(
            status_code=404,
            code="NOT_FOUND",
            message="Product not found"
        )
    
    if is_seller_call:
        seller_id = get_seller_id_from_request(request)
        if str(product.seller_id) != seller_id:
            # ✅ IDOR-защита: чужой товар → 404 (не 403)
            raise ApiError(
                status_code=404,
                code="NOT_FOUND",
                message="Product not found"
            )
        
        return ProductService.build_seller_response(product, db)
    else:
        return ProductService.build_service_response(product, db)