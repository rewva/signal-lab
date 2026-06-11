# GK End-to-End Glue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect the selection layer to the renderer to the publisher — turn a `DayPlan` + an operator-verified `Question` into a 1080x1920 MP4 and a `PENDING_APPROVAL` publisher job, threading the source citation + URLs through for a future review dashboard.

**Architecture:** A small pure assembler (`selection/assemble.py`) maps the verified `Question` + frozen plan fields into render `QuizProps` and a `POST /api/jobs` body. A thin CLI (`selection/build.py`) writes props, renders via the existing `render.mjs` subprocess, then POSTs the job. The publisher's `Job` gains two additive fields (`source_citation`, `sources`). All decisions made at planning time are frozen into one render-request JSON so `build.py` never re-derives them.

**Tech Stack:** Python 3.12 (stdlib only — `urllib.request`, `subprocess`, `dataclasses`); pytest; the existing Remotion/Node renderer; FastAPI + sqlite3 publisher.

**Spec:** `docs/specs/2026-06-11-gk-end-to-end-glue-design.md`

**Conventions:**
- Run Python tests from `daily-gk-quiz/`: `.venv\Scripts\python.exe -m pytest tests/ -q`
- Run publisher tests from `publisher/`: `.venv\Scripts\python.exe -m pytest tests/ -q` (or the publisher's own venv/runner — match how its 175 tests are currently run)
- ASCII quotes only in data/config files (CLAUDE.md).
- Commit after each task.

---

### Task 1: Add `source_citation` to the `Question` model

**Files:**
- Modify: `daily-gk-quiz/selection/models.py`
- Modify: `daily-gk-quiz/tests/test_models.py`
- Modify: `daily-gk-quiz/tests/test_models_render.py`

- [ ] **Step 1: Write the failing test**

In `daily-gk-quiz/tests/test_models.py`, add `source_citation` to the `_q` base dict and a new reject test:

```python
def _q(**over):
    base = dict(
        domain="polity", difficulty="basic",
        fact_key="polity/article-21-right-to-life", entity="Article 21",
        question="Article 21 guarantees the right to what?",
        answer="Life and personal liberty",
        distractors=["Equality", "Freedom of speech", "Property"],
        exam_relevance=["SSC", "RRB"],
        sources=["https://a.gov.in", "https://b.org"],
        explanation="Article 21 protects life and personal liberty.",
        source_citation="Constitution of India, Art. 21",
        mnemonic=None,
    )
    base.update(over)
    return Question(**base)


def test_question_requires_source_citation():
    with pytest.raises(ValueError, match="source_citation is required"):
        _q(source_citation="").validate()


def test_question_keeps_source_citation_through_dict():
    q = _q(source_citation="RBI Monetary Policy, Feb 2026")
    assert Question.from_dict(q.to_dict()).source_citation == "RBI Monetary Policy, Feb 2026"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_models.py -q`
Expected: FAIL — `TypeError: Question.__init__() got an unexpected keyword argument 'source_citation'`.

- [ ] **Step 3: Add the field, validation, and from_dict mapping**

In `daily-gk-quiz/selection/models.py`, add the field at the END of the dataclass field list (after `is_trick`, to avoid shifting any positional construction):

```python
    explanation: str = ""          # trailing defaults keep positional construction valid
    mnemonic: Optional[str] = None
    is_trick: bool = False
    source_citation: str = ""      # human-readable on-screen citation (distinct from sources URLs)
```

Add the validation check in `validate()`, immediately after the explanation check:

```python
        if not self.explanation.strip():
            raise ValueError("explanation is required (per-video pedagogy)")
        if not self.source_citation.strip():
            raise ValueError("source_citation is required (on-screen citation / trust badge)")
```

Add to `from_dict()` (after the `explanation=`/`mnemonic=` line):

```python
            explanation=d.get("explanation", ""), mnemonic=d.get("mnemonic"),
            is_trick=d.get("is_trick", False),
            source_citation=d.get("source_citation", ""),
```

(`to_dict()` uses `asdict()`, so the field round-trips automatically.)

- [ ] **Step 4: Run the model tests to verify they pass**

Run: `.venv\Scripts\python.exe -m pytest tests/test_models.py -q`
Expected: PASS (all tests, including the two new ones).

- [ ] **Step 5: Keep the render-fixture realistic**

In `daily-gk-quiz/tests/test_models_render.py`, add `source_citation` to its `_q` base dict (these tests do not call `.validate()`, but keep the fixture honest):

```python
    base = dict(domain="polity", difficulty="basic", fact_key="polity/art-21",
                entity="Article 21", question="Q?", answer="Article 21",
                distractors=["a", "b", "c"], exam_relevance=["SSC"],
                sources=["https://1", "https://2"], explanation="why",
                source_citation="Constitution of India, Art. 21")
```

- [ ] **Step 6: Run the full selection suite (guard against other fixtures)**

Run: `.venv\Scripts\python.exe -m pytest tests/ -q`
Expected: PASS (46 prior + 2 new). If any other test constructs a `Question` and calls `.validate()`, add `source_citation="..."` to that fixture too.

- [ ] **Step 7: Commit**

```bash
git add daily-gk-quiz/selection/models.py daily-gk-quiz/tests/test_models.py daily-gk-quiz/tests/test_models_render.py
git commit -m "feat: add required source_citation to Question (on-screen trust citation)"
```

---

### Task 2: Add a `labels` map to `data/domains.json`

**Files:**
- Modify: `daily-gk-quiz/data/domains.json`
- Test: `daily-gk-quiz/tests/test_seed_data.py`

- [ ] **Step 1: Write the failing test**

Append to `daily-gk-quiz/tests/test_seed_data.py`:

```python
def test_every_weighted_domain_has_a_label():
    import json
    data = json.load(open("data/domains.json"))
    assert "labels" in data, "domains.json must carry a display-label map"
    for slug in data["weights"]:
        assert slug in data["labels"], f"missing label for domain {slug}"
        assert data["labels"][slug].strip(), f"empty label for domain {slug}"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_seed_data.py::test_every_weighted_domain_has_a_label -q`
Expected: FAIL — `assert "labels" in data`.

- [ ] **Step 3: Add the `labels` map**

In `daily-gk-quiz/data/domains.json`, add a top-level `"labels"` object (ASCII only):

```json
  "labels": {
    "current-affairs": "Current Affairs",
    "general-science": "General Science",
    "static-gk": "Static GK",
    "history": "History",
    "polity": "Polity",
    "geography": "Geography",
    "economy": "Economy",
    "banking-financial-awareness": "Banking & Financial Awareness",
    "sports-awards-misc": "Sports & Awards"
  }
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_seed_data.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add daily-gk-quiz/data/domains.json daily-gk-quiz/tests/test_seed_data.py
git commit -m "feat: domain display-label map in domains.json"
```

---

### Task 3: `assemble.order_options` — place the answer in its slot

**Files:**
- Create: `daily-gk-quiz/selection/assemble.py`
- Test: `daily-gk-quiz/tests/test_assemble.py`

- [ ] **Step 1: Write the failing test**

Create `daily-gk-quiz/tests/test_assemble.py`:

```python
import pytest
from selection.assemble import order_options


def test_answer_placed_in_each_position():
    answer = "Article 21"
    distractors = ["Article 19", "Article 14", "Article 32"]
    for pos in ("A", "B", "C", "D"):
        opts = order_options(answer, distractors, pos)
        assert [o["letter"] for o in opts] == ["A", "B", "C", "D"]
        by_letter = {o["letter"]: o["text"] for o in opts}
        assert by_letter[pos] == answer
        # the three distractors fill the other slots, in order
        others = [o["text"] for o in opts if o["letter"] != pos]
        assert others == distractors


def test_position_c_layout():
    opts = order_options("ANS", ["d0", "d1", "d2"], "C")
    assert opts == [
        {"letter": "A", "text": "d0"},
        {"letter": "B", "text": "d1"},
        {"letter": "C", "text": "ANS"},
        {"letter": "D", "text": "d2"},
    ]


def test_rejects_wrong_distractor_count():
    with pytest.raises(ValueError):
        order_options("ANS", ["only", "two"], "A")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_assemble.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'selection.assemble'`.

- [ ] **Step 3: Implement `order_options`**

Create `daily-gk-quiz/selection/assemble.py`:

```python
from __future__ import annotations

POSITIONS = ("A", "B", "C", "D")


def order_options(answer: str, distractors: list[str], position: str) -> list[dict]:
    """The 4 A/B/C/D options with `answer` in `position` and the 3 distractors
    filling the remaining slots in order. Deterministic."""
    if len(distractors) != 3:
        raise ValueError("order_options needs exactly 3 distractors")
    if position not in POSITIONS:
        raise ValueError(f"position must be one of {POSITIONS}")
    remaining = list(distractors)
    options = []
    for letter in POSITIONS:
        text = answer if letter == position else remaining.pop(0)
        options.append({"letter": letter, "text": text})
    return options
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_assemble.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add daily-gk-quiz/selection/assemble.py daily-gk-quiz/tests/test_assemble.py
git commit -m "feat: order_options places correct answer in its A/B/C/D slot"
```

---

### Task 4: `assemble.quiz_props` — build the render props

**Files:**
- Modify: `daily-gk-quiz/selection/assemble.py`
- Test: `daily-gk-quiz/tests/test_assemble.py`

- [ ] **Step 1: Write the failing test**

Add to `daily-gk-quiz/tests/test_assemble.py`:

```python
from selection.assemble import quiz_props, RenderPlan
from selection.models import Question

LABELS = {"polity": "Polity", "current-affairs": "Current Affairs"}


def _question(**over):
    base = dict(
        domain="polity", difficulty="basic", fact_key="polity/article-21",
        entity="Article 21", question="Article 21 guarantees what?",
        answer="Life and personal liberty",
        distractors=["Equality", "Free speech", "Property"],
        exam_relevance=["SSC", "RRB"], sources=["https://a.gov.in", "https://b.org"],
        explanation="It protects life and personal liberty.",
        source_citation="Constitution of India, Art. 21",
    )
    base.update(over)
    return Question(**base)


EXPECTED_PROP_KEYS = {
    "dayNumber", "category", "difficulty", "examPrefix", "template", "question",
    "options", "correctLetter", "explanation", "sourceLine", "cta", "trickHook",
}


def test_quiz_props_full_mapping():
    plan = RenderPlan(answer_position="C", cta="Comment A or B", trick_hook="")
    props = quiz_props(_question(), plan, day_number=47, labels=LABELS)
    assert set(props.keys()) == EXPECTED_PROP_KEYS  # matches the zod QuizProps schema
    assert props["dayNumber"] == 47
    assert props["category"] == "Polity"
    assert props["difficulty"] == "basic"
    assert props["examPrefix"] == "SSC"
    assert props["template"] == "standard"
    assert props["correctLetter"] == "C"
    assert props["options"][2] == {"letter": "C", "text": "Life and personal liberty"}
    assert props["sourceLine"] == "Constitution of India, Art. 21"
    assert props["cta"] == "Comment A or B"
    assert props["trickHook"] == ""


def test_quiz_props_trick_template_and_hook():
    plan = RenderPlan(answer_position="A", cta="Comment A or B", trick_hook="Common Exam Trap")
    props = quiz_props(_question(is_trick=True), plan, day_number=5, labels=LABELS)
    assert props["template"] == "trick"
    assert props["trickHook"] == "Common Exam Trap"


def test_quiz_props_empty_exam_relevance_gives_blank_prefix():
    props = quiz_props(_question(exam_relevance=[]), RenderPlan("A", "cta", ""),
                       day_number=1, labels=LABELS)
    assert props["examPrefix"] == ""


def test_quiz_props_category_falls_back_to_titlecased_slug():
    props = quiz_props(_question(domain="general-science"), RenderPlan("A", "cta", ""),
                       day_number=1, labels=LABELS)
    assert props["category"] == "General Science"  # slug not in LABELS -> fallback
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_assemble.py -q`
Expected: FAIL — `ImportError: cannot import name 'quiz_props'`.

- [ ] **Step 3: Implement `RenderPlan` + `quiz_props`**

Add to `daily-gk-quiz/selection/assemble.py` (import at top, `RenderPlan` near the top, function below `order_options`):

```python
from dataclasses import dataclass

from selection.selection import template_for


@dataclass
class RenderPlan:
    """The subset of DayPlan frozen at planning time and needed for assembly.
    A real DayPlan is structurally compatible (same attribute names)."""
    answer_position: str
    cta: str
    trick_hook: str = ""


def _category_label(domain: str, labels: dict) -> str:
    if domain in labels:
        return labels[domain]
    return domain.replace("-", " ").title()  # fallback: "general-science" -> "General Science"


def quiz_props(question, plan, day_number: int, labels: dict) -> dict:
    """Map a verified Question + frozen plan fields into the renderer's QuizProps dict."""
    return {
        "dayNumber": day_number,
        "category": _category_label(question.domain, labels),
        "difficulty": question.difficulty,
        "examPrefix": question.exam_relevance[0] if question.exam_relevance else "",
        "template": template_for(question.is_trick),
        "question": question.question,
        "options": order_options(question.answer, question.distractors, plan.answer_position),
        "correctLetter": plan.answer_position,
        "explanation": question.explanation,
        "sourceLine": question.source_citation,
        "cta": plan.cta,
        "trickHook": plan.trick_hook,
    }
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_assemble.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add daily-gk-quiz/selection/assemble.py daily-gk-quiz/tests/test_assemble.py
git commit -m "feat: quiz_props maps verified Question + plan into render QuizProps"
```

---

### Task 5: `assemble.job_submission` — build the publisher job body

**Files:**
- Modify: `daily-gk-quiz/selection/assemble.py`
- Test: `daily-gk-quiz/tests/test_assemble.py`

- [ ] **Step 1: Write the failing test**

Add to `daily-gk-quiz/tests/test_assemble.py`:

```python
from selection.assemble import job_submission


def test_job_submission_full_body():
    body = job_submission(
        _question(), day_number=47, video_path="out/polity__article-21.mp4",
        description="Did you know Article 21 covers privacy?",
        ai_disclosure=True, labels=LABELS,
    )
    assert body["channel_id"] == "daily-gk-quiz"
    assert body["platforms"] == ["youtube", "facebook", "instagram"]
    assert body["video_path"] == "out/polity__article-21.mp4"
    assert body["title"] == "Daily GK #47 - Polity"
    assert body["description"].startswith("Did you know Article 21 covers privacy?")
    assert "Source: Constitution of India, Art. 21" in body["description"]
    assert body["tags"] == ["#SSC", "#RRB", "#Polity", "#DailyGK", "#GKQuiz"]
    assert body["per_platform"] == {"youtube": {"ai_disclosure": True}}
    # threaded for the future review dashboard
    assert body["source_citation"] == "Constitution of India, Art. 21"
    assert body["sources"] == ["https://a.gov.in", "https://b.org"]


def test_job_submission_compound_category_hashtag_is_alphanumeric():
    body = job_submission(
        _question(domain="banking-financial-awareness", exam_relevance=["IBPS-SBI"]),
        day_number=1, video_path="out/x.mp4", description="d",
        ai_disclosure=False, labels={"banking-financial-awareness": "Banking & Financial Awareness"},
    )
    assert body["tags"] == ["#IBPSSBI", "#BankingFinancialAwareness", "#DailyGK", "#GKQuiz"]
    assert body["per_platform"] == {"youtube": {"ai_disclosure": False}}
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_assemble.py -q`
Expected: FAIL — `ImportError: cannot import name 'job_submission'`.

- [ ] **Step 3: Implement `job_submission`**

Add to `daily-gk-quiz/selection/assemble.py`:

```python
DEFAULT_PLATFORMS = ("youtube", "facebook", "instagram")
DEFAULT_CHANNEL_ID = "daily-gk-quiz"


def _hashtag(text: str) -> str:
    """A compact alphanumeric hashtag: 'IBPS-SBI' -> '#IBPSSBI'."""
    cleaned = "".join(ch for ch in text if ch.isalnum())
    return "#" + cleaned


def job_submission(question, day_number: int, video_path: str, description: str,
                   ai_disclosure: bool, labels: dict,
                   channel_id: str = DEFAULT_CHANNEL_ID,
                   platforms: list[str] | None = None) -> dict:
    """Build the POST /api/jobs body for one verified, rendered question."""
    category = _category_label(question.domain, labels)
    tags = [_hashtag(e) for e in question.exam_relevance]
    tags += [_hashtag(category), "#DailyGK", "#GKQuiz"]
    full_description = f"{description}\n\nSource: {question.source_citation}"
    return {
        "channel_id": channel_id,
        "video_path": video_path,
        "title": f"Daily GK #{day_number} - {category}",
        "description": full_description,
        "tags": tags,
        "platforms": list(platforms) if platforms is not None else list(DEFAULT_PLATFORMS),
        "per_platform": {"youtube": {"ai_disclosure": ai_disclosure}},
        "source_citation": question.source_citation,
        "sources": list(question.sources),
    }
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_assemble.py -q`
Expected: PASS (all assemble tests).

- [ ] **Step 5: Commit**

```bash
git add daily-gk-quiz/selection/assemble.py daily-gk-quiz/tests/test_assemble.py
git commit -m "feat: job_submission builds publisher POST body with threaded citation/sources"
```

---

### Task 6: Publisher — thread `source_citation` + `sources` through the job

**Files:**
- Modify: `publisher/src/publisher/models.py`
- Modify: `publisher/src/publisher/db.py`
- Modify: `publisher/src/publisher/api.py`
- Test: `publisher/tests/test_api.py`

- [ ] **Step 1: Write the failing test**

Add to `publisher/tests/test_api.py` (reuse the file's existing `client` fixture and `_submission` helper):

```python
def test_job_persists_and_returns_source_citation_and_sources(client):
    body = _submission()
    body["source_citation"] = "Constitution of India, Art. 21"
    body["sources"] = ["https://a.gov.in", "https://b.org"]
    job_id = client.post("/api/jobs", json=body).json()["id"]
    got = client.get(f"/api/jobs/{job_id}").json()
    assert got["source_citation"] == "Constitution of India, Art. 21"
    assert got["sources"] == ["https://a.gov.in", "https://b.org"]


def test_source_fields_default_to_empty_when_omitted(client):
    job_id = client.post("/api/jobs", json=_submission()).json()["id"]
    got = client.get(f"/api/jobs/{job_id}").json()
    assert got["source_citation"] == ""
    assert got["sources"] == []
```

(If `_submission` is module-local rather than fixture-shared, match the existing pattern in `test_api.py` for building a submission and a client.)

- [ ] **Step 2: Run the test to verify it fails**

Run (from `publisher/`): `.venv\Scripts\python.exe -m pytest tests/test_api.py -q`
Expected: FAIL — `KeyError: 'source_citation'` on the returned view.

- [ ] **Step 3a: Extend the `Job` model**

In `publisher/src/publisher/models.py`, add two fields to `Job` between `attempts` and `id` (keeps `id` last; both defaulted):

```python
    attempts: int = 0  # posting attempts made; drives retry-vs-fail
    source_citation: str = ""  # review-gate citation label (for the dashboard verify tag)
    sources: list[str] = field(default_factory=list)  # verify links the operator clicks
    id: Optional[int] = None
```

- [ ] **Step 3b: Extend the schema + persistence**

In `publisher/src/publisher/db.py`:

Add two columns to the `jobs` table in `SCHEMA` (after `attempts`):

```sql
    attempts        INTEGER NOT NULL DEFAULT 0,
    source_citation TEXT NOT NULL DEFAULT '',
    sources         TEXT NOT NULL DEFAULT '[]'
```

Extend `create_job`'s INSERT — add the two columns, two placeholders, and the two values:

```python
        job.id = self._write(
            "INSERT INTO jobs (channel_id, video_path, title, description, tags, "
            "platforms, per_platform, status, submitted_at, scheduled_for, posted_at, "
            "deleted_at, attempts, source_citation, sources) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (job.channel_id, job.video_path, job.title, job.description,
             json.dumps(job.tags), json.dumps(job.platforms),
             json.dumps(job.per_platform), job.status, job.submitted_at,
             job.scheduled_for, job.posted_at, job.deleted_at, job.attempts,
             job.source_citation, json.dumps(job.sources)),
        )
```

Extend `_row_to_job` — add the two fields:

```python
            posted_at=row["posted_at"], deleted_at=row["deleted_at"],
            attempts=row["attempts"],
            source_citation=row["source_citation"],
            sources=json.loads(row["sources"]),
        )
```

- [ ] **Step 3c: Extend the API intake + view**

In `publisher/src/publisher/api.py`:

Add to `JobSubmission`:

```python
    per_platform: dict[str, Any] = Field(default_factory=dict)
    source_citation: str = ""
    sources: list[str] = Field(default_factory=list)
```

Pass them through in `submit_job`'s `Job(...)`:

```python
            per_platform=submission.per_platform, status="PENDING_APPROVAL",
            source_citation=submission.source_citation, sources=submission.sources,
```

Add to `JobView`:

```python
    submitted_at: str | None
    scheduled_for: str | None
    source_citation: str
    sources: list[str]
```

Map them in `_to_view`:

```python
        submitted_at=job.submitted_at, scheduled_for=job.scheduled_for,
        source_citation=job.source_citation, sources=job.sources,
    )
```

- [ ] **Step 4: Run the publisher suite to verify it passes**

Run (from `publisher/`): `.venv\Scripts\python.exe -m pytest -q` (publisher has its own `.venv`)
Expected: PASS (175 prior + 2 new). The new columns are additive with defaults; existing tests use fresh DBs via `init_schema`, so no migration is needed.

> NOTE: `CREATE TABLE IF NOT EXISTS` will NOT add columns to a pre-existing `publisher.db`. The operator's live DB does not exist yet (live setup is a later step), so deleting any local dev `publisher.db` is sufficient. No migration code in scope.

- [ ] **Step 5: Commit**

```bash
git add publisher/src/publisher/models.py publisher/src/publisher/db.py publisher/src/publisher/api.py publisher/tests/test_api.py
git commit -m "feat: thread source_citation + sources through publisher job (for review dashboard)"
```

---

### Task 7: `selection/build.py` — orchestrate props -> render -> POST

**Files:**
- Create: `daily-gk-quiz/selection/build.py`
- Test: `daily-gk-quiz/tests/test_build.py`

The CLI's two side effects (render subprocess, HTTP POST) are injected so the orchestration is unit-testable; `main()` wires the real ones.

- [ ] **Step 1: Write the failing test**

Create `daily-gk-quiz/tests/test_build.py`:

```python
import json
import pytest
from selection import build


def _request():
    return {
        "question": {
            "domain": "polity", "difficulty": "basic", "fact_key": "polity/article-21",
            "entity": "Article 21", "question": "Article 21 guarantees what?",
            "answer": "Life and personal liberty",
            "distractors": ["Equality", "Free speech", "Property"],
            "exam_relevance": ["SSC", "RRB"], "sources": ["https://a.gov.in", "https://b.org"],
            "explanation": "Protects life and liberty.",
            "source_citation": "Constitution of India, Art. 21",
        },
        "answer_position": "C", "hook": "h", "cta": "Comment A or B",
        "trick_hook": "", "day_number": 47,
        "description": "Did you know?", "ai_disclosure": True,
    }


def _setup(tmp_path, request):
    req_path = tmp_path / "approved.json"
    req_path.write_text(json.dumps(request), encoding="utf-8")
    labels = {"polity": "Polity"}
    return req_path, labels


def test_fact_key_slugged_into_output_path(tmp_path):
    assert build.slug_filename("polity/article-21") == "polity__article-21.mp4"


def test_build_writes_props_renders_then_posts(tmp_path):
    req_path, labels = _setup(tmp_path, _request())
    calls = {"render": None, "post": None}

    def fake_render(props_path, out_path):
        calls["render"] = (props_path, out_path)
        return 0  # success

    def fake_post(url, payload):
        calls["post"] = (url, payload)
        return {"id": 99, "status": "PENDING_APPROVAL"}

    out_dir = tmp_path / "out"
    result = build.build(str(req_path), labels=labels, publisher_url="http://pub",
                         out_dir=str(out_dir), props_path=str(tmp_path / "props.json"),
                         render=fake_render, post=fake_post)

    # props written and valid
    props = json.loads((tmp_path / "props.json").read_text(encoding="utf-8"))
    assert props["correctLetter"] == "C"
    assert props["category"] == "Polity"
    # render called before post, with the slugged output path
    assert calls["render"][1].endswith("polity__article-21.mp4")
    # post received the assembled job body
    assert calls["post"][0] == "http://pub/api/jobs"
    assert calls["post"][1]["source_citation"] == "Constitution of India, Art. 21"
    assert result["id"] == 99


def test_build_aborts_post_when_render_fails(tmp_path):
    req_path, labels = _setup(tmp_path, _request())
    posted = []

    def failing_render(props_path, out_path):
        return 1  # non-zero -> render failed

    def fake_post(url, payload):
        posted.append(payload)
        return {}

    with pytest.raises(build.RenderFailed):
        build.build(str(req_path), labels=labels, publisher_url="http://pub",
                    out_dir=str(tmp_path / "out"), props_path=str(tmp_path / "props.json"),
                    render=failing_render, post=fake_post)
    assert posted == []  # never POSTed a job for a missing video


def test_build_rejects_unverified_question(tmp_path):
    bad = _request()
    bad["question"]["source_citation"] = ""
    req_path, labels = _setup(tmp_path, bad)
    with pytest.raises(ValueError, match="source_citation is required"):
        build.build(str(req_path), labels=labels, publisher_url="http://pub",
                    out_dir=str(tmp_path / "out"), props_path=str(tmp_path / "props.json"),
                    render=lambda p, o: 0, post=lambda u, p: {})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_build.py -q`
Expected: FAIL — `AttributeError: module 'selection.build' has no attribute 'slug_filename'`.

- [ ] **Step 3: Implement `build.py`**

Create `daily-gk-quiz/selection/build.py`:

```python
"""Orchestrate one daily quiz: verified Question + frozen plan -> props -> MP4 -> publisher job.

The two side effects (render subprocess, HTTP POST) are injected so build() is unit-testable;
main() wires the real implementations. See docs/specs/2026-06-11-gk-end-to-end-glue-design.md.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

from selection.assemble import RenderPlan, job_submission, quiz_props
from selection.models import Question


class RenderFailed(RuntimeError):
    pass


def slug_filename(fact_key: str) -> str:
    """fact_key contains '/', which is a path separator -> flatten it for the MP4 name."""
    return fact_key.replace("/", "__") + ".mp4"


def _real_render(props_path: str, out_path: str,
                 render_dir: str = "render", node: str = "node") -> int:
    """Run the Remotion CLI as a subprocess (cwd=render/, since render.mjs resolves
    src/index.ts relative to cwd). Returns the process exit code."""
    proc = subprocess.run(
        [node, "render.mjs", os.path.abspath(props_path), os.path.abspath(out_path)],
        cwd=render_dir,
    )
    return proc.returncode


def _real_post(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req) as resp:  # noqa: S310 (operator's own localhost publisher)
        return json.loads(resp.read().decode("utf-8"))


def build(request_path: str, *, labels: dict, publisher_url: str,
          out_dir: str = "out", props_path: str = "render/props.json",
          render=_real_render, post=_real_post) -> dict:
    """Assemble props, render the MP4, then POST the job. Returns the publisher's JobView dict."""
    request = json.loads(Path(request_path).read_text(encoding="utf-8"))
    question = Question.from_dict(request["question"]).validate()
    plan = RenderPlan(answer_position=request["answer_position"],
                      cta=request["cta"], trick_hook=request.get("trick_hook", ""))
    day_number = request["day_number"]

    props = quiz_props(question, plan, day_number, labels)
    Path(props_path).parent.mkdir(parents=True, exist_ok=True)
    Path(props_path).write_text(json.dumps(props, indent=2), encoding="utf-8")

    out_path = str(Path(out_dir) / slug_filename(question.fact_key))
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    code = render(props_path, out_path)
    if code != 0:
        raise RenderFailed(f"render exited {code}; not submitting a job for a missing video")

    body = job_submission(question, day_number, out_path, request["description"],
                          request["ai_disclosure"], labels)
    return post(publisher_url.rstrip("/") + "/api/jobs", body)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render + submit one daily GK quiz")
    parser.add_argument("--request", required=True, help="path to the render-request JSON")
    parser.add_argument("--publisher-url", default="http://127.0.0.1:8077")  # publisher config.py default
    parser.add_argument("--out", default="out")
    parser.add_argument("--domains", default="data/domains.json")
    args = parser.parse_args(argv)

    labels = json.loads(Path(args.domains).read_text(encoding="utf-8"))["labels"]
    result = build(args.request, labels=labels, publisher_url=args.publisher_url,
                   out_dir=args.out)
    print(f"submitted job {result.get('id')} ({result.get('status')})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_build.py -q`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add daily-gk-quiz/selection/build.py daily-gk-quiz/tests/test_build.py
git commit -m "feat: build.py orchestrates props -> render -> POST (render-fail aborts before POST)"
```

---

### Task 8: Rewrite SKILL.md steps 4-6 (the operator recipe)

**Files:**
- Modify: `daily-gk-quiz/SKILL.md`

No automated test — this is operator-facing prose. Verify by re-reading against the spec.

- [ ] **Step 1: Update step 4 (accuracy gate) to present the citation**

In `daily-gk-quiz/SKILL.md` step 4, add `source_citation` to the fields presented at the gate:

```
   sources. Present to the operator: question, correct answer, 3 distractors, `domain`,
   `difficulty`, `exam_relevance`, `fact_key`, the human-readable `source_citation`, and BOTH
   source URLs. **Do not proceed until the operator confirms the fact AND the citation.**
```

- [ ] **Step 2: Replace step 5 with the render-request + build command**

Replace step 5 ("Hand off to render") with:

````
5. **Assemble + render + submit.** After the operator confirms, write the **render request** —
   the verified question plus the plan fields frozen at step 1 — to a JSON file:

   ```json
   {
     "question": { "domain": "...", "difficulty": "...", "fact_key": "...", "entity": "...",
       "question": "...", "answer": "...", "distractors": ["...","...","..."],
       "exam_relevance": ["SSC","RRB"], "sources": ["https://...","https://..."],
       "explanation": "...", "source_citation": "Constitution of India, Art. 21",
       "mnemonic": null, "is_trick": false },
     "answer_position": "<plan.answer_position>", "hook": "<plan.hook>",
     "cta": "<plan.cta>", "trick_hook": "<plan.trick_hook>",
     "day_number": <history count + 1>,
     "description": "<the edited, varied caption you wrote — anti-slop>",
     "ai_disclosure": true
   }
   ```

   Then (publisher must be running) render the MP4 and submit the PENDING_APPROVAL job:

   ```bash
   cd daily-gk-quiz && .venv\Scripts\python.exe -m selection.build --request approved.json
   ```

   This writes `render/props.json`, renders `out/<fact_key>.mp4` (run with the Bash sandbox
   disabled — headless Chrome), and POSTs `/api/jobs`. Review gate #2 + posting happen in the
   publisher.
````

- [ ] **Step 3: Update step 6 (history append) to include the citation**

In the step 6 `Question(...)` command, add `source_citation`:

```python
... explanation='...', source_citation='Constitution of India, Art. 21', mnemonic=None).validate()
```

- [ ] **Step 4: Re-read SKILL.md against the spec**

Confirm steps 4-6 reference `source_citation`, the render-request shape matches §5 of the spec, and the build command matches `build.py`'s `main()` args.

- [ ] **Step 5: Commit**

```bash
git add daily-gk-quiz/SKILL.md
git commit -m "docs: SKILL recipe wires the assemble->render->submit glue (steps 4-6)"
```

---

### Task 9: Full verification + one real end-to-end run

**Files:** none (verification only)

- [ ] **Step 1: Run both full test suites**

Run (from `daily-gk-quiz/`): `.venv\Scripts\python.exe -m pytest tests/ -q`
Expected: PASS — 46 prior + new (models, seed, assemble x ~9, build x 4).

Run (from `publisher/`): `.venv\Scripts\python.exe -m pytest tests/ -q`
Expected: PASS — 175 prior + 2 new.

Run (from `daily-gk-quiz/render/`): `npx tsc --noEmit && npx vitest run`
Expected: tsc clean; 29 vitest PASS (render unchanged — this confirms no regression).

- [ ] **Step 2: Real end-to-end local run (manual verification)**

Start the publisher (from `publisher/`): `.venv\Scripts\python.exe main.py` — serves on `http://127.0.0.1:8077` (config.py default; matches `build.py`'s `--publisher-url` default). Then from `daily-gk-quiz/` write a real `approved.json` (reshape `render/sample-props.json`'s question into the render-request JSON) and run, **with the Bash sandbox disabled**:

```bash
cd daily-gk-quiz && .venv\Scripts\python.exe -m selection.build --request approved.json
```

Verify, with evidence (per superpowers:verification-before-completion):
- `render/props.json` exists and validates (the render would fail otherwise — zod gate).
- `out/<fact_key>.mp4` exists and is a real 1080x1920 video (open it).
- `GET /api/jobs/<id>` returns the job in `PENDING_APPROVAL` with the correct `source_citation` + `sources`.

- [ ] **Step 3: Final commit (if any cleanup)**

```bash
git add -A
git commit -m "chore: end-to-end glue verified (render -> PENDING_APPROVAL job)"
```

---

## Self-Review notes (for the implementer)

- **Spec coverage:** §3 -> Task 1; §4.4 labels -> Task 2; §4.1 -> Task 3; §4.2 -> Task 4; §4.3 -> Task 5; §6 publisher threading -> Task 6; §5 render request + §7 build.py -> Task 7; §8 SKILL -> Task 8; §9 testing -> spread across tasks + Task 9.
- **Signature note (refines spec §4.3):** `job_submission` takes `labels` (for `category`) and drops the unused `plan` param the spec sketched — it needs no plan fields. `quiz_props` keeps `(question, plan, day_number, labels)`.
- **Type consistency:** `RenderPlan(answer_position, cta, trick_hook)` defined in Task 4, reused in Task 7. `slug_filename`, `RenderFailed`, `build()` signature defined in Task 7 match the Task 7 tests. Publisher `Job.source_citation`/`sources` (Task 6) match the `JobView` fields the assembler/dashboard expect.
- **`render()` injection:** the test's `fake_render` takes `(props_path, out_path)`; `_real_render` has extra defaulted params (`render_dir`, `node`) so it stays call-compatible with the injected two-arg form used by `build()`.
