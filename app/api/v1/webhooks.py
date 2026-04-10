import json

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.idempotency import is_duplicate
from app.core.security import verify_webhook_signature
from app.models.event import WebhookEvent
from app.config import settings
from app.providers.registry import get_provider
from app.schemas.webhook import WebhookEventResponse

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


@router.post("/{provider}", response_model=WebhookEventResponse, status_code=status.HTTP_201_CREATED)
async def ingest_webhook(
    provider: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    # 1. Verify signature — raises 400 or 401 on failure
    payload_bytes = await verify_webhook_signature(provider, request)

    # 2. Parse payload
    payload = json.loads(payload_bytes)
    headers = dict(request.headers)

    # 3. Extract event metadata via provider
    webhook_provider = get_provider(provider)
    event_type = webhook_provider.extract_event_type(headers, payload)
    idempotency_key = webhook_provider.extract_idempotency_key(headers, payload)

    # 4. Deduplicate — return 200 if already processed
    if await is_duplicate(idempotency_key, db):
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"detail": "Duplicate event, already processed."},
        )

    # 5. Persist to immutable event log
    event = WebhookEvent(
        provider=provider,
        event_type=event_type,
        idempotency_key=idempotency_key,
        payload=payload,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)

    # 6. Enqueue dispatch task
    from app.workers.tasks import dispatch_event
    dispatch_event.delay(
        event_id=str(event.id),
        target_url=settings.target_url,
        payload=payload,
    )

    return event
