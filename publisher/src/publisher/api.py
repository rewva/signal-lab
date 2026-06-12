"""FastAPI intake. POST /api/jobs is the single contract every upstream pipeline uses.

Pipelines (daily-gk-quiz, future channels) stay decoupled -- they submit a video path plus
metadata and never learn how posting works. Submitted jobs land in PENDING_APPROVAL and wait
for the operator's approval gate before scheduling.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field, field_validator

from publisher.approval import reject_job, schedule_job
from publisher.db import Database
from publisher.lifecycle import InvalidTransition
from publisher.models import Account, Job

ALLOWED_PLATFORMS = {"youtube", "facebook", "instagram"}

_REVIEW_PAGE = Path(__file__).parent / "static" / "review.html"


class JobSubmission(BaseModel):
    channel_id: str
    video_path: str
    title: str
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    platforms: list[str]
    per_platform: dict[str, Any] = Field(default_factory=dict)
    source_citation: str = ""
    sources: list[str] = Field(default_factory=list)

    @field_validator("platforms")
    @classmethod
    def _validate_platforms(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("at least one platform is required")
        unknown = set(value) - ALLOWED_PLATFORMS
        if unknown:
            raise ValueError(f"unknown platform(s): {sorted(unknown)}")
        return value


class ApproveRequest(BaseModel):
    scheduled_for: Optional[str] = None  # ISO-8601 override; omit for the next free slot


class RejectRequest(BaseModel):
    reason: str = ""


class AccountCreate(BaseModel):
    brand: str
    platform: str
    account_id: str
    token_key_ref: Optional[str] = None  # defaults to "<brand>:<platform>"
    credentials: Optional[dict[str, Any]] = None  # seeded into the vault if provided

    @field_validator("platform")
    @classmethod
    def _validate_platform(cls, value: str) -> str:
        if value not in ALLOWED_PLATFORMS:
            raise ValueError(f"unknown platform: {value}")
        return value


class AccountView(BaseModel):
    id: int
    brand: str
    platform: str
    account_id: str
    token_key_ref: str
    token_broken: bool
    expires_at: Optional[str]


class WindowCreate(BaseModel):
    time_slot: str  # "HH:MM"
    days_of_week: list[int]

    @field_validator("days_of_week")
    @classmethod
    def _validate_days(cls, value: list[int]) -> list[int]:
        if any(d < 0 or d > 6 for d in value):
            raise ValueError("days_of_week must be 0 (Mon) .. 6 (Sun)")
        return value


class WindowView(BaseModel):
    time_slot: str
    days_of_week: list[int]


def _to_account_view(account: Account) -> "AccountView":
    return AccountView(
        id=account.id, brand=account.brand, platform=account.platform,
        account_id=account.account_id, token_key_ref=account.token_key_ref,
        token_broken=account.token_broken, expires_at=account.expires_at,
    )


class JobView(BaseModel):
    id: int
    channel_id: str
    title: str
    description: str
    status: str
    platforms: list[str]
    per_platform: dict[str, Any]
    submitted_at: str | None
    scheduled_for: str | None
    source_citation: str
    sources: list[str]
    reject_reason: str


def _to_view(job: Job) -> JobView:
    return JobView(
        id=job.id, channel_id=job.channel_id, title=job.title,
        description=job.description, status=job.status,
        platforms=job.platforms, per_platform=job.per_platform,
        submitted_at=job.submitted_at, scheduled_for=job.scheduled_for,
        source_citation=job.source_citation, sources=job.sources,
        reject_reason=job.reject_reason,
    )


def create_app(db: Database, vault: Any = None) -> FastAPI:
    app = FastAPI(title="signal-lab-publisher")

    @app.get("/", response_class=HTMLResponse)
    def review_page() -> HTMLResponse:
        return HTMLResponse(_REVIEW_PAGE.read_text(encoding="utf-8"))

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/jobs", status_code=201, response_model=JobView)
    def submit_job(submission: JobSubmission) -> JobView:
        job = db.create_job(Job(
            channel_id=submission.channel_id, video_path=submission.video_path,
            title=submission.title, description=submission.description,
            tags=submission.tags, platforms=submission.platforms,
            per_platform=submission.per_platform, status="PENDING_APPROVAL",
            source_citation=submission.source_citation, sources=submission.sources,
        ))
        return _to_view(job)

    @app.get("/api/jobs", response_model=list[JobView])
    def list_jobs(status: str | None = None) -> list[JobView]:
        return [_to_view(j) for j in db.list_jobs(status=status)]

    @app.get("/api/jobs/{job_id}", response_model=JobView)
    def get_job(job_id: int) -> JobView:
        job = db.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")
        return _to_view(job)

    @app.get("/api/jobs/{job_id}/video")
    def get_job_video(job_id: int) -> FileResponse:
        job = db.get_job(job_id)
        if job is None or not job.video_path or not Path(job.video_path).is_file():
            raise HTTPException(status_code=404, detail="video not found")
        return FileResponse(job.video_path, media_type="video/mp4")

    @app.post("/api/jobs/{job_id}/approve", response_model=JobView)
    def approve_job(job_id: int, body: ApproveRequest | None = None) -> JobView:
        scheduled_for = body.scheduled_for if body else None
        try:
            job = schedule_job(db, job_id, now=datetime.now(timezone.utc),
                               scheduled_for=scheduled_for)
        except LookupError:
            raise HTTPException(status_code=404, detail="job not found")
        except InvalidTransition as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        return _to_view(job)

    @app.post("/api/jobs/{job_id}/reject", response_model=JobView)
    def reject(job_id: int, body: RejectRequest | None = None) -> JobView:
        reason = body.reason if body else ""
        try:
            job = reject_job(db, job_id, reason=reason)
        except LookupError:
            raise HTTPException(status_code=404, detail="job not found")
        except InvalidTransition as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        return _to_view(job)

    # --- accounts -----------------------------------------------------------

    @app.post("/api/accounts", status_code=201, response_model=AccountView)
    def create_account(body: AccountCreate) -> AccountView:
        token_key_ref = body.token_key_ref or f"{body.brand}:{body.platform}"
        if body.credentials is not None:
            if vault is None:
                raise HTTPException(status_code=400,
                                    detail="no vault configured to store credentials")
            vault.set(token_key_ref, body.credentials)
        account = db.add_account(Account(
            brand=body.brand, platform=body.platform, account_id=body.account_id,
            token_key_ref=token_key_ref,
        ))
        return _to_account_view(account)

    @app.get("/api/accounts", response_model=list[AccountView])
    def list_accounts() -> list[AccountView]:
        return [_to_account_view(a) for a in db.list_accounts()]

    # --- posting windows ----------------------------------------------------

    @app.post("/api/accounts/{account_id}/windows", status_code=201,
              response_model=WindowView)
    def add_window(account_id: int, body: WindowCreate) -> WindowView:
        if db.get_account(account_id) is None:
            raise HTTPException(status_code=404, detail="account not found")
        db.add_posting_window(account_id, body.time_slot, body.days_of_week)
        return WindowView(time_slot=body.time_slot, days_of_week=body.days_of_week)

    @app.get("/api/accounts/{account_id}/windows", response_model=list[WindowView])
    def list_windows(account_id: int) -> list[WindowView]:
        if db.get_account(account_id) is None:
            raise HTTPException(status_code=404, detail="account not found")
        return [WindowView(time_slot=w.time_slot, days_of_week=w.days_of_week)
                for w in db.list_posting_windows(account_id)]

    return app
