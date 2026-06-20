# src/api/invoices.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from src.database import get_db
from src.dependencies.auth import get_current_seller_id
from src.schemas.invoice import InvoiceCreateRequest, InvoiceResponse
from src.services.invoice_service import InvoiceService

router = APIRouter(prefix="/api/v1/invoices", tags=["Invoices"])

@router.post("/", response_model=InvoiceResponse, status_code=201)
def create_invoice(
    invoice_data: InvoiceCreateRequest,
    seller_id: UUID = Depends(get_current_seller_id),
    db: Session = Depends(get_db)
):
    """
    Создание накладной на поступление товара.
    
    - Только SKU из MODERATED товаров
    - Только свои SKU (проверка seller_id)
    - Статус накладной: PENDING
    """
    service = InvoiceService(db)
    
    try:
        invoice = service.create_invoice(
            seller_id=str(seller_id),
            items=invoice_data.items
        )
        return invoice
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"code": "INVALID_REQUEST", "message": str(e)})
    except PermissionError as e:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": str(e)})