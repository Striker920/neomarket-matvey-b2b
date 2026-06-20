from sqlalchemy import Column, String, Text, Boolean, DateTime, JSON
from sqlalchemy.sql import func
import uuid
from src.database import Base
from sqlalchemy.orm import relationship


class Product(Base):
    __tablename__ = "products"

    class Status:
        CREATED = "CREATED"
        ON_MODERATION = "ON_MODERATION"
        MODERATED = "MODERATED"
        BLOCKED = "BLOCKED"
        HARD_BLOCKED = "HARD_BLOCKED"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    seller_id = Column(String(36), nullable=False, index=True)
    category_id = Column(String(36), nullable=False, index=True)
    
    title = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False, default="")
    description = Column(Text, nullable=False)
    
    status = Column(String(50), nullable=False, default="CREATED")
    deleted = Column(Boolean, default=False, nullable=False)
    blocked = Column(Boolean, default=False, nullable=False)
    blocking_reason_id = Column(String(36), nullable=False, default=lambda: str(uuid.uuid4()))
    moderator_comment = Column(Text, nullable=False, default="")
    
    images = Column(JSON, nullable=False, default=list)
    characteristics = Column(JSON, default=list)
    skus = Column(JSON, default=list)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), default=func.now(), nullable=False)

    blockings = relationship("ProductBlocking", back_populates="product", lazy="select")