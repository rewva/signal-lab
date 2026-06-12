# Design: Bank generation harness (sub-project #2)

**Date:** 2026-06-12
**Status:** Approved design (plan next -- no implementation in this phase)
**Owner:** sdevendran
**Relates to:** `docs/specs/2026-06-12-gk-question-bank-foundation-design.md` (the foundation this
fills), `docs/research/2026-06-12-static-question-bank-research.md` (the 7-step pipeline + sourcing
this implements), `daily-gk-quiz/SKILL.md` (the "Replenishing the bank" prose this makes concrete).
This is **sub-project #2** of the question-bank build; the foundation (#1) is on `main` (5d93eaf).

---

## 1. What this is (and is not)

The foundation gave us a trustworthy bank with 16 seeds and all the *consumption + storage*
machinery (`BankEntry`, the deterministic QA gate `check_entry`, stdlib dedup, `add_entry` ->
drafts, `verify`/`health` CLI, the yield-weighted draw). What is missing is the *production*
front-half: a way to author verified static MCQs in batches and scale the bank toward the
1,500 -> 3,000-5,000 target.

This spec defines that harness as a **Claude-Code recipe + a small stdlib ingest tool**. The
*intelligence* (authoring, adversarial review) lives in subagents dispatched when the recipe runs;
the *deterministic glue* (batch validate -> dedup -> add as drafts -> report) is the only new code.
It reuses the entire foundation. **No new infrastructure, no API keys, no RAG corpus, no standalone
program.**

**Out of scope (YAGNI / deferred):** automated source-fetching/corroboration (the operator gate
covers it; many gov portals 403 bots anyway -- see the source-map research); a RAG/embedding corpus;
a standalone Anthropic-API program (the repo has no LLM-API infra and this stays recipe-driven); an
interactive bulk-verify TUI (the recipe + per-item `verify` CLI suffices); difficulty
auto-calibration from response data (needs live data -- a later round).

---

## 2. The flow (operator-triggered, Claude-orchestrated)

1. **Target.** `python -m selection.bank health` surfaces low-stock `(domain, difficulty)` cells.
   The recipe picks the most-depleted cells to fill, weighted toward the high-yield domains from the
   research (history / science / polity / static-awareness).
2. **Author (subagents).** For a target cell, a fresh subagent authors N grounded MCQs. Each must
   carry: a canonical `fact_key`, the stem, the correct `answer`, exactly 3 **same-category**
   distractors, `exam_relevance`, an `explanation`, a human-readable `source_citation`, and **>= 2
   real source URLs** (prefer the Tier-1/2 deep-linkable sources from the research source map:
   constitutionofindia.net, ncert.nic.in, ich/whc.unesco.org, pib.gov.in, rbi.org.in, sebi.gov.in).
   The authoring prompt states the QA-gate rules up front so drafts pass structurally, and forbids
   volatile facts (anything that would be `static_class="current-adjacent"` -- rates, current
   winners, this-year counts). Each draft also declares `static_class`, `source_tier`, `yield_weight`.
3. **Adversarial review (subagent).** A *fresh, separate* reviewer tries to **refute** each draft:
   wrong answer key? a distractor also defensibly correct (multiple-correct)? hallucinated or
   outdated fact? ambiguous stem? Per-item verdict: `pass` / `fail` / `uncertain`.
   - `fail` -> **dropped** (logged with the refutation reason; never reaches the operator).
   - `pass` -> kept.
   - `uncertain` -> kept, carrying the reviewer's note forward for the operator's attention.
   (This catches the research's #1 failure mode -- wrong answer key, >6% of items in public
   benchmarks -- before the operator spends time on it. Using a *fresh* reviewer avoids the
   self-verification "least-incorrect" bias the research flagged.)
4. **Ingest (new code, SS3).** The surviving batch (a JSON file) is run through
   `python -m selection.ingest --batch batch.json`, which for each item: `Question.validate()`
   (enforces the >= 2 sources rule already in the model) -> `check_entry` (structural QA) ->
   `find_duplicates` (vs the live bank) -> `add_entry` (lands it `status="draft"`). It prints a
   per-item report: accepted / rejected+reason / soft-warnings / near-dup flags, and a summary.
5. **Operator accuracy gate (#1).** The recipe walks the operator through each new draft -- question,
   answer, 3 distractors, `source_citation`, both source URLs, and any reviewer `uncertain` note --
   exactly like the daily SKILL step 4. On confirmation, Claude runs
   `python -m selection.bank verify <fact_key>` (draft -> verified, now drawable). Rejected drafts
   are left as drafts (re-authorable) or `retire`d.

---

## 3. New code (small, testable)

### 3.1 `selection/ingest.py`
- `ingest_batch(bank: list[BankEntry], drafts: list[BankEntry], today: date) -> IngestReport`:
  for each draft, in order: (a) `entry.question.validate()` (enforces the `>= 2 sources` rule the
  model already has; catch `ValueError` -> rejected), then (b) `add_entry(bank, entry, today)` --
  which is the single QA+dedup+append path (it re-runs `check_entry` and `find_duplicates` and
  raises `BankError` on a hard failure or duplicate -> rejected; on success it appends the entry to
  `bank` as a draft and returns `(stamped, warnings)`). Accepted items are recorded with their soft
  warnings / near-dup notes. We deliberately do NOT call `check_entry` separately -- `add_entry`
  owns that -- so there is no double validation. The function mutates `bank` (appending accepted
  drafts only) and returns a structured report.
- `IngestReport` = a dataclass (or dict) with: `accepted: list[str]` (fact_keys),
  `rejected: list[(fact_key, reason)]`, `warnings: list[(fact_key, list[str])]`, and counts.
- Drafts are parsed from the batch JSON via `BankEntry.from_dict` (so the batch file is just a JSON
  array of `BankEntry` dicts with `status="draft"`).
- A thin CLI `main(argv)`: `python -m selection.ingest --batch batch.json [--bank PATH]` loads the
  bank via `Store`, calls `ingest_batch`, `Store.save_bank`, prints the report, returns 0 (or 1 if
  nothing was accepted). The pure `ingest_batch` is the heavily-tested unit; the CLI is thin glue.

### 3.2 `selection/bank.py` -- add a `drafts` subcommand
`python -m selection.bank drafts` lists every `status=="draft"` entry's `fact_key` + stem (so the
recipe can enumerate what the operator still needs to verify). Pure read; no mutation.

---

## 4. The recipe (prose -- a new skill doc)

`daily-gk-quiz/skills/generate-bank.md` (a SKILL-style recipe), plus a one-line pointer from
`SKILL.md`'s "Replenishing the bank" section. It documents steps 1-5 of SS2 concretely: the
targeting command, the **authoring subagent prompt** (grounding + citation + QA-rule + no-volatile
rules), the **adversarial-reviewer subagent prompt** (refute + verdict + `fresh reviewer` rule), the
batch JSON shape, the `ingest` command, and the operator-verification loop. The subagents are
dispatched *when the recipe runs* -- they are not code and have no unit tests.

---

## 5. Data shapes

- **Batch file** (authoring output, ingest input): a JSON array of `BankEntry` dicts, each with
  `status="draft"` and `verified_date=null`. An item MAY carry an extra top-level `"review_note"`
  key (the reviewer's `uncertain` note); `BankEntry.from_dict` reads only the fields it knows, so the
  extra key is harmlessly ignored by `ingest` and never persisted to the bank.
- **Reviewer notes:** the `uncertain` note is operator-facing context only. It is NOT a persisted
  `BankEntry` field (the foundation has none, and we are not adding one this round -- YAGNI). It
  rides along in the batch file's `review_note` key (ignored by ingest, per above) and is shown to
  the operator at gate #1. (If persistence is ever wanted, add a `review_note` field to `BankEntry`
  then.)

---

## 6. Testing (TDD)

- **`ingest_batch` (pure):** a clean batch -> all accepted, all land as `draft`; a batch containing
  a hard-QA failure -> that item rejected with reason, others accepted; a duplicate (same fact_key
  or >=0.87 stem) -> rejected; a near-dup (0.80-0.87) -> accepted **with** a near-dup warning; a
  soft-warning item -> accepted **with** the warning; the `< 2 sources` case -> rejected via
  `Question.validate`. Report shape + counts asserted. `bank` mutated only by accepted items.
- **`ingest` CLI:** round-trips a batch file through a tmp bank, persists drafts, prints a report,
  returns 0; empty/all-rejected batch returns 1.
- **`bank drafts` CLI:** lists only `draft` entries (not verified/retired), with fact_key + stem.
- The recipe doc is prose -- no unit tests; its subagent steps are exercised when the operator runs
  it (a manual end-to-end "author -> review -> ingest -> verify a small real batch" is the
  acceptance check).

---

## 7. Open questions / locked defaults

Locked: recipe + ingest tool (no API program / no RAG); adversarial `fail` -> dropped, `uncertain`
-> kept-and-flagged; operator verification is recipe-driven (reuses gate #1, no new TUI);
author-from-knowledge + cite >= 2 real sources; reviewer notes are not persisted as a `BankEntry`
field this round. Tunable later: batch size N per cell; whether to add automated source-fetching
once a non-bot-blocked source set is identified; difficulty calibration from real response data.
