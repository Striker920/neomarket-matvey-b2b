import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class ProductStatus(str, Enum):
    DRAFT = "draft"
    ON_MODERATION = "on_moderation"
    APPROVED = "approved"
    DECLINED = "declined"
    BLOCKED = "blocked"
    HARD_BLOCKED = "hard_blocked"
    ARCHIVED = "archived"

class Product(Base):
    __tablename__ = "products"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    seller_id = Column(String(36), nullable=False)
    title = Column(String(255), nullable=False)
    status = Column(SAEnum(ProductStatus), default=ProductStatus.DRAFT, nullable=False)
    
    skus = relationship("SKU", back_populates="product", cascade="all, delete-orphan")

class SKU(Base):
    __tablename__ = "skus"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False)
    name = Column(String(255), nullable=False)
    price = Column(Integer, nullable=False) # В копейках
    stock_quantity = Column(Integer, default=0, nullable=False)
    article = Column(String(64), nullable=True, unique=True)
    
    product = relationship("Product", back_populates="skus")
    images = relationship("SKUImage", back_populates="sku", cascade="all, delete-orphan")

class SKUImage(Base):
    __tablename__ = "sku_images"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sku_id = Column(String(36), ForeignKey("skus.id"), nullable=False)
    url = Column(String(512), nullable=False)
    
    sku = relationship("SKU", back_populates="images")

class ModerationEventOutbox(Base):
    __tablename__ = "moderation_event_outbox"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type = Column(String(50), nullable=False)
    aggregate_id = Column(String(36), nullable=False)
    payload = Column(JSON, nullable=False)
    idempotency_key = Column(String(128), unique=True, nullable=False)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)