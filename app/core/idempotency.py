from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import WebhookEvent


async def is_duplicate(idempotency_key: str, db: AsyncSession) -> bool:
    """Return True if an event with this idempotency key already exists."""
    result = await db.execute(
        select(WebhookEvent.id).where(
            WebhookEvent.idempotency_key == idempotency_key
        )
    )
    return result.first() is not None
