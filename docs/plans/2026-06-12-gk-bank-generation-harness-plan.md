# Bank Generation Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the production front-half of the question bank: a stdlib `ingest` tool that batch-validates authored MCQ drafts through the existing QA gate + dedup and lands them as drafts, a `bank drafts` listing command, and a Claude-Code recipe documenting the author -> adversarial-review -> ingest -> operator-verify flow.

**Architecture:** Pure-function `ingest_batch` in a new `selection/ingest.py` (reuses `Question.validate` + `bank.add_entry`, which already own QA + dedup + draft-stamping), wrapped by a thin CLI. A `drafts` subcommand added to the existing `selection/bank.py` CLI. The authoring + adversarial-review intelligence lives in subagents dispatched by a new prose recipe `daily-gk-quiz/skills/generate-bank.md` (no code). Stdlib only.

**Tech Stack:** Python 3.12, dataclasses, json, argparse, pytest. Tests in `daily-gk-quiz/tests/`, import `selection.*`.

**Working directory for ALL commands:** `D:\Rewva\signal-lab\daily-gk-quiz`. Test runner: `.venv\Scripts\python.exe -m pytest <args>` (from that dir). ASCII quotes only.

**Spec:** `docs/specs/2026-06-12-gk-bank-generation-harness-design.md`.

**Existing code this builds on (already on main):**
- `selection/models.py`: `BankEntry` (question, static_class, source_tier, yield_weight, status, verified_date, review_due_date) with `to_dict`/`from_dict`; `Question.validate()` raises `ValueError` (enforces difficulty in DIFFICULTIES, exactly 3 distractors, >= 2 sources, non-empty explanation + source_citation, exam_relevance subset of `("SSC","IBPS-SBI","RRB")`).
- `selection/bank.py`: `add_entry(bank, entry, today) -> (stamped, warnings)` raises `BankError` on hard-QA-fail or duplicate, else appends a `status="draft"` entry and returns soft warnings + near-dup notes. Also `BankError`, `verify_entry`, `is_drawable`, `bank_health`, and a `main(argv)` CLI with `--bank`/`--history` global args and `health`/`verify` subcommands.
- `selection/store.py`: `Store(history_path, bank_path)` with `load_bank()`/`save_bank(entries)` over `BankEntry`.

---

### Task 1: `ingest_batch` + `IngestReport` (pure)

**Files:**
- Create: `selection/ingest.py`
- Test: `tests/test_ingest.py` (Create)

- [ ] **Step 1: Write the failing test**

Create `tests/test_ingest.py`:

```python
from datetime import date

from selection.models import BankEntry, Question
from selection.ingest import ingest_batch, IngestReport

TODAY = date(2026, 6, 12)


def _draft(fk, stem, sources=("https://a", "https://b"), distractors=("b", "c", "d"),
           explanation="why", source_citation="cite"):
    q = Question("polity", "basic", fk, "X", stem, "a", list(distractors),
                 ["SSC"], list(sources), explanation=explanation,
                 source_citation=source_citation)
    return BankEntry(question=q, static_class="permanent", source_tier=2,
                     yield_weight="high", status="draft")


def test_clean_batch_all_accepted_and_landed_as_drafts():
    bank: list[BankEntry] = []
    drafts = [_draft("polity/a", "First distinct stem about one topic."),
              _draft("polity/b", "Second different stem on another matter.")]
    report = ingest_batch(bank, drafts, TODAY)
    assert set(report.accepted) == {"polity/a", "polity/b"}
    assert report.rejected == []
    assert len(bank) == 2
    assert all(e.status == "draft" for e in bank)


def test_too_few_sources_rejected_by_validate():
    bank: list[BankEntry] = []
    report = ingest_batch(bank, [_draft("polity/a", "A stem here about things.",
                                        sources=("https://only-one",))], TODAY)
    assert report.accepted == []
    assert report.rejected[0][0] == "polity/a"
    assert "source" in report.rejected[0][1].lower()
    assert len(bank) == 0  # nothing appended


def test_hard_qa_failure_rejected_others_accepted():
    bank: list[BankEntry] = []
    bad = _draft("polity/bad", "Bad item with a blank distractor.", distractors=("b", "c", ""))
    good = _draft("polity/good", "A perfectly fine stem about a subject.")
    report = ingest_batch(bank, [bad, good], TODAY)
    assert "polity/good" in report.accepted
    assert any(fk == "polity/bad" for fk, _ in report.rejected)
    assert len(bank) == 1


def test_duplicate_rejected():
    bank: list[BankEntry] = []
    first = _draft("polity/a", "A unique stem about one specific topic.")
    dup = _draft("polity/a", "Completely different wording but same fact key.")
    report = ingest_batch(bank, [first, dup], TODAY)
    assert report.accepted == ["polity/a"]
    assert any(fk == "polity/a" and "duplicate" in reason.lower()
               for fk, reason in report.rejected)
    assert len(bank) == 1


def test_near_duplicate_accepted_with_warning():
    bank: list[BankEntry] = []
    first = _draft("polity/a", "Which Article guarantees the right to free speech in India today?")
    near = _draft("polity/b", "Which Article guarantees the right to free speech across India now?")
    report = ingest_batch(bank, [first, near], TODAY)
    assert set(report.accepted) == {"polity/a", "polity/b"}
    assert any(fk == "polity/b" and any("near-duplicate" in w for w in warns)
               for fk, warns in report.warnings)


def test_report_is_ingestreport_instance():
    assert isinstance(ingest_batch([], [], TODAY), IngestReport)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_ingest.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'selection.ingest'`).

- [ ] **Step 3: Write minimal implementation**

Create `selection/ingest.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from selection.bank import BankError, add_entry
from selection.models import BankEntry


@dataclass
class IngestReport:
    accepted: list[str] = field(default_factory=list)              # fact_keys
    rejected: list[tuple[str, str]] = field(default_factory=list)  # (fact_key, reason)
    warnings: list[tuple[str, list[str]]] = field(default_factory=list)  # (fact_key, warnings)


def ingest_batch(bank: list[BankEntry], drafts: list[BankEntry], today: date) -> IngestReport:
    """Validate + add each draft through the single QA+dedup path (add_entry). Mutates `bank`,
    appending only accepted drafts. Returns a per-item report. add_entry owns check_entry +
    find_duplicates, so we do NOT call check_entry separately here."""
    report = IngestReport()
    for entry in drafts:
        fk = entry.question.fact_key
        try:
            entry.question.validate()  # enforces >= 2 sources, 3 distractors, required fields
        except ValueError as exc:
            report.rejected.append((fk, str(exc)))
            continue
        try:
            _stamped, warnings = add_entry(bank, entry, today)
        except BankError as exc:
            report.rejected.append((fk, str(exc)))
            continue
        report.accepted.append(fk)
        if warnings:
            report.warnings.append((fk, warnings))
    return report
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_ingest.py -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add daily-gk-quiz/selection/ingest.py daily-gk-quiz/tests/test_ingest.py
git commit -m "feat(gk-bank): ingest_batch validates + adds authored drafts with a per-item report"
```

---

### Task 2: `ingest` CLI

**Files:**
- Modify: `selection/ingest.py` (add `main` + `__main__` guard)
- Test: `tests/test_ingest_cli.py` (Create)

- [ ] **Step 1: Write the failing test**

Create `tests/test_ingest_cli.py`:

```python
import json

from selection.models import BankEntry, Question
from selection.ingest import main


def _draft_dict(fk, stem):
    q = Question("polity", "basic", fk, "X", stem, "a", ["b", "c", "d"],
                 ["SSC"], ["https://a", "https://b"], explanation="why",
                 source_citation="cite")
    return BankEntry(question=q, static_class="permanent", source_tier=2,
                     yield_weight="high", status="draft").to_dict()


def test_ingest_cli_persists_drafts_and_returns_zero(tmp_path, capsys):
    batch = tmp_path / "batch.json"
    batch.write_text(json.dumps([_draft_dict("polity/a", "A distinct stem about a topic."),
                                 _draft_dict("polity/b", "Another stem on a separate matter.")]),
                     encoding="utf-8")
    bank = tmp_path / "bank.json"
    bank.write_text("[]", encoding="utf-8")
    rc = main(["--batch", str(batch), "--bank", str(bank), "--history", str(tmp_path / "h.json")])
    assert rc == 0
    saved = json.loads(bank.read_text(encoding="utf-8"))
    assert {e["question"]["fact_key"] for e in saved} == {"polity/a", "polity/b"}
    assert all(e["status"] == "draft" for e in saved)
    assert "accepted=2" in capsys.readouterr().out


def test_ingest_cli_all_rejected_returns_one(tmp_path):
    batch = tmp_path / "batch.json"
    # only one source -> Question.validate rejects
    q = Question("polity", "basic", "polity/x", "X", "stem here about things.", "a",
                 ["b", "c", "d"], ["SSC"], ["https://only"], explanation="w",
                 source_citation="c")
    bad = BankEntry(question=q, static_class="permanent", source_tier=2,
                    yield_weight="high", status="draft").to_dict()
    batch.write_text(json.dumps([bad]), encoding="utf-8")
    bank = tmp_path / "bank.json"
    bank.write_text("[]", encoding="utf-8")
    rc = main(["--batch", str(batch), "--bank", str(bank), "--history", str(tmp_path / "h.json")])
    assert rc == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_ingest_cli.py -v`
Expected: FAIL (`ImportError: cannot import name 'main'`).

- [ ] **Step 3: Write minimal implementation**

At the top of `selection/ingest.py`, add imports:

```python
import argparse
import json
from pathlib import Path
```

Append to `selection/ingest.py`:

```python
def main(argv=None) -> int:
    from selection.store import Store

    parser = argparse.ArgumentParser(prog="selection.ingest")
    parser.add_argument("--batch", required=True)
    parser.add_argument("--bank", default="state/question-bank.json")
    parser.add_argument("--history", default="state/question-history.json")
    args = parser.parse_args(argv)

    raw = json.loads(Path(args.batch).read_text(encoding="utf-8"))
    drafts = [BankEntry.from_dict(d) for d in raw]

    store = Store(args.history, args.bank)
    bank = store.load_bank()
    report = ingest_batch(bank, drafts, date.today())
    store.save_bank(bank)

    for fk in report.accepted:
        print(f"ACCEPT {fk}")
    for fk, warns in report.warnings:
        print(f"  WARN {fk}: {warns}")
    for fk, reason in report.rejected:
        print(f"REJECT {fk}: {reason}")
    print(f"accepted={len(report.accepted)} rejected={len(report.rejected)}")
    return 0 if report.accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_ingest_cli.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add daily-gk-quiz/selection/ingest.py daily-gk-quiz/tests/test_ingest_cli.py
git commit -m "feat(gk-bank): ingest CLI -- batch file -> drafts in the bank + report"
```

---

### Task 3: `bank drafts` subcommand

**Files:**
- Modify: `selection/bank.py` (`main`: register `drafts` subparser + handle it)
- Test: `tests/test_bank_cli.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_bank_cli.py` (it already imports `json`, `BankEntry`, `Question`, `main` and has `_entry_dict(fk, status="draft")` and `_write_bank(path, entries)` helpers):

```python
def test_drafts_lists_only_draft_entries(tmp_path, capsys):
    bank = tmp_path / "bank.json"
    _write_bank(bank, [_entry_dict("polity/draft1", status="draft"),
                       _entry_dict("polity/verified1", status="verified"),
                       _entry_dict("polity/draft2", status="draft")])
    rc = main(["--bank", str(bank), "--history", str(tmp_path / "h.json"), "drafts"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "polity/draft1" in out and "polity/draft2" in out
    assert "polity/verified1" not in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_bank_cli.py::test_drafts_lists_only_draft_entries -v`
Expected: FAIL (argparse errors on the unknown `drafts` subcommand -> `SystemExit`).

- [ ] **Step 3: Write minimal implementation**

In `selection/bank.py` `main`, register the subparser (after the `verify` subparser block, before `args = parser.parse_args(argv)`):

```python
    sub.add_parser("drafts")
```

Add the handler (after the `verify` block, before the final `return 0`):

```python
    if args.cmd == "drafts":
        for e in bank:
            if e.status == "draft":
                print(f"{e.question.fact_key}\t{e.question.question}")
        return 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_bank_cli.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Run the full suite**

Run: `.venv\Scripts\python.exe -m pytest -q`
Expected: all PASS (foundation + new ingest tests, no regressions).

- [ ] **Step 6: Commit**

```bash
git add daily-gk-quiz/selection/bank.py daily-gk-quiz/tests/test_bank_cli.py
git commit -m "feat(gk-bank): bank drafts subcommand lists unverified entries"
```

---

### Task 4: The generation recipe (prose)

**Files:**
- Create: `daily-gk-quiz/skills/generate-bank.md`
- Modify: `daily-gk-quiz/SKILL.md` (point the "Replenishing the bank" section at the recipe)

No tests (prose recipe). The acceptance check is a manual end-to-end run by the operator.

- [ ] **Step 1: Create the recipe**

Create `daily-gk-quiz/skills/generate-bank.md` with this content (ASCII quotes only):

```markdown
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
```

- [ ] **Step 2: Point SKILL.md at the recipe**

In `daily-gk-quiz/SKILL.md`, replace the "## Replenishing the bank" section body with:

```markdown
## Replenishing the bank
Use the **generate-bank** recipe (`skills/generate-bank.md`): target low-stock cells via
`selection.bank health`, author + adversarially review batches with subagents, ingest as drafts via
`selection.ingest`, and verify each at operator gate #1 (`selection.bank verify`). Only verified
entries are ever drawn.
```

- [ ] **Step 3: Verify the docs are tracked + commit**

Run from repo root: `git -C D:\Rewva\signal-lab status --short` (confirm both files show).

```bash
git add daily-gk-quiz/skills/generate-bank.md daily-gk-quiz/SKILL.md
git commit -m "docs(gk-bank): generate-bank recipe (author -> review -> ingest -> verify)"
```

---

## Self-Review notes (author)

- **Spec coverage:** SS2 flow -> Task 4 recipe (steps 1-5); SS3.1 ingest_batch/IngestReport ->
  Task 1; SS3.1 CLI -> Task 2; SS3.2 `bank drafts` -> Task 3; SS4 recipe doc -> Task 4; SS6 testing
  -> each task's tests. All covered.
- **Single QA path:** Task 1 calls `Question.validate()` then `add_entry` only -- no separate
  `check_entry` (matches the spec's "add_entry owns that" fix).
- **Type consistency:** `ingest_batch(bank, drafts, today) -> IngestReport` is identical across Task
  1 (def), Task 2 (CLI call). `IngestReport` fields (accepted/rejected/warnings) match between the
  dataclass and every test assertion. `main(argv)` returns int (0/1) in both CLIs.
- **No placeholders:** every code + doc step is concrete; the recipe is complete prose.
- **Note for executor:** Task 1's near-dup test relies on the two stems scoring 0.80-0.87 difflib;
  they are intentionally near-identical ("free speech in India today" vs "free speech across India
  now"). If the ratio lands outside that band, nudge the wording (keep both stems > 0.80 and < 0.87)
  -- the behavior under test (accepted + near-dup warning) is what matters.
