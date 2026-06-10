"""Tests for the YouTube adapter: OAuth refresh, videos.insert resource, publish flow."""

from datetime import datetime, timedelta, timezone

import httpx
import pytest
import respx

from publisher.adapters import PublishOutcome, RetryableError
from publisher.adapters.youtube import (
    GOOGLE_TOKEN_URI,
    TokenBrokenError,
    YouTubeAdapter,
    classify_upload_status,
)
from publisher.adapters.errors import FatalError

NOW = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)


def make_adapter(uploader=None):
    return YouTubeAdapter(client_id="cid", client_secret="secret", uploader=uploader)


# --- videos.insert resource building ---------------------------------------

def test_build_resource_public_by_default():
    body = make_adapter().build_video_resource("Title", "Desc", ["a", "b"], {})
    assert body["snippet"]["title"] == "Title"
    assert body["snippet"]["description"] == "Desc"
    assert body["snippet"]["tags"] == ["a", "b"]
    assert body["status"]["privacyStatus"] == "public"
    assert "publishAt" not in body["status"]


def test_build_resource_scheduled_sets_private_plus_publish_at():
    # research: scheduled publishing = privacyStatus private + status.publishAt
    body = make_adapter().build_video_resource(
        "T", "D", [], {"publish_at": "2026-06-09T09:00:00+00:00"}
    )
    assert body["status"]["privacyStatus"] == "private"
    assert body["status"]["publishAt"] == "2026-06-09T09:00:00+00:00"


def test_build_resource_truncates_title_to_100_chars():
    long = "x" * 250
    body = make_adapter().build_video_resource(long, "D", [], {})
    assert len(body["snippet"]["title"]) == 100


def test_build_resource_sets_made_for_kids_flag():
    body = make_adapter().build_video_resource("T", "D", [], {"made_for_kids": True})
    assert body["status"]["selfDeclaredMadeForKids"] is True


# --- token refresh ----------------------------------------------------------

@respx.mock
def test_refresh_is_noop_when_token_still_valid():
    creds = {"access_token": "still-good", "refresh_token": "rt",
             "expires_at": (NOW + timedelta(hours=1)).isoformat()}
    result = make_adapter().refresh_access_token(creds, now=NOW)
    assert result["access_token"] == "still-good"
    assert not respx.calls  # no network call when token is valid


@respx.mock
def test_refresh_when_expired_fetches_new_token_with_60s_margin():
    respx.post(GOOGLE_TOKEN_URI).mock(
        return_value=httpx.Response(200, json={"access_token": "fresh", "expires_in": 3599})
    )
    creds = {"access_token": "old", "refresh_token": "rt",
             "expires_at": (NOW - timedelta(hours=1)).isoformat()}
    result = make_adapter().refresh_access_token(creds, now=NOW)
    assert result["access_token"] == "fresh"
    expected = (NOW + timedelta(seconds=3599 - 60)).isoformat()
    assert result["expires_at"] == expected


@respx.mock
def test_refresh_marks_token_broken_on_4xx():
    respx.post(GOOGLE_TOKEN_URI).mock(
        return_value=httpx.Response(400, json={"error": "invalid_grant"})
    )
    creds = {"refresh_token": "revoked",
             "expires_at": (NOW - timedelta(hours=1)).isoformat()}
    with pytest.raises(TokenBrokenError):
        make_adapter().refresh_access_token(creds, now=NOW)


# --- publish flow -----------------------------------------------------------

def test_publish_uploads_and_returns_youtu_be_url():
    captured = {}

    def fake_uploader(video_path, body, access_token):
        captured["video_path"] = video_path
        captured["body"] = body
        captured["access_token"] = access_token
        return "VIDEO_ID_9"

    creds = {"access_token": "good", "refresh_token": "rt",
             "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()}
    outcome = make_adapter(uploader=fake_uploader).publish(
        video_path="C:/v/quiz.mp4", title="Daily GK", description="d",
        tags=["gk"], extra={}, credentials=creds,
    )
    assert isinstance(outcome, PublishOutcome)
    assert outcome.external_post_id == "VIDEO_ID_9"
    assert outcome.post_url == "https://youtu.be/VIDEO_ID_9"
    assert captured["video_path"] == "C:/v/quiz.mp4"
    assert captured["access_token"] == "good"
    assert captured["body"]["snippet"]["title"] == "Daily GK"


# --- HTTP status classification ---------------------------------------------

@pytest.mark.parametrize("status", [429, 500, 502, 503])
def test_classify_transient_statuses_as_retryable(status):
    with pytest.raises(RetryableError):
        classify_upload_status(status)


@pytest.mark.parametrize("status", [400, 401, 403, 404])
def test_classify_client_errors_as_fatal(status):
    with pytest.raises(FatalError):
        classify_upload_status(status)


def test_classify_success_does_not_raise():
    assert classify_upload_status(200) is None
