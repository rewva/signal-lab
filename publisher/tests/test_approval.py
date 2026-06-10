"""Tests for the approval service: PENDING_APPROVAL -> SCHEDULED, or -> REJECTED."""

from datetime import datetime, timedelta, timezone

import pytest

from publisher.approval import reject_job, schedule_job
from publisher.db import Database
from publisher.lifecycle import InvalidTransition
from publisher.models import Account, Job

NOW = datetime(2026, 6, 8, 8, 0, 0, tzinfo=timezone.utc)
ALL_DAYS = [0, 1, 2, 3, 4, 5, 6]


@pytest.fixture
def db(tmp_path):
    d = Database(tmp_path / "pub.db")
    d.init_schema()
    yield d
    d.close()


def _pending_job(db, **over):
    base = dict(channel_id="gk-quiz", video_path="v.mp4", title="t",
                platforms=["youtube"], status="PENDING_APPROVAL")
    base.update(over)
    return db.create_job(Job(**base))


def _account_with_window(db, time_slot="09:00", days=ALL_DAYS):
    acc = db.add_account(Account(brand="gk-quiz", platform="youtube",
                                 account_id="UC1", token_key_ref="gk-quiz:youtube"))
    db.add_posting_window(acc.id, time_slot, days)
    return acc


def test_explicit_time_schedules_at_that_time(db):
    job = _pending_job(db)
    when = "2026-06-10T15:30:00+00:00"
    result = schedule_job(db, job.id, now=NOW, scheduled_for=when)
    assert result.status == "SCHEDULED"
    assert db.get_job(job.id).scheduled_for == when


def test_default_uses_next_posting_window(db):
    _account_with_window(db, "09:00")
    job = _pending_job(db)
    schedule_job(db, job.id, now=NOW)  # NOW is 08:00 -> next 09:00 slot today
    assert db.get_job(job.id).scheduled_for == datetime(2026, 6, 8, 9, 0, tzinfo=timezone.utc).isoformat()


def test_default_skips_slot_occupied_by_another_scheduled_job(db):
    _account_with_window(db, "09:00")
    _account_with_window(db, "12:00")
    # an existing SCHEDULED job occupies ~09:00
    db.create_job(Job(channel_id="gk-quiz", video_path="x", title="x",
                      platforms=["youtube"], status="SCHEDULED",
                      scheduled_for=datetime(2026, 6, 8, 9, 5, tzinfo=timezone.utc).isoformat()))
    job = _pending_job(db)
    schedule_job(db, job.id, now=NOW)
    assert db.get_job(job.id).scheduled_for == datetime(2026, 6, 8, 12, 0, tzinfo=timezone.utc).isoformat()


def test_no_windows_schedules_immediately(db):
    job = _pending_job(db)  # no account/windows configured
    schedule_job(db, job.id, now=NOW)
    got = db.get_job(job.id)
    assert got.status == "SCHEDULED"
    assert got.scheduled_for == NOW.isoformat()


def test_schedule_rejects_non_pending_job(db):
    job = _pending_job(db, status="POSTED")
    with pytest.raises(InvalidTransition):
        schedule_job(db, job.id, now=NOW)


def test_reject_marks_rejected_and_soft_deletes(db):
    job = _pending_job(db)
    result = reject_job(db, job.id)
    assert result.status == "REJECTED"
    assert db.get_job(job.id) is None  # soft-deleted, hidden by default
    assert db.get_job(job.id, include_deleted=True).status == "REJECTED"


def test_reject_non_pending_raises(db):
    job = _pending_job(db, status="SCHEDULED")
    with pytest.raises(InvalidTransition):
        reject_job(db, job.id)
