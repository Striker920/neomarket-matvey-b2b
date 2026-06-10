from sqlalchemy.orm import Session
from src.models.base import B2CCascadeOutbox
from src.core.config import settings

class B2CDispatcher:
    def __init__(self, base_url: str = None):
        self.base_url = base_url or getattr(settings, "B2C_SERVICE_URL", "http://localhost:8001")

    def send_pending_events(self, db: Session):
        events = db.query(B2CCascadeOutbox).filter(
            B2CCascadeOutbox.status == "pending"
        ).all()
        
        for event in events:
            try:
                # В реальном приложении здесь был бы HTTP запрос в B2C:
                # httpx.post(f"{self.base_url}/api/v1/events/product_blocked", json=event.payload)
                event.status = "sent"
            except Exception:
                event.status = "failed"
        
        if events:
            db.commit()

b2c_dispatcher = B2CDispatcher()