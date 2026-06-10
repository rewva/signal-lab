"""Tests for the DB capabilities the posting orchestrator needs: attempts + setters."""

import pytest

from publisher.db import Database
from publisher.models import Job


@pytest.fixture
def db(tmp_path):
    d = Database(tmp_path / "pub.db")
    d.init_schema()
    yield d
    d.close()


def _job(**over):
    base = dict(channel_id="gk-quiz", video_path="v.mp4", title="t",
                status="SCHEDULED")
    base.update(over)
    return Job(**base)


def test_new_job_starts_with_zero_attempts(db):
    assert db.create_job(_job()).attempts == 0
    assert db.get_job(db.create_job(_job()).id).attempts == 0


def test_increment_attempts_persists_and_returns_new_count(db):
    job = db.create_job(_job())
    assert db.increment_attempts(job.id) == 1
    assert db.increment_attempts(job.id) == 2
    assert db.get_job(job.id).attempts == 2


def test_set_scheduled_for_persists(db):
    job = db.create_job(_job())
    db.set_scheduled_for(job.id, "2026-06-09T09:00:00+00:00")
    assert db.get_job(job.id).scheduled_for == "2026-06-09T09:00:00+00:00"


def test_set_posted_at_persists(db):
    job = db.create_job(_job())
    db.set_posted_at(job.id, "2026-06-08T10:00:00+00:00")
    assert db.get_job(job.id).posted_at == "2026-06-08T10:00:00+00:00"
