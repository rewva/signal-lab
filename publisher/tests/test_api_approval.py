"""Tests for the approve/reject endpoints."""

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


def _submit(client, **over):
    base = dict(channel_id="gk-quiz", video_path="v.mp4", title="t",
                platforms=["youtube"])
    base.update(over)
    return client.post("/api/jobs", json=base).json()["id"]


def test_approve_without_body_schedules_job(client):
    job_id = _submit(client)
    resp = client.post(f"/api/jobs/{job_id}/approve")
    assert resp.status_code == 200
    assert resp.json()["status"] == "SCHEDULED"
    assert resp.json()["scheduled_for"] is not None


def test_approve_with_explicit_time(client):
    job_id = _submit(client)
    when = "2026-06-10T15:30:00+00:00"
    resp = client.post(f"/api/jobs/{job_id}/approve", json={"scheduled_for": when})
    assert resp.status_code == 200
    assert resp.json()["scheduled_for"] == when


def test_approve_unknown_job_is_404(client):
    assert client.post("/api/jobs/9999/approve").status_code == 404


def test_approve_already_scheduled_is_409(client):
    job_id = _submit(client)
    client.post(f"/api/jobs/{job_id}/approve")           # -> SCHEDULED
    second = client.post(f"/api/jobs/{job_id}/approve")  # invalid from SCHEDULED
    assert second.status_code == 409


def test_reject_marks_rejected_and_hides_job(client):
    job_id = _submit(client)
    resp = client.post(f"/api/jobs/{job_id}/reject")
    assert resp.status_code == 200
    assert resp.json()["status"] == "REJECTED"
    assert client.get(f"/api/jobs/{job_id}").status_code == 404  # soft-deleted


def test_reject_unknown_job_is_404(client):
    assert client.post("/api/jobs/9999/reject").status_code == 404
