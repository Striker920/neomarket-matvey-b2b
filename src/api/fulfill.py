from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional

from src.database import get_db
from src.config import settings
from src.schemas.fulfill import FulfillRequest
from src.services.fulfill_service import FulfillService

router = APIRouter(prefix="/api/v1", tags=["Fulfill"])


def verify_service_key(x_service_key: Optional[str] = Header(None)):
    if not x_service_key or x_service_key != settings.B2C_SERVICE_KEY:
        raise HTTPException(
            status_code=401,
            detail={"code": "INVALID_SERVICE_KEY", "message": "Invalid X-Service-Key header"}
        )
    return True


@router.post("/fulfill")
def fulfill(
    request: FulfillRequest,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_service_key)
):
    service = FulfillService(db)
    result = service.fulfill(request)

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
