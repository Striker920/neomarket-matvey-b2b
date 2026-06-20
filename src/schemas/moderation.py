from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime


class FieldReport(BaseModel):
    field_name: str
    comment: str


class ModerationEventRequest(BaseModel):
    idempotency_key: str = Field(..., description="UUID для идемпотентности")
    product_id: str = Field(..., description="ID товара")
    event_type: Literal["MODERATED", "BLOCKED"] = Field(..., description="Тип события")
    occurred_at: datetime = Field(..., description="Время возникновения события")

    moderator_id: Optional[str] = Field(None, description="ID модератора")
    moderator_comment: Optional[str] = Field(None, description="Комментарий модератора")
    blocking_reason_id: Optional[str] = Field(None, description="ID причины блокировки")
    hard_block: bool = Field(default=False, description="Жёсткая блокировка")
    field_reports: Optional[List[FieldReport]] = Field(None, description="Отчеты по полям")
