import pytest


@pytest.mark.asyncio
async def test_list_events_empty(client):
    response = await client.get("/api/v1/events")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_events_after_ingestion(client, payload, valid_headers):
    await client.post("/api/v1/webhooks/github", content=payload, headers=valid_headers)
    response = await client.get("/api/v1/events")
    assert response.status_code == 200
    assert len(response.json()) == 1


@pytest.mark.asyncio
async def test_filter_by_provider(client, payload, valid_headers):
    await client.post("/api/v1/webhooks/github", content=payload, headers=valid_headers)
    response = await client.get("/api/v1/events?provider=github")
    assert response.status_code == 200
    assert len(response.json()) == 1

    response = await client.get("/api/v1/events?provider=stripe")
    assert response.status_code == 200
    assert len(response.json()) == 0


@pytest.mark.asyncio
async def test_filter_by_event_type(client, payload, valid_headers):
    await client.post("/api/v1/webhooks/github", content=payload, headers=valid_headers)
    response = await client.get("/api/v1/events?event_type=push")
    assert response.status_code == 200
    assert len(response.json()) == 1

    response = await client.get("/api/v1/events?event_type=pull_request")
    assert response.status_code == 200
    assert len(response.json()) == 0


@pytest.mark.asyncio
async def test_get_event_detail(client, payload, valid_headers):
    ingest = await client.post("/api/v1/webhooks/github", content=payload, headers=valid_headers)
    event_id = ingest.json()["id"]

    response = await client.get(f"/api/v1/events/{event_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == event_id
    assert data["provider"] == "github"
    assert "delivery_attempts" in data


@pytest.mark.asyncio
async def test_get_event_not_found(client):
    response = await client.get("/api/v1/events/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_retry_non_dead_lettered_event_returns_400(client, payload, valid_headers):
    ingest = await client.post("/api/v1/webhooks/github", content=payload, headers=valid_headers)
    event_id = ingest.json()["id"]

    response = await client.post(f"/api/v1/events/{event_id}/retry")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_retry_not_found_returns_404(client):
    response = await client.post("/api/v1/events/00000000-0000-0000-0000-000000000000/retry")
    assert response.status_code == 404
