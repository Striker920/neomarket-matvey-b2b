import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class ProductStatus(str, Enum):
    DRAFT = "DRAFT"
    ON_MODERATION = "ON_MODERATION"
    MODERATED = "MODERATED"
    BLOCKED = "BLOCKED"
    HARD_BLOCKED = "HARD_BLOCKED"
    ARCHIVED = "ARCHIVED"

class SKUStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    OUT_OF_STOCK = "OUT_OF_STOCK"

class Product(Base):
    __tablename__ = "products"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    seller_id = Column(String(36), nullable=False)
    title = Column(String(255), nullable=False)
    status = Column(SAEnum(ProductStatus), default=ProductStatus.DRAFT, nullable=False)
    block_reason = Column(String(500), nullable=True)
    blocking_reason_id = Column(String(36), nullable=True)
    field_reports = Column(JSON, nullable=True)
    skus = relationship("SKU", back_populates="product", cascade="all, delete-orphan")

class SKU(Base):
    __tablename__ = "skus"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False)
    name = Column(String(255), nullable=False)
    price = Column(Integer, nullable=False)
    stock_quantity = Column(Integer, default=0, nullable=False)
    article = Column(String(64), nullable=True, unique=True)
    status = Column(SAEnum(SKUStatus), default=SKUStatus.ACTIVE, nullable=False) # Добавлено
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    product = relationship("Product", back_populates="skus")
    images = relationship("SKUImage", back_populates="sku", cascade="all, delete-orphan")
    characteristics = relationship("SKUCharacteristic", back_populates="sku", cascade="all, delete-orphan")

class SKUImage(Base):
    __tablename__ = "sku_images"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sku_id = Column(String(36), ForeignKey("skus.id"), nullable=False)
    url = Column(String(512), nullable=False)
    sku = relationship("SKU", back_populates="images")

class SKUCharacteristic(Base):
    __tablename__ = "sku_characteristics"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sku_id = Column(String(36), ForeignKey("skus.id"), nullable=False)
    name = Column(String(100), nullable=False)
    value = Column(String(255), nullable=False)
    sku = relationship("SKU", back_populates="characteristics")

class ModerationEventOutbox(Base):
    __tablename__ = "moderation_event_outbox"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type = Column(String(50), nullable=False)
    aggregate_id = Column(String(36), nullable=False)
    payload = Column(JSON, nullable=False)
    idempotency_key = Column(String(128), unique=True, nullable=False)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

class B2CCascadeOutbox(Base):
    __tablename__ = "b2c_cascade_outbox"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type = Column(String(50), nullable=False)
    product_id = Column(String(36), nullable=False)
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class ProcessedEvent(Base):
    __tablename__ = "processed_events"
    idempotency_key = Column(String(128), primary_key=True)
    sender_service = Column(String(50), primary_key=True, default="moderation")
    event_type = Column(String(50), nullable=False)
    processed_at = Column(DateTime, default=datetime.utcnow)