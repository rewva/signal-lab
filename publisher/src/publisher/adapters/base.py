"""Adapter base class and the lightweight publish-result value object."""

from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class PublishOutcome:
    """What a successful publish returns, before it is persisted as a PostResult."""

    external_post_id: str
    post_url: Optional[str] = None


class Adapter(abc.ABC):
    """One platform's publish contract. Each concrete adapter fully encapsulates its HTTP.

    Implementations set ``platform`` and raise RetryableError / FatalError on failure --
    never retrying internally.
    """

    platform: str

    @abc.abstractmethod
    def publish(
        self,
        *,
        video_path: str,
        title: str,
        description: str,
        tags: list[str],
        extra: dict[str, Any],
        credentials: dict[str, Any],
    ) -> PublishOutcome:
        """Publish the normalised video and return its external id + url."""
        raise NotImplementedError
