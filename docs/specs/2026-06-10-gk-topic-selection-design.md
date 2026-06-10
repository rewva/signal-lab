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

A bank of GK domains for Indian competitive exams, each with sub-topics and a **selection
weight**. The weights are **evidence-based**, derived from a verified exam-pattern analysis
across all the target exams (`docs/ga-exam-pattern-research.md`) -- not a hand-guess. Current
Affairs is NOT enumerated; it is the "search the last ~6 months" lane (recency matters --
banking CA runs ~4-6 months back, Railways ~6-8).

| Domain | Weight | Exam relevance (for the caption tag) |
|---|---|---|
| Current Affairs (last ~6 months) | **30%** | universal (all exams) |
| General Science | **18%** | universal; **Railways-heavy** |
| Static GK (awards, books, days, dances...) | 12% | universal |
| History | 10% | core-academic (SSC-heavy) |
| Polity & Constitution | 8% | core-academic |
| Geography (Indian + world, physical) | 8% | core-academic |
| Economy | 7% | core-academic |
| Banking / Financial Awareness | 5% | **exam-specific -- IBPS/SBI only** |
| Sports / Awards / Misc | 2% | universal |

Two relevance rules fall out of the analysis and drive selection:
- **Banking/Financial Awareness is IBPS/SBI-only.** On a banking-relevant day it's tagged for
  IBPS/SBI; it is never presented as relevant to SSC/RRB. Kept modest (5%) so a channel serving
  all families doesn't over-index on banking.
- **General Science skews Railways.** Tag GS questions as especially relevant to RRB.

Each question carries an **`exam_relevance`** tag (which of SSC / IBPS-SBI / RRB it maps to),
surfaced in the caption ("relevant for SSC CGL, RRB NTPC") to raise perceived value.

### 3.2 `state/question-history.json` -- append-only, single source of truth

One record per posted question. This file feeds BOTH dedupe and balance, so there is no
second file to drift out of sync.

```json
{
  "date": "2026-06-10",
  "domain": "polity",
  "fact_key": "polity/article-21-right-to-life",
  "entity": "Article 21",
  "difficulty": "intermediate",
  "exam_relevance": ["SSC", "RRB"],
  "question": "...",
  "answer": "...",
  "sources": ["https://primary.gov.in/...", "https://second-source/..."]
}
```

`difficulty` is one of `basic` / `intermediate` / `advanced`; `exam_relevance` is the subset of
`SSC` / `IBPS-SBI` / `RRB` the fact maps to. Both are derived from history for rotation/balance
(below) and shown in the caption.

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

### 3.4 Difficulty dimension (basic / intermediate / advanced)

Format stays **1 question per video**; difficulty **rotates across days** so the channel serves
the whole tier (entry-level Railways/CHSL through CGL-Tier-2 / Banking-PO depth). Target mix,
from the verified analysis: **~50% basic, 35% intermediate, 15% advanced.** Selection picks the
level whose recent share (derived from the history log) is furthest below target, so the
rotation self-corrects without a separate counter file. Each video is tagged with its level.

### 3.5 Question bank -- hybrid (pre-built static + live current affairs)

`domains.json` is the topic *plan*, not the questions. Questions come from two lanes:

**`state/question-bank.json`** -- a growing, pre-built bank of **verified STATIC-GK MCQs**
(history, polity, geography, science, static GK, etc.). Each entry is a full, already-verified
question (same shape as a history record, minus `date`/`posted`) carrying `domain`,
`difficulty`, `exam_relevance`, `fact_key`, `answer`, 3 distractors, and both `sources`. Built
in batches up front and **replenished when it runs low**, so a static-GK day never starts cold
and questions can be quality-reviewed in batches rather than one-at-a-time at 7am.

**Current-affairs lane** -- generated **live** each morning (CA must be fresh; a stored bank
goes stale). Drawn from the last ~6 months.

Why hybrid: with the §3.1 weights, ~70% of days are static -> the bank covers them with a
buffer; only the ~30% current-affairs days need live work. The bank is a *buffer*, not a
schedule -- the daily algorithm (§4) still picks domain + difficulty, then either pulls a
matching unused entry from the bank or (CA, or bank-miss) generates live.

---

## 4. The daily selection algorithm (step 1, before the gate)

1. **Load history.** Read `question-history.json`; compute the recent shares of (a) each
   domain, and (b) each difficulty level.
2. **Choose domain + difficulty.** Pick the domain by the evidence-based weights (§3.1),
   favouring the one whose recent share is furthest below target; prefer a strong
   *current-affairs* item if the day has an exam-relevant one. Independently pick the
   **difficulty** whose recent share is furthest below the 50/35/15 target (§3.4).
3. **Source the MCQ** at the chosen domain + difficulty:
   - **Current-affairs lane:** generate live from the last ~6 months.
   - **Static lane:** pull a matching unused entry from `question-bank.json`; if the bank has
     none at that domain+difficulty (a bank miss), generate live as a fallback.
   Either way, compute/confirm its `fact_key` and `exam_relevance`. (Bank entries are
   pre-verified, so steps 5-6 are a re-confirm, not first-time work.)
4. **Dedupe gate (hard).** If `fact_key` appears in history within the window (default
   **120 days**; current-affairs facts effectively never recur), discard and draft another.
5. **Correctness gate.** Corroborate the fact across **>=2 independent reputable sources**,
   preferring a **primary/official** one (RBI, ISRO, PIB, official gazette, etc.). If it
   cannot be corroborated, **discard the question -- do not weaken the standard.**
6. **Distractor sanity check.** Confirm none of the 3 wrong options is also defensibly correct.
7. **Present to the operator (gate #2).** Show: question, correct answer, the 3 distractors,
   `domain`, `difficulty`, `exam_relevance`, `fact_key`, and **both** source URLs. Nothing
   renders until the operator confirms.
8. **Record on success.** After posting, append the full record (with `fact_key`, `difficulty`,
   `exam_relevance`, and both sources) to `question-history.json`.

---

## 5. Parameters (tunable)

| Parameter | Default | Notes |
|---|---|---|
| Dedupe window | **120 days** | Static facts blocked for this long; current-affairs facts rarely recur regardless. |
| Min independent sources | **2** | At least one should be primary/official where one exists. |
| Lane preference | current-affairs first, else under-covered static | Soft rule; a thin-news day falls back to static GK. |
| Topic weights | §3.1 blueprint | Evidence-based (`docs/ga-exam-pattern-research.md`); tune to the dominant audience segment. |
| Difficulty mix | **50% basic / 35% intermediate / 15% advanced** | Self-correcting from history. |
| Current-affairs recency | **~6 months** | Banking ~4-6mo, Railways ~6-8mo; 6mo is the blend. |

---

## 6. Engagement & retention design (not-boring + comments)

The format only works if people watch to the reveal and comment. Three levers, baked into the
per-day output:

**Retention -- the video must not feel templated.**
- **Rotating hook (first ~1.5s).** A pattern-interrupt opener that varies daily so the channel
  never reads as a fixed template (also satisfies the anti-slop "materially varied" rule):
  e.g. *"This came in SSC CGL 2024,"* *"90% pick the wrong option,"* *"Only toppers solve this
  in 5 seconds."* Stored as a small rotating set; the skill picks a fresh one per day.
- **Tension mechanics.** Countdown with a ticking sound, a *ding* on reveal, tight 15-20s
  pacing, and the parent design's 2-3 rotating card layouts/colours.
- **Payoff.** A satisfying answer reveal + the one-line "why it matters / exam relevance" --
  the bit that makes it educational, not slop.

**Comments -- the rotating CTA, which doubles as the channel's intent signal.**
- Core: *"Comment your answer (A/B/C/D) before the reveal."*
- Key move: rotate in *"Comment which exam you're prepping -- SSC / Banking / Railways."* This
  drives comments AND surfaces which exam segment dominates the audience -- the exact data that
  triggers the deferred per-exam-split decision (`plan.md`). One CTA serves engagement, the
  algorithm, and strategy at once.
- Difficulty-bragging: *"Comment 'GOT IT' if you solved it in 3 seconds."*
- Operator posts a **pinned comment** (the answer + a teaser for tomorrow) and replies to the
  first few comments -- a light manual action that meaningfully lifts ranking.

These touch the render template and the caption/CTA (parent-design territory); this spec
specifies the *rotation logic + the exam-segment CTA*, the parent design implements the card.

---

## 7. What this does NOT change

- Render (Remotion quiz card), TTS (Kokoro), captions, and the three posting scripts keep their
  parent-design structure (this spec adds the rotating hook + CTA logic they render).
- The two approval gates stay manual.
- No scheduler, no extra API cost (Claude in-session remains the brain).

---

## 8. Out of scope (YAGNI)

- Semantic-similarity dedupe (embedding model) -- the `fact_key` slug is sufficient and free;
  revisit only if reworded repeats still slip through in practice.
- A separate domain-coverage file -- balance is derived from `question-history.json`.
- Auto-selecting without the operator accuracy gate.

---

## 9. Open questions

- **`fact_key` collisions / drift:** Claude must slug consistently (same fact -> same key
  across days). Mitigation: at selection time, show Claude the recent `fact_key` list so it
  reuses the existing slug for a fact rather than minting a near-duplicate. Watch in the first
  ~2 weeks; formalize a slugging convention in `references/question-style.md` if needed.
- **Distractor check rigor:** kept lightweight here; if exam-grade ambiguity shows up, promote
  to a full per-distractor verification (the heavier option from the brainstorm).
