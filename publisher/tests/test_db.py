"""Tests for the SQLite data layer: accounts, jobs, post_results."""

import pytest

from publisher.db import Database
from publisher.models import Account, Job, PostResult


@pytest.fixture
def db(tmp_path):
    d = Database(tmp_path / "pub.db")
    d.init_schema()
    yield d
    d.close()


# --- accounts ---------------------------------------------------------------

def test_add_account_assigns_id_and_defaults_token_healthy(db):
    acc = db.add_account(
        Account(brand="gk-quiz", platform="youtube", account_id="UC123",
                token_key_ref="gk-quiz:youtube")
    )
    assert acc.id is not None
    fetched = db.get_account(acc.id)
    assert fetched.brand == "gk-quiz"
    assert fetched.token_broken is False
    assert fetched.expires_at is None


def test_mark_token_broken_persists(db):
    acc = db.add_account(
        Account(brand="gk-quiz", platform="youtube", account_id="UC1",
                token_key_ref="gk-quiz:youtube")
    )
    db.mark_token_broken(acc.id, True)
    assert db.get_account(acc.id).token_broken is True


def test_list_accounts_for_brand_platform(db):
    db.add_account(Account(brand="gk-quiz", platform="youtube", account_id="UC1",
                           token_key_ref="k1"))
    db.add_account(Account(brand="psych", platform="youtube", account_id="UC2",
                           token_key_ref="k2"))
    rows = db.list_accounts(brand="gk-quiz")
    assert [a.account_id for a in rows] == ["UC1"]


# --- jobs -------------------------------------------------------------------

def _job(**over):
    base = dict(channel_id="gk-quiz", video_path="C:/v/quiz.mp4", title="Daily GK",
                description="desc", tags=["gk", "quiz"], platforms=["youtube", "instagram"],
                per_platform={"youtube": {"title": "YT title"}}, status="PENDING_APPROVAL")
    base.update(over)
    return Job(**base)


def test_create_job_assigns_id_and_submitted_at(db):
    job = db.create_job(_job())
    assert job.id is not None
    assert job.submitted_at is not None


def test_get_job_roundtrips_list_and_json_fields(db):
    job = db.create_job(_job(
        source_citation="Constitution of India, Art. 21",
        sources=["https://a.gov.in", "https://b.org"],
    ))
    got = db.get_job(job.id)
    assert got.tags == ["gk", "quiz"]
    assert got.platforms == ["youtube", "instagram"]
    assert got.per_platform["youtube"]["title"] == "YT title"
    assert got.source_citation == "Constitution of India, Art. 21"
    assert got.sources == ["https://a.gov.in", "https://b.org"]


def test_is_pending_true_for_in_flight_status(db):
    assert db.create_job(_job(status="SCHEDULED")).is_pending is True


@pytest.mark.parametrize("terminal", ["POSTED", "FAILED", "REJECTED"])
def test_is_pending_false_for_terminal_status(db, terminal):
    assert db.create_job(_job(status=terminal)).is_pending is False


def test_update_job_status_persists(db):
    job = db.create_job(_job())
    db.update_job_status(job.id, "APPROVED")
    assert db.get_job(job.id).status == "APPROVED"


def test_soft_delete_hides_job_from_default_get_and_list(db):
    job = db.create_job(_job())
    db.soft_delete_job(job.id)
    assert db.get_job(job.id) is None
    assert db.get_job(job.id, include_deleted=True).deleted_at is not None
    assert job.id not in [j.id for j in db.list_jobs()]


def test_list_jobs_filters_by_status(db):
    db.create_job(_job(status="SCHEDULED"))
    db.create_job(_job(status="POSTED"))
    assert [j.status for j in db.list_jobs(status="SCHEDULED")] == ["SCHEDULED"]


# --- post_results -----------------------------------------------------------

def test_record_post_result_links_to_job(db):
    job = db.create_job(_job())
    db.record_post_result(
        PostResult(job_id=job.id, platform="youtube", account_id="UC1",
                   external_post_id="vid123", post_url="https://youtu.be/vid123")
    )
    results = db.list_post_results(job.id)
    assert len(results) == 1
    assert results[0].post_url == "https://youtu.be/vid123"
    assert results[0].error is None


def test_reject_reason_defaults_empty_and_persists(tmp_path):
    from publisher.db import Database
    from publisher.models import Job
    db = Database(tmp_path / "pub.db"); db.init_schema()
    job = db.create_job(Job(channel_id="gk", video_path="x.mp4", title="T", status="PENDING_APPROVAL"))
    assert db.get_job(job.id).reject_reason == ""
    db.set_reject_reason(job.id, "fact wrong")
    assert db.get_job(job.id).reject_reason == "fact wrong"
    db.close()
