from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.sql import func
from src.database import Base


class FulfillOperation(Base):
    __tablename__ = "fulfill_operations"

    order_id = Column(String(255), primary_key=True, index=True)
    result = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
