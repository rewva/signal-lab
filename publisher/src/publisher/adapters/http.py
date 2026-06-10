"""Shared HTTP status -> typed-error classification for platform adapters."""

from __future__ import annotations

from publisher.adapters.errors import FatalError, RetryableError


def classify_status(status_code: int) -> None:
    """Raise the right typed error for an HTTP status; return None on success.

    Transient (429 / 5xx) -> RetryableError; other client errors (4xx) -> FatalError.
    """
    if status_code < 400:
        return None
    if status_code == 429 or status_code >= 500:
        raise RetryableError(f"transient HTTP failure: {status_code}")
    raise FatalError(f"permanent HTTP failure: {status_code}")
