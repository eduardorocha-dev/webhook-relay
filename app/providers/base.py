from abc import ABC, abstractmethod


class WebhookProvider(ABC):
    """Abstract base for all webhook providers.

    Every provider must implement three methods:
    - verify_signature: reject forged requests at the gate
    - extract_event_type: normalize the event name (e.g. "push", "payment_intent.created")
    - extract_idempotency_key: unique delivery ID used for deduplication
    """

    @abstractmethod
    def verify_signature(self, payload: bytes, headers: dict[str, str]) -> bool:
        """Return True if the request signature is valid, False otherwise."""

    @abstractmethod
    def extract_event_type(self, headers: dict[str, str], payload: dict) -> str:
        """Return the event type string for this delivery."""

    @abstractmethod
    def extract_idempotency_key(self, headers: dict[str, str], payload: dict) -> str:
        """Return a unique key that identifies this delivery for deduplication."""
