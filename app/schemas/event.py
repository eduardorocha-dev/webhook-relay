import uuid
from datetime import datetime

from pydantic import BaseModel


class DeliveryAttemptResponse(BaseModel):
    id: uuid.UUID
    attempt_number: int
    status: str
    target_url: str
    response_code: int | None
    error_detail: str | None
    attempted_at: datetime

    model_config = {"from_attributes": True}


class EventDetailResponse(BaseModel):
    id: uuid.UUID
    provider: str
    event_type: str
    idempotency_key: str
    received_at: datetime
    delivery_attempts: list[DeliveryAttemptResponse] = []

    model_config = {"from_attributes": True}


class EventListResponse(BaseModel):
    id: uuid.UUID
    provider: str
    event_type: str
    received_at: datetime

    model_config = {"from_attributes": True}
