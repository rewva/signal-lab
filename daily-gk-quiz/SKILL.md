---
name: daily-gk-quiz
description: Research, verify, and prepare one daily GA-tier MCQ quiz Short (SSC/Banking/Railways), with two operator approval gates.
---

# daily-gk-quiz

One verified General-Awareness MCQ per day for the SSC/Banking/Railways aspirant tier.
Design: `docs/specs/2026-06-10-gk-topic-selection-design.md`. This recipe covers topic
SELECTION + accuracy (steps 1-2); render/voice/post are separate.

## Daily recipe

1. **Plan the day.** Run the planner to get today's target:
   ```bash
   cd daily-gk-quiz && .venv\Scripts\python.exe -c "import json,datetime; from selection.store import Store; from selection.planner import plan_today; d=json.load(open('data/domains.json')); p=json.load(open('data/prompts.json')); s=Store('state/question-history.json','state/question-bank.json'); plan=plan_today(history=s.load_history(), bank=s.load_bank(), weights=d['weights'], target_mix={'basic':0.5,'intermediate':0.35,'advanced':0.15}, hooks=p['hooks'], ctas=p['ctas'], today=datetime.date.today()); print(plan)"
   ```
   This yields: `domain`, `difficulty`, `recent_fact_keys` (do NOT repeat these),
   `bank_candidate` (a ready static MCQ, or None), `hook`, `cta`.

2. **Source the question.**
   - If `domain == current-affairs`: web-search exam-relevant news from the **last ~6 months**
     and draft one MCQ at the target difficulty.
   - Else if `bank_candidate` is not None: use it (already verified -- re-confirm in step 4).
   - Else (bank miss): draft a fresh static MCQ at the target domain + difficulty.
   Set a canonical `fact_key`; if the fact matches one already in `recent_fact_keys`, pick a
   different fact (dedupe). Set `exam_relevance` from `data/domains.json`. Write a required
   `explanation` ("why the answer is right / exam relevance" -- the anti-slop added value) and,
   where useful, a `mnemonic`.

3. **Distractor sanity check.** Confirm none of the 3 wrong options is also defensibly correct.

4. **Accuracy gate (#1 -- mandatory).** Corroborate the fact across **>=2 independent reputable
   sources**, preferring a primary/official one (RBI, ISRO, PIB, gazette). Present to the
   operator: question, correct answer, 3 distractors, `domain`, `difficulty`, `exam_relevance`,
   `fact_key`, and BOTH source URLs. **Do not proceed until the operator confirms the fact.**

5. **Hand off to render** with the approved question + the `hook` and `cta` from step 1.
   Render is **block-composed** (varied structure per question) with an on-screen
   **verified-source badge** and **edited captions** -- the differentiation layer (parent design
   sec 9 / spec sec 6). Render/voice/post implementation are out of this skill's scope.
   Record the `hook` and `cta` you used when appending to history (step 6) so the rotation can avoid repeating them.

6. **Review gate (#2)** and posting happen downstream. **Only after a successful post**, append
   the question to history:
   ```bash
   cd daily-gk-quiz && .venv\Scripts\python.exe -c "import datetime; from selection.store import Store; from selection.models import Question, HistoryRecord; s=Store('state/question-history.json','state/question-bank.json'); q=Question(domain='...', difficulty='...', fact_key='...', entity='...', question='...', answer='...', distractors=['...','...','...'], exam_relevance=['...'], sources=['...','...'], explanation='...', mnemonic=None).validate(); s.append_history(HistoryRecord(datetime.date.today().isoformat(), q, hook='<the hook used>', cta='<the cta used>'))"
   ```
   If a bank candidate was used, also remove it from `question-bank.json` (rewrite the bank
   without that `fact_key`) and replenish the bank when it runs low.

## Replenishing the bank
Periodically batch-draft + verify static MCQs across under-covered domains/difficulties and
append them (validated) to `state/question-bank.json` so static-GK days never start cold.
