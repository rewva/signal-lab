"""Compose the runtime: db + vault + adapters + orchestrator + FastAPI app + scheduler tick.

``build_runtime`` is the single wiring point. Its collaborators are injectable so the
integration test can run the full select_due -> orchestrator -> adapter -> db path with
fakes (no real keyring or network), while production uses the defaults.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from publisher.api import create_app
from publisher.config import Settings
from publisher.db import Database
from publisher.orchestrator import PostingOrchestrator
from publisher.scheduler import select_due


@dataclass
class Runtime:
    db: Database
    orchestrator: PostingOrchestrator
    app: Any
    tick: Callable[..., None]


def build_runtime(
    settings: Settings,
    adapters: Optional[dict[str, Any]] = None,
    vault: Any = None,
    normalizer: Any = None,
) -> Runtime:
    db = Database(settings.db_path)
    db.init_schema()

    if vault is None:
        vault = _default_vault(settings)
    if normalizer is None:
        from publisher.normalizer import Normalizer

        normalizer = Normalizer()
    if adapters is None:
        adapters = _default_adapters(settings)

    orchestrator = PostingOrchestrator(
        db=db, vault=vault, normalizer=normalizer, adapters=adapters,
        work_dir=settings.work_dir, backoff_seconds=settings.backoff_seconds,
    )

    def tick(now: Optional[datetime] = None) -> None:
        now = now or datetime.now(timezone.utc)
        for job in select_due(db.list_jobs(status="SCHEDULED"), now):
            orchestrator.post_job(job)

    return Runtime(db=db, orchestrator=orchestrator,
                   app=create_app(db, vault=vault), tick=tick)


def _default_vault(settings: Settings):
    from publisher.vault import Cipher, KeyringKeyProvider, TokenVault

    master_key = KeyringKeyProvider().get_or_create()
    return TokenVault(settings.vault_path, Cipher(master_key))


def _default_adapters(settings: Settings) -> dict[str, Any]:
    from publisher.adapters.facebook import FacebookReelsAdapter
    from publisher.adapters.instagram import InstagramReelsAdapter
    from publisher.adapters.youtube import YouTubeAdapter

    # FB/IG read page_id / ig_user_id + token from the per-account vault credentials at
    # publish time, so they need no constructor config (unlike YouTube's OAuth client).
    return {
        "youtube": YouTubeAdapter(
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
        ),
        "facebook": FacebookReelsAdapter(),
        "instagram": InstagramReelsAdapter(),
    }
