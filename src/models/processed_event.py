import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.sql import func
from src.database import Base


class ProcessedEvent(Base):
    __tablename__ = "processed_events"

    idempotency_key = Column(String(128), primary_key=True)
    sender_service = Column(String(50), primary_key=True, default="moderation")
    event_type = Column(String(50), nullable=False)
    processed_at = Column(DateTime, default=datetime.utcnow)
