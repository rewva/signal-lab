# Design: GK end-to-end glue (DayPlan + verified question -> rendered MP4 -> publisher job)

**Date:** 2026-06-11
**Status:** Approved design (plan only -- no implementation in this phase)
**Owner:** sdevendran
**Relates to:** `docs/specs/2026-06-10-gk-topic-selection-design.md` (selection layer, upstream),
`docs/specs/2026-06-10-gk-render-layer-design.md` (render layer, downstream of this),
`docs/specs/2026-06-04-daily-gk-quiz-design.md` (parent). Threads data toward a future
**review dashboard** (separate next-round spec).

---

## 1. What this is (the gap it closes)

The topic-selection layer produces a `DayPlan` + an operator-verified `Question`. The render
layer turns a typed `QuizProps` JSON into a 1080x1920 MP4. The publisher accepts a job via
`POST /api/jobs`. **Nothing currently connects them** -- the SKILL's step 5 ("hand off to
render") is prose, not code.

This spec defines the **glue**: a small, mostly-pure Python layer that maps a verified
`Question` + `DayPlan` into render props, renders the MP4, and submits the publisher job --
plus the minimal threading of the **source citation + source URLs** through to the job so a
future review dashboard can show a clickable "verify" tag beside the playable video.

Out of scope this round: the review dashboard itself (next focused spec), TTS/captions audio
(parent design), live account setup.

---

## 2. The two seams (exact contracts)

**Upstream -- selection layer (`daily-gk-quiz/selection/`)**

- `DayPlan`: `domain`, `difficulty`, `recent_fact_keys`, `bank_candidate`, `hook`, `cta`,
  `answer_position` (`"A".."D"`), `trick_hook`.
- `Question`: `domain`, `difficulty`, `fact_key`, `entity`, `question`, `answer`,
  `distractors[3]`, `exam_relevance[]`, `sources[]` (URLs), `explanation`, `mnemonic`,
  `is_trick`. **+ new `source_citation`** (this spec, §3).
- `template_for(is_trick) -> "standard" | "trick"` already exists.

**Downstream -- render layer (`daily-gk-quiz/render/`)** consumes `QuizProps` (zod):
`dayNumber`, `category`, `difficulty`, `examPrefix`, `template`, `question`,
`options[4] = {letter, text}`, `correctLetter`, `explanation`, `sourceLine`, `cta`, `trickHook`.

**Downstream -- publisher (`publisher/`)** `POST /api/jobs` (`JobSubmission`): `channel_id`,
`video_path`, `title`, `description`, `tags[]`, `platforms[]`, `per_platform{}`.
**+ new `source_citation`, `sources[]`** (this spec, §6).

---

## 3. Data-model change (one field)

Add **`source_citation: str`** to `Question` -- the human-readable on-screen citation
(`"Constitution of India, Art. 21"`), distinct from the `sources` URLs (the verify links).

- **Required** in `validate()`, alongside the already-required `explanation`. Both are the
  moat made tangible: `explanation` = the per-video pedagogy, `source_citation` = the
  visible trust signal. A question with no citation cannot render the VERIFIED-SOURCE badge,
  so it is not renderable.
- Reviewed by the operator at **accuracy gate #1** (added to the gate's presented fields).
- Stored in `question-history.json` (it is part of `Question`, so it round-trips for free via
  `to_dict`/`from_dict`).
- **Mechanical churn:** existing `Question(...)` test fixtures, seed/bank entries, and the
  SKILL's history-append command gain the field.

No other model changes. `answer_position`, `hook`, `cta`, `trick_hook` already exist on
`DayPlan` / `HistoryRecord`.

---

## 4. `selection/assemble.py` -- pure functions (the heart, TDD'd)

No I/O, no subprocess, no network -- fully unit-testable.

### 4.1 `order_options(answer, distractors, position) -> list[{letter, text}]`
Places the correct `answer` in the `position` slot (`DayPlan.answer_position`) and fills the
remaining three A/B/C/D slots with the three `distractors` in order. Deterministic. Example:
`position="C"` -> `A=distractors[0], B=distractors[1], C=answer, D=distractors[2]`.

### 4.2 `quiz_props(question, plan, day_number, labels) -> dict`
Builds the `QuizProps` dict:

| Prop | Source |
|---|---|
| `dayNumber` | passed in (history count + 1, §5) |
| `category` | `labels[question.domain]` (display name; §4.4) |
| `difficulty` | `question.difficulty` |
| `examPrefix` | `question.exam_relevance[0]` if any, else `""` |
| `template` | `template_for(question.is_trick)` |
| `question` | `question.question` |
| `options` | `order_options(question.answer, question.distractors, plan.answer_position)` |
| `correctLetter` | `plan.answer_position` |
| `explanation` | `question.explanation` |
| `sourceLine` | `question.source_citation` |
| `cta` | `plan.cta` |
| `trickHook` | `plan.trick_hook` (`""` for standard template) |

### 4.3 `job_submission(question, plan, day_number, video_path, description, channel_id, platforms) -> dict`
Builds the `POST /api/jobs` body:

- `channel_id` = `"daily-gk-quiz"` (default), `platforms` = `["youtube","facebook","instagram"]`
  (default), `video_path` = the rendered MP4.
- `title` = lightly templated: `"Daily GK #{day_number} -- {category}"`. (Title sameness in a
  daily series is normal and acceptable; the *description* carries the varied substance.)
- `description` = the **Claude-authored caption** (edited/varied -- anti-slop) with a
  source-attribution line appended (`"\n\nSource: {source_citation}"`).
- `tags` = derived hashtags from `exam_relevance` + `category` (e.g. `#SSC #RRB #Polity #DailyGK`).
- `per_platform` = `{ "youtube": { "ai_disclosure": <bool> } }` -- the synthetic-media toggle
  (parent design §9). Defaults true when a synthetic voice narrates; the build passes the flag.
- **`source_citation`** = `question.source_citation`, **`sources`** = `question.sources`
  (threaded for the dashboard verify tag, §6).

### 4.4 Helpers
`category` display names live in **`data/domains.json`** as a `labels` map (`{"polity":
"Polity", "current-affairs": "Current Affairs", ...}`) -- data, not code, so it is editable
without touching `assemble.py`. A missing label falls back to the slug title-cased.

---

## 5. The render request (one JSON freezing every decision)

After gate #1, the SKILL writes **one JSON** = the verified `Question` fields **plus** the
plan-derived presentation fields chosen at planning time:

```json
{
  "question": { ...full Question incl. source_citation... },
  "answer_position": "C",
  "hook": "...",
  "cta": "Comment A or B",
  "trick_hook": "Common Exam Trap",
  "day_number": 47,
  "description": "the Claude-authored caption",
  "ai_disclosure": true
}
```

This freezes the exact `answer_position` / `cta` / `trick_hook` from planning so `build.py`
never re-derives them (which could drift -- e.g. a re-run `balance_answer_position` after a
different history state). `day_number` defaults to `len(history) + 1` if omitted.

---

## 6. Publisher threading (minimal, additive)

Add optional **`source_citation: str = ""`** and **`sources: list[str] = []`** to:
`JobSubmission` (intake) -> `Job` (model) -> persistence (`db.create_job` / row) -> `JobView`
(so the dashboard API can read them back).

Purely additive (defaults keep existing callers/tests valid). The dashboard (next round) reads
`JobView.source_citation` (the tag label) + `JobView.sources` (the links the operator clicks to
verify) and renders them beside the playable `video_path`.

---

## 7. `selection/build.py` -- thin orchestration CLI

`python -m selection.build --request approved.json [--publisher-url URL] [--out PATH]`

The `description` and `ai_disclosure` are carried **inside** the render request (§5), so the
request JSON is the single source of truth. (`--description` may be added later as an optional
override, but is not required for v1.)

1. Load `approved.json` (§5), `data/domains.json` (weights + labels), and history (for the
   default `day_number`).
2. `assemble.quiz_props(...)` -> write `render/props.json`.
3. Run `node render.mjs props.json out/<fact_key>.mp4` as a subprocess (run with the Bash
   sandbox disabled -- the Windows/headless-Chrome gotcha; `render.mjs` already calls
   `ensureBrowser()`).
4. **On render success only**, `assemble.job_submission(...)` -> `POST /api/jobs` (default
   `http://127.0.0.1:8077`, the publisher's `config.py` default). The job lands
   **PENDING_APPROVAL** -- this *is* review gate #2; nothing posts to social here.
5. Print the job id + the video path.

**Error handling**
- Render subprocess non-zero -> abort **before** POST (never create a job pointing at a missing
  video).
- POST fails -> keep the MP4 on disk (re-submittable); surface the error.
- Empty `source_citation` -> rejected at `Question.validate()` (can't render the trust badge).

`main()` is thin glue over the §4 pure functions; the side effects (subprocess, HTTP) are the
only non-unit-tested surface.

---

## 8. SKILL.md step 5 rewrite

Replace the prose "hand off to render" with: the **render-request JSON shape** (§5) and the
concrete `python -m selection.build ...` command (§7). Step 4 (accuracy gate) gains
`source_citation` in the presented fields. Step 6 (history append) gains `source_citation` in
the `Question(...)` constructor.

---

## 9. Testing (TDD throughout)

- **`assemble.py` (pure, unit):** `order_options` for each of A/B/C/D (correct slot + distractor
  fill order); `quiz_props` full mapping incl. `examPrefix` empty case, standard-vs-trick
  `template`/`trickHook`, `category` label + slug fallback; `job_submission` title template,
  hashtag derivation, `ai_disclosure` flag, threaded `source_citation`/`sources`.
- **`build.py` (orchestration):** render-subprocess + HTTP POST **mocked** -- assert props
  written correctly, render invoked with the right args, POST body matches `job_submission`,
  and POST is **skipped when render fails**. Plus **one real local end-to-end run** as manual
  verification (renders a real MP4, creates a real PENDING_APPROVAL job).
- **Publisher (API):** posting with `source_citation`/`sources` persists and round-trips
  through `GET /api/jobs/{id}`; omitting them still works (back-compat).
- **`Question.validate()`:** rejects empty `source_citation`.

---

## 10. Out of scope (YAGNI)

- The review dashboard (next round; this spec only threads its data).
- TTS / captions audio (parent design).
- Auto-posting without gate #2 (the publisher's PENDING_APPROVAL gate stays).
- A generic job-metadata bag on the publisher -- only the two fields the dashboard needs are
  threaded.
- Re-deriving the plan inside `build.py` -- the render request (§5) freezes the decisions.

---

## 11. Open questions

- **`ai_disclosure` default:** v1 may ship music-only or Kokoro TTS. The build passes the flag
  explicitly (`--ai-disclosure` / from the render request); the safe default when a synthetic
  voice is used is `true`. Confirm Meta's 2026 Reels AI-label field separately (parent design
  §12 still-open item) -- YouTube side is handled by `per_platform.youtube.ai_disclosure`.
- **Publisher running for `build.py`:** the POST assumes a running publisher at
  `--publisher-url`. Acceptable for the operator's manual daily run; revisit only if an
  in-process call is later preferred.
