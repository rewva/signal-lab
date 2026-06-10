"""Tests for the posting orchestrator (executor): dispatch, retry/backoff, lifecycle."""

from datetime import datetime, timedelta, timezone

import pytest

from publisher.adapters.errors import FatalError, RetryableError
from publisher.adapters.youtube import TokenBrokenError
from publisher.db import Database
from publisher.models import Account, Job, PostResult
from publisher.orchestrator import PostingOrchestrator

NOW = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)
BACKOFF = 300


class FakeAdapter:
    def __init__(self, platform, outcome=None, error=None):
        self.platform = platform
        self._outcome = outcome
        self._error = error
        self.calls = []

    def publish(self, *, video_path, title, description, tags, extra, credentials):
        self.calls.append(dict(video_path=video_path, title=title,
                               description=description, tags=tags, extra=extra,
                               credentials=credentials))
        if self._error:
            raise self._error
        return self._outcome


class FakeNormalizer:
    def __init__(self):
        self.calls = []

    def normalize(self, src, dst):
        self.calls.append((src, dst))
        return "NORMALIZED.mp4"


class FakeVault:
    def __init__(self, creds):
        self._creds = creds

    def get(self, key):
        return self._creds.get(key)


class Outcome:
    def __init__(self, external_post_id, post_url=None):
        self.external_post_id = external_post_id
        self.post_url = post_url


@pytest.fixture
def db(tmp_path):
    d = Database(tmp_path / "pub.db")
    d.init_schema()
    yield d
    d.close()


def build(db, tmp_path, adapters, vault_creds, alerts=None):
    return PostingOrchestrator(
        db=db,
        vault=FakeVault(vault_creds),
        normalizer=FakeNormalizer(),
        adapters=adapters,
        work_dir=tmp_path / "work",
        now=lambda: NOW,
        backoff_seconds=BACKOFF,
        alert=(alerts.append if alerts is not None else None),
    )


def make_job(db, platforms, **over):
    base = dict(channel_id="gk-quiz", video_path="C:/v/quiz.mp4", title="Daily GK",
                description="d", tags=["gk"], platforms=platforms, status="SCHEDULED")
    base.update(over)
    return db.create_job(Job(**base))


def add_account(db, platform, key="gk-quiz:" ):
    db.add_account(Account(brand="gk-quiz", platform=platform,
                           account_id=f"ACC-{platform}", token_key_ref=key + platform))


# --- happy path -------------------------------------------------------------

def test_single_platform_success_marks_posted(db, tmp_path):
    add_account(db, "youtube")
    job = make_job(db, ["youtube"])
    yt = FakeAdapter("youtube", outcome=Outcome("vid1", "https://youtu.be/vid1"))
    orch = build(db, tmp_path, {"youtube": yt}, {"gk-quiz:youtube": {"access_token": "x"}})

    orch.post_job(job)

    got = db.get_job(job.id)
    assert got.status == "POSTED"
    assert got.posted_at == NOW.isoformat()
    results = db.list_post_results(job.id)
    assert len(results) == 1
    assert results[0].external_post_id == "vid1"
    assert results[0].error is None


def test_adapter_receives_normalized_path_and_metadata(db, tmp_path):
    add_account(db, "youtube")
    job = make_job(db, ["youtube"])
    yt = FakeAdapter("youtube", outcome=Outcome("vid1"))
    build(db, tmp_path, {"youtube": yt}, {"gk-quiz:youtube": {"access_token": "x"}}).post_job(job)
    assert yt.calls[0]["video_path"] == "NORMALIZED.mp4"
    assert yt.calls[0]["title"] == "Daily GK"
    assert yt.calls[0]["credentials"] == {"access_token": "x"}


def test_per_platform_title_override_is_applied(db, tmp_path):
    add_account(db, "youtube")
    job = make_job(db, ["youtube"], per_platform={"youtube": {"title": "Custom YT Title"}})
    yt = FakeAdapter("youtube", outcome=Outcome("vid1"))
    build(db, tmp_path, {"youtube": yt}, {"gk-quiz:youtube": {"access_token": "x"}}).post_job(job)
    assert yt.calls[0]["title"] == "Custom YT Title"


def test_multi_platform_all_success(db, tmp_path):
    add_account(db, "youtube")
    add_account(db, "instagram")
    job = make_job(db, ["youtube", "instagram"])
    adapters = {"youtube": FakeAdapter("youtube", outcome=Outcome("v")),
                "instagram": FakeAdapter("instagram", outcome=Outcome("i"))}
    creds = {"gk-quiz:youtube": {"a": 1}, "gk-quiz:instagram": {"b": 2}}
    build(db, tmp_path, adapters, creds).post_job(job)
    assert db.get_job(job.id).status == "POSTED"
    assert len(db.list_post_results(job.id)) == 2


# --- retry / backoff --------------------------------------------------------

def test_retryable_failure_requeues_with_backoff(db, tmp_path):
    add_account(db, "youtube")
    add_account(db, "instagram")
    job = make_job(db, ["youtube", "instagram"])
    adapters = {"youtube": FakeAdapter("youtube", outcome=Outcome("v")),
                "instagram": FakeAdapter("instagram", error=RetryableError("503"))}
    creds = {"gk-quiz:youtube": {"a": 1}, "gk-quiz:instagram": {"b": 2}}
    build(db, tmp_path, adapters, creds).post_job(job)

    got = db.get_job(job.id)
    assert got.status == "SCHEDULED"
    assert got.scheduled_for == (NOW + timedelta(seconds=BACKOFF)).isoformat()
    assert got.attempts == 1


def test_retry_skips_already_succeeded_platform(db, tmp_path):
    add_account(db, "youtube")
    add_account(db, "instagram")
    job = make_job(db, ["youtube", "instagram"])
    # youtube already posted on a prior attempt
    db.record_post_result(PostResult(job_id=job.id, platform="youtube",
                                     account_id="ACC-youtube", external_post_id="old"))
    yt = FakeAdapter("youtube", outcome=Outcome("should-not-be-called"))
    ig = FakeAdapter("instagram", outcome=Outcome("i"))
    creds = {"gk-quiz:youtube": {"a": 1}, "gk-quiz:instagram": {"b": 2}}
    build(db, tmp_path, {"youtube": yt, "instagram": ig}, creds).post_job(job)

    assert yt.calls == []           # not re-posted
    assert len(ig.calls) == 1
    assert db.get_job(job.id).status == "POSTED"


def test_retryable_failure_at_last_attempt_fails(db, tmp_path):
    add_account(db, "youtube")
    job = make_job(db, ["youtube"])
    db.increment_attempts(job.id)   # 1
    db.increment_attempts(job.id)   # 2 -> this run makes it 3 == MAX
    alerts = []
    yt = FakeAdapter("youtube", error=RetryableError("503"))
    build(db, tmp_path, {"youtube": yt}, {"gk-quiz:youtube": {"a": 1}}, alerts).post_job(job)

    assert db.get_job(job.id).status == "FAILED"
    assert len(alerts) == 1


# --- fatal / token-broken / missing account ---------------------------------

def test_fatal_error_fails_immediately_without_requeue(db, tmp_path):
    add_account(db, "youtube")
    job = make_job(db, ["youtube"])
    alerts = []
    yt = FakeAdapter("youtube", error=FatalError("400 bad request"))
    build(db, tmp_path, {"youtube": yt}, {"gk-quiz:youtube": {"a": 1}}, alerts).post_job(job)

    got = db.get_job(job.id)
    assert got.status == "FAILED"
    assert got.scheduled_for is None
    assert len(alerts) == 1


def test_token_broken_marks_account_and_fails(db, tmp_path):
    add_account(db, "youtube")
    job = make_job(db, ["youtube"])
    yt = FakeAdapter("youtube", error=TokenBrokenError("refresh rejected"))
    build(db, tmp_path, {"youtube": yt}, {"gk-quiz:youtube": {"a": 1}}).post_job(job)

    assert db.get_job(job.id).status == "FAILED"
    acc = db.list_accounts(brand="gk-quiz", platform="youtube")[0]
    assert acc.token_broken is True


def test_missing_account_fails_the_job(db, tmp_path):
    job = make_job(db, ["youtube"])  # no account added
    yt = FakeAdapter("youtube", outcome=Outcome("v"))
    build(db, tmp_path, {"youtube": yt}, {}).post_job(job)
    assert db.get_job(job.id).status == "FAILED"
    assert yt.calls == []  # never attempted without an account
