"""Unit tests for the account-connect helper's pure logic + Meta discovery flow."""

import pytest

from publisher.connect import (
    account_payload,
    fb_credentials,
    ig_credentials,
    meta_exchange_long_lived,
    meta_ig_user_id,
    meta_list_pages,
    pick_page,
    youtube_credentials,
)


def test_credential_shapes_match_adapters():
    assert youtube_credentials("rt") == {"refresh_token": "rt"}
    assert fb_credentials({"id": "P1", "access_token": "tok"}) == {
        "page_id": "P1", "page_access_token": "tok"}
    assert ig_credentials("IG1", "tok") == {"ig_user_id": "IG1", "access_token": "tok"}


def test_account_payload_defaults_token_key_ref():
    p = account_payload("daily-gk-quiz", "youtube", "chan", {"refresh_token": "rt"})
    assert p["token_key_ref"] == "daily-gk-quiz:youtube"
    assert p["platform"] == "youtube" and p["credentials"] == {"refresh_token": "rt"}


def test_pick_page_single_auto():
    pages = [{"id": "P1", "name": "GK"}]
    assert pick_page(pages, None)["id"] == "P1"


def test_pick_page_by_name_and_id():
    pages = [{"id": "P1", "name": "GK"}, {"id": "P2", "name": "Other"}]
    assert pick_page(pages, "P2")["name"] == "Other"
    assert pick_page(pages, "GK")["id"] == "P1"


def test_pick_page_ambiguous_or_missing_raises():
    pages = [{"id": "P1", "name": "GK"}, {"id": "P2", "name": "Other"}]
    with pytest.raises(SystemExit):
        pick_page(pages, None)          # ambiguous
    with pytest.raises(SystemExit):
        pick_page(pages, "Nope")        # not found
    with pytest.raises(SystemExit):
        pick_page([], None)             # none


# --- Meta flow with a fake httpx-like client ------------------------------------------------

class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _FakeHttp:
    def __init__(self, routes):
        self._routes = routes      # list of (url_suffix, payload)
        self.calls = []

    def get(self, url, params=None):
        self.calls.append((url, params))
        for suffix, payload in self._routes:
            if url.endswith(suffix):
                return _Resp(payload)
        raise AssertionError(f"unexpected GET {url}")


def test_meta_exchange_long_lived_sends_exchange_grant():
    http = _FakeHttp([("/oauth/access_token", {"access_token": "LONG"})])
    assert meta_exchange_long_lived(http, "app", "secret", "short") == "LONG"
    _, params = http.calls[0]
    assert params["grant_type"] == "fb_exchange_token"
    assert params["fb_exchange_token"] == "short"


def test_meta_list_pages_returns_data():
    http = _FakeHttp([("/me/accounts", {"data": [{"id": "P1", "name": "GK", "access_token": "t"}]})])
    pages = meta_list_pages(http, "user")
    assert pages[0]["id"] == "P1"


def test_meta_ig_user_id_present_and_absent():
    with_ig = _FakeHttp([("/P1", {"instagram_business_account": {"id": "IG1"}})])
    assert meta_ig_user_id(with_ig, "P1", "tok") == "IG1"
    without = _FakeHttp([("/P1", {})])
    assert meta_ig_user_id(without, "P1", "tok") is None
