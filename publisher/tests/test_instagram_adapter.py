"""Tests for the Instagram Reels adapter (container create -> upload -> poll -> publish)."""

import httpx
import pytest
import respx

from publisher.adapters import PublishOutcome
from publisher.adapters.errors import FatalError, RetryableError
from publisher.adapters.instagram import IG_GRAPH, IG_RUPLOAD, InstagramReelsAdapter

IG_USER = "IG123"
CREDS = {"ig_user_id": IG_USER, "access_token": "IG_TOKEN"}


def make_adapter(max_polls=10):
    return InstagramReelsAdapter(
        file_reader=lambda path: b"FAKEVIDEOBYTES",
        sleep=lambda _s: None,
        max_polls=max_polls,
        poll_interval=0,
    )


def _mock_create(status_field="CONT1"):
    return respx.post(f"{IG_GRAPH}/{IG_USER}/media").mock(
        return_value=httpx.Response(200, json={"id": "CONT1"}))


def _mock_upload():
    return respx.post(f"{IG_RUPLOAD}/CONT1").mock(return_value=httpx.Response(200, json={"success": True}))


def _mock_publish():
    return respx.post(f"{IG_GRAPH}/{IG_USER}/media_publish").mock(
        return_value=httpx.Response(200, json={"id": "MEDIA1"}))


def _mock_permalink():
    return respx.get(f"{IG_GRAPH}/MEDIA1").mock(
        return_value=httpx.Response(200, json={"permalink": "https://www.instagram.com/reel/abc/"}))


@respx.mock
def test_publishes_reel_end_to_end():
    _mock_create()
    _mock_upload()
    respx.get(f"{IG_GRAPH}/CONT1").mock(side_effect=[
        httpx.Response(200, json={"status_code": "IN_PROGRESS"}),
        httpx.Response(200, json={"status_code": "FINISHED"}),
    ])
    _mock_publish()
    _mock_permalink()

    outcome = make_adapter().publish(
        video_path="reel.mp4", title="t", description="caption", tags=[],
        extra={}, credentials=CREDS,
    )
    assert isinstance(outcome, PublishOutcome)
    assert outcome.external_post_id == "MEDIA1"
    assert outcome.post_url == "https://www.instagram.com/reel/abc/"


@respx.mock
def test_create_carries_reels_type_and_caption():
    create = _mock_create()
    _mock_upload()
    respx.get(f"{IG_GRAPH}/CONT1").mock(return_value=httpx.Response(200, json={"status_code": "FINISHED"}))
    _mock_publish()
    _mock_permalink()

    make_adapter().publish(video_path="reel.mp4", title="t", description="my caption",
                           tags=[], extra={}, credentials=CREDS)

    body = create.calls.last.request.content.decode()
    assert "media_type=REELS" in body
    assert "my+caption" in body or "my%20caption" in body


@respx.mock
def test_container_error_status_is_fatal():
    _mock_create()
    _mock_upload()
    respx.get(f"{IG_GRAPH}/CONT1").mock(return_value=httpx.Response(200, json={"status_code": "ERROR"}))
    with pytest.raises(FatalError):
        make_adapter().publish(video_path="reel.mp4", title="t", description="c", tags=[],
                               extra={}, credentials=CREDS)


@respx.mock
def test_container_never_finishing_is_retryable():
    _mock_create()
    _mock_upload()
    respx.get(f"{IG_GRAPH}/CONT1").mock(return_value=httpx.Response(200, json={"status_code": "IN_PROGRESS"}))
    with pytest.raises(RetryableError):
        make_adapter(max_polls=2).publish(video_path="reel.mp4", title="t", description="c",
                                          tags=[], extra={}, credentials=CREDS)


@respx.mock
def test_create_failure_is_fatal():
    respx.post(f"{IG_GRAPH}/{IG_USER}/media").mock(return_value=httpx.Response(400, json={"error": "bad"}))
    with pytest.raises(FatalError):
        make_adapter().publish(video_path="reel.mp4", title="t", description="c", tags=[],
                               extra={}, credentials=CREDS)
