import hashlib
import hmac
import json

import pytest

from app.config import settings
from app.providers.github import GitHubProvider
from app.providers.registry import get_provider

provider = GitHubProvider()


@pytest.fixture
def payload() -> bytes:
    return json.dumps({"ref": "refs/heads/main"}).encode()


def make_sig(payload: bytes) -> str:
    sig = hmac.new(settings.github_webhook_secret.encode(), payload, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


def test_registry_returns_github_provider():
    assert isinstance(get_provider("github"), GitHubProvider)


def test_registry_returns_none_for_unknown():
    assert get_provider("unknown") is None


def test_valid_signature(payload):
    assert provider.verify_signature(payload, {"x-hub-signature-256": make_sig(payload)})


def test_invalid_signature(payload):
    assert not provider.verify_signature(payload, {"x-hub-signature-256": "sha256=wrong"})


def test_missing_signature(payload):
    assert not provider.verify_signature(payload, {})


def test_extract_event_type():
    assert provider.extract_event_type({"x-github-event": "push"}, {}) == "push"


def test_extract_event_type_missing():
    assert provider.extract_event_type({}, {}) == "unknown"


def test_extract_idempotency_key():
    assert provider.extract_idempotency_key({"x-github-delivery": "abc-123"}, {}) == "abc-123"
