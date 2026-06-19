"""Connect the operator's own accounts -> store posting credentials in the vault.

This is the one-time OAuth helper the orchestrator depends on: it runs each platform's
authorization, then POSTs the resulting credentials to ``/api/accounts`` (which seeds the
encrypted vault under ``<brand>:<platform>``). After this, ``approve`` in the review queue
actually posts.

    python -m publisher.connect youtube --brand daily-gk-quiz --account-id <channel handle>
    python -m publisher.connect meta    --brand daily-gk-quiz --user-token <short-lived> \
        --app-id <id> --app-secret <secret> [--page <page id or name>]

YouTube uses Google's loopback OAuth flow (opens a browser, needs the operator's Google Cloud
OAuth *Desktop* client + YouTube Data API v3 enabled). Meta exchanges a short-lived user token
(from the Graph API Explorer) into a long-lived Page token and discovers the linked IG business
account -- no App Review needed while the app holds Standard Access for role-holder accounts.
See docs/connect-accounts.md for the exact console steps.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Any, Optional

YT_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
GRAPH = "https://graph.facebook.com/v25.0"


# --- pure helpers (unit-tested) -------------------------------------------------------------

def youtube_credentials(refresh_token: str) -> dict[str, str]:
    return {"refresh_token": refresh_token}


def fb_credentials(page: dict[str, Any]) -> dict[str, str]:
    return {"page_id": page["id"], "page_access_token": page["access_token"]}


def ig_credentials(ig_user_id: str, access_token: str) -> dict[str, str]:
    return {"ig_user_id": ig_user_id, "access_token": access_token}


def pick_page(pages: list[dict[str, Any]], selector: Optional[str]) -> dict[str, Any]:
    """Choose the Page to post to: by id/name, or the only one if there's exactly one."""
    if not pages:
        raise SystemExit("no Pages on this user token -- is the user a role-holder on the Page?")
    if selector is None:
        if len(pages) == 1:
            return pages[0]
        names = [f"{p.get('name')} ({p.get('id')})" for p in pages]
        raise SystemExit(f"multiple Pages; pass --page <id or name>: {names}")
    for p in pages:
        if selector in (p.get("id"), p.get("name")):
            return p
    raise SystemExit(f"page {selector!r} not found among {[p.get('name') for p in pages]}")


def account_payload(brand: str, platform: str, account_id: str,
                    credentials: dict[str, Any]) -> dict[str, Any]:
    return {
        "brand": brand, "platform": platform, "account_id": account_id,
        "token_key_ref": f"{brand}:{platform}", "credentials": credentials,
    }


# --- I/O seams ------------------------------------------------------------------------------

def post_account(publisher_url: str, payload: dict[str, Any]) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(publisher_url.rstrip("/") + "/api/accounts",
                                 data=data, headers={"Content-Type": "application/json"},
                                 method="POST")
    with urllib.request.urlopen(req) as resp:  # noqa: S310 -- operator's localhost publisher
        return json.loads(resp.read().decode("utf-8"))


def run_youtube_flow(client_id: str, client_secret: str) -> str:
    """Loopback OAuth -> a long-lived refresh token (access_type=offline + prompt=consent)."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    cfg = {"installed": {
        "client_id": client_id, "client_secret": client_secret,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost"],
    }}
    flow = InstalledAppFlow.from_client_config(cfg, scopes=YT_SCOPES)
    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
    if not creds.refresh_token:
        raise SystemExit("Google returned no refresh_token; revoke prior grant and retry "
                         "(needs prompt=consent + access_type=offline)")
    return creds.refresh_token


def meta_exchange_long_lived(http, app_id: str, app_secret: str, short_token: str) -> str:
    r = http.get(f"{GRAPH}/oauth/access_token", params={
        "grant_type": "fb_exchange_token", "client_id": app_id,
        "client_secret": app_secret, "fb_exchange_token": short_token,
    })
    r.raise_for_status()
    return r.json()["access_token"]


def meta_list_pages(http, user_token: str) -> list[dict[str, Any]]:
    r = http.get(f"{GRAPH}/me/accounts",
                 params={"fields": "id,name,access_token", "access_token": user_token})
    r.raise_for_status()
    return r.json().get("data", [])


def meta_ig_user_id(http, page_id: str, page_token: str) -> Optional[str]:
    r = http.get(f"{GRAPH}/{page_id}",
                 params={"fields": "instagram_business_account", "access_token": page_token})
    r.raise_for_status()
    iba = r.json().get("instagram_business_account")
    return iba.get("id") if iba else None


# --- commands -------------------------------------------------------------------------------

def cmd_youtube(args) -> int:
    from publisher.config import Settings

    settings = Settings()
    client_id = args.client_id or settings.google_client_id
    client_secret = args.client_secret or settings.google_client_secret
    if not (client_id and client_secret):
        raise SystemExit("set PUBLISHER_GOOGLE_CLIENT_ID / _SECRET (or pass --client-id/--client-secret)")
    refresh = run_youtube_flow(client_id, client_secret)
    payload = account_payload(args.brand, "youtube", args.account_id, youtube_credentials(refresh))
    out = post_account(args.publisher_url, payload)
    print(f"connected youtube account #{out.get('id')} ({out.get('token_key_ref')})")
    return 0


def cmd_meta(args) -> int:
    import httpx

    with httpx.Client(timeout=30) as http:
        user_token = (meta_exchange_long_lived(http, args.app_id, args.app_secret, args.user_token)
                      if args.app_id and args.app_secret else args.user_token)
        pages = meta_list_pages(http, user_token)
        page = pick_page(pages, args.page)
        page_id, page_token = page["id"], page["access_token"]

        fb = account_payload(args.brand, "facebook", args.account_id or page_id, fb_credentials(page))
        out_fb = post_account(args.publisher_url, fb)
        print(f"connected facebook account #{out_fb.get('id')} (page {page.get('name')})")

        ig_id = meta_ig_user_id(http, page_id, page_token)
        if not ig_id:
            print("no linked Instagram business account on this Page -- skipping IG "
                  "(link an IG Business/Creator account to the Page, then re-run)")
            return 0
        ig = account_payload(args.brand, "instagram", ig_id, ig_credentials(ig_id, page_token))
        out_ig = post_account(args.publisher_url, ig)
        print(f"connected instagram account #{out_ig.get('id')} (ig_user {ig_id})")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Connect own accounts into the publisher vault")
    parser.add_argument("--publisher-url", default="http://127.0.0.1:8077")
    sub = parser.add_subparsers(dest="cmd", required=True)

    yt = sub.add_parser("youtube", help="authorize YouTube via Google loopback OAuth")
    yt.add_argument("--brand", required=True)
    yt.add_argument("--account-id", required=True, help="channel handle/id (label only)")
    yt.add_argument("--client-id", default="")
    yt.add_argument("--client-secret", default="")
    yt.set_defaults(func=cmd_youtube)

    mt = sub.add_parser("meta", help="store FB Page + linked IG creds from a user token")
    mt.add_argument("--brand", required=True)
    mt.add_argument("--user-token", required=True, help="short- or long-lived user token")
    mt.add_argument("--app-id", default="", help="Meta app id (to exchange for long-lived)")
    mt.add_argument("--app-secret", default="")
    mt.add_argument("--page", default=None, help="Page id or name (if the user has several)")
    mt.add_argument("--account-id", default=None, help="label override (defaults to page id)")
    mt.set_defaults(func=cmd_meta)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (urllib.error.URLError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
