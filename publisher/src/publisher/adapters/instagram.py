"""Instagram Reels adapter -- verified container flow (see docs/posting-pipeline-api-research.md).

1. create  : POST {graph}/{ig_user_id}/media  media_type=REELS upload_type=resumable -> container_id
2. upload  : POST {rupload}/{container_id}  (binary, Authorization: OAuth <token>)
3. poll    : GET {graph}/{container_id}?fields=status_code  until FINISHED (ERROR -> fatal)
4. publish : POST {graph}/{ig_user_id}/media_publish creation_id=<container_id> -> media_id
5. permalink (best-effort): GET {graph}/{media_id}?fields=permalink

Credentials (from the vault) carry ``ig_user_id`` and ``access_token``.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Optional

import httpx

from publisher.adapters.base import Adapter, PublishOutcome
from publisher.adapters.errors import FatalError, RetryableError
from publisher.adapters.http import classify_status

GRAPH_VERSION = "v25.0"
IG_GRAPH = f"https://graph.facebook.com/{GRAPH_VERSION}"
IG_RUPLOAD = "https://rupload.facebook.com/ig-api-upload"


def _read_file(path: str) -> bytes:
    with open(path, "rb") as fh:
        return fh.read()


class InstagramReelsAdapter(Adapter):
    platform = "instagram"

    def __init__(
        self,
        http: Optional[httpx.Client] = None,
        file_reader: Callable[[str], bytes] = _read_file,
        sleep: Callable[[float], None] = time.sleep,
        max_polls: int = 30,
        poll_interval: float = 5.0,
    ):
        self._http = http or httpx.Client(timeout=120)
        self._read_file = file_reader
        self._sleep = sleep
        self._max_polls = max_polls
        self._poll_interval = poll_interval

    def publish(
        self,
        *,
        video_path: str,
        title: str,
        description: str,
        tags: list[str],
        extra: dict[str, Any],
        credentials: dict[str, Any],
    ) -> PublishOutcome:
        ig_user_id = credentials["ig_user_id"]
        token = credentials["access_token"]
        caption = description or title

        container_id = self._create_container(ig_user_id, token, caption)
        self._upload(container_id, token, self._read_file(video_path))
        self._wait_until_finished(container_id, token)
        media_id = self._publish_container(ig_user_id, token, container_id)

        return PublishOutcome(
            external_post_id=media_id,
            post_url=self._permalink(media_id, token),
        )

    def _create_container(self, ig_user_id: str, token: str, caption: str) -> str:
        resp = self._http.post(
            f"{IG_GRAPH}/{ig_user_id}/media",
            data={"media_type": "REELS", "upload_type": "resumable",
                  "caption": caption, "access_token": token},
        )
        classify_status(resp.status_code)
        return resp.json()["id"]

    def _upload(self, container_id: str, token: str, video_bytes: bytes) -> None:
        resp = self._http.post(
            f"{IG_RUPLOAD}/{container_id}",
            headers={
                "Authorization": f"OAuth {token}",
                "offset": "0",
                "file_size": str(len(video_bytes)),
                "Content-Type": "application/octet-stream",
            },
            content=video_bytes,
        )
        classify_status(resp.status_code)

    def _wait_until_finished(self, container_id: str, token: str) -> None:
        for _ in range(self._max_polls):
            resp = self._http.get(
                f"{IG_GRAPH}/{container_id}",
                params={"fields": "status_code", "access_token": token},
            )
            classify_status(resp.status_code)
            status = resp.json().get("status_code")
            if status == "FINISHED":
                return
            if status == "ERROR":
                raise FatalError(f"container {container_id} processing failed (ERROR)")
            self._sleep(self._poll_interval)
        raise RetryableError(f"container {container_id} not FINISHED within poll budget")

    def _publish_container(self, ig_user_id: str, token: str, container_id: str) -> str:
        resp = self._http.post(
            f"{IG_GRAPH}/{ig_user_id}/media_publish",
            data={"creation_id": container_id, "access_token": token},
        )
        classify_status(resp.status_code)
        return resp.json()["id"]

    def _permalink(self, media_id: str, token: str) -> Optional[str]:
        # best-effort: the reel is already published; a permalink failure is non-fatal
        try:
            resp = self._http.get(
                f"{IG_GRAPH}/{media_id}",
                params={"fields": "permalink", "access_token": token},
            )
            if resp.status_code < 400:
                return resp.json().get("permalink")
        except httpx.HTTPError:
            pass
        return None
