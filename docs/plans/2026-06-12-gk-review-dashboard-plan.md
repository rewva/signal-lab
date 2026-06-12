# Review Dashboard (gate #2 review queue) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a minimal browser review queue to the publisher so the operator can watch each PENDING_APPROVAL video, click its citation to verify the source, and approve (next free slot) or reject (with a persisted reason).

**Architecture:** Extend the existing FastAPI monolith (`publisher/src/publisher/api.py`, `create_app`) in place. Add (1) a `reject_reason` field threaded `Job` -> DB -> `reject_job` -> reject endpoint -> `JobView`; (2) `description` on `JobView`; (3) a `status` query param on `GET /api/jobs`; (4) a `GET /api/jobs/{id}/video` `FileResponse` streaming endpoint; (5) a `GET /` route serving a single static HTML+vanilla-JS review page. No new process, no build step, no JS framework.

**Tech Stack:** Python 3.12, FastAPI, Starlette `FileResponse`/`HTMLResponse`, SQLite (stdlib sqlite3, no ORM), pytest + `fastapi.testclient.TestClient`. Test runner: `publisher\.venv\Scripts\python.exe -m pytest`.

**Working directory for all commands:** `D:\Rewva\signal-lab\publisher` (the publisher has its own venv at `publisher\.venv`). On Windows/PowerShell use `publisher\.venv\Scripts\python.exe`; the commands below show the bash form `.venv/Scripts/python.exe` -- either works.

**Conventions to follow (already in the repo):**
- API tests live in `publisher/tests/test_api*.py`, use a `client` fixture: `db = Database(tmp_path / "pub.db"); db.init_schema(); TestClient(create_app(db))`.
- DB list/dict columns are JSON text; scalar additive columns use `TEXT NOT NULL DEFAULT ''`.
- ASCII quotes only in any data/markup/config.

---

### Task 1: Thread `reject_reason` through the model + DB

**Files:**
- Modify: `publisher/src/publisher/models.py:44-46` (add field to `Job`)
- Modify: `publisher/src/publisher/db.py:29-47` (schema column), `:149-163` (create_job insert), `:200-203` (soft_delete / setter), `:205-217` (`_row_to_job`)
- Test: `publisher/tests/test_db.py`

- [ ] **Step 1: Write the failing test**

Add to `publisher/tests/test_db.py`:

```python
def test_reject_reason_defaults_empty_and_persists(tmp_path):
    from publisher.db import Database
    from publisher.models import Job
    db = Database(tmp_path / "pub.db"); db.init_schema()
    job = db.create_job(Job(channel_id="gk", video_path="x.mp4", title="T", status="PENDING_APPROVAL"))
    assert db.get_job(job.id).reject_reason == ""
    db.set_reject_reason(job.id, "fact wrong")
    assert db.get_job(job.id).reject_reason == "fact wrong"
    db.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_db.py::test_reject_reason_defaults_empty_and_persists -v`
Expected: FAIL (`TypeError: __init__() got an unexpected keyword`/`AttributeError: 'Database' object has no attribute 'set_reject_reason'`, or `no column named reject_reason`).

- [ ] **Step 3: Write minimal implementation**

In `models.py`, add to `Job` (after `sources`, before `id`):

```python
    reject_reason: str = ""  # operator's reason captured at the review gate
```

In `db.py` SCHEMA `jobs` table, add after the `sources` column line:

```python
    sources         TEXT NOT NULL DEFAULT '[]',
    reject_reason   TEXT NOT NULL DEFAULT ''
```

(Note: the existing `-- NOTE:` comment about dropping `publisher.db` already covers the "won't add columns to a pre-existing DB" caveat; this new column is subject to the same caveat.)

In `db.create_job`, add `reject_reason` to the INSERT column list, add one `?` placeholder, and add `job.reject_reason` to the params tuple (keep order consistent -- append it last, after `json.dumps(job.sources)`):

```python
            "deleted_at, attempts, source_citation, sources, reject_reason) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (job.channel_id, job.video_path, job.title, job.description,
             json.dumps(job.tags), json.dumps(job.platforms),
             json.dumps(job.per_platform), job.status, job.submitted_at,
             job.scheduled_for, job.posted_at, job.deleted_at, job.attempts,
             job.source_citation, json.dumps(job.sources), job.reject_reason),
```

Add a setter near `soft_delete_job`:

```python
    def set_reject_reason(self, job_pk: int, reason: str) -> None:
        self._write("UPDATE jobs SET reject_reason = ? WHERE id = ?", (reason, job_pk))
```

In `_row_to_job`, add (after `sources=...`):

```python
            reject_reason=row["reject_reason"],
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_db.py::test_reject_reason_defaults_empty_and_persists -v`
Expected: PASS.

- [ ] **Step 5: Run the full db suite to catch INSERT-arity regressions**

Run: `.venv/Scripts/python.exe -m pytest tests/test_db.py tests/test_db_orchestration.py -v`
Expected: all PASS (confirms the 16-placeholder INSERT still matches every caller).

- [ ] **Step 6: Commit**

```bash
git add publisher/src/publisher/models.py publisher/src/publisher/db.py publisher/tests/test_db.py
git commit -m "feat(publisher): persist reject_reason on jobs"
```

---

### Task 2: Thread `reject_reason` into `reject_job` + the reject endpoint

**Files:**
- Modify: `publisher/src/publisher/approval.py:39-46` (`reject_job` signature)
- Modify: `publisher/src/publisher/api.py:46-47` (new `RejectRequest`), `:163-171` (reject endpoint)
- Test: `publisher/tests/test_approval.py`, `publisher/tests/test_api_approval.py`

- [ ] **Step 1: Write the failing tests**

Add to `publisher/tests/test_approval.py`:

```python
def test_reject_job_persists_reason(tmp_path):
    from publisher.db import Database
    from publisher.models import Job
    from publisher.approval import reject_job
    db = Database(tmp_path / "pub.db"); db.init_schema()
    job = db.create_job(Job(channel_id="gk", video_path="x.mp4", title="T", status="PENDING_APPROVAL"))
    rejected = reject_job(db, job.id, reason="citation broken")
    assert rejected.status == "REJECTED"
    assert rejected.reject_reason == "citation broken"
    db.close()
```

Add to `publisher/tests/test_api_approval.py` (follow its existing fixture/imports):

```python
def test_reject_with_reason_via_api(client):
    job_id = client.post("/api/jobs", json=_submission()).json()["id"]
    resp = client.post(f"/api/jobs/{job_id}/reject", json={"reason": "wrong answer"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "REJECTED"
    assert resp.json()["reject_reason"] == "wrong answer"

def test_reject_without_body_still_works(client):
    job_id = client.post("/api/jobs", json=_submission()).json()["id"]
    resp = client.post(f"/api/jobs/{job_id}/reject")
    assert resp.status_code == 200
    assert resp.json()["reject_reason"] == ""
```

(If `test_api_approval.py` has no `_submission` helper, copy the one from `tests/test_api.py:18-25`.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_approval.py::test_reject_job_persists_reason tests/test_api_approval.py -k reject -v`
Expected: the new tests FAIL (`reject_job() got an unexpected keyword argument 'reason'` / `reject_reason` missing in JobView).

- [ ] **Step 3: Write minimal implementation**

In `approval.py`, change `reject_job`:

```python
def reject_job(db: Database, job_id: int, reason: str = "") -> Job:
    job = db.get_job(job_id)
    if job is None:
        raise LookupError(f"job {job_id} not found")
    validate_transition(job.status, "REJECTED")
    db.update_job_status(job_id, "REJECTED")
    if reason:
        db.set_reject_reason(job_id, reason)
    db.soft_delete_job(job_id)
    return db.get_job(job_id, include_deleted=True)
```

In `api.py`, add a request model below `ApproveRequest` (line ~48):

```python
class RejectRequest(BaseModel):
    reason: str = ""
```

Change the reject endpoint:

```python
    @app.post("/api/jobs/{job_id}/reject", response_model=JobView)
    def reject(job_id: int, body: RejectRequest | None = None) -> JobView:
        reason = body.reason if body else ""
        try:
            job = reject_job(db, job_id, reason=reason)
        except LookupError:
            raise HTTPException(status_code=404, detail="job not found")
        except InvalidTransition as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        return _to_view(job)
```

(`JobView.reject_reason` is added in Task 3; these API tests assert it, so run Task 3 before re-running the API-level assertions, OR temporarily add `reject_reason` to JobView now. To keep tasks independent, add the `JobView` field + `_to_view` mapping here as part of Step 3 -- see Task 3 Step 3 for the exact lines -- then Task 3 only adds `description`.)

To keep this task self-contained, also apply the `reject_reason` half of Task 3 now: add `reject_reason: str` to `JobView` (api.py:100-111) and `reject_reason=job.reject_reason` to `_to_view` (api.py:113-119).

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_approval.py::test_reject_job_persists_reason tests/test_api_approval.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add publisher/src/publisher/approval.py publisher/src/publisher/api.py publisher/tests/test_approval.py publisher/tests/test_api_approval.py
git commit -m "feat(publisher): reject endpoint accepts and persists a reason"
```

---

### Task 3: Expose `description` on `JobView` + `status` filter on `GET /api/jobs`

**Files:**
- Modify: `publisher/src/publisher/api.py:100-119` (`JobView` + `_to_view`), `:140-142` (`list_jobs`)
- Test: `publisher/tests/test_api.py`

- [ ] **Step 1: Write the failing tests**

Add to `publisher/tests/test_api.py`:

```python
def test_jobview_exposes_description(client):
    job_id = client.post("/api/jobs", json=_submission(description="my caption")).json()["id"]
    assert client.get(f"/api/jobs/{job_id}").json()["description"] == "my caption"


def test_list_jobs_filters_by_status(client):
    client.post("/api/jobs", json=_submission(title="A"))
    client.post("/api/jobs", json=_submission(title="B"))
    pending = client.get("/api/jobs", params={"status": "PENDING_APPROVAL"}).json()
    assert len(pending) == 2
    assert client.get("/api/jobs", params={"status": "SCHEDULED"}).json() == []
    assert len(client.get("/api/jobs").json()) == 2  # no filter == all
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_api.py -k "description or filters_by_status" -v`
Expected: FAIL (`KeyError: 'description'` in JobView / `status` param ignored or 422).

- [ ] **Step 3: Write minimal implementation**

In `api.py`, add to `JobView` (after `per_platform`):

```python
    description: str
```

Add to `_to_view(...)` call args:

```python
        description=job.description,
```

(If Task 2 already added `reject_reason` to `JobView`/`_to_view`, leave it; otherwise add it now too.)

Change `list_jobs`:

```python
    @app.get("/api/jobs", response_model=list[JobView])
    def list_jobs(status: str | None = None) -> list[JobView]:
        return [_to_view(j) for j in db.list_jobs(status=status)]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_api.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add publisher/src/publisher/api.py publisher/tests/test_api.py
git commit -m "feat(publisher): JobView exposes description; GET /api/jobs takes a status filter"
```

---

### Task 4: `GET /api/jobs/{id}/video` streaming endpoint

**Files:**
- Modify: `publisher/src/publisher/api.py` (new endpoint in `create_app`, after `get_job`)
- Test: `publisher/tests/test_api_video.py` (Create)

- [ ] **Step 1: Write the failing test**

Create `publisher/tests/test_api_video.py`:

```python
"""Tests for GET /api/jobs/{id}/video -- streams the MP4 for the review dashboard."""

import pytest
from fastapi.testclient import TestClient

from publisher.api import create_app
from publisher.db import Database
from publisher.models import Job


@pytest.fixture
def client(tmp_path):
    db = Database(tmp_path / "pub.db"); db.init_schema()
    yield TestClient(create_app(db)), db, tmp_path
    db.close()


def test_video_streams_existing_file(client):
    tc, db, tmp_path = client
    video = tmp_path / "quiz.mp4"
    video.write_bytes(b"\x00\x00\x00\x18ftypmp42fake-mp4-bytes")
    job = db.create_job(Job(channel_id="gk", video_path=str(video), title="T",
                            status="PENDING_APPROVAL"))
    resp = tc.get(f"/api/jobs/{job.id}/video")
    assert resp.status_code == 200
    assert resp.content == b"\x00\x00\x00\x18ftypmp42fake-mp4-bytes"
    assert "video" in resp.headers["content-type"]


def test_video_missing_job_is_404(client):
    tc, db, tmp_path = client
    assert tc.get("/api/jobs/999/video").status_code == 404


def test_video_missing_file_is_404(client):
    tc, db, tmp_path = client
    job = db.create_job(Job(channel_id="gk", video_path=str(tmp_path / "gone.mp4"),
                            title="T", status="PENDING_APPROVAL"))
    assert tc.get(f"/api/jobs/{job.id}/video").status_code == 404


def test_video_empty_path_is_404(client):
    tc, db, tmp_path = client
    job = db.create_job(Job(channel_id="gk", video_path="", title="T",
                            status="PENDING_APPROVAL"))
    assert tc.get(f"/api/jobs/{job.id}/video").status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_api_video.py -v`
Expected: FAIL (404 for the streaming test -- route does not exist yet).

- [ ] **Step 3: Write minimal implementation**

In `api.py`, add the import at the top (with the other fastapi imports):

```python
from fastapi.responses import FileResponse
from pathlib import Path
```

Add the endpoint inside `create_app`, right after the `get_job` route (line ~149):

```python
    @app.get("/api/jobs/{job_id}/video")
    def get_job_video(job_id: int) -> FileResponse:
        job = db.get_job(job_id)
        if job is None or not job.video_path or not Path(job.video_path).is_file():
            raise HTTPException(status_code=404, detail="video not found")
        return FileResponse(job.video_path, media_type="video/mp4")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_api_video.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add publisher/src/publisher/api.py publisher/tests/test_api_video.py
git commit -m "feat(publisher): stream a job's MP4 via GET /api/jobs/{id}/video"
```

---

### Task 5: `GET /` serves the review page (HTML shell)

**Files:**
- Create: `publisher/src/publisher/static/review.html`
- Modify: `publisher/src/publisher/api.py` (new `GET /` route in `create_app`)
- Test: `publisher/tests/test_api_review_page.py` (Create)

- [ ] **Step 1: Write the failing test**

Create `publisher/tests/test_api_review_page.py`:

```python
"""Tests that GET / serves the review-queue HTML page wired to the right endpoints."""

import pytest
from fastapi.testclient import TestClient

from publisher.api import create_app
from publisher.db import Database


@pytest.fixture
def client(tmp_path):
    db = Database(tmp_path / "pub.db"); db.init_schema()
    yield TestClient(create_app(db))
    db.close()


def test_root_serves_html(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "Review Queue" in resp.text


def test_page_references_the_api_endpoints(client):
    html = client.get("/").text
    # the JS must target the real endpoints
    assert "/api/jobs?status=PENDING_APPROVAL" in html
    assert "/api/jobs/" in html          # video + approve + reject paths
    assert "/approve" in html
    assert "/reject" in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_api_review_page.py -v`
Expected: FAIL (`GET /` returns 404).

- [ ] **Step 3: Write the page + the route**

Create `publisher/src/publisher/static/review.html` (ASCII quotes only; no external CDNs):

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Daily GK -- Review Queue</title>
<style>
  :root { color-scheme: dark; }
  body { margin: 0; background: #0d0b1f; color: #f2f2f7;
         font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; }
  header { padding: 16px 24px; background: #15123b; font-size: 20px; font-weight: 700; }
  #queue { display: grid; gap: 20px; padding: 24px;
           grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); }
  .card { background: #1a1733; border: 1px solid #2c2752; border-radius: 14px;
          padding: 16px; display: flex; flex-direction: column; gap: 10px; }
  .card video { width: 100%; border-radius: 10px; background: #000; aspect-ratio: 9/16; }
  .title { font-weight: 600; font-size: 16px; }
  .caption { font-size: 13px; color: #c7c4d8; white-space: pre-wrap; }
  .cite { font-size: 13px; color: #c6f24e; }
  .cite a { display: inline-block; margin: 2px 6px 2px 0; padding: 2px 8px;
            background: #2c2752; color: #c6f24e; border-radius: 6px;
            text-decoration: none; font-size: 12px; }
  .actions { display: flex; gap: 10px; margin-top: 4px; }
  button { flex: 1; padding: 10px; border: 0; border-radius: 8px; font-weight: 600;
           cursor: pointer; font-size: 14px; }
  .approve { background: #c6f24e; color: #15123b; }
  .reject  { background: #3a2740; color: #ff9db0; }
  .reason { width: 100%; box-sizing: border-box; margin-top: 8px; padding: 8px;
            border-radius: 8px; border: 1px solid #2c2752; background: #100e26;
            color: #f2f2f7; resize: vertical; }
  .hidden { display: none; }
  .err { color: #ff9db0; font-size: 12px; }
  #empty { padding: 40px 24px; color: #8e8aa8; }
</style>
</head>
<body>
<header>Daily GK -- Review Queue</header>
<div id="empty" class="hidden">No videos awaiting review.</div>
<div id="queue"></div>
<script>
const QUEUE = document.getElementById("queue");
const EMPTY = document.getElementById("empty");

async function load() {
  QUEUE.innerHTML = "";
  const jobs = await fetch("/api/jobs?status=PENDING_APPROVAL").then(r => r.json());
  EMPTY.classList.toggle("hidden", jobs.length > 0);
  for (const job of jobs) QUEUE.appendChild(card(job));
}

function el(tag, cls, text) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text != null) n.textContent = text;
  return n;
}

function card(job) {
  const c = el("div", "card");

  const v = el("video");
  v.controls = true; v.preload = "metadata";
  v.src = "/api/jobs/" + job.id + "/video";
  c.appendChild(v);

  c.appendChild(el("div", "title", job.title));
  if (job.description) c.appendChild(el("div", "caption", job.description));

  if (job.source_citation || (job.sources && job.sources.length)) {
    const cite = el("div", "cite", job.source_citation ? ("Source: " + job.source_citation + " ") : "Sources: ");
    (job.sources || []).forEach((url, i) => {
      const a = el("a", null, "verify " + (i + 1));
      a.href = url; a.target = "_blank"; a.rel = "noopener noreferrer";
      cite.appendChild(a);
    });
    c.appendChild(cite);
  }

  const err = el("div", "err");
  const actions = el("div", "actions");
  const approve = el("button", "approve", "Approve");
  const reject = el("button", "reject", "Reject");
  actions.appendChild(approve); actions.appendChild(reject);

  const reason = el("textarea", "reason hidden");
  reason.placeholder = "Reason for rejecting (optional)...";
  const confirm = el("button", "reject hidden", "Confirm reject");

  approve.onclick = () => act(c, err, "/api/jobs/" + job.id + "/approve", {});
  reject.onclick = () => { reason.classList.remove("hidden"); confirm.classList.remove("hidden"); };
  confirm.onclick = () => act(c, err, "/api/jobs/" + job.id + "/reject", { reason: reason.value });

  c.appendChild(err);
  c.appendChild(actions);
  c.appendChild(reason);
  c.appendChild(confirm);
  return c;
}

async function act(card, err, url, body) {
  err.textContent = "";
  try {
    const r = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (r.status === 409) { await load(); return; }   // already acted on elsewhere
    if (!r.ok) throw new Error("HTTP " + r.status);
    card.remove();
    if (!QUEUE.children.length) EMPTY.classList.remove("hidden");
  } catch (e) {
    err.textContent = "Failed: " + e.message + " (retry)";
  }
}

load();
</script>
</body>
</html>
```

In `api.py`, add the import (with the other responses import):

```python
from fastapi.responses import FileResponse, HTMLResponse
```

Add a module-level constant near the top of `api.py` (after imports):

```python
_REVIEW_PAGE = Path(__file__).parent / "static" / "review.html"
```

Add the route inside `create_app` (near `health`):

```python
    @app.get("/", response_class=HTMLResponse)
    def review_page() -> HTMLResponse:
        return HTMLResponse(_REVIEW_PAGE.read_text(encoding="utf-8"))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_api_review_page.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add publisher/src/publisher/api.py publisher/src/publisher/static/review.html publisher/tests/test_api_review_page.py
git commit -m "feat(publisher): serve a review-queue page at GET /"
```

---

### Task 6: Full suite + manual smoke verification

**Files:** none (verification only)

- [ ] **Step 1: Run the entire publisher suite**

Run: `.venv/Scripts/python.exe -m pytest -q`
Expected: all PASS (prior 177 + the new tests; no regressions).

- [ ] **Step 2: Manual smoke (operator path)**

Start the publisher and submit a job pointing at a real rendered MP4 (use one from `daily-gk-quiz/out/` if present, else any local .mp4):

```bash
.venv/Scripts/python.exe main.py   # serves on http://127.0.0.1:8077
```

In a second shell, submit a pending job (adjust video_path to a real file):

```bash
curl -s -X POST http://127.0.0.1:8077/api/jobs -H "Content-Type: application/json" -d "{\"channel_id\":\"daily-gk-quiz\",\"video_path\":\"D:/Rewva/signal-lab/daily-gk-quiz/out/SOME.mp4\",\"title\":\"Daily GK #1\",\"description\":\"caption\",\"platforms\":[\"youtube\"],\"source_citation\":\"Constitution of India, Art. 21\",\"sources\":[\"https://www.constitutionofindia.net/articles/article-21/\"]}"
```

Open `http://127.0.0.1:8077/` in a browser. Confirm:
- the card shows the **playable video** (plays + seeks),
- the **citation chip** opens the source URL in a new tab,
- **Approve** removes the card and the job is now `SCHEDULED` (`GET /api/jobs?status=SCHEDULED`),
- **Reject** with a reason removes the card and `GET /api/jobs/{id}` (the job is soft-deleted; check via a fresh submit) shows `reject_reason`.

- [ ] **Step 3: Note results**

Record in the commit / PR description what was eyeballed (video played, citation opened, approve->SCHEDULED, reject reason persisted). If `ffprobe`/browser is unavailable, state what was skipped and why (per repo gotchas, ffprobe is not installed -- video playback in a real browser is the check that matters here, not ffprobe).

---

## Self-Review notes (author)

- **Spec coverage:** SS3.1 -> Task 5; SS3.2 -> Task 4; SS3.3 -> Task 3 (status filter); SS3.4/SS4 reject-reason -> Tasks 1+2; SS5 page/card -> Task 5; SS6 description on JobView -> Task 3; SS7 testing -> each task's tests + Task 6. All covered.
- **Ordering caveat:** Task 2's API test asserts `reject_reason` in `JobView`, so Task 2 Step 3 adds the `JobView.reject_reason` field + `_to_view` mapping itself (noted inline) to stay self-contained; Task 3 then only adds `description`. If executed strictly in order this is clean.
- **DB INSERT arity:** Task 1 changes `create_job` to 16 columns/placeholders -- Step 5 runs the db + orchestration suites to catch any mismatch.
- **No placeholders:** every code + command step is concrete.
