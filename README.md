# webhook-relay

A FastAPI microservice that receives webhook events from external providers (GitHub, Stripe, etc.), verifies their authenticity, deduplicates them, persists them to an immutable log, and reliably delivers them to downstream services with automatic retries.

---

## Why This Exists

Webhooks in production are unreliable by nature. Providers send duplicates. Your services go down at the worst time. If you don't handle these edge cases, you lose data or process things twice — both of which cause bugs that are painful to debug.

**webhook-relay** sits between external providers and your internal systems to guarantee that every event is verified, stored, and delivered — or explicitly flagged for manual intervention. No event is ever silently lost.

---

## Key Features

- **Signature verification** — HMAC-SHA256 validation rejects forged requests at the gate.
- **Idempotent ingestion** — Deduplication via idempotency keys prevents double-processing.
- **Immutable event log** — Every event persisted to PostgreSQL as a complete audit trail.
- **Async dispatch with retry** — Celery workers deliver events with exponential backoff; persistent failures route to a dead-letter queue for manual retry.
- **Provider abstraction** — Strategy pattern makes adding new webhook providers a single-file change.

---

## Architecture

```
                         ┌──────────────────────────────────────────────────┐
                         │               webhook-relay                      │
                         │                                                  │
  GitHub/Stripe/etc.     │  ┌───────────┐   ┌───────────┐   ┌────────────┐  │
  ─── POST ──────────▶  │  │  Verify   │─▶│  Dedup    │─▶│  Persist   │  │
                         │  │  Signature│   │  (idemp.) │   │  to DB     │  │
                         │  └───────────┘   └───────────┘   └─────┬──────┘  │
                         │                                        │         │
                         │                                        ▼         │
                         │                                ┌───────────┐     │
                         │                                │  Enqueue  │     │
                         │                                │  (Celery) │     │
                         │                                └─────┬─────┘     │
                         └──────────────────────────────────────┼───────────┘
                                                                │
                                                          ┌─────┴─────┐
                                                          ▼           ▼
                                                       Success      DLQ
                                                     (delivered)  (manual retry)
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI |
| Database | PostgreSQL (asyncpg) |
| Task Queue | Celery + Redis |
| Migrations | Alembic |
| Testing | pytest, pytest-asyncio |
| Containerization | Docker, Docker Compose |

---

## Project Structure

```
webhook-relay/
├── app/
│   ├── main.py                    # FastAPI app factory & middleware
│   ├── config.py                  # Settings via pydantic-settings
│   ├── api/
│   │   ├── deps.py                # Dependency injection (DB session, etc.)
│   │   └── v1/
│   │       ├── webhooks.py        # POST /webhooks/{provider}
│   │       ├── events.py          # GET  /events, event detail, manual retry
│   │       └── health.py          # Liveness & readiness probes
│   ├── core/
│   │   ├── security.py            # HMAC signature verification
│   │   └── idempotency.py         # Idempotency key check & storage
│   ├── providers/                 # Strategy pattern — one module per provider
│   │   ├── base.py                # Abstract base: WebhookProvider
│   │   ├── github.py              # GitHub-specific implementation
│   │   └── stripe.py              # Stripe-specific implementation
│   ├── models/
│   │   ├── event.py               # WebhookEvent (immutable log)
│   │   └── delivery.py            # DeliveryAttempt (dispatch tracking)
│   ├── schemas/                   # Pydantic request/response schemas
│   ├── db/
│   │   ├── session.py             # Async engine & session factory
│   │   └── migrations/            # Alembic migration versions
│   └── workers/
│       ├── celery_app.py          # Celery instance & config
│       ├── tasks.py               # dispatch_event (retry with backoff)
│       └── dead_letter.py         # DLQ persistence & manual retry
├── tests/
│   ├── conftest.py                # Fixtures: test DB, async client, mock broker
│   ├── test_ingestion.py          # Signature, idempotency, persistence
│   ├── test_providers.py          # Per-provider strategy verification
│   ├── test_dispatch.py           # Retry logic, backoff, DLQ routing
│   └── test_events_api.py         # Event log queries & filtering
├── docker-compose.yml
├── Dockerfile
├── alembic.ini
├── pyproject.toml
└── .env.example
```

---

## Getting Started

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Make (optional, for shortcuts)

### Run with Docker Compose

```bash
# Clone the repo
git clone https://github.com/your-username/webhook-relay.git
cd webhook-relay

# Copy env template and fill in secrets
cp .env.example .env

# Start all services (app + PostgreSQL + Redis + Celery worker)
docker compose up --build
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### Run Locally (without Docker)

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Run database migrations
alembic upgrade head

# Start the API server
uvicorn app.main:app --reload

# In a separate terminal, start the Celery worker
celery -A app.workers.celery_app worker --loglevel=info
```

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/webhooks/{provider}` | Ingest a webhook event |
| `GET` | `/api/v1/events` | Query event log (filter by provider, type, date range) |
| `GET` | `/api/v1/events/{event_id}` | Event detail with delivery history |
| `POST` | `/api/v1/events/{event_id}/retry` | Re-dispatch a dead-lettered event |
| `GET` | `/health` | Liveness & readiness check |

### Example: Sending a Test Webhook

```bash
curl -X POST http://localhost:8000/api/v1/webhooks/github \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=<computed-signature>" \
  -H "X-GitHub-Event: push" \
  -H "X-GitHub-Delivery: <unique-delivery-id>" \
  -d '{"ref": "refs/heads/main", "commits": [...]}'
```

### Example: Querying the Event Log

```bash
# All events from GitHub
curl http://localhost:8000/api/v1/events?provider=github

# Filter by event type
curl http://localhost:8000/api/v1/events?event_type=push
```

---

## Configuration

Environment variables (see `.env.example`):

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | — |
| `REDIS_URL` | Redis connection string (Celery broker) | — |
| `GITHUB_WEBHOOK_SECRET` | Secret for GitHub signature verification | — |
| `STRIPE_WEBHOOK_SECRET` | Secret for Stripe signature verification | — |
| `MAX_RETRY_ATTEMPTS` | Retries before routing to DLQ | `5` |
| `RETRY_BASE_DELAY_SECONDS` | Initial backoff delay | `10` |

---

## Design Decisions

### Strategy Pattern for Providers

Each provider implements a common `WebhookProvider` interface with three methods: `verify_signature`, `extract_event_type`, and `extract_idempotency_key`. The ingestion endpoint is entirely provider-agnostic — adding support for a new provider means creating one file in `app/providers/` and registering it in the provider map. No existing code changes.

### Two-Model Data Design

`WebhookEvent` is an append-only record of what arrived. `DeliveryAttempt` tracks every dispatch effort separately. This separation keeps the audit log immutable while allowing delivery state to evolve through retries.

### Retry → DLQ → Manual Retry

Celery tasks retry with exponential backoff (10s → 20s → 40s → 80s → 160s). After exhausting retries, the event moves to a dead-letter queue with full error context. A dedicated endpoint lets you manually re-trigger delivery — useful for cases where a downstream service was down for maintenance.

---

## Running Tests

```bash
# Run all tests
pytest

# With coverage
pytest --cov=app --cov-report=term-missing

# Run a specific test file
pytest tests/test_ingestion.py -v
```

---

## Related Projects

- [**fintrack-api**](https://github.com/your-username/fintrack-api) — A financial tracking REST API demonstrating CRUD operations, JWT authentication, scheduled jobs, and domain modeling. Together with webhook-relay, these two projects cover complementary backend concerns: traditional REST API design vs. event-driven architecture.

---

## License

MIT