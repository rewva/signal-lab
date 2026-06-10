"""Tests for the FastAPI intake: POST /api/jobs is the one contract upstream pipelines use."""

import pytest
from fastapi.testclient import TestClient

from publisher.api import create_app
from publisher.db import Database


@pytest.fixture
def client(tmp_path):
    db = Database(tmp_path / "pub.db")
    db.init_schema()
    yield TestClient(create_app(db))
    db.close()


def _submission(**over):
    base = dict(
        channel_id="gk-quiz", video_path="C:/v/quiz.mp4", title="Daily GK",
        description="desc", tags=["gk", "quiz"], platforms=["youtube", "instagram"],
        per_platform={"youtube": {"title": "YT title"}},
    )
    base.update(over)
    return base


def test_health_ok(client):
    assert client.get("/health").status_code == 200


def test_submit_job_creates_pending_approval(client):
    resp = client.post("/api/jobs", json=_submission())
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] is not None
    assert body["status"] == "PENDING_APPROVAL"
    assert body["submitted_at"] is not None


def test_submitted_job_is_retrievable(client):
    job_id = client.post("/api/jobs", json=_submission()).json()["id"]
    got = client.get(f"/api/jobs/{job_id}")
    assert got.status_code == 200
    assert got.json()["title"] == "Daily GK"
    assert got.json()["per_platform"]["youtube"]["title"] == "YT title"


def test_submit_missing_required_field_is_422(client):
    bad = _submission()
    del bad["video_path"]
    assert client.post("/api/jobs", json=bad).status_code == 422


def test_submit_unknown_platform_is_422(client):
    assert client.post("/api/jobs", json=_submission(platforms=["tiktok"])).status_code == 422


def test_submit_empty_platforms_is_422(client):
    assert client.post("/api/jobs", json=_submission(platforms=[])).status_code == 422


def test_get_unknown_job_is_404(client):
    assert client.get("/api/jobs/9999").status_code == 404


def test_list_jobs_returns_submitted(client):
    client.post("/api/jobs", json=_submission())
    client.post("/api/jobs", json=_submission(title="Second"))
    listing = client.get("/api/jobs").json()
    assert len(listing) == 2
    assert {j["title"] for j in listing} == {"Daily GK", "Second"}
