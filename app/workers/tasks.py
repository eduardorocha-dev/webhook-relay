import asyncio
import uuid
from datetime import datetime, timezone

import httpx

from app.db.session import AsyncSessionLocal
from app.models.delivery import DeliveryAttempt
from app.workers.celery_app import celery
from app.config import settings


@celery.task(
    bind=True,
    max_retries=settings.max_retry_attempts,
    default_retry_delay=settings.retry_base_delay_seconds,
)
def dispatch_event(self, event_id: str, target_url: str, payload: dict) -> None:
    """Dispatch a webhook event to the target URL with exponential backoff retries."""
    attempt_number = self.request.retries + 1

    async def _dispatch():
        async with AsyncSessionLocal() as db:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.post(target_url, json=payload)
                    response.raise_for_status()

                attempt = DeliveryAttempt(
                    event_id=uuid.UUID(event_id),
                    attempt_number=attempt_number,
                    status="success",
                    target_url=target_url,
                    response_code=response.status_code,
                    attempted_at=datetime.now(timezone.utc),
                )
                db.add(attempt)
                await db.commit()

            except Exception as exc:
                attempt = DeliveryAttempt(
                    event_id=uuid.UUID(event_id),
                    attempt_number=attempt_number,
                    status="failed",
                    target_url=target_url,
                    response_code=getattr(exc, "response", None) and exc.response.status_code,
                    error_detail=str(exc),
                    attempted_at=datetime.now(timezone.utc),
                )
                db.add(attempt)
                await db.commit()

                try:
                    raise self.retry(
                        exc=exc,
                        countdown=settings.retry_base_delay_seconds * (2 ** self.request.retries),
                    )
                except self.MaxRetriesExceededError:
                    from app.workers.dead_letter import move_to_dead_letter
                    asyncio.run(move_to_dead_letter(
                        event_id=uuid.UUID(event_id),
                        attempt_number=attempt_number,
                        target_url=target_url,
                        error=str(exc),
                    ))

    asyncio.run(_dispatch())
