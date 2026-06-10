"""Runtime settings, sourced from environment (prefix PUBLISHER_) or a .env file."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PUBLISHER_", env_file=".env", extra="ignore"
    )

    # storage
    db_path: str = "publisher.db"
    vault_path: str = "vault/tokens.enc"
    work_dir: str = "work"

    # YouTube OAuth client (Google Cloud project)
    google_client_id: str = ""
    google_client_secret: str = ""

    # scheduling
    poll_interval_seconds: int = 60   # how often the scheduler tick fires
    backoff_seconds: int = 300        # retry backoff (5 min)

    # server
    host: str = "127.0.0.1"
    port: int = 8077
