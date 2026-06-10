"""Facebook Page Reels adapter -- verified 3-phase flow (see docs/posting-pipeline-api-research.md).

1. start  : POST {graph}/{page_id}/video_reels  upload_phase=start            -> video_id
2. upload : POST {rupload}/{video_id}  (binary, Authorization: OAuth <token>)
3. finish : POST {graph}/{page_id}/video_reels  upload_phase=finish video_state=PUBLISHED

Credentials (from the vault) carry ``page_id`` and ``page_access_token``. Page tokens are
long-lived, so there is no refresh step; an auth rejection surfaces as FatalError.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

import httpx

from publisher.adapters.base import Adapter, PublishOutcome
from publisher.adapters.http import classify_status

GRAPH_VERSION = "v25.0"
FB_GRAPH = f"https://graph.facebook.com/{GRAPH_VERSION}"
FB_RUPLOAD = f"https://rupload.facebook.com/video-upload/{GRAPH_VERSION}"


def _read_file(path: str) -> bytes:
    with open(path, "rb") as fh:
        return fh.read()


class FacebookReelsAdapter(Adapter):
    platform = "facebook"

    def __init__(
        self,
        http: Optional[httpx.Client] = None,
        file_reader: Callable[[str], bytes] = _read_file,
    ):
        self._http = http or httpx.Client(timeout=120)
        self._read_file = file_reader

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
        page_id = credentials["page_id"]
        token = credentials["page_access_token"]
        caption = description or title

        video_id = self._start(page_id, token)
        self._upload(video_id, token, self._read_file(video_path))
        self._finish(page_id, token, video_id, caption)

        return PublishOutcome(
            external_post_id=video_id,
            post_url=f"https://www.facebook.com/reel/{video_id}",
        )

    def _start(self, page_id: str, token: str) -> str:
        resp = self._http.post(
            f"{FB_GRAPH}/{page_id}/video_reels",
            data={"upload_phase": "start", "access_token": token},
        )
        classify_status(resp.status_code)
        return resp.json()["video_id"]

    def _upload(self, video_id: str, token: str, video_bytes: bytes) -> None:
        resp = self._http.post(
            f"{FB_RUPLOAD}/{video_id}",
            headers={
                "Authorization": f"OAuth {token}",
                "offset": "0",
                "file_size": str(len(video_bytes)),
                "Content-Type": "application/octet-stream",
            },
            content=video_bytes,
        )
        classify_status(resp.status_code)

    def _finish(self, page_id: str, token: str, video_id: str, caption: str) -> None:
        resp = self._http.post(
            f"{FB_GRAPH}/{page_id}/video_reels",
            data={
                "upload_phase": "finish",
                "video_id": video_id,
                "video_state": "PUBLISHED",
                "description": caption,
                "access_token": token,
            },
        )
        classify_status(resp.status_code)
