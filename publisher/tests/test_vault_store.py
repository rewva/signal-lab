"""Tests for the TokenVault: encrypted, file-backed per-account credential store."""

from publisher.vault import Cipher, TokenVault

KEY = bytes(range(32))


def make_vault(tmp_path):
    return TokenVault(tmp_path / "tokens.enc", Cipher(KEY))


def test_load_missing_file_returns_empty_dict(tmp_path):
    assert make_vault(tmp_path).load() == {}


def test_set_then_get_roundtrips_credentials(tmp_path):
    vault = make_vault(tmp_path)
    vault.set("gk-quiz:youtube", {"refresh_token": "rt-123", "expires_at": "2026-06-08T00:00:00Z"})
    assert vault.get("gk-quiz:youtube") == {
        "refresh_token": "rt-123",
        "expires_at": "2026-06-08T00:00:00Z",
    }


def test_get_unknown_account_returns_none(tmp_path):
    assert make_vault(tmp_path).get("nope") is None


def test_credentials_persist_across_instances(tmp_path):
    make_vault(tmp_path).set("gk-quiz:youtube", {"refresh_token": "rt-123"})
    reopened = make_vault(tmp_path)
    assert reopened.get("gk-quiz:youtube")["refresh_token"] == "rt-123"


def test_file_on_disk_is_encrypted(tmp_path):
    vault = make_vault(tmp_path)
    vault.set("gk-quiz:youtube", {"refresh_token": "super-secret-rt"})
    raw = (tmp_path / "tokens.enc").read_bytes()
    assert b"super-secret-rt" not in raw
    assert b"refresh_token" not in raw


def test_set_updates_existing_without_dropping_other_accounts(tmp_path):
    vault = make_vault(tmp_path)
    vault.set("a:youtube", {"refresh_token": "a"})
    vault.set("b:facebook", {"page_token": "b"})
    vault.set("a:youtube", {"refresh_token": "a2"})
    assert vault.get("a:youtube")["refresh_token"] == "a2"
    assert vault.get("b:facebook")["page_token"] == "b"


def test_delete_removes_account(tmp_path):
    vault = make_vault(tmp_path)
    vault.set("a:youtube", {"refresh_token": "a"})
    vault.delete("a:youtube")
    assert vault.get("a:youtube") is None
