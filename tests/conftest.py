import hashlib
import hmac
import json

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.db.session import Base
from app.main import app as fastapi_app
from app.api.deps import get_db

TEST_DATABASE_URL = settings.database_url.replace("/webhookdb", "/webhookdb_test")

test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
TestSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db(setup_db):
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(db):
    async def override_get_db():
        yield db

    fastapi_app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(fastapi_app), base_url="http://test") as c:
        yield c

    fastapi_app.dependency_overrides.clear()


@pytest.fixture
def payload() -> bytes:
    return json.dumps({"ref": "refs/heads/main", "commits": []}).encode()


@pytest.fixture
def valid_headers(payload) -> dict:
    sig = hmac.new(
        settings.github_webhook_secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return {
        "content-type": "application/json",
        "x-hub-signature-256": f"sha256={sig}",
        "x-github-event": "push",
        "x-github-delivery": "test-delivery-001",
    }
