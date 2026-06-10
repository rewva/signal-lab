"""Tests for posting_windows storage (drives default-slot scheduling at approval)."""

import pytest

from publisher.db import Database
from publisher.models import Account
from publisher.scheduler import PostingWindow


@pytest.fixture
def db(tmp_path):
    d = Database(tmp_path / "pub.db")
    d.init_schema()
    yield d
    d.close()


def _account(db, platform="youtube"):
    return db.add_account(Account(brand="gk-quiz", platform=platform,
                                  account_id=f"ACC-{platform}",
                                  token_key_ref=f"gk-quiz:{platform}"))


def test_add_and_list_posting_window_roundtrips(db):
    acc = _account(db)
    db.add_posting_window(acc.id, "09:00", [0, 1, 2, 3, 4])
    windows = db.list_posting_windows(acc.id)
    assert len(windows) == 1
    assert isinstance(windows[0], PostingWindow)
    assert windows[0].time_slot == "09:00"
    assert windows[0].days_of_week == [0, 1, 2, 3, 4]


def test_list_returns_only_that_accounts_windows(db):
    a = _account(db, "youtube")
    b = _account(db, "instagram")
    db.add_posting_window(a.id, "09:00", [0])
    db.add_posting_window(b.id, "18:00", [5, 6])
    assert [w.time_slot for w in db.list_posting_windows(a.id)] == ["09:00"]
    assert [w.time_slot for w in db.list_posting_windows(b.id)] == ["18:00"]


def test_list_empty_when_none_configured(db):
    acc = _account(db)
    assert db.list_posting_windows(acc.id) == []
