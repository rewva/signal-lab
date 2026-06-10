"""Platform publish adapters (YouTube / Facebook / Instagram)."""

from publisher.adapters.base import Adapter, PublishOutcome
from publisher.adapters.errors import AdapterError, FatalError, RetryableError

__all__ = [
    "Adapter",
    "PublishOutcome",
    "AdapterError",
    "RetryableError",
    "FatalError",
]
