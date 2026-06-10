"""Posting orchestrator: drive one SCHEDULED job through to POSTED (or FAILED/requeue).

Composes the tested pure pieces (lifecycle, normalizer, adapters, db). Per attempt it
normalises the source once, dispatches to each target platform's adapter (skipping any
platform that already succeeded on a prior attempt), and records a PostResult per platform.
Then it decides the job's fate:

- every platform succeeded            -> POSTED (+ posted_at)
- a FatalError / token-broken / config gap -> FAILED (+ alert), no retry
- only transient failures, attempts left   -> requeue SCHEDULED at now + backoff
- only transient failures, attempts spent   -> FAILED (+ alert)

Retry is non-blocking: the job goes back to SCHEDULED with a future scheduled_for, and the
scheduler picks it up again later -- no sleeping on the scheduler thread.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from publisher.adapters.errors import FatalError, RetryableError
from publisher.db import Database
from publisher.lifecycle import MAX_ATTEMPTS, validate_transition
from publisher.models import Job, PostResult


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PostingOrchestrator:
    def __init__(
        self,
        db: Database,
        vault: Any,  # anything with .get(token_key_ref) -> dict | None
        normalizer: Any,  # anything with .normalize(src, dst) -> str
        adapters: dict[str, Any],
        work_dir: str | os.PathLike[str],
        now: Callable[[], datetime] = _utcnow,
        backoff_seconds: int = 300,
        max_attempts: int = MAX_ATTEMPTS,
        alert: Optional[Callable[[str], None]] = None,
    ):
        self._db = db
        self._vault = vault
        self._normalizer = normalizer
        self._adapters = adapters
        self._work_dir = Path(work_dir)
        self._now = now
        self._backoff = backoff_seconds
        self._max_attempts = max_attempts
        self._alert = alert or (lambda _msg: None)

    def post_job(self, job: Job) -> None:
        validate_transition(job.status, "POSTING")
        self._db.update_job_status(job.id, "POSTING")
        attempt = self._db.increment_attempts(job.id)

        normalized = self._normalize(job)

        succeeded = self._succeeded_platforms(job.id)
        retryable_seen = False
        fatal_seen = False

        for platform in job.platforms:
            if platform in succeeded:
                continue  # already posted on a prior attempt -- never double-post
            try:
                self._publish_one(job, platform, normalized)
                succeeded.add(platform)
            except RetryableError as exc:
                self._record_error(job.id, platform, str(exc))
                retryable_seen = True
            except FatalError as exc:
                self._handle_fatal(job, platform, exc)
                fatal_seen = True

        self._resolve(job, attempt, succeeded, retryable_seen, fatal_seen)

    # --- steps --------------------------------------------------------------

    def _normalize(self, job: Job) -> str:
        dst = self._work_dir / "normalised" / str(job.id) / Path(job.video_path).name
        dst.parent.mkdir(parents=True, exist_ok=True)
        return self._normalizer.normalize(job.video_path, str(dst))

    def _publish_one(self, job: Job, platform: str, video_path: str) -> None:
        adapter = self._adapters[platform]
        accounts = self._db.list_accounts(brand=job.channel_id, platform=platform)
        if not accounts:
            raise FatalError(f"no connected account for {job.channel_id}/{platform}")
        account = accounts[0]
        credentials = self._vault.get(account.token_key_ref)
        if credentials is None:
            raise FatalError(f"no credentials in vault for {account.token_key_ref}")

        overrides = job.per_platform.get(platform, {})
        outcome = adapter.publish(
            video_path=video_path,
            title=overrides.get("title", job.title),
            description=overrides.get("description", job.description),
            tags=overrides.get("tags", job.tags),
            extra=overrides,
            credentials=credentials,
        )
        self._db.record_post_result(PostResult(
            job_id=job.id, platform=platform, account_id=account.account_id,
            external_post_id=outcome.external_post_id, post_url=outcome.post_url,
        ))

    def _handle_fatal(self, job: Job, platform: str, exc: FatalError) -> None:
        # a rejected refresh token is a FatalError subclass -> flag the account broken
        from publisher.adapters.youtube import TokenBrokenError

        accounts = self._db.list_accounts(brand=job.channel_id, platform=platform)
        if isinstance(exc, TokenBrokenError) and accounts:
            self._db.mark_token_broken(accounts[0].id, True)
        account_id = accounts[0].account_id if accounts else ""
        self._db.record_post_result(PostResult(
            job_id=job.id, platform=platform, account_id=account_id, error=str(exc),
        ))

    def _resolve(self, job: Job, attempt: int, succeeded: set[str],
                 retryable_seen: bool, fatal_seen: bool) -> None:
        if all(p in succeeded for p in job.platforms):
            self._db.update_job_status(job.id, "POSTED")
            self._db.set_posted_at(job.id, self._now().isoformat())
            return
        if fatal_seen or attempt >= self._max_attempts:
            self._db.update_job_status(job.id, "FAILED")
            self._alert(f"job {job.id} FAILED after {attempt} attempt(s)")
            return
        if retryable_seen:
            self._db.update_job_status(job.id, "SCHEDULED")
            self._db.set_scheduled_for(
                job.id, (self._now() + timedelta(seconds=self._backoff)).isoformat()
            )

    # --- helpers ------------------------------------------------------------

    def _succeeded_platforms(self, job_id: int) -> set[str]:
        return {r.platform for r in self._db.list_post_results(job_id) if r.error is None}

    def _record_error(self, job_id: int, platform: str, message: str) -> None:
        accounts = self._db.list_accounts()
        account_id = next((a.account_id for a in accounts if a.platform == platform), "")
        self._db.record_post_result(PostResult(
            job_id=job_id, platform=platform, account_id=account_id, error=message,
        ))
