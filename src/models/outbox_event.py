from sqlalchemy import Column, String, DateTime, JSON, Integer
from sqlalchemy.sql import func
import uuid
from src.database import Base


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(255), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    event_type = Column(String(100), nullable=False)
    aggregate_id = Column(String(255), nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(String(50), default="PENDING")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
