"""Two-layer token vault.

Layer 1 (master key): a 32-byte random key held in the OS keyring (Windows Credential
Manager, protected by DPAPI). See ``key_provider`` for sourcing.

Layer 2 (this module's ``Cipher``): AES-256-GCM encryption of the token JSON, stored at
``vault/tokens.enc``. Plaintext tokens live only in memory after decryption.
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any, Optional, Protocol

import keyring
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

NONCE_BYTES = 12  # 96-bit nonce, the AES-GCM standard

KEYRING_SERVICE = "signal-lab"
KEYRING_USERNAME = "master-key"


class Cipher:
    """AES-256-GCM authenticated encryption with a per-message random nonce.

    Blob layout: ``nonce (12 bytes) || ciphertext+tag``.
    """

    def __init__(self, key: bytes):
        if len(key) != 32:
            raise ValueError("master key must be exactly 32 bytes (AES-256)")
        self._aead = AESGCM(key)

    def encrypt(self, plaintext: bytes) -> bytes:
        nonce = os.urandom(NONCE_BYTES)
        return nonce + self._aead.encrypt(nonce, plaintext, None)

    def decrypt(self, blob: bytes) -> bytes:
        nonce, ciphertext = blob[:NONCE_BYTES], blob[NONCE_BYTES:]
        return self._aead.decrypt(nonce, ciphertext, None)


class KeyBackend(Protocol):
    """The slice of the keyring API the provider needs (get/set password)."""

    def get_password(self, service: str, username: str) -> Optional[str]: ...

    def set_password(self, service: str, username: str, value: str) -> None: ...


class KeyringKeyProvider:
    """Sources the 32-byte master key from the OS keyring, creating it on first use.

    On Windows the default backend is Credential Manager (DPAPI-protected). The backend
    is injectable so tests can use an in-memory stand-in.
    """

    def __init__(self, backend: KeyBackend | None = None):
        self._backend = backend or keyring

    def get_or_create(self) -> bytes:
        stored = self._backend.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
        if stored is not None:
            return base64.b64decode(stored)
        key = os.urandom(32)
        self._backend.set_password(
            KEYRING_SERVICE, KEYRING_USERNAME, base64.b64encode(key).decode("ascii")
        )
        return key


class TokenVault:
    """Encrypted, file-backed store of per-account platform credentials.

    Keyed by ``"<brand>:<platform>"``. The whole credential map is serialised to JSON,
    encrypted with the master key, and written to a single ``tokens.enc`` file. Plaintext
    exists only in memory and only for the duration of a load/save call.
    """

    def __init__(self, path: str | os.PathLike[str], cipher: Cipher):
        self._path = Path(path)
        self._cipher = cipher

    def load(self) -> dict[str, Any]:
        if not self._path.exists():
            return {}
        return json.loads(self._cipher.decrypt(self._path.read_bytes()).decode("utf-8"))

    def _save(self, data: dict[str, Any]) -> None:
        blob = self._cipher.encrypt(json.dumps(data).encode("utf-8"))
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.write_bytes(blob)
        tmp.replace(self._path)  # atomic on the same volume

    def get(self, account_key: str) -> Optional[dict[str, Any]]:
        return self.load().get(account_key)

    def set(self, account_key: str, credentials: dict[str, Any]) -> None:
        data = self.load()
        data[account_key] = credentials
        self._save(data)

    def delete(self, account_key: str) -> None:
        data = self.load()
        if data.pop(account_key, None) is not None:
            self._save(data)
