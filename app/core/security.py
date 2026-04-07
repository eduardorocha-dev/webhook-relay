from fastapi import HTTPException, Request, status

from app.providers.registry import get_provider


async def verify_webhook_signature(provider_name: str, request: Request) -> bytes:
    """Read the raw request body and verify the provider signature.

    Returns the raw payload bytes so the caller doesn't need to read the
    body a second time (FastAPI only allows one read per request).

    Raises 400 if the provider is unknown.
    Raises 401 if the signature is invalid.
    """
    provider = get_provider(provider_name)
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown provider: {provider_name}",
        )

    payload = await request.body()
    headers = dict(request.headers)

    if not provider.verify_signature(payload, headers):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    return payload
