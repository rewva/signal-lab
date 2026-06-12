---
name: generate-bank
description: Batch-author, adversarially review, and ingest verified static-GK MCQs to replenish the question bank (operator gate #1 before they go live).
---

# generate-bank

Fill the static question bank in batches so static-GK days never start cold. Runs the research
7-step pipeline as a recipe: target -> author -> adversarial review -> ingest (drafts) -> operator
verify. Foundation modules (`selection/bank.py`, `selection/ingest.py`) do the deterministic work;
subagents do the authoring + review.

## Steps

1. **Target the gaps.** Find under-stocked cells:
   `cd daily-gk-quiz && .venv\Scripts\python.exe -m selection.bank --bank state/question-bank.json health`
   Pick the `low_stock` (domain, difficulty) cells, biasing toward high-yield domains (history,
   general-science, polity, static-gk -- see `docs/research/2026-06-12-static-question-bank-research.md`).

2. **Author (one subagent per cell).** Dispatch a fresh subagent to author ~10 MCQs for a target
   (domain, difficulty). Its prompt MUST require, per question:
   - a canonical `fact_key` (e.g. `history/battle-of-plassey-1757`);
   - exactly 3 distractors in the SAME category as the answer (near-misses, not random);
   - `exam_relevance` from `("SSC","IBPS-SBI","RRB")`;
   - an `explanation` (why the answer is right / exam relevance -- the anti-slop value);
   - a human-readable `source_citation` AND >= 2 real source URLs, preferring Tier-1/2
     deep-linkable sources (constitutionofindia.net, ncert.nic.in, ich/whc.unesco.org, pib.gov.in,
     rbi.org.in, sebi.gov.in);
   - `static_class` = "permanent" or "slowly-changing" -- NEVER a volatile/current fact (no repo
     rate, no this-year winner/count; those are current-affairs, generated live, not banked);
   - `source_tier` (1/2/3) and `yield_weight` (high/medium/low).
   Output: a JSON array of `BankEntry` dicts with `status="draft"`, `verified_date=null`.

3. **Adversarial review (a DIFFERENT, fresh subagent).** Give it the authored batch and tell it to
   try to REFUTE each item: is the answer key wrong? is any distractor also defensibly correct? is
   the fact hallucinated or outdated? is the stem ambiguous? Verdict per item: pass / fail /
   uncertain.
   - Drop every `fail` (record why -- do not pass it on).
   - Keep `pass` and `uncertain`; for `uncertain`, add a `"review_note"` key to that item's JSON
     (ingest ignores it; you surface it to the operator in step 5).
   Write the survivors to `batch.json`.

4. **Ingest as drafts.**
   `cd daily-gk-quiz && .venv\Scripts\python.exe -m selection.ingest --batch batch.json --bank state/question-bank.json`
   Read the report: ACCEPT lines landed as drafts; REJECT lines (hard QA / duplicate / < 2 sources)
   and WARN lines (soft warnings / near-dup) need a look. Fix + re-ingest rejects if easily salvaged.

5. **Operator accuracy gate (#1).** List what needs verifying:
   `.venv\Scripts\python.exe -m selection.bank --bank state/question-bank.json drafts`
   For each draft, present to the operator: question, correct answer, 3 distractors, domain,
   difficulty, `source_citation`, BOTH source URLs, and any reviewer `review_note`. On the
   operator's confirmation of the fact AND citation:
   `.venv\Scripts\python.exe -m selection.bank --bank state/question-bank.json verify <fact_key>`
   (draft -> verified -> now drawable by the daily planner). Leave unconfirmed drafts as drafts;
   the daily draw never touches non-verified entries.

