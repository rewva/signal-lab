"""Integration tests for the runtime wiring: app + scheduler tick over the orchestrator."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from publisher.bootstrap import build_runtime
from publisher.config import Settings
from publisher.models import Account, Job

NOW = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)


class FakeAdapter:
    platform = "youtube"

    def __init__(self):
        self.calls = []

    def publish(self, *, video_path, title, description, tags, extra, credentials):
        self.calls.append(title)

        class _O:
            external_post_id = "vid1"
            post_url = "https://youtu.be/vid1"

        return _O()


class FakeNormalizer:
    def normalize(self, src, dst):
        return dst


class FakeVault:
    def get(self, key):
        return {"access_token": "x"}


@pytest.fixture
def runtime(tmp_path):
    settings = Settings(
        db_path=str(tmp_path / "pub.db"),
        vault_path=str(tmp_path / "tokens.enc"),
        work_dir=str(tmp_path / "work"),
    )
    return build_runtime(
        settings,
        adapters={"youtube": FakeAdapter()},
        vault=FakeVault(),
        normalizer=FakeNormalizer(),
    )


def test_health_endpoint_is_wired(runtime):
    assert TestClient(runtime.app).get("/health").status_code == 200


def test_schema_initialised(runtime):
    # the db is usable immediately -- accounts table exists
    assert runtime.db.list_accounts() == []


def test_tick_posts_a_due_scheduled_job(runtime):
    runtime.db.add_account(Account(brand="gk-quiz", platform="youtube",
                                   account_id="UC1", token_key_ref="gk-quiz:youtube"))
    job = runtime.db.create_job(Job(
        channel_id="gk-quiz", video_path="v.mp4", title="Daily GK",
        platforms=["youtube"], status="SCHEDULED",
        scheduled_for=(NOW - timedelta(minutes=1)).isoformat(),
    ))
    runtime.tick(now=NOW)
    assert runtime.db.get_job(job.id).status == "POSTED"


def test_tick_ignores_future_job(runtime):
    runtime.db.add_account(Account(brand="gk-quiz", platform="youtube",
                                   account_id="UC1", token_key_ref="gk-quiz:youtube"))
    job = runtime.db.create_job(Job(
        channel_id="gk-quiz", video_path="v.mp4", title="t",
        platforms=["youtube"], status="SCHEDULED",
        scheduled_for=(NOW + timedelta(hours=1)).isoformat(),
    ))
    runtime.tick(now=NOW)
    assert runtime.db.get_job(job.id).status == "SCHEDULED"
