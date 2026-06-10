"""YouTube adapter: OAuth 2.0 token refresh + videos.insert.

Verified facts (see docs/posting-pipeline-api-research.md):
- Upload via videos.insert, scope youtube.upload, no App Review for own channel.
- Scheduled publish = privacyStatus 'private' + status.publishAt (YouTube flips it public).
- Quota: dedicated 100 videos.insert/day cap -- trivial for 1-5/day.

The live media upload is the one integration seam: it is injected (``uploader``) so the
publish/refresh logic is fully unit-tested, and the default uploader (google-api-python-
client, resumable upload) is exercised by integration testing against a real channel once
the operator has provisioned OAuth credentials.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Callable, Optional

import httpx

from publisher.adapters.base import Adapter, PublishOutcome
from publisher.adapters.errors import FatalError
from publisher.adapters.http import classify_status

GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"
REFRESH_MARGIN_SECONDS = 60  # refresh slightly before real expiry
TITLE_MAX = 100  # YouTube hard limit on video title length

Uploader = Callable[[str, dict[str, Any], str], str]  # (video_path, body, access_token) -> video_id


class TokenBrokenError(FatalError):
    """The refresh token was rejected (4xx). The account must be reconnected."""


# kept as the adapter's public name; delegates to the shared classifier
classify_upload_status = classify_status


class YouTubeAdapter(Adapter):
    platform = "youtube"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        *,
        http: Optional[httpx.Client] = None,
        uploader: Optional[Uploader] = None,
        token_uri: str = GOOGLE_TOKEN_URI,
    ):
        self._client_id = client_id
        self._client_secret = client_secret
        self._http = http or httpx.Client(timeout=30)
        self._uploader = uploader or _default_uploader
        self._token_uri = token_uri

    def build_video_resource(
        self, title: str, description: str, tags: list[str], extra: dict[str, Any]
    ) -> dict[str, Any]:
        status: dict[str, Any] = {}
        publish_at = extra.get("publish_at")
        if publish_at:
            status["privacyStatus"] = "private"  # YouTube publishes it at publish_at
            status["publishAt"] = publish_at
        else:
            status["privacyStatus"] = extra.get("privacy_status", "public")
        if "made_for_kids" in extra:
            status["selfDeclaredMadeForKids"] = bool(extra["made_for_kids"])
        return {
            "snippet": {
                "title": title[:TITLE_MAX],
                "description": description,
                "tags": tags,
            },
            "status": status,
        }

    def refresh_access_token(self, credentials: dict[str, Any], now: datetime) -> dict[str, Any]:
        expires_at = credentials.get("expires_at")
        if credentials.get("access_token") and expires_at:
            if datetime.fromisoformat(expires_at) > now:
                return credentials  # still valid -- no network
        resp = self._http.post(
            self._token_uri,
            data={
                "grant_type": "refresh_token",
                "refresh_token": credentials["refresh_token"],
                "client_id": self._client_id,
                "client_secret": self._client_secret,
            },
        )
        if resp.status_code >= 400:
            raise TokenBrokenError(
                f"refresh rejected: HTTP {resp.status_code} {resp.text}"
            )
        data = resp.json()
        refreshed = dict(credentials)
        refreshed["access_token"] = data["access_token"]
        refreshed["expires_at"] = (
            now + timedelta(seconds=data["expires_in"] - REFRESH_MARGIN_SECONDS)
        ).isoformat()
        return refreshed

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
        creds = self.refresh_access_token(credentials, now=_utcnow())
        body = self.build_video_resource(title, description, tags, extra)
        video_id = self._uploader(video_path, body, creds["access_token"])
        return PublishOutcome(
            external_post_id=video_id, post_url=f"https://youtu.be/{video_id}"
        )


def _utcnow() -> datetime:
    from datetime import timezone

    return datetime.now(timezone.utc)


def _default_uploader(video_path: str, body: dict[str, Any], access_token: str) -> str:
    """Live resumable upload via google-api-python-client (integration seam).

    Covered by integration testing against a real channel, not unit tests -- requires
    provisioned OAuth credentials. Errors are classified via ``classify_upload_status``.
    """
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload

    creds = Credentials(token=access_token)
    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True,
                            mimetype="video/*")
    try:
        request = youtube.videos().insert(
            part=",".join(body.keys()), body=body, media_body=media
        )
        response = None
        while response is None:
            _, response = request.next_chunk()
        return response["id"]
    except HttpError as exc:  # translate to typed errors
        classify_upload_status(exc.resp.status)
        raise  # pragma: no cover -- classify always raises for >=400
