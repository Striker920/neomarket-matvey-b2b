import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON
from src.database import Base


class B2CCascadeOutbox(Base):
    __tablename__ = "b2c_cascade_outbox"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type = Column(String(50), nullable=False)
    product_id = Column(String(36), nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
