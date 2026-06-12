"""Tests for GET /api/jobs/{id}/video -- streams the MP4 for the review dashboard."""

import pytest
from fastapi.testclient import TestClient

from publisher.api import create_app
from publisher.db import Database
from publisher.models import Job


@pytest.fixture
def client(tmp_path):
    db = Database(tmp_path / "pub.db"); db.init_schema()
    yield TestClient(create_app(db)), db, tmp_path
    db.close()


def test_video_streams_existing_file(client):
    tc, db, tmp_path = client
    video = tmp_path / "quiz.mp4"
    video.write_bytes(b"\x00\x00\x00\x18ftypmp42fake-mp4-bytes")
    job = db.create_job(Job(channel_id="gk", video_path=str(video), title="T",
                            status="PENDING_APPROVAL"))
    resp = tc.get(f"/api/jobs/{job.id}/video")
    assert resp.status_code == 200
    assert resp.content == b"\x00\x00\x00\x18ftypmp42fake-mp4-bytes"
    assert "video" in resp.headers["content-type"]


def test_video_supports_range_requests(client):
    # FileResponse serves partial content so the browser <video> can seek/scrub.
    tc, db, tmp_path = client
    video = tmp_path / "quiz.mp4"
    video.write_bytes(b"\x00\x00\x00\x18ftypmp42fake-mp4-bytes")
    job = db.create_job(Job(channel_id="gk", video_path=str(video), title="T",
                            status="PENDING_APPROVAL"))
    resp = tc.get(f"/api/jobs/{job.id}/video", headers={"Range": "bytes=0-3"})
    assert resp.status_code == 206
    assert resp.content == b"\x00\x00\x00\x18"


def test_video_missing_job_is_404(client):
    tc, db, tmp_path = client
    assert tc.get("/api/jobs/999/video").status_code == 404


def test_video_missing_file_is_404(client):
    tc, db, tmp_path = client
    job = db.create_job(Job(channel_id="gk", video_path=str(tmp_path / "gone.mp4"),
                            title="T", status="PENDING_APPROVAL"))
    assert tc.get(f"/api/jobs/{job.id}/video").status_code == 404


def test_video_empty_path_is_404(client):
    tc, db, tmp_path = client
    job = db.create_job(Job(channel_id="gk", video_path="", title="T",
                            status="PENDING_APPROVAL"))
    assert tc.get(f"/api/jobs/{job.id}/video").status_code == 404
