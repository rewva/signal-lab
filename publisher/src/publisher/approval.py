"""Approval service: move a job from the PENDING_APPROVAL gate onward.

Approve -> APPROVED -> SCHEDULED, timed by an operator override or the next free per-account
posting window (falling back to "now" if no windows are configured). Reject -> REJECTED +
soft delete. Both enforce the lifecycle state machine.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from publisher.db import Database
from publisher.lifecycle import validate_transition
from publisher.models import Job
from publisher.scheduler import next_free_slot


def schedule_job(
    db: Database,
    job_id: int,
    now: datetime,
    scheduled_for: Optional[str] = None,
) -> Job:
    job = db.get_job(job_id)
    if job is None:
        raise LookupError(f"job {job_id} not found")
    validate_transition(job.status, "APPROVED")
    db.update_job_status(job_id, "APPROVED")

    when = scheduled_for or _default_slot(db, job, now) or now.isoformat()

    validate_transition("APPROVED", "SCHEDULED")
    db.update_job_status(job_id, "SCHEDULED")
    db.set_scheduled_for(job_id, when)
    return db.get_job(job_id)


def reject_job(db: Database, job_id: int, reason: str = "") -> Job:
    job = db.get_job(job_id)
    if job is None:
        raise LookupError(f"job {job_id} not found")
    validate_transition(job.status, "REJECTED")
    db.update_job_status(job_id, "REJECTED")
    if reason:
        db.set_reject_reason(job_id, reason)
    db.soft_delete_job(job_id)
    return db.get_job(job_id, include_deleted=True)


def _default_slot(db: Database, job: Job, now: datetime) -> Optional[str]:
    """Next free window across the brand's accounts, avoiding other SCHEDULED jobs."""
    windows = []
    for account in db.list_accounts(brand=job.channel_id):
        windows += db.list_posting_windows(account.id)
    occupied = [
        datetime.fromisoformat(j.scheduled_for)
        for j in db.list_jobs(status="SCHEDULED")
        if j.id != job.id and j.scheduled_for
    ]
    slot = next_free_slot(windows, now, occupied)
    return slot.isoformat() if slot else None
