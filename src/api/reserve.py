from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional

from src.database import get_db
from src.config import settings
from src.schemas.reserve import ReserveRequest, UnreserveRequest
from src.services.reserve_service import ReserveService

router = APIRouter(prefix="/api/v1", tags=["Reserve"])


def verify_service_key(x_service_key: Optional[str] = Header(None)):
    if not x_service_key or x_service_key != settings.B2C_SERVICE_KEY:
        raise HTTPException(
            status_code=401,
            detail={"code": "UNAUTHORIZED", "message": "Invalid or missing X-Service-Key"}
        )
    return True


@router.post("/reserve")
def reserve(
    request: ReserveRequest,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_service_key)
):
    service = ReserveService(db)
    result = service.reserve(request)

    if result.get("reserved") is False:
        return result

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
            "SKU_NOT_FOUND": 404,
            "INSUFFICIENT_RESERVATION": 409,
        }.get(result["code"], 400)

        raise HTTPException(
            status_code=status_code,
            detail={"code": result["code"], "message": result["message"]}
        )

    return result
