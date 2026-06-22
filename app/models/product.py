from sqlalchemy import Column, String, Integer, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid

from app.core.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seller_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    category_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False, unique=True)
    description = Column(Text)
    status = Column(String(50), nullable=False, default="CREATED")
    deleted = Column(Boolean, default=False)
    
    # ✅ ДОБАВЛЕНО: внешний ключ на blocking_reasons
    blocking_reason_id = Column(UUID(as_uuid=True), ForeignKey("blocking_reasons.id"), nullable=True)
    
    moderator_comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")
    characteristics = relationship("ProductCharacteristic", back_populates="product", cascade="all, delete-orphan")
    skus = relationship("SKU", back_populates="product", cascade="all, delete-orphan")
    field_reports = relationship("FieldReport", back_populates="product", cascade="all, delete-orphan")
    blocking_reason = relationship("BlockingReason", foreign_keys=[blocking_reason_id])


class ProductImage(Base):
    __tablename__ = "product_images"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    url = Column(String(500), nullable=False)
    ordering = Column(Integer, default=0)

    product = relationship("Product", back_populates="images")


class ProductCharacteristic(Base):
    __tablename__ = "product_characteristics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    name = Column(String(255), nullable=False)
    value = Column(String(500), nullable=False)

    product = relationship("Product", back_populates="characteristics")


class SKU(Base):
    __tablename__ = "skus"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    name = Column(String(255), nullable=False)
    price = Column(Integer, nullable=False)
    discount = Column(Integer, default=0)
    cost_price = Column(Integer, nullable=True)
    stock_quantity = Column(Integer, default=0)
    active_quantity = Column(Integer, default=0)
    reserved_quantity = Column(Integer, default=0)
    article = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    product = relationship("Product", back_populates="skus")
    characteristics = relationship("SKUCharacteristic", back_populates="sku", cascade="all, delete-orphan")
    images = relationship("SKUImage", back_populates="sku", cascade="all, delete-orphan")


class SKUCharacteristic(Base):
    __tablename__ = "sku_characteristics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sku_id = Column(UUID(as_uuid=True), ForeignKey("skus.id"), nullable=False)
    name = Column(String(255), nullable=False)
    value = Column(String(500), nullable=False)

    sku = relationship("SKU", back_populates="characteristics")


class SKUImage(Base):
    __tablename__ = "sku_images"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sku_id = Column(UUID(as_uuid=True), ForeignKey("skus.id"), nullable=False)
    url = Column(String(500), nullable=False)
    ordering = Column(Integer, default=0)

    sku = relationship("SKU", back_populates="images")


class BlockingReason(Base):
    __tablename__ = "blocking_reasons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    comment = Column(Text, nullable=True)


class FieldReport(Base):
    __tablename__ = "field_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    field_name = Column(String(100), nullable=False)
    sku_id = Column(UUID(as_uuid=True), ForeignKey("skus.id"), nullable=True)
    comment = Column(Text, nullable=False)

    product = relationship("Product", back_populates="field_reports")