import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db
from app.config import settings
from app.models.delivery import DeliveryAttempt
from app.models.event import WebhookEvent
from app.schemas.event import EventDetailResponse, EventListResponse

router = APIRouter(prefix="/api/v1/events", tags=["events"])


@router.get("", response_model=list[EventListResponse])
async def list_events(
    provider: str | None = Query(None),
    event_type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Query the event log with optional filters."""
    query = select(WebhookEvent).order_by(WebhookEvent.received_at.desc())

    if provider:
        query = query.where(WebhookEvent.provider == provider)
    if event_type:
        query = query.where(WebhookEvent.event_type == event_type)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{event_id}", response_model=EventDetailResponse)
async def get_event(event_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get a single event with its full delivery history."""
    result = await db.execute(
        select(WebhookEvent)
        .options(selectinload(WebhookEvent.delivery_attempts))
        .where(WebhookEvent.id == event_id)
    )
    event = result.scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


@router.post("/{event_id}/retry", response_model=EventDetailResponse)
async def retry_event(event_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Re-dispatch a dead-lettered event."""
    result = await db.execute(
        select(WebhookEvent)
        .options(selectinload(WebhookEvent.delivery_attempts))
        .where(WebhookEvent.id == event_id)
    )
    event = result.scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    # Only allow retry if the last attempt was dead_letter
    attempts = sorted(event.delivery_attempts, key=lambda a: a.attempt_number)
    if not attempts or attempts[-1].status != "dead_letter":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Event is not in dead-letter queue",
        )

    from app.workers.tasks import dispatch_event
    dispatch_event.delay(
        event_id=str(event.id),
        target_url=settings.target_url,
        payload=event.payload,
    )

    return event
