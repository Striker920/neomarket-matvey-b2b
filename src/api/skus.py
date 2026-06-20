from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from src.database import get_db
from src.schemas.product import SKUCreateRequest, SKUCreateResponse, SKUUpdateRequest, SKUResponse
from src.services.product_service import ProductService
from src.dependencies.auth import get_current_seller_id
from src.services.event_service import send_edited_event

router = APIRouter(prefix="/api/v1/skus", tags=["SKUs"])


@router.post("/", response_model=SKUCreateResponse, status_code=201)
def create_sku(
    sku_data: SKUCreateRequest,
    seller_id: UUID = Depends(get_current_seller_id),
    db: Session = Depends(get_db)
):
    service = ProductService(db)
    new_sku = service.create_sku(str(seller_id), sku_data)
    return new_sku


@router.patch("/{sku_id}", response_model=SKUResponse)
def update_sku(
    sku_id: UUID,
    sku_data: SKUUpdateRequest,
    seller_id: UUID = Depends(get_current_seller_id),
    db: Session = Depends(get_db)
):
    service = ProductService(db)

    updated_sku = service.update_sku(
        sku_id=str(sku_id),
        seller_id=str(seller_id),
        update_data=sku_data.model_dump(exclude_unset=True)
    )

    send_edited_event(
        product_id=updated_sku["product_id"],
        seller_id=str(seller_id),
        changes={"sku_updated": str(sku_id)}
    )

    return updated_sku


@router.delete("/{sku_id}")
def delete_sku(
    sku_id: UUID,
    seller_id: UUID = Depends(get_current_seller_id),
    db: Session = Depends(get_db)
):
    service = ProductService(db)
    result = service.delete_sku(str(sku_id), str(seller_id))

    if "code" in result:
        status_code = {
            "NOT_FOUND": 404,
            "NOT_OWNER": 403,
            "FORBIDDEN": 403,
            "CONFLICT": 409,
        }.get(result["code"], 400)

        raise HTTPException(
            status_code=status_code,
            detail={"code": result["code"], "message": result["message"]}
        )

    return {"ok": True}
