import uuid
from datetime import datetime

from pydantic import BaseModel


class WebhookEventResponse(BaseModel):
    id: uuid.UUID
    provider: str
    event_type: str
    idempotency_key: str
    received_at: datetime

    model_config = {"from_attributes": True}
