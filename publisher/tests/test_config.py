"""Tests for settings loading."""

from publisher.config import Settings


def test_defaults():
    s = Settings()
    assert s.poll_interval_seconds == 60
    assert s.backoff_seconds == 300


def test_env_override(monkeypatch):
    monkeypatch.setenv("PUBLISHER_POLL_INTERVAL_SECONDS", "15")
    assert Settings().poll_interval_seconds == 15
