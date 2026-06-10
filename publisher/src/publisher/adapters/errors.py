"""Typed adapter exceptions. Adapters classify failures; the orchestrator decides retry."""

from __future__ import annotations


class AdapterError(Exception):
    """Base for all platform adapter failures."""


class RetryableError(AdapterError):
    """Transient failure (network, 5xx, rate-limit). Safe to retry with backoff."""


class FatalError(AdapterError):
    """Permanent failure (bad request, invalid credentials, policy rejection). Do not retry."""
