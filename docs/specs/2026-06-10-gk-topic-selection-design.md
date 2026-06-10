# Design: GK topic selection, correctness & dedupe (daily-gk-quiz step 1-2)

**Date:** 2026-06-10
**Status:** Approved design (plan only -- no implementation in this phase)
**Owner:** sdevendran
**Amends:** `docs/specs/2026-06-04-daily-gk-quiz-design.md` (fills in step 1 "pick today's
question" + step 2 "accuracy gate"; render/post steps unchanged)

---

## 1. Why this exists

The parent design names the pieces -- `state/question-history.json` for dedupe, an operator
accuracy gate, "ad-hoc best question wins" -- but is deliberately thin on the mechanics. This
spec makes three things concrete:

1. **How a topic is sourced** each day (so coverage stays balanced, not drifting to easy topics).
2. **How the day's fact is verified correct** before the operator ever sees it.
3. **How repeats are caught** -- including "same answer, reworded question," the failure mode
   that matters.

The spine that ties all three together is a single concept: the **`fact_key`**.

---

## 2. Locked decisions (from brainstorm 2026-06-10)

| Pillar | Decision |
|---|---|
| Target market | **SSC / Banking / Railways "General Awareness" tier** (SSC CGL/CHSL, IBPS/SBI, RRB). Refines the parent design's "broad general GK" -- narrower for *intent signal* (the metric `plan.md` uses to pick a winner), still a huge pool, and an exact format fit: those exams' GA section IS static-GK + current-affairs MCQs. UPSC deliberately excluded (analytical/long-form, poor quiz-short fit). |
| Topic sourcing | **Curated topic plan + live news feed.** A hand-authored bank of static GK domains, plus a current-affairs lane that searches the day's exam-relevant news. Claude picks from a planned space. |
| Dedupe level | **Fact/entity level.** Each question carries a canonical `fact_key`; reuse within a window is hard-blocked. Catches reworded repeats. |
| Correctness bar | **Two-source cross-check + primary-source bias.** Corroborate across >=2 independent reputable sources, prefer a primary/official one; reject if it cannot be corroborated. |
| Distractor check | **Lightweight add** (not in the chosen option, included by design): confirm none of the 3 wrong options is also defensibly correct. Cuttable if the operator disagrees. |

---

## 3. Data model & state

Two files do all the work.

### 3.1 `topics/domains.json` -- the curated plan (hand-authored once, edited rarely)

A bank of GK domains for Indian competitive exams. Each static domain lists sub-topics and a
selection weight. **Weights are tuned to the SSC / Banking / Railways GA syllabus** -- those
sections are current-affairs-heavy with a substantial static-GK base, so Current Affairs
carries the highest weight and the static domains are weighted by how often they appear in
those papers (Static GK, Polity, History, Geography are heavily tested; Economy matters more
for Banking). Current Affairs is NOT enumerated -- it is the "search the last 48-72h" lane.

Static domains (initial set, weighted for the GA tier):

```
History            -- ancient / medieval / modern, freedom struggle
Polity & Constitution
Geography          -- Indian + world, physical
Economy            -- (weighted up for Banking: banking awareness, RBI, schemes)
General Science    -- physics / chemistry / biology
Static GK          -- awards, books-authors, important days, dances, etc.
```

Plus the rolling lane (highest weight -- GA sections lean current-affairs):

```
Current Affairs    -- schemes, appointments, sports, summits, science & tech,
                      defence, reports / indices, banking & economy news
                      (sourced live, not enumerated)
```

### 3.2 `state/question-history.json` -- append-only, single source of truth

One record per posted question. This file feeds BOTH dedupe and balance, so there is no
second file to drift out of sync.

```json
{
  "date": "2026-06-10",
  "domain": "polity",
  "fact_key": "polity/article-21-right-to-life",
  "entity": "Article 21",
  "question": "...",
  "answer": "...",
  "sources": ["https://primary.gov.in/...", "https://second-source/..."]
}
```

### 3.3 The `fact_key` -- the spine

A canonical slug of the *fact being tested*, NOT the wording. Examples:

```
polity/article-21-right-to-life
current-affairs/2026-repo-rate-cut
history/battle-of-plassey-1757
```

- **Dedupe** reads `fact_key`.
- **Balance** is derived from the `domain` values already in the log (least-recently-covered
  domains float to the top) -- not stored separately.
- **Correctness** evidence (the `sources`) is attached to the same record.

One concept, three concerns covered.

---

## 4. The daily selection algorithm (step 1, before the gate)

1. **Load history.** Read `question-history.json`; compute which static domains are
   least-recently covered.
2. **Choose the lane.** Prefer a strong *current-affairs* item if the day has one that is
   exam-relevant; otherwise pick an **under-covered static domain** from the bank (this keeps
   the rotation balanced instead of drifting to easy topics).
3. **Draft the MCQ** (question + correct answer + 3 distractors) and compute its `fact_key`.
4. **Dedupe gate (hard).** If `fact_key` appears in history within the window (default
   **120 days**; current-affairs facts effectively never recur), discard and draft another.
5. **Correctness gate.** Corroborate the fact across **>=2 independent reputable sources**,
   preferring a **primary/official** one (RBI, ISRO, PIB, official gazette, etc.). If it
   cannot be corroborated, **discard the question -- do not weaken the standard.**
6. **Distractor sanity check.** Confirm none of the 3 wrong options is also defensibly correct.
7. **Present to the operator (gate #2).** Show: question, correct answer, the 3 distractors,
   `domain`, `fact_key`, and **both** source URLs. Nothing renders until the operator confirms.
8. **Record on success.** After posting, append the full record (with `fact_key` + both
   sources) to `question-history.json`.

---

## 5. Parameters (tunable)

| Parameter | Default | Notes |
|---|---|---|
| Dedupe window | **120 days** | Static facts blocked for this long; current-affairs facts rarely recur regardless. |
| Min independent sources | **2** | At least one should be primary/official where one exists. |
| Lane preference | current-affairs first, else under-covered static | Soft rule; a thin-news day falls back to static GK. |

---

## 6. What this does NOT change

- Render (Remotion quiz card), TTS (Kokoro), captions, and the three posting scripts are
  unchanged from the parent design.
- The two approval gates stay manual.
- No scheduler, no extra API cost (Claude in-session remains the brain).

---

## 7. Out of scope (YAGNI)

- Semantic-similarity dedupe (embedding model) -- the `fact_key` slug is sufficient and free;
  revisit only if reworded repeats still slip through in practice.
- A separate domain-coverage file -- balance is derived from `question-history.json`.
- Auto-selecting without the operator accuracy gate.

---

## 8. Open questions

- **`fact_key` collisions / drift:** Claude must slug consistently (same fact -> same key
  across days). Mitigation: at selection time, show Claude the recent `fact_key` list so it
  reuses the existing slug for a fact rather than minting a near-duplicate. Watch in the first
  ~2 weeks; formalize a slugging convention in `references/question-style.md` if needed.
- **Distractor check rigor:** kept lightweight here; if exam-grade ambiguity shows up, promote
  to a full per-distractor verification (the heavier option from the brainstorm).
