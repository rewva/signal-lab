"""Tests for the master-key provider (Layer 1).

In production the backend is the OS keyring (Windows Credential Manager + DPAPI). Tests
inject an in-memory backend so they never touch the real credential store.
"""

import pytest

from publisher.vault import KeyringKeyProvider

SERVICE = "signal-lab"
USERNAME = "master-key"


class FakeBackend:
    """Minimal stand-in for the keyring module's get/set password API."""

    def __init__(self):
        self.store: dict[tuple[str, str], str] = {}

    def get_password(self, service, username):
        return self.store.get((service, username))

    def set_password(self, service, username, value):
        self.store[(service, username)] = value


def test_get_or_create_returns_32_byte_key():
    kp = KeyringKeyProvider(backend=FakeBackend())
    assert len(kp.get_or_create()) == 32


def test_get_or_create_is_idempotent():
    kp = KeyringKeyProvider(backend=FakeBackend())
    assert kp.get_or_create() == kp.get_or_create()


def test_key_is_persisted_under_signal_lab_master_key():
    backend = FakeBackend()
    KeyringKeyProvider(backend=backend).get_or_create()
    assert (SERVICE, USERNAME) in backend.store


def test_existing_key_is_reused_not_regenerated():
    backend = FakeBackend()
    first = KeyringKeyProvider(backend=backend).get_or_create()
    # a fresh provider over the same backend must return the same key
    second = KeyringKeyProvider(backend=backend).get_or_create()
    assert first == second


def test_two_providers_with_separate_backends_differ():
    a = KeyringKeyProvider(backend=FakeBackend()).get_or_create()
    b = KeyringKeyProvider(backend=FakeBackend()).get_or_create()
    assert a != b
