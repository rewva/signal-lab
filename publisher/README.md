# signal-lab-publisher

Automated short-video posting to YouTube / Facebook / Instagram for signal-lab channels.
A single FastAPI monolith with an embedded scheduler: upstream content pipelines (e.g.
`daily-gk-quiz`) submit a video + metadata via `POST /api/jobs` and never learn how posting
works.

Design decisions are locked in the `reference-publisher-design-decisions` memory and
`docs/posting-pipeline-api-research.md` (verified platform-API facts, GO verdict).

## Status

Built TDD, **175 tests passing**. Fully drivable over HTTP (`python main.py`), all three
platforms (YouTube + Facebook + Instagram): register account + seed token -> set posting
windows -> submit job -> PENDING_APPROVAL -> approve (SCHEDULED) -> scheduler tick ->
orchestrator -> POSTED.

| Module | What it does | Status |
|---|---|---|
| `vault.py` | Two-layer token vault: OS-keyring master key (Layer 1) + AES-256-GCM `tokens.enc` (Layer 2) | done |
| `models.py` | Dataclasses: Account, Job (`is_pending` computed, `attempts`), PostResult | done |
| `db.py` | SQLite store, thread-safe, soft deletes, per-platform overrides, attempts/setters | done |
| `lifecycle.py` | Job state machine + retry-vs-fail decision (3 attempts) | done |
| `adapters/` | Adapter base + RetryableError / FatalError typed errors | done |
| `adapters/youtube.py` | OAuth refresh (60s margin, token-broken on 4xx) + `videos.insert` resource + publish | done |
| `adapters/facebook.py` | Page Reels 3-phase: start -> rupload binary -> finish PUBLISHED | done |
| `adapters/instagram.py` | Reels container: create -> upload -> poll status_code -> media_publish -> permalink | done |
| `adapters/http.py` | shared 429/5xx->Retryable, 4xx->Fatal classifier | done |
| `normalizer.py` | FFmpeg normalize to MP4/H.264/1080x1920/AAC-LC 128k/48kHz + Fast Start; `-c copy` when conformant | done |
| `scheduler.py` | Due-job selection + next-free-slot picker (per-account windows, +/-30min buffer) | done |
| `api.py` | FastAPI app + `POST /api/jobs` intake (PENDING_APPROVAL), list/get | done |
| `orchestrator.py` | Drives a job: normalize -> per-platform dispatch (skip already-succeeded) -> record results -> POSTED / FAILED+alert / requeue with backoff | done |
| `config.py` | pydantic-settings (env prefix `PUBLISHER_`, optional `.env`) | done |
| `bootstrap.py` | `build_runtime()` wires db + vault + adapters + orchestrator + app + scheduler tick | done |
| `main.py` | `python main.py` -> FastAPI + APScheduler 60s tick | done |
| `approval.py` + endpoints | `POST /api/jobs/{id}/approve` (next free slot or override) and `/reject`; posting_windows storage | done |
| account/window endpoints | `POST/GET /api/accounts` (+ credential seeding into the vault), `POST/GET /api/accounts/{id}/windows` | done |

## HTTP surface

- `POST /api/accounts` `{brand, platform, account_id, token_key_ref?, credentials?}` — register + seed vault
- `GET /api/accounts` — list with token health
- `POST /api/accounts/{id}/windows` `{time_slot, days_of_week}` / `GET` — posting windows
- `POST /api/jobs` — submit (PENDING_APPROVAL); `GET /api/jobs`, `GET /api/jobs/{id}`
- `POST /api/jobs/{id}/approve` `{scheduled_for?}` — schedule; `POST /api/jobs/{id}/reject`

FB/IG credentials in the vault carry the platform token + id:
`facebook` -> `{page_id, page_access_token}`, `instagram` -> `{ig_user_id, access_token}`,
`youtube` -> `{refresh_token, access_token?, expires_at?}`.

## Not yet built (next layer)

- **OAuth helper** — currently you seed tokens via the `credentials` field; an
  authorization-code flow helper would be friendlier (esp. YouTube).
- **Dashboard** (Queue/Accounts/Calendar/History/Alerts) — Phase 1 UI.
- **Live integration tests** against real accounts (YouTube `_default_uploader`, FB/IG flows)
  — needs the one-time Meta role-holder app setup + Google OAuth client + ffmpeg installed.

## One-time operator setup (before live posting)

- **YouTube:** create a Google Cloud project + OAuth client (scope `youtube.upload`). No App Review.
- **Meta (FB + IG):** create a Meta app; add your own FB Page + IG Business/Creator accounts as
  **role-holders** (Admin/Dev/Tester). This keeps you in Standard Access -- **no App Review or
  Business Verification** (see research doc). Generate page + IG tokens.
- **ffmpeg / ffprobe** on PATH (not currently installed on this machine).

## Develop

```powershell
py -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv\Scripts\python.exe -m pytest      # 175 tests

# run the monolith (set PUBLISHER_GOOGLE_CLIENT_ID / _SECRET first for live YouTube)
.venv\Scripts\python.exe main.py
```
