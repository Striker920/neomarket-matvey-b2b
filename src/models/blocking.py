from sqlalchemy import Column, DateTime, String, Text, JSON, ForeignKey, func
from src.database import Base
import uuid
from sqlalchemy.orm import relationship

class BlockingReason(Base):
    __tablename__ = "blocking_reasons"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)

class ProductBlocking(Base):
    __tablename__ = "product_blockings"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False)
    blocking_reason_id = Column(String(36), ForeignKey("blocking_reasons.id"), nullable=False)
    field_reports = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    product = relationship("Product", back_populates="blockings")
    blocking_reason = relationship("BlockingReason")