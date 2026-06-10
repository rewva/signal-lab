"""Tests for the adapter base contract and the typed error hierarchy.

Adapters never retry themselves -- they raise RetryableError (transient: network, 5xx,
rate-limit) or FatalError (permanent: bad request, invalid creds, policy rejection) and let
the orchestrator decide. This keeps each platform's HTTP call fully encapsulated.
"""

import pytest

from publisher.adapters import Adapter, PublishOutcome
from publisher.adapters.errors import AdapterError, FatalError, RetryableError


def test_error_hierarchy():
    assert issubclass(RetryableError, AdapterError)
    assert issubclass(FatalError, AdapterError)


def test_retryable_and_fatal_are_distinct():
    assert not issubclass(RetryableError, FatalError)
    assert not issubclass(FatalError, RetryableError)


def test_adapter_is_abstract():
    with pytest.raises(TypeError):
        Adapter()  # cannot instantiate without implementing publish


def test_concrete_adapter_publishes():
    class DummyAdapter(Adapter):
        platform = "dummy"

        def publish(self, *, video_path, title, description, tags, extra, credentials):
            return PublishOutcome(external_post_id="abc",
                                  post_url="https://example.com/abc")

    outcome = DummyAdapter().publish(
        video_path="v.mp4", title="t", description="d", tags=[], extra={}, credentials={}
    )
    assert outcome.external_post_id == "abc"
    assert outcome.post_url == "https://example.com/abc"


def test_publish_outcome_defaults():
    outcome = PublishOutcome(external_post_id="id1")
    assert outcome.post_url is None
