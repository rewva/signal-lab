"""Tests for the AES-256-GCM cipher that protects the token vault (Layer 2)."""

import pytest

from publisher.vault import Cipher

KEY = bytes(range(32))  # deterministic 32-byte key for tests


def test_encrypt_then_decrypt_returns_original_plaintext():
    cipher = Cipher(KEY)
    blob = cipher.encrypt(b"super-secret-refresh-token")
    assert cipher.decrypt(blob) == b"super-secret-refresh-token"


def test_ciphertext_does_not_contain_plaintext():
    cipher = Cipher(KEY)
    blob = cipher.encrypt(b"super-secret-refresh-token")
    assert b"super-secret-refresh-token" not in blob


def test_same_plaintext_encrypts_to_different_blobs():
    # random nonce per encryption -> no deterministic ciphertext leak
    cipher = Cipher(KEY)
    assert cipher.encrypt(b"x") != cipher.encrypt(b"x")


def test_decrypt_with_wrong_key_raises():
    blob = Cipher(KEY).encrypt(b"x")
    wrong = Cipher(bytes([1]) + bytes(31))
    with pytest.raises(Exception):
        wrong.decrypt(blob)


def test_decrypt_tampered_blob_raises():
    cipher = Cipher(KEY)
    blob = bytearray(cipher.encrypt(b"hello world"))
    blob[-1] ^= 0xFF  # flip a bit in the auth tag region
    with pytest.raises(Exception):
        cipher.decrypt(bytes(blob))


def test_key_must_be_32_bytes():
    with pytest.raises(ValueError):
        Cipher(b"too-short")
