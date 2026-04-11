import pytest


@pytest.mark.asyncio
async def test_valid_webhook_returns_201(client, payload, valid_headers):
    response = await client.post("/api/v1/webhooks/github", content=payload, headers=valid_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["provider"] == "github"
    assert data["event_type"] == "push"
    assert data["idempotency_key"] == "test-delivery-001"


@pytest.mark.asyncio
async def test_duplicate_webhook_returns_200(client, payload, valid_headers):
    await client.post("/api/v1/webhooks/github", content=payload, headers=valid_headers)
    response = await client.post("/api/v1/webhooks/github", content=payload, headers=valid_headers)
    assert response.status_code == 200
    assert "already processed" in response.json()["detail"]


@pytest.mark.asyncio
async def test_invalid_signature_returns_401(client, payload):
    headers = {
        "content-type": "application/json",
        "x-hub-signature-256": "sha256=invalidsig",
        "x-github-event": "push",
        "x-github-delivery": "test-delivery-002",
    }
    response = await client.post("/api/v1/webhooks/github", content=payload, headers=headers)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_unknown_provider_returns_400(client, payload):
    response = await client.post("/api/v1/webhooks/stripe", content=payload, headers={})
    assert response.status_code == 400
