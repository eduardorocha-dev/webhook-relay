from app.providers.base import WebhookProvider
from app.providers.github import GitHubProvider

_registry: dict[str, WebhookProvider] = {
    "github": GitHubProvider(),
}


def get_provider(name: str) -> WebhookProvider | None:
    return _registry.get(name)
