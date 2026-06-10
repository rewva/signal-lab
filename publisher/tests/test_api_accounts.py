"""Tests for account management, credential seeding, and posting-window endpoints."""

import pytest
from fastapi.testclient import TestClient

from publisher.api import create_app
from publisher.db import Database


class FakeVault:
    def __init__(self):
        self.store = {}

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value):
        self.store[key] = value


@pytest.fixture
def ctx(tmp_path):
    db = Database(tmp_path / "pub.db")
    db.init_schema()
    vault = FakeVault()
    client = TestClient(create_app(db, vault=vault))
    yield client, db, vault
    db.close()


def _account_body(**over):
    base = dict(brand="gk-quiz", platform="youtube", account_id="UC1")
    base.update(over)
    return base


# --- accounts ---------------------------------------------------------------

def test_create_account_returns_201_with_defaults(ctx):
    client, _, _ = ctx
    resp = client.post("/api/accounts", json=_account_body())
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] is not None
    assert body["token_broken"] is False
    assert body["token_key_ref"] == "gk-quiz:youtube"  # default


def test_create_account_with_credentials_seeds_vault(ctx):
    client, _, vault = ctx
    client.post("/api/accounts", json=_account_body(
        credentials={"refresh_token": "rt-1", "access_token": "at-1"}))
    assert vault.get("gk-quiz:youtube") == {"refresh_token": "rt-1", "access_token": "at-1"}


def test_create_account_unknown_platform_is_422(ctx):
    client, _, _ = ctx
    assert client.post("/api/accounts", json=_account_body(platform="tiktok")).status_code == 422


def test_list_accounts_reflects_token_health(ctx):
    client, db, _ = ctx
    acc_id = client.post("/api/accounts", json=_account_body()).json()["id"]
    db.mark_token_broken(acc_id, True)
    listed = client.get("/api/accounts").json()
    assert listed[0]["token_broken"] is True


# --- posting windows --------------------------------------------------------

def test_add_and_list_posting_window(ctx):
    client, _, _ = ctx
    acc_id = client.post("/api/accounts", json=_account_body()).json()["id"]
    resp = client.post(f"/api/accounts/{acc_id}/windows",
                       json={"time_slot": "09:00", "days_of_week": [0, 1, 2, 3, 4]})
    assert resp.status_code == 201
    windows = client.get(f"/api/accounts/{acc_id}/windows").json()
    assert windows == [{"time_slot": "09:00", "days_of_week": [0, 1, 2, 3, 4]}]


def test_add_window_to_unknown_account_is_404(ctx):
    client, _, _ = ctx
    resp = client.post("/api/accounts/9999/windows",
                       json={"time_slot": "09:00", "days_of_week": [0]})
    assert resp.status_code == 404


def test_window_rejects_out_of_range_day(ctx):
    client, _, _ = ctx
    acc_id = client.post("/api/accounts", json=_account_body()).json()["id"]
    resp = client.post(f"/api/accounts/{acc_id}/windows",
                       json={"time_slot": "09:00", "days_of_week": [7]})
    assert resp.status_code == 422
