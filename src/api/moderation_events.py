from fastapi import APIRouter, Depends, HTTPException, status, Header, Response, BackgroundTasks
from sqlalchemy.orm import Session
from src.database import get_db, SessionLocal
from src.schemas.moderation import ModerationEventRequest
from src.services.moderation_service import apply_moderation_decision
from src.services.b2c_dispatcher import b2c_dispatcher
from src.config import settings


router = APIRouter(prefix="/api/v1", tags=["B2B: Moderation Events"])


def dispatch_b2c_task():
    db = SessionLocal()
    try:
        b2c_dispatcher.send_pending_events(db)
    finally:
        db.close()


@router.post(
    "/moderation/events",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Приём событий от Moderation Service"
)
def handle_moderation_event(
    payload: ModerationEventRequest,
    response: Response,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    x_service_key: str | None = Header(None, alias="X-Service-Key")
):
    if not x_service_key or x_service_key != settings.MODERATION_SERVICE_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid X-Service-Key"
        )

    try:
        result = apply_moderation_decision(db, payload, sender_service="moderation")

        if result["status"] == "duplicate":
            response.headers["X-Idempotent-Replay"] = "true"

        background_tasks.add_task(dispatch_b2c_task)

        return None
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Товар не найден")
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
