# GK Topic Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the deterministic topic-selection layer of the `daily-gk-quiz` skill -- the code that picks each day's domain + difficulty, draws from a pre-built question bank, hard-blocks duplicates by `fact_key`, and rotates anti-template hooks/CTAs -- plus its seed data and the SKILL.md recipe that orchestrates it.

**Architecture:** A small stdlib-only Python package `selection/` with three focused modules: `models.py` (dataclasses + (de)serialization), `store.py` (atomic JSON I/O for the history log + question bank), and `selection.py` (pure selection logic: dedupe, weighted domain/difficulty balance, bank draw, rotation). A `planner.py` integrates them into one `plan_today()` returning a `DayPlan`. The Claude-judgment steps (research, draft MCQ, verify facts) live in `SKILL.md`, not in code -- they call the helpers for the deterministic parts and the operator gates stay manual. Clock is injected everywhere for testability.

**Tech Stack:** Python 3.12, stdlib only (dataclasses, json, datetime, pathlib), pytest. Mirrors the `publisher/` package's TDD style (injected clock, atomic writes, no ORM).

**Spec:** `docs/specs/2026-06-10-gk-topic-selection-design.md`
**Research basis:** `docs/ga-exam-pattern-research.md`

---

## File Structure

| File | Responsibility |
|---|---|
| `daily-gk-quiz/pyproject.toml` | Package + pytest config (editable install, like publisher) |
| `daily-gk-quiz/selection/__init__.py` | Package marker + public exports |
| `daily-gk-quiz/selection/models.py` | `Question`, `HistoryRecord` dataclasses + `to_dict`/`from_dict` + validation |
| `daily-gk-quiz/selection/store.py` | Load/save `question-history.json` + `question-bank.json`; atomic append |
| `daily-gk-quiz/selection/selection.py` | Pure logic: `is_duplicate`, `recent_shares`, `pick_domain`, `pick_difficulty`, `draw_from_bank`, `pick_rotation` |
| `daily-gk-quiz/selection/planner.py` | `plan_today()` -> `DayPlan` integrating the above |
| `daily-gk-quiz/data/domains.json` | Weighted topic plan (the §3.1 blueprint) |
| `daily-gk-quiz/data/prompts.json` | Rotation pools: anti-template `hooks` + `ctas` |
| `daily-gk-quiz/state/question-history.json` | Append-only posted log (seeded empty `[]`) |
| `daily-gk-quiz/state/question-bank.json` | Pre-built verified static MCQs (seeded empty `[]`) |
| `daily-gk-quiz/SKILL.md` | The daily recipe Claude follows (orchestrates helpers + gates) |
| `daily-gk-quiz/tests/test_*.py` | One test module per code file |

**Data shapes (locked, used across all tasks):**

```python
# Question: a quiz item (bank entry or freshly drafted). No date.
#   domain: str                      one of the domains.json keys
#   difficulty: str                  "basic" | "intermediate" | "advanced"
#   fact_key: str                    canonical slug, e.g. "polity/article-21-right-to-life"
#   entity: str                      short human label, e.g. "Article 21"
#   question: str
#   answer: str                      the correct option text
#   distractors: list[str]           exactly 3 wrong options
#   exam_relevance: list[str]        subset of ["SSC", "IBPS-SBI", "RRB"]
#   sources: list[str]               >= 2 URLs

# HistoryRecord: a posted Question stamped with a date.
#   date: str                        ISO "YYYY-MM-DD"
#   question: Question
```

---

## Task 1: Package scaffold

**Files:**
- Create: `daily-gk-quiz/pyproject.toml`
- Create: `daily-gk-quiz/selection/__init__.py`
- Create: `daily-gk-quiz/tests/test_smoke.py`

- [ ] **Step 1: Write the failing test**

`daily-gk-quiz/tests/test_smoke.py`:
```python
def test_package_imports():
    import selection
    assert selection is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd daily-gk-quiz && py -m pytest tests/test_smoke.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'selection'`

- [ ] **Step 3: Create the package + config**

`daily-gk-quiz/pyproject.toml`:
```toml
[project]
name = "daily-gk-quiz-selection"
version = "0.1.0"
requires-python = ">=3.12"

[project.optional-dependencies]
dev = ["pytest>=8"]

[tool.setuptools]
packages = ["selection"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

`daily-gk-quiz/selection/__init__.py`:
```python
"""Deterministic topic-selection layer for the daily-gk-quiz skill."""
```

- [ ] **Step 4: Install + run test to verify it passes**

Run: `cd daily-gk-quiz && py -m venv .venv && .venv\Scripts\python.exe -m pip install -e ".[dev]" && .venv\Scripts\python.exe -m pytest -v`
Expected: PASS (1 test)

- [ ] **Step 5: Commit**

```bash
git add daily-gk-quiz/pyproject.toml daily-gk-quiz/selection/__init__.py daily-gk-quiz/tests/test_smoke.py
git commit -m "chore: scaffold daily-gk-quiz selection package"
```

---

## Task 2: Data models

**Files:**
- Create: `daily-gk-quiz/selection/models.py`
- Test: `daily-gk-quiz/tests/test_models.py`

- [ ] **Step 1: Write the failing test**

`daily-gk-quiz/tests/test_models.py`:
```python
import pytest
from selection.models import Question, HistoryRecord

def _q(**over):
    base = dict(
        domain="polity", difficulty="basic",
        fact_key="polity/article-21-right-to-life", entity="Article 21",
        question="Article 21 guarantees the right to what?",
        answer="Life and personal liberty",
        distractors=["Equality", "Freedom of speech", "Property"],
        exam_relevance=["SSC", "RRB"],
        sources=["https://a.gov.in", "https://b.org"],
    )
    base.update(over)
    return Question(**base)

def test_question_roundtrips_through_dict():
    q = _q()
    assert Question.from_dict(q.to_dict()) == q

def test_question_rejects_wrong_distractor_count():
    with pytest.raises(ValueError, match="exactly 3 distractors"):
        _q(distractors=["only", "two"]).validate()

def test_question_rejects_too_few_sources():
    with pytest.raises(ValueError, match="at least 2 sources"):
        _q(sources=["https://only-one"]).validate()

def test_question_rejects_bad_difficulty():
    with pytest.raises(ValueError, match="difficulty"):
        _q(difficulty="impossible").validate()

def test_history_record_roundtrips_flat():
    rec = HistoryRecord(date="2026-06-10", question=_q())
    d = rec.to_dict()
    assert d["date"] == "2026-06-10"
    assert d["fact_key"] == "polity/article-21-right-to-life"  # flattened, not nested
    assert HistoryRecord.from_dict(d) == rec
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd daily-gk-quiz && .venv\Scripts\python.exe -m pytest tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'selection.models'`

- [ ] **Step 3: Write minimal implementation**

`daily-gk-quiz/selection/models.py`:
```python
from __future__ import annotations

from dataclasses import dataclass, asdict, field

DIFFICULTIES = ("basic", "intermediate", "advanced")
EXAMS = ("SSC", "IBPS-SBI", "RRB")

@dataclass
class Question:
    domain: str
    difficulty: str
    fact_key: str
    entity: str
    question: str
    answer: str
    distractors: list[str]
    exam_relevance: list[str]
    sources: list[str]

    def validate(self) -> "Question":
        if self.difficulty not in DIFFICULTIES:
            raise ValueError(f"difficulty must be one of {DIFFICULTIES}")
        if len(self.distractors) != 3:
            raise ValueError("a question needs exactly 3 distractors")
        if len(self.sources) < 2:
            raise ValueError("a question needs at least 2 sources")
        bad = [e for e in self.exam_relevance if e not in EXAMS]
        if bad:
            raise ValueError(f"unknown exam_relevance {bad}; allowed {EXAMS}")
        return self

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Question":
        return cls(
            domain=d["domain"], difficulty=d["difficulty"], fact_key=d["fact_key"],
            entity=d["entity"], question=d["question"], answer=d["answer"],
            distractors=list(d["distractors"]), exam_relevance=list(d["exam_relevance"]),
            sources=list(d["sources"]),
        )

@dataclass
class HistoryRecord:
    date: str
    question: Question

    def to_dict(self) -> dict:
        return {"date": self.date, **self.question.to_dict()}

    @classmethod
    def from_dict(cls, d: dict) -> "HistoryRecord":
        return cls(date=d["date"], question=Question.from_dict(d))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd daily-gk-quiz && .venv\Scripts\python.exe -m pytest tests/test_models.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add daily-gk-quiz/selection/models.py daily-gk-quiz/tests/test_models.py
git commit -m "feat: Question + HistoryRecord models with validation"
```

---

## Task 3: State store (atomic JSON I/O)

**Files:**
- Create: `daily-gk-quiz/selection/store.py`
- Test: `daily-gk-quiz/tests/test_store.py`

- [ ] **Step 1: Write the failing test**

`daily-gk-quiz/tests/test_store.py`:
```python
from selection.models import Question, HistoryRecord
from selection.store import Store

def _q(fk="history/x"):
    return Question("history", "basic", fk, "X", "q?", "a",
                    ["b", "c", "d"], ["SSC"], ["https://1", "https://2"])

def test_load_missing_files_returns_empty(tmp_path):
    s = Store(tmp_path / "hist.json", tmp_path / "bank.json")
    assert s.load_history() == []
    assert s.load_bank() == []

def test_append_history_persists_and_reloads(tmp_path):
    s = Store(tmp_path / "hist.json", tmp_path / "bank.json")
    s.append_history(HistoryRecord("2026-06-10", _q()))
    again = Store(tmp_path / "hist.json", tmp_path / "bank.json")
    recs = again.load_history()
    assert len(recs) == 1 and recs[0].date == "2026-06-10"

def test_save_bank_roundtrips(tmp_path):
    s = Store(tmp_path / "hist.json", tmp_path / "bank.json")
    s.save_bank([_q("history/a"), _q("history/b")])
    assert [q.fact_key for q in s.load_bank()] == ["history/a", "history/b"]

def test_append_is_atomic_no_tmp_left(tmp_path):
    s = Store(tmp_path / "hist.json", tmp_path / "bank.json")
    s.append_history(HistoryRecord("2026-06-10", _q()))
    assert not (tmp_path / "hist.json.tmp").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd daily-gk-quiz && .venv\Scripts\python.exe -m pytest tests/test_store.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'selection.store'`

- [ ] **Step 3: Write minimal implementation**

`daily-gk-quiz/selection/store.py`:
```python
from __future__ import annotations

import json
from pathlib import Path

from selection.models import Question, HistoryRecord

class Store:
    def __init__(self, history_path, bank_path):
        self._history_path = Path(history_path)
        self._bank_path = Path(bank_path)

    def load_history(self) -> list[HistoryRecord]:
        return [HistoryRecord.from_dict(d) for d in self._read(self._history_path)]

    def load_bank(self) -> list[Question]:
        return [Question.from_dict(d) for d in self._read(self._bank_path)]

    def save_bank(self, questions: list[Question]) -> None:
        self._write(self._bank_path, [q.to_dict() for q in questions])

    def append_history(self, record: HistoryRecord) -> None:
        rows = self._read(self._history_path)
        rows.append(record.to_dict())
        self._write(self._history_path, rows)

    def _read(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        return json.loads(path.read_text(encoding="utf-8"))

    def _write(self, path: Path, rows: list[dict]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(rows, indent=2, ensure_ascii=True), encoding="utf-8")
        tmp.replace(path)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd daily-gk-quiz && .venv\Scripts\python.exe -m pytest tests/test_store.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add daily-gk-quiz/selection/store.py daily-gk-quiz/tests/test_store.py
git commit -m "feat: atomic JSON store for history + question bank"
```

---

## Task 4: Dedupe by fact_key + window

**Files:**
- Create: `daily-gk-quiz/selection/selection.py`
- Test: `daily-gk-quiz/tests/test_dedupe.py`

- [ ] **Step 1: Write the failing test**

`daily-gk-quiz/tests/test_dedupe.py`:
```python
from datetime import date
from selection.models import Question, HistoryRecord
from selection.selection import is_duplicate

def _rec(fk, d):
    q = Question("history", "basic", fk, "X", "q?", "a",
                 ["b", "c", "d"], ["SSC"], ["https://1", "https://2"])
    return HistoryRecord(d, q)

def test_recent_fact_key_is_duplicate():
    hist = [_rec("history/plassey-1757", "2026-06-01")]
    assert is_duplicate("history/plassey-1757", hist, date(2026, 6, 10), window_days=120)

def test_fact_key_outside_window_is_not_duplicate():
    hist = [_rec("history/plassey-1757", "2026-01-01")]  # >120 days before
    assert not is_duplicate("history/plassey-1757", hist, date(2026, 6, 10), window_days=120)

def test_unseen_fact_key_is_not_duplicate():
    hist = [_rec("history/plassey-1757", "2026-06-01")]
    assert not is_duplicate("polity/article-21", hist, date(2026, 6, 10), window_days=120)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd daily-gk-quiz && .venv\Scripts\python.exe -m pytest tests/test_dedupe.py -v`
Expected: FAIL — `ImportError: cannot import name 'is_duplicate'`

- [ ] **Step 3: Write minimal implementation**

Create `daily-gk-quiz/selection/selection.py` with:
```python
from __future__ import annotations

from datetime import date, timedelta

from selection.models import HistoryRecord

def is_duplicate(fact_key: str, history: list[HistoryRecord],
                 today: date, window_days: int = 120) -> bool:
    cutoff = today - timedelta(days=window_days)
    for rec in history:
        if rec.question.fact_key == fact_key and date.fromisoformat(rec.date) >= cutoff:
            return True
    return False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd daily-gk-quiz && .venv\Scripts\python.exe -m pytest tests/test_dedupe.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add daily-gk-quiz/selection/selection.py daily-gk-quiz/tests/test_dedupe.py
git commit -m "feat: fact_key dedupe within a recency window"
```

---

## Task 5: Weighted domain balance

**Files:**
- Modify: `daily-gk-quiz/selection/selection.py`
- Test: `daily-gk-quiz/tests/test_domain_balance.py`

- [ ] **Step 1: Write the failing test**

`daily-gk-quiz/tests/test_domain_balance.py`:
```python
from datetime import date
from selection.models import Question, HistoryRecord
from selection.selection import pick_domain

def _rec(domain, d):
    q = Question(domain, "basic", f"{domain}/x-{d}", "X", "q?", "a",
                 ["b", "c", "d"], ["SSC"], ["https://1", "https://2"])
    return HistoryRecord(d, q)

WEIGHTS = {"current-affairs": 30, "general-science": 18, "static-gk": 12}

def test_empty_history_picks_highest_weight():
    assert pick_domain([], WEIGHTS, date(2026, 6, 10), window_days=120) == "current-affairs"

def test_picks_domain_furthest_below_its_weight():
    # current-affairs already over-covered; static-gk untouched -> static-gk most under target
    hist = [_rec("current-affairs", "2026-06-08"), _rec("current-affairs", "2026-06-09")]
    assert pick_domain(hist, WEIGHTS, date(2026, 6, 10), window_days=120) == "static-gk"

def test_ignores_history_outside_window():
    hist = [_rec("current-affairs", "2025-01-01")]  # stale, ignored
    assert pick_domain(hist, WEIGHTS, date(2026, 6, 10), window_days=120) == "current-affairs"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd daily-gk-quiz && .venv\Scripts\python.exe -m pytest tests/test_domain_balance.py -v`
Expected: FAIL — `ImportError: cannot import name 'pick_domain'`

- [ ] **Step 3: Add the implementation**

Append to `daily-gk-quiz/selection/selection.py`:
```python
def _recent(history: list[HistoryRecord], today: date, window_days: int) -> list[HistoryRecord]:
    cutoff = today - timedelta(days=window_days)
    return [r for r in history if date.fromisoformat(r.date) >= cutoff]

def recent_shares(values: list[str], universe) -> dict[str, float]:
    """Normalized frequency of each value, 0 for unseen members of `universe`."""
    total = len(values) or 1
    counts = {k: 0 for k in universe}
    for v in values:
        counts[v] = counts.get(v, 0) + 1
    return {k: counts[k] / total for k in counts}

def pick_domain(history: list[HistoryRecord], weights: dict[str, float],
                today: date, window_days: int = 120) -> str:
    targets = {k: w / sum(weights.values()) for k, w in weights.items()}
    seen = [r.question.domain for r in _recent(history, today, window_days)]
    shares = recent_shares(seen, weights.keys())
    deficits = {k: targets[k] - shares[k] for k in weights}
    return max(deficits, key=lambda k: (deficits[k], weights[k]))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd daily-gk-quiz && .venv\Scripts\python.exe -m pytest tests/test_domain_balance.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add daily-gk-quiz/selection/selection.py daily-gk-quiz/tests/test_domain_balance.py
git commit -m "feat: weighted domain balance picks furthest-below-target"
```

---

## Task 6: Difficulty balance (50/35/15)

**Files:**
- Modify: `daily-gk-quiz/selection/selection.py`
- Test: `daily-gk-quiz/tests/test_difficulty_balance.py`

- [ ] **Step 1: Write the failing test**

`daily-gk-quiz/tests/test_difficulty_balance.py`:
```python
from datetime import date
from selection.models import Question, HistoryRecord
from selection.selection import pick_difficulty

DEFAULT_MIX = {"basic": 0.50, "intermediate": 0.35, "advanced": 0.15}

def _rec(diff, d):
    q = Question("history", diff, f"history/x-{d}", "X", "q?", "a",
                 ["b", "c", "d"], ["SSC"], ["https://1", "https://2"])
    return HistoryRecord(d, q)

def test_empty_history_picks_basic():
    assert pick_difficulty([], DEFAULT_MIX, date(2026, 6, 10), window_days=120) == "basic"

def test_picks_level_furthest_below_target():
    # all-basic recent history -> advanced (0% vs 15% target) is most under
    hist = [_rec("basic", f"2026-06-0{n}") for n in range(1, 6)]
    assert pick_difficulty(hist, DEFAULT_MIX, date(2026, 6, 10), window_days=120) == "advanced"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd daily-gk-quiz && .venv\Scripts\python.exe -m pytest tests/test_difficulty_balance.py -v`
Expected: FAIL — `ImportError: cannot import name 'pick_difficulty'`

- [ ] **Step 3: Add the implementation**

Append to `daily-gk-quiz/selection/selection.py`:
```python
def pick_difficulty(history: list[HistoryRecord], target_mix: dict[str, float],
                    today: date, window_days: int = 120) -> str:
    seen = [r.question.difficulty for r in _recent(history, today, window_days)]
    shares = recent_shares(seen, target_mix.keys())
    order = {"basic": 3, "intermediate": 2, "advanced": 1}  # tie-break toward basic
    deficits = {k: target_mix[k] - shares[k] for k in target_mix}
    return max(deficits, key=lambda k: (deficits[k], order[k]))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd daily-gk-quiz && .venv\Scripts\python.exe -m pytest tests/test_difficulty_balance.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add daily-gk-quiz/selection/selection.py daily-gk-quiz/tests/test_difficulty_balance.py
git commit -m "feat: difficulty balance toward the 50/35/15 mix"
```

---

## Task 7: Draw from the question bank

**Files:**
- Modify: `daily-gk-quiz/selection/selection.py`
- Test: `daily-gk-quiz/tests/test_bank_draw.py`

- [ ] **Step 1: Write the failing test**

`daily-gk-quiz/tests/test_bank_draw.py`:
```python
from selection.models import Question
from selection.selection import draw_from_bank

def _q(domain, diff, fk):
    return Question(domain, diff, fk, "X", "q?", "a",
                    ["b", "c", "d"], ["SSC"], ["https://1", "https://2"])

BANK = [
    _q("history", "basic", "history/plassey-1757"),
    _q("history", "advanced", "history/buxar-1764"),
    _q("polity", "basic", "polity/article-21"),
]

def test_draws_matching_domain_and_difficulty():
    got = draw_from_bank(BANK, "history", "basic", used_fact_keys=set())
    assert got is not None and got.fact_key == "history/plassey-1757"

def test_skips_already_used_fact_keys():
    got = draw_from_bank(BANK, "history", "basic",
                         used_fact_keys={"history/plassey-1757"})
    assert got is None  # no other history+basic entry

def test_bank_miss_returns_none():
    assert draw_from_bank(BANK, "economy", "basic", used_fact_keys=set()) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd daily-gk-quiz && .venv\Scripts\python.exe -m pytest tests/test_bank_draw.py -v`
Expected: FAIL — `ImportError: cannot import name 'draw_from_bank'`

- [ ] **Step 3: Add the implementation**

Append to `daily-gk-quiz/selection/selection.py` (add `from typing import Optional` and `from selection.models import Question` to the imports at the top):
```python
def draw_from_bank(bank: list[Question], domain: str, difficulty: str,
                   used_fact_keys: set[str]) -> Optional[Question]:
    for q in bank:
        if (q.domain == domain and q.difficulty == difficulty
                and q.fact_key not in used_fact_keys):
            return q
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd daily-gk-quiz && .venv\Scripts\python.exe -m pytest tests/test_bank_draw.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add daily-gk-quiz/selection/selection.py daily-gk-quiz/tests/test_bank_draw.py
git commit -m "feat: draw an unused matching entry from the question bank"
```

---

## Task 8: Hook / CTA rotation

**Files:**
- Modify: `daily-gk-quiz/selection/selection.py`
- Test: `daily-gk-quiz/tests/test_rotation.py`

- [ ] **Step 1: Write the failing test**

`daily-gk-quiz/tests/test_rotation.py`:
```python
from selection.selection import pick_rotation

POOL = ["hook-a", "hook-b", "hook-c"]

def test_avoids_most_recent():
    # recent[-1] is the last used; result must differ
    assert pick_rotation(POOL, recent=["hook-a"]) != "hook-a"

def test_picks_least_recently_used():
    # hook-a used longmost ago, hook-c most recent -> expect hook-a
    assert pick_rotation(POOL, recent=["hook-a", "hook-b", "hook-c"]) == "hook-a"

def test_empty_recent_returns_first():
    assert pick_rotation(POOL, recent=[]) == "hook-a"

def test_single_item_pool_returns_it():
    assert pick_rotation(["only"], recent=["only"]) == "only"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd daily-gk-quiz && .venv\Scripts\python.exe -m pytest tests/test_rotation.py -v`
Expected: FAIL — `ImportError: cannot import name 'pick_rotation'`

- [ ] **Step 3: Add the implementation**

Append to `daily-gk-quiz/selection/selection.py`:
```python
def pick_rotation(pool: list[str], recent: list[str]) -> str:
    """Least-recently-used item in `pool`. `recent` is oldest-to-newest usage."""
    if len(pool) == 1:
        return pool[0]
    def last_used(item: str) -> int:
        # higher index = used more recently; -1 = never used
        for i in range(len(recent) - 1, -1, -1):
            if recent[i] == item:
                return i
        return -1
    return min(pool, key=last_used)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd daily-gk-quiz && .venv\Scripts\python.exe -m pytest tests/test_rotation.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add daily-gk-quiz/selection/selection.py daily-gk-quiz/tests/test_rotation.py
git commit -m "feat: least-recently-used hook/CTA rotation"
```

---

## Task 9: Planner — integrate into a DayPlan

**Files:**
- Create: `daily-gk-quiz/selection/planner.py`
- Test: `daily-gk-quiz/tests/test_planner.py`

- [ ] **Step 1: Write the failing test**

`daily-gk-quiz/tests/test_planner.py`:
```python
from datetime import date
from selection.models import Question
from selection.planner import plan_today, DayPlan

WEIGHTS = {"current-affairs": 30, "general-science": 18, "static-gk": 12, "history": 10}
MIX = {"basic": 0.50, "intermediate": 0.35, "advanced": 0.15}

def _q(domain, diff, fk):
    return Question(domain, diff, fk, "X", "q?", "a",
                    ["b", "c", "d"], ["SSC"], ["https://1", "https://2"])

def test_plan_picks_domain_difficulty_and_recent_fact_keys():
    plan = plan_today(history=[], bank=[], weights=WEIGHTS, target_mix=MIX,
                      hooks=["h1", "h2"], ctas=["c1", "c2"],
                      today=date(2026, 6, 10), window_days=120)
    assert isinstance(plan, DayPlan)
    assert plan.domain == "current-affairs"   # highest weight, empty history
    assert plan.difficulty == "basic"          # empty history
    assert plan.recent_fact_keys == set()
    assert plan.hook == "h1" and plan.cta == "c1"
    assert plan.bank_candidate is None         # empty bank -> live generation

def test_plan_pulls_bank_candidate_when_static_match_exists():
    bank = [_q("history", "basic", "history/plassey-1757")]
    # single-domain weights force domain == "history" so the bank candidate matches
    plan = plan_today(history=[], bank=bank,
                      weights={"history": 100}, target_mix=MIX,
                      hooks=["h1"], ctas=["c1"],
                      today=date(2026, 6, 10), window_days=120)
    assert plan.domain == "history" and plan.difficulty == "basic"
    assert plan.bank_candidate is not None
    assert plan.bank_candidate.fact_key == "history/plassey-1757"

def test_current_affairs_never_pulls_from_bank():
    bank = [_q("current-affairs", "basic", "current-affairs/old-news")]
    plan = plan_today(history=[], bank=bank,
                      weights={"current-affairs": 100}, target_mix=MIX,
                      hooks=["h1"], ctas=["c1"],
                      today=date(2026, 6, 10), window_days=120)
    assert plan.domain == "current-affairs"
    assert plan.bank_candidate is None  # CA is always generated live
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd daily-gk-quiz && .venv\Scripts\python.exe -m pytest tests/test_planner.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'selection.planner'`

- [ ] **Step 3: Write minimal implementation**

`daily-gk-quiz/selection/planner.py`:
```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from selection.models import Question, HistoryRecord
from selection.selection import (
    pick_domain, pick_difficulty, draw_from_bank, pick_rotation, _recent,
)

CURRENT_AFFAIRS = "current-affairs"

@dataclass
class DayPlan:
    domain: str
    difficulty: str
    recent_fact_keys: set[str]
    bank_candidate: Optional[Question]
    hook: str
    cta: str

def plan_today(*, history: list[HistoryRecord], bank: list[Question],
               weights: dict[str, float], target_mix: dict[str, float],
               hooks: list[str], ctas: list[str],
               today: date, window_days: int = 120) -> DayPlan:
    domain = pick_domain(history, weights, today, window_days)
    difficulty = pick_difficulty(history, target_mix, today, window_days)
    recent_fact_keys = {r.question.fact_key for r in _recent(history, today, window_days)}

    bank_candidate = None
    if domain != CURRENT_AFFAIRS:  # current affairs is always generated live
        bank_candidate = draw_from_bank(bank, domain, difficulty, recent_fact_keys)

    hook = pick_rotation(hooks, _recent_used(history, "hook"))
    cta = pick_rotation(ctas, _recent_used(history, "cta"))
    return DayPlan(domain, difficulty, recent_fact_keys, bank_candidate, hook, cta)

def _recent_used(history: list[HistoryRecord], _kind: str) -> list[str]:
    # Hooks/CTAs aren't stored on past records in v1, so rotation starts fresh each run.
    # Returns empty -> pick_rotation yields the first pool item. (See spec open question.)
    return []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd daily-gk-quiz && .venv\Scripts\python.exe -m pytest tests/test_planner.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Refactor note + commit**

The `_recent_used` stub returns `[]` because v1 does not persist which hook/CTA was used. If hook/CTA repetition becomes visible, add `hook`/`cta` fields to `HistoryRecord` and feed real usage here. Commit:
```bash
git add daily-gk-quiz/selection/planner.py daily-gk-quiz/tests/test_planner.py
git commit -m "feat: plan_today integrates balance + dedupe + bank + rotation into DayPlan"
```

---

## Task 10: Seed data + validity test

**Files:**
- Create: `daily-gk-quiz/data/domains.json`
- Create: `daily-gk-quiz/data/prompts.json`
- Create: `daily-gk-quiz/state/question-history.json`
- Create: `daily-gk-quiz/state/question-bank.json`
- Test: `daily-gk-quiz/tests/test_seed_data.py`

- [ ] **Step 1: Write the failing test**

`daily-gk-quiz/tests/test_seed_data.py`:
```python
import json
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
STATE = Path(__file__).resolve().parent.parent / "state"

def test_domain_weights_sum_to_100():
    weights = json.loads((DATA / "domains.json").read_text(encoding="utf-8"))["weights"]
    assert sum(weights.values()) == 100

def test_domains_include_the_blueprint_set():
    weights = json.loads((DATA / "domains.json").read_text(encoding="utf-8"))["weights"]
    assert "current-affairs" in weights and "banking-financial-awareness" in weights

def test_prompts_have_hooks_and_ctas():
    p = json.loads((DATA / "prompts.json").read_text(encoding="utf-8"))
    assert len(p["hooks"]) >= 3 and len(p["ctas"]) >= 3

def test_state_files_seed_empty_lists():
    assert json.loads((STATE / "question-history.json").read_text(encoding="utf-8")) == []
    assert json.loads((STATE / "question-bank.json").read_text(encoding="utf-8")) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd daily-gk-quiz && .venv\Scripts\python.exe -m pytest tests/test_seed_data.py -v`
Expected: FAIL — `FileNotFoundError` for `data/domains.json`

- [ ] **Step 3: Create the seed files**

`daily-gk-quiz/data/domains.json` (weights = the verified §3.1 blueprint; sub-topics abbreviated):
```json
{
  "weights": {
    "current-affairs": 30,
    "general-science": 18,
    "static-gk": 12,
    "history": 10,
    "polity": 8,
    "geography": 8,
    "economy": 7,
    "banking-financial-awareness": 5,
    "sports-awards-misc": 2
  },
  "exam_relevance": {
    "current-affairs": ["SSC", "IBPS-SBI", "RRB"],
    "general-science": ["SSC", "RRB"],
    "static-gk": ["SSC", "IBPS-SBI", "RRB"],
    "history": ["SSC", "RRB"],
    "polity": ["SSC", "RRB"],
    "geography": ["SSC", "RRB"],
    "economy": ["SSC", "IBPS-SBI", "RRB"],
    "banking-financial-awareness": ["IBPS-SBI"],
    "sports-awards-misc": ["SSC", "IBPS-SBI", "RRB"]
  }
}
```

`daily-gk-quiz/data/prompts.json`:
```json
{
  "hooks": [
    "This came in SSC CGL 2024 -- can you solve it?",
    "90% pick the wrong option here.",
    "Only toppers crack this in 5 seconds.",
    "Most aspirants get this wrong -- do you?"
  ],
  "ctas": [
    "Comment your answer (A/B/C/D) before the reveal!",
    "Comment which exam you're prepping -- SSC / Banking / Railways.",
    "Comment 'GOT IT' if you solved it in 3 seconds.",
    "Follow for one verified GA question every day."
  ]
}
```

`daily-gk-quiz/state/question-history.json`:
```json
[]
```

`daily-gk-quiz/state/question-bank.json`:
```json
[]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd daily-gk-quiz && .venv\Scripts\python.exe -m pytest tests/test_seed_data.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add daily-gk-quiz/data daily-gk-quiz/state daily-gk-quiz/tests/test_seed_data.py
git commit -m "feat: seed domains.json blueprint, prompts pools, empty state files"
```

---

## Task 11: SKILL.md recipe (orchestration)

**Files:**
- Create: `daily-gk-quiz/SKILL.md`

This task has no unit test — it is the human/Claude-facing recipe that wires the tested helpers to the judgment steps and the two operator gates.

- [ ] **Step 1: Write `daily-gk-quiz/SKILL.md`**

````markdown
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
   - Else if `bank_candidate` is not None: use it (already verified — re-confirm in step 4).
   - Else (bank miss): draft a fresh static MCQ at the target domain + difficulty.
   Set a canonical `fact_key`; if the fact matches one already in `recent_fact_keys`, pick a
   different fact (dedupe). Set `exam_relevance` from `data/domains.json`.

3. **Distractor sanity check.** Confirm none of the 3 wrong options is also defensibly correct.

4. **Accuracy gate (#1 — mandatory).** Corroborate the fact across **>=2 independent reputable
   sources**, preferring a primary/official one (RBI, ISRO, PIB, gazette). Present to the
   operator: question, correct answer, 3 distractors, `domain`, `difficulty`, `exam_relevance`,
   `fact_key`, and BOTH source URLs. **Do not proceed until the operator confirms the fact.**

5. **Hand off to render** with the approved question + the `hook` and `cta` from step 1
   (render/voice/post are out of this skill's scope — see the parent design).

6. **Review gate (#2)** and posting happen downstream. **Only after a successful post**, append
   the question to history:
   ```bash
   cd daily-gk-quiz && .venv\Scripts\python.exe -c "import datetime; from selection.store import Store; from selection.models import Question, HistoryRecord; s=Store('state/question-history.json','state/question-bank.json'); q=Question(domain='...', difficulty='...', fact_key='...', entity='...', question='...', answer='...', distractors=['...','...','...'], exam_relevance=['...'], sources=['...','...']).validate(); s.append_history(HistoryRecord(datetime.date.today().isoformat(), q))"
   ```
   If a bank candidate was used, also remove it from `question-bank.json` (rewrite the bank
   without that `fact_key`) and replenish the bank when it runs low.

## Replenishing the bank
Periodically batch-draft + verify static MCQs across under-covered domains/difficulties and
append them (validated) to `state/question-bank.json` so static-GK days never start cold.
````

- [ ] **Step 2: Verify the planner command runs end-to-end**

Run the step-1 command from the SKILL.md against the seeded (empty) state.
Expected: prints a `DayPlan(domain='current-affairs', difficulty='basic', recent_fact_keys=set(), bank_candidate=None, hook='This came in SSC CGL 2024 -- can you solve it?', cta='Comment your answer (A/B/C/D) before the reveal!')`

- [ ] **Step 3: Commit**

```bash
git add daily-gk-quiz/SKILL.md
git commit -m "feat: SKILL.md daily recipe orchestrating planner + accuracy gate"
```

---

## Task 12: Full suite green + .gitignore

**Files:**
- Create: `daily-gk-quiz/.gitignore`

- [ ] **Step 1: Add `.gitignore`**

`daily-gk-quiz/.gitignore`:
```
.venv/
__pycache__/
*.pyc
*.tmp
```

- [ ] **Step 2: Run the full suite**

Run: `cd daily-gk-quiz && .venv\Scripts\python.exe -m pytest -v`
Expected: PASS — all tests across test_smoke, test_models, test_store, test_dedupe, test_domain_balance, test_difficulty_balance, test_bank_draw, test_rotation, test_planner, test_seed_data (no warnings).

- [ ] **Step 3: Commit**

```bash
git add daily-gk-quiz/.gitignore
git commit -m "chore: gitignore for daily-gk-quiz venv + caches"
```

---

## Notes for the implementer

- **State files are committed seeded-empty (`[]`).** They mutate at runtime; that's expected. Do not commit a history/bank full of generated questions as part of this plan.
- **The planner is pure** except the SKILL.md wrapper that reads files + passes `today`. Keep network/LLM work out of `selection/` — it stays unit-testable.
- **`_recent` is imported across modules** — it lives in `selection.py` and is reused by `planner.py`. That underscore import is intentional, not a leak.
- **Windows paths** use backslashes in the run commands (`.venv\Scripts\python.exe`); on POSIX use `.venv/bin/python`.
