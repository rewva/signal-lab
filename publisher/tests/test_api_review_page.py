"""Tests that GET / serves the review-queue HTML page wired to the right endpoints."""

import pytest
from fastapi.testclient import TestClient

from publisher.api import create_app
from publisher.db import Database


@pytest.fixture
def client(tmp_path):
    db = Database(tmp_path / "pub.db"); db.init_schema()
    yield TestClient(create_app(db))
    db.close()


def test_root_serves_html(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "Review Queue" in resp.text


def test_page_references_the_api_endpoints(client):
    html = client.get("/").text
    assert "/api/jobs?status=PENDING_APPROVAL" in html
    assert "/api/jobs/" in html
    assert "/approve" in html
    assert "/reject" in html
