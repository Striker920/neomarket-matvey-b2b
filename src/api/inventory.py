from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from src.database import get_db
from src.config import settings
from src.schemas.reserve import (
    ReserveRequest,
    UnreserveRequest
)
from src.services.reserve_service import ReserveService
from typing import Optional
from fastapi import Header


async def verify_service_key(X_Service_Key: Optional[str] = Header(None)):
    if X_Service_Key != settings.B2C_SERVICE_KEY:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "INVALID_SERVICE_KEY",
                "message": "Invalid X-Service-Key header"
            }
        )
    return True


router = APIRouter(prefix="/api/v1/inventory", tags=["Inventory"])


@router.post("/reserve")
def reserve(
    request: ReserveRequest,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_service_key)
):
    service = ReserveService(db)
    result = service.reserve(request)

    if "code" in result:
        status_code = {
            "INVALID_QUANTITY": 400,
            "SKU_NOT_FOUND": 404,
            "PARTIAL_INSUFFICIENT_STOCK": 409,
        }.get(result["code"], 409)

        return JSONResponse(
            status_code=status_code,
            content={
                "code": result["code"],
                "message": result["message"],
                "details": result.get("details")
            }
        )

    return result


@router.post("/unreserve")
def unreserve(
    request: UnreserveRequest,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_service_key)
):
    service = ReserveService(db)
    result = service.unreserve(request)

    if "code" in result:
        status_code = {
            "INVALID_QUANTITY": 400,
            "SKU_NOT_FOUND": 404,
            "INSUFFICIENT_RESERVATION": 409,
        }.get(result["code"], 409)

        return JSONResponse(
            status_code=status_code,
            content={
                "code": result["code"],
                "message": result["message"],
                "details": result.get("details")
            }
        )

    return result
