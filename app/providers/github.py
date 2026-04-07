import hashlib
import hmac

from app.config import settings
from app.providers.base import WebhookProvider


class GitHubProvider(WebhookProvider):
    def verify_signature(self, payload: bytes, headers: dict[str, str]) -> bool:
        signature = headers.get("x-hub-signature-256", "")
        if not signature.startswith("sha256="):
            return False

        expected = hmac.new(
            settings.github_webhook_secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(signature[7:], expected)

    def extract_event_type(self, headers: dict[str, str], payload: dict) -> str:
        return headers.get("x-github-event", "unknown")

    def extract_idempotency_key(self, headers: dict[str, str], payload: dict) -> str:
        return headers.get("x-github-delivery", "")
