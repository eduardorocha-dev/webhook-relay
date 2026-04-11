import uuid
from datetime import datetime, timezone

from sqlalchemy import update

from app.db.session import AsyncSessionLocal
from app.models.delivery import DeliveryAttempt


async def move_to_dead_letter(event_id: uuid.UUID, attempt_number: int, target_url: str, error: str) -> None:
    """Persist a final failed delivery attempt to the dead-letter queue."""
    async with AsyncSessionLocal() as db:
        attempt = DeliveryAttempt(
            event_id=event_id,
            attempt_number=attempt_number,
            status="dead_letter",
            target_url=target_url,
            error_detail=error,
            attempted_at=datetime.now(timezone.utc),
        )
        db.add(attempt)
        await db.commit()
