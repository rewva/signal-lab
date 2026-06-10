"""Plain data models for the publisher's SQLite rows.

Kept deliberately simple (dataclasses, no ORM) to honour the <150MB-RAM monolith
constraint. List/dict fields are JSON-serialised by the data layer; timestamps are
ISO-8601 UTC strings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

# Statuses for which a job is still "in flight". is_pending is computed, never stored
# (mirrors the SM reference: cleaner under races than a stored enum).
TERMINAL_STATUSES = frozenset({"POSTED", "FAILED", "REJECTED"})


@dataclass
class Account:
    brand: str
    platform: str  # youtube | facebook | instagram
    account_id: str  # the platform's own id (channel id, page id, ig user id)
    token_key_ref: str  # key into the TokenVault, e.g. "gk-quiz:youtube"
    token_broken: bool = False
    expires_at: Optional[str] = None  # ISO-8601 UTC; for inline health checks
    id: Optional[int] = None


@dataclass
class Job:
    channel_id: str
    video_path: str
    title: str
    description: str = ""
    tags: list[str] = field(default_factory=list)
    platforms: list[str] = field(default_factory=list)
    per_platform: dict[str, Any] = field(default_factory=dict)
    status: str = "SUBMITTED"
    submitted_at: Optional[str] = None
    scheduled_for: Optional[str] = None
    posted_at: Optional[str] = None
    deleted_at: Optional[str] = None
    attempts: int = 0  # posting attempts made; drives retry-vs-fail
    id: Optional[int] = None

    @property
    def is_pending(self) -> bool:
        return self.status not in TERMINAL_STATUSES


@dataclass
class PostResult:
    job_id: int
    platform: str
    account_id: str
    external_post_id: Optional[str] = None
    post_url: Optional[str] = None
    error: Optional[str] = None
    created_at: Optional[str] = None
    id: Optional[int] = None
