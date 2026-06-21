from enum import Enum
from sqlalchemy import Column, String, DateTime, JSON, Enum as SAEnum
from datetime import datetime, timezone

from src.database import Base


class InvoiceStatus(str, Enum):
    """
    Статусы накладной по спецификации b2b/openapi.yaml:
    - CREATED: накладная только что создана
    - PARTIALLY_ACCEPTED: частично принята на склад
    - ACCEPTED: полностью принята
    - CANCELLED: отменена
    """
    CREATED = "CREATED"
    PARTIALLY_ACCEPTED = "PARTIALLY_ACCEPTED"
    ACCEPTED = "ACCEPTED"
    CANCELLED = "CANCELLED"


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(String, primary_key=True)
    seller_id = Column(String, nullable=False, index=True)
    status = Column(SAEnum(InvoiceStatus), nullable=False, default=InvoiceStatus.CREATED)
    items = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))