from __future__ import annotations

from .base import GenerationProvider
from .hosted_provider import HostedGeminiProvider
from .local_provider import LocalModelProvider
from .offline_provider import OfflineCompositeProvider

_PROVIDERS: dict[str, GenerationProvider] = {
    "offline": OfflineCompositeProvider(),
    "local": LocalModelProvider(),
    "hosted": HostedGeminiProvider(),
}


def get_provider(mode: str) -> GenerationProvider:
    return _PROVIDERS[mode]


def all_providers() -> list[dict]:
    return [p.describe() for p in _PROVIDERS.values()]
