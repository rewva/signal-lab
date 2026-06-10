"""Tests for the Facebook Reels adapter (3-phase start/rupload/finish flow)."""

import httpx
import pytest
import respx

from publisher.adapters import PublishOutcome
from publisher.adapters.errors import FatalError, RetryableError
from publisher.adapters.facebook import FB_GRAPH, FB_RUPLOAD, FacebookReelsAdapter

PAGE = "PAGE123"
CREDS = {"page_id": PAGE, "page_access_token": "PAGE_TOKEN"}


def make_adapter():
    return FacebookReelsAdapter(file_reader=lambda path: b"FAKEVIDEOBYTES")


def _mock_graph_start_and_finish():
    def responder(request):
        body = request.content.decode()
        if "upload_phase=start" in body:
            return httpx.Response(200, json={"video_id": "VID1"})
        return httpx.Response(200, json={"success": True})

    return respx.post(f"{FB_GRAPH}/{PAGE}/video_reels").mock(side_effect=responder)


@respx.mock
def test_publishes_reel_and_returns_outcome():
    _mock_graph_start_and_finish()
    respx.post(f"{FB_RUPLOAD}/VID1").mock(return_value=httpx.Response(200, json={"success": True}))

    outcome = make_adapter().publish(
        video_path="reel.mp4", title="t", description="My reel caption", tags=[],
        extra={}, credentials=CREDS,
    )
    assert isinstance(outcome, PublishOutcome)
    assert outcome.external_post_id == "VID1"
    assert "VID1" in outcome.post_url


@respx.mock
def test_upload_uses_page_token_auth_header():
    _mock_graph_start_and_finish()
    upload = respx.post(f"{FB_RUPLOAD}/VID1").mock(return_value=httpx.Response(200, json={"success": True}))

    make_adapter().publish(video_path="reel.mp4", title="t", description="d", tags=[],
                           extra={}, credentials=CREDS)

    sent = upload.calls.last.request
    assert sent.headers["Authorization"] == "OAuth PAGE_TOKEN"
    assert sent.headers["file_size"] == str(len(b"FAKEVIDEOBYTES"))


@respx.mock
def test_finish_phase_carries_description_and_published_state():
    graph = _mock_graph_start_and_finish()
    respx.post(f"{FB_RUPLOAD}/VID1").mock(return_value=httpx.Response(200, json={"success": True}))

    make_adapter().publish(video_path="reel.mp4", title="t", description="My caption",
                           tags=[], extra={}, credentials=CREDS)

    finish_body = graph.calls.last.request.content.decode()
    assert "upload_phase=finish" in finish_body
    assert "video_state=PUBLISHED" in finish_body
    assert "My+caption" in finish_body or "My%20caption" in finish_body


@respx.mock
def test_start_failure_is_fatal():
    respx.post(f"{FB_GRAPH}/{PAGE}/video_reels").mock(return_value=httpx.Response(400, json={"error": "bad"}))
    with pytest.raises(FatalError):
        make_adapter().publish(video_path="reel.mp4", title="t", description="d", tags=[],
                               extra={}, credentials=CREDS)


@respx.mock
def test_upload_server_error_is_retryable():
    _mock_graph_start_and_finish()
    respx.post(f"{FB_RUPLOAD}/VID1").mock(return_value=httpx.Response(503))
    with pytest.raises(RetryableError):
        make_adapter().publish(video_path="reel.mp4", title="t", description="d", tags=[],
                               extra={}, credentials=CREDS)
