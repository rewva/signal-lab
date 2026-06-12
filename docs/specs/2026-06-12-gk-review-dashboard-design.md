# Design: Review dashboard v1 (gate #2 review queue)

**Date:** 2026-06-12
**Status:** Approved design (plan next -- no implementation in this phase)
**Owner:** sdevendran
**Relates to:** `docs/specs/2026-06-11-gk-end-to-end-glue-design.md` (threaded the
`source_citation`/`sources` this dashboard consumes), `publisher/` (the FastAPI monolith this
extends in place).

---

## 1. What this is (the gap it closes)

Jobs land in **PENDING_APPROVAL** (review gate #2), but the only way to act on them today is a
raw `POST /api/jobs/{id}/approve|reject`. The operator cannot **watch the video** or **verify the
citation** before approving -- which is the entire point of gate #2 and the trust / anti-slop
moat. This spec adds a minimal **review queue** UI: one card per pending job with a playable
video, a clickable citation -> source verify tag, and Approve / Reject.

**Scope this round: review queue only.** No Accounts / Calendar / History / Alerts tabs. Those
are deferred (the publisher's planned full dashboard is a later round).

---

## 2. Approach

A single **server-rendered HTML page + vanilla JS**, served by the **existing publisher FastAPI
app** (`create_app`). No new process, no build step, no JS framework -- this honours the
<150MB-RAM monolith ethos and the no-build-step nature of the repo. The JS calls the JSON API
that already exists (`GET /api/jobs`, `POST .../approve`, `POST .../reject`) plus two small new
endpoints (the page itself + video streaming).

---

## 3. New server pieces (all inside `create_app`)

### 3.1 `GET /` -> the review page (`HTMLResponse`)
Returns a static HTML document (read from `publisher/src/publisher/static/review.html`, or
inlined). Contains the markup shell + the vanilla JS that fetches the queue and renders cards.

### 3.2 `GET /api/jobs/{id}/video` -> `FileResponse`
Streams the MP4 at the job's `video_path`.

- **Why an endpoint, not a `StaticFiles` mount:** `video_path` is now an **absolute path
  anywhere on disk** (the glue absolutizes it). A per-job endpoint means the browser never
  learns the filesystem path, and we return a clean **404** if the job or the file is missing.
- `FileResponse` natively supports **HTTP range requests**, so the `<video>` element can seek /
  scrub.
- 404 if the job does not exist; 404 if `video_path` is empty or the file is absent on disk.

### 3.3 `GET /api/jobs?status=PENDING_APPROVAL` -> filtered list
`db.list_jobs(status=...)` already supports a status filter; expose it as an optional
`status` query param on the existing `GET /api/jobs` (additive; omitting it preserves today's
"all jobs" behaviour). The page requests `status=PENDING_APPROVAL`.

### 3.4 Approve / Reject -- mostly existing
`POST /api/jobs/{id}/approve` (next free slot; **no time picker in v1**) and
`POST /api/jobs/{id}/reject` already exist. Reject gains a **reason** (see SS4).

---

## 4. Reject-with-reason (the one data-model change)

The operator's reject reason is captured and persisted (useful later for tracking why questions
get killed -- a quality signal for the anti-slop moat).

- **`Job`** gains `reject_reason: str = ""` (additive, defaulted -- keeps all existing
  callers/tests valid). Placed alongside the other review-gate fields.
- **DB:** `reject_reason TEXT NOT NULL DEFAULT ''` column on `jobs`; written by a small setter
  (or folded into `soft_delete_job`); read in `_row_to_job`. (Same caveat as before:
  `CREATE TABLE IF NOT EXISTS` will not add the column to a pre-existing DB -- drop `publisher.db`
  if you hit "no column named reject_reason".)
- **`reject_job(db, job_id, reason="")`** persists the reason before the soft delete. Default
  `""` keeps the existing no-arg behaviour.
- **API:** the reject endpoint accepts an optional `RejectRequest { reason: str = "" }` body and
  threads it into `reject_job`. Omitting the body still works (back-compat).
- **`JobView`** gains `reject_reason: str` (so a future History tab can show it; the review queue
  itself only shows PENDING jobs, which have no reason yet).

No other model changes.

---

## 5. The page (one review card per PENDING_APPROVAL job)

Each card renders from a `JobView`:

- **Playable `<video controls preload="metadata">`** with `src="/api/jobs/{id}/video"`.
- **Title** (`title`) + **caption** (`description` -- see SS6, the data gap).
- **Citation verify tag:** `source_citation` is the visible label; **each URL in `sources`**
  becomes a clickable chip opening the source in a new tab
  (`target="_blank" rel="noopener noreferrer"`). This *is* the "click the citation -> verify"
  interaction. If `sources` is empty, the citation label still shows (no clickable chip).
- **Approve** button -> `POST /api/jobs/{id}/approve` (empty body = next free slot). On 200 the
  card is removed from the queue.
- **Reject** button -> reveals a small reason textarea + confirm ->
  `POST /api/jobs/{id}/reject` with `{ reason }`. On 200 the card is removed.
- **Empty state:** "No videos awaiting review." when the queue is empty.
- **Error handling:** a fetch failure shows an inline error on the card; the card stays so the
  operator can retry. A 409 (already approved/rejected elsewhere) refreshes the queue.

Styling: minimal inline CSS, dark card, large video. ASCII quotes only in any embedded data.
No framework, no external fonts/CDNs (offline-friendly localhost tool).

---

## 6. Data gap to close: `description` on `JobView`

`JobView` exposes `source_citation` + `sources` but **not** the caption text the operator reads
while reviewing. Add **`description: str`** to `JobView` (additive; already on `Job`). The
on-screen *question* text is baked into the rendered video, so the card does not need it
separately -- the video + caption + citation are sufficient for the review decision.

---

## 7. Testing (TDD throughout)

- **`GET /`** returns `200` with `text/html` and contains the review-page marker.
- **`GET /api/jobs/{id}/video`**: streams an existing file (200, correct media type); **404** for
  a missing job; **404** for a job whose `video_path` file is absent. (Use a tmp file fixture.)
- **`GET /api/jobs?status=PENDING_APPROVAL`** returns only pending jobs; no param returns all
  (back-compat).
- **Reject with reason:** `POST .../reject {reason}` persists `reject_reason`; round-trips via
  `GET /api/jobs/{id}` (include-deleted path) / `JobView`. Omitting the body still rejects
  (back-compat). `reject_reason` empty by default on non-rejected jobs.
- **`description` on `JobView`** round-trips.
- The page's JS is thin; verify the **fetch targets** (URLs/methods) are correct via a small DOM
  smoke test **or** by asserting the served HTML references the right endpoints. (No headless
  browser required for v1; keep it to served-markup assertions + the API-layer tests that already
  cover approve/reject behaviour.)

---

## 8. Out of scope (YAGNI)

- Accounts / Calendar / History / Alerts tabs (later round).
- A scheduling **time picker** on approve (v1 = next free slot only).
- Auth / login (localhost single-operator tool).
- Editing the caption/citation from the dashboard (rejects send it back upstream instead).
- Live re-render or re-submit from the UI.
- WebSocket / auto-refresh (operator reloads; the queue is low-volume -- one video/day).

---

## 9. Open questions

- **Page route:** `GET /` vs `GET /review`. Defaulting to `GET /` (the publisher has no other
  root UI); revisit if a landing page is later wanted.
- **Static file vs inlined HTML:** leaning to a `static/review.html` file served via
  `FileResponse`/`HTMLResponse` (editable without touching Python). Confirm during planning.
