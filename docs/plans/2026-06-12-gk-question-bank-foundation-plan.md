# Question-Bank Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the trust machinery + unbiased draw for the daily-gk-quiz question bank: a `BankEntry` wrapper with lifecycle/QA metadata, a deterministic QA gate + stdlib dedup, bank maintenance with a hard static-vs-volatile split, a yield-weighted random draw that replaces the biased first-in-list match, and a seed set of verified anchor facts.

**Architecture:** Extend the existing `daily-gk-quiz/selection/` layer in place. `Question` stays pure; a new `BankEntry` wraps it with bank-only fields. New pure modules `bank_qa.py` (QA gate + dedup) and `bank.py` (maintenance + CLI). `selection.draw_from_bank` is rewritten to yield-weighted random with a `difflib` anti-similarity penalty. `Store`/`plan_today` switch from `list[Question]` to `list[BankEntry]`. Stdlib only (no ML/deps), matching the layer's existing style.

**Tech Stack:** Python 3.12, dataclasses, `difflib`, `random`, pytest. Tests live in `daily-gk-quiz/tests/`, import `selection.*`.

**Working directory for ALL commands:** `D:\Rewva\signal-lab\daily-gk-quiz`. Test runner (Windows/PowerShell): `.venv\Scripts\python.exe -m pytest <args>` (bash form `.venv/Scripts/python.exe -m pytest` also works). ASCII quotes only in every file (data + code).

**Spec:** `docs/specs/2026-06-12-gk-question-bank-foundation-design.md`. **Anchor facts source:** `docs/research/2026-06-12-static-question-bank-research.md`.

**Conventions (already in the repo, follow exactly):**
- `Question` dataclass: `models.py` (domain, difficulty, fact_key, entity, question, answer, distractors[3], exam_relevance[], sources[], explanation, mnemonic, is_trick, source_citation).
- `Store._read/_write` do atomic JSON with `ensure_ascii=True, indent=2`.
- Tests use a local `_q(...)` factory building a `Question`; no shared conftest.

---

### Task 1: `BankEntry` model + constants + round-trip

**Files:**
- Modify: `selection/models.py` (add constants + `BankEntry` after `Question`, before `HistoryRecord`)
- Test: `tests/test_bank_entry.py` (Create)

- [ ] **Step 1: Write the failing test**

Create `tests/test_bank_entry.py`:

```python
from selection.models import BankEntry, Question, YIELD_WEIGHTS, STATIC_CLASSES, STATUSES


def _q(fk="polity/article-21"):
    return Question("polity", "basic", fk, "Article 21", "q?", "a",
                    ["b", "c", "d"], ["SSC"], ["https://1", "https://2"],
                    explanation="because", source_citation="Constitution of India, Art. 21")


def test_constants_present():
    assert STATIC_CLASSES == ("permanent", "slowly-changing")
    assert STATUSES == ("draft", "verified", "retired")
    assert YIELD_WEIGHTS == {"high": 3, "medium": 2, "low": 1}


def test_bankentry_roundtrips_with_nested_question():
    e = BankEntry(question=_q(), static_class="permanent", source_tier=2,
                  yield_weight="high", status="verified",
                  verified_date="2026-06-12", review_due_date=None)
    d = e.to_dict()
    assert d["question"]["fact_key"] == "polity/article-21"  # nested, not flattened
    assert d["static_class"] == "permanent" and d["source_tier"] == 2
    back = BankEntry.from_dict(d)
    assert back == e


def test_bankentry_defaults():
    e = BankEntry(question=_q(), static_class="permanent", source_tier=1, yield_weight="low")
    assert e.status == "draft" and e.verified_date is None and e.review_due_date is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_bank_entry.py -v`
Expected: FAIL (`ImportError: cannot import name 'BankEntry'`).

- [ ] **Step 3: Write minimal implementation**

In `selection/models.py`, after the `Question` class (before `HistoryRecord`), add the constants and dataclass:

```python
STATIC_CLASSES = ("permanent", "slowly-changing")
STATUSES = ("draft", "verified", "retired")
YIELD_WEIGHTS = {"high": 3, "medium": 2, "low": 1}


@dataclass
class BankEntry:
    question: Question
    static_class: str          # one of STATIC_CLASSES
    source_tier: int           # 1 | 2 | 3
    yield_weight: str          # key of YIELD_WEIGHTS
    status: str = "draft"      # one of STATUSES
    verified_date: Optional[str] = None    # ISO date; set when verified
    review_due_date: Optional[str] = None  # ISO date; None for permanent

    def to_dict(self) -> dict:
        return {
            "question": self.question.to_dict(),
            "static_class": self.static_class,
            "source_tier": self.source_tier,
            "yield_weight": self.yield_weight,
            "status": self.status,
            "verified_date": self.verified_date,
            "review_due_date": self.review_due_date,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "BankEntry":
        return cls(
            question=Question.from_dict(d["question"]),
            static_class=d["static_class"],
            source_tier=d["source_tier"],
            yield_weight=d["yield_weight"],
            status=d.get("status", "draft"),
            verified_date=d.get("verified_date"),
            review_due_date=d.get("review_due_date"),
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_bank_entry.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add daily-gk-quiz/selection/models.py daily-gk-quiz/tests/test_bank_entry.py
git commit -m "feat(gk-bank): add BankEntry wrapper + lifecycle constants"
```

---

### Task 2: QA gate `check_entry` (hard + soft rules)

**Files:**
- Create: `selection/bank_qa.py`
- Test: `tests/test_bank_qa.py` (Create)

- [ ] **Step 1: Write the failing test**

Create `tests/test_bank_qa.py`:

```python
from selection.models import BankEntry, Question
from selection.bank_qa import check_entry


def _entry(**over):
    q_over = over.pop("q", {})
    base = dict(domain="polity", difficulty="basic", fact_key="polity/article-21",
                entity="Article 21", question="Which Article guarantees the right to life?",
                answer="Article 21", distractors=["Article 19", "Article 14", "Article 32"],
                exam_relevance=["SSC"], sources=["https://1", "https://2"],
                explanation="Art 21 protects life and liberty.",
                source_citation="Constitution of India, Art. 21")
    base.update(q_over)
    e = dict(static_class="permanent", source_tier=2, yield_weight="high")
    e.update(over)
    return BankEntry(question=Question(**base), **e)


def test_clean_entry_has_no_hard_errors():
    hard, soft = check_entry(_entry())
    assert hard == []


def test_duplicate_option_is_hard_error():
    hard, _ = check_entry(_entry(q={"distractors": ["Article 21", "Article 14", "Article 32"]}))
    assert any("distinct" in h for h in hard)


def test_blank_field_is_hard_error():
    hard, _ = check_entry(_entry(q={"explanation": "   "}))
    assert any("explanation" in h for h in hard)


def test_banned_phrase_is_hard_error():
    hard, _ = check_entry(_entry(q={"distractors": ["All of the above", "Article 14", "Article 32"]}))
    assert any("all/none of the above" in h for h in hard)


def test_bad_enums_are_hard_errors():
    hard, _ = check_entry(_entry(static_class="current-adjacent", source_tier=9, yield_weight="huge"))
    assert any("static_class" in h for h in hard)
    assert any("source_tier" in h for h in hard)
    assert any("yield_weight" in h for h in hard)


def test_answer_length_tell_is_soft_warning():
    long_ans = "Article 21 which guarantees the right to life and personal liberty to all persons"
    hard, soft = check_entry(_entry(q={"answer": long_ans}))
    assert hard == []  # not a hard failure
    assert any("answer-length" in s for s in soft)


def test_absolute_term_distractor_is_soft_warning():
    _, soft = check_entry(_entry(q={"distractors": ["Always Article 19", "Article 14", "Article 32"]}))
    assert any("absolute term" in s for s in soft)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_bank_qa.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'selection.bank_qa'`).

- [ ] **Step 3: Write minimal implementation**

Create `selection/bank_qa.py`:

```python
from __future__ import annotations

import re

from selection.models import BankEntry, STATIC_CLASSES, YIELD_WEIGHTS

BANNED_OPTION_PHRASES = ("all of the above", "none of the above")
ABSOLUTE_TERMS = ("always", "never", "only", "all", "none")


def check_entry(entry: BankEntry) -> tuple[list[str], list[str]]:
    """Deterministic MCQ-quality gate. Returns (hard_errors, soft_warnings).
    A non-empty hard list means the entry must be rejected."""
    q = entry.question
    hard: list[str] = []
    soft: list[str] = []
    options = [q.answer] + list(q.distractors)

    # --- HARD ---
    if len(options) != 4:
        hard.append("must have exactly 4 options (answer + 3 distractors)")
    if any(not o or not o.strip() for o in options):
        hard.append("no option may be blank")
    if len({o.strip().lower() for o in options}) != len(options):
        hard.append("all 4 options must be distinct")
    if not q.answer.strip():
        hard.append("correct answer must be non-empty")
    for name in ("question", "explanation", "source_citation"):
        if not getattr(q, name).strip():
            hard.append(f"{name} must be non-empty")
    if not q.sources:
        hard.append("sources must be non-empty")
    if any(p in o.lower() for o in options for p in BANNED_OPTION_PHRASES):
        hard.append("options must not contain all/none of the above")
    if entry.static_class not in STATIC_CLASSES:
        hard.append(f"static_class must be one of {STATIC_CLASSES}")
    if entry.source_tier not in (1, 2, 3):
        hard.append("source_tier must be 1, 2, or 3")
    if entry.yield_weight not in YIELD_WEIGHTS:
        hard.append(f"yield_weight must be one of {tuple(YIELD_WEIGHTS)}")

    # --- SOFT ---
    avg = sum(len(o) for o in options) / len(options) if options else 0
    if avg and len(q.answer) > 1.5 * avg:
        soft.append("correct answer is much longer than distractors (answer-length tell)")
    for d in q.distractors:
        if any(re.search(rf"\b{t}\b", d.lower()) for t in ABSOLUTE_TERMS):
            soft.append("a distractor uses an absolute term (always/never/only/all/none)")
            break
    for term in ("not", "except", "least"):
        if re.search(rf"\b{term}\b", q.question.lower()) and term.upper() not in q.question:
            soft.append("stem is negatively phrased without emphasis (capitalise NOT/EXCEPT/LEAST)")
            break

    return hard, soft
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_bank_qa.py -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add daily-gk-quiz/selection/bank_qa.py daily-gk-quiz/tests/test_bank_qa.py
git commit -m "feat(gk-bank): deterministic MCQ QA gate (hard + soft rules)"
```

---

### Task 3: Dedup (`normalize_stem`, `find_duplicates`)

**Files:**
- Modify: `selection/bank_qa.py` (append dedup functions + thresholds)
- Test: `tests/test_bank_dedup.py` (Create)

- [ ] **Step 1: Write the failing test**

Create `tests/test_bank_dedup.py`:

```python
from selection.models import BankEntry, Question
from selection.bank_qa import normalize_stem, find_duplicates


def _entry(fk, stem):
    q = Question("polity", "basic", fk, "X", stem, "a", ["b", "c", "d"],
                 ["SSC"], ["https://1", "https://2"],
                 explanation="e", source_citation="cite")
    return BankEntry(question=q, static_class="permanent", source_tier=2, yield_weight="high")


def test_normalize_stem_strips_punct_and_case():
    assert normalize_stem("Who is the 9th P.M.  of India?") == "who is the 9th p m of india"


def test_same_fact_key_is_duplicate():
    bank = [_entry("polity/a", "Totally different wording here about something else.")]
    cand = _entry("polity/a", "Another phrasing entirely unrelated to the above one.")
    dups, near = find_duplicates(cand, bank)
    assert len(dups) == 1 and not near


def test_high_similarity_is_duplicate():
    bank = [_entry("polity/a", "Which Article guarantees the right to life in India?")]
    cand = _entry("polity/b", "Which Article guarantees the right to life in India?")
    dups, near = find_duplicates(cand, bank)
    assert len(dups) == 1 and not near


def test_distinct_stems_are_clean():
    bank = [_entry("polity/a", "Who was the first President of India?")]
    cand = _entry("polity/b", "What is the chemical symbol for gold?")
    dups, near = find_duplicates(cand, bank)
    assert not dups and not near
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_bank_dedup.py -v`
Expected: FAIL (`ImportError: cannot import name 'normalize_stem'`).

- [ ] **Step 3: Write minimal implementation**

Append to `selection/bank_qa.py` (add `import difflib` to the top imports alongside `import re`):

```python
DUP_THRESHOLD = 0.87
NEAR_DUP_THRESHOLD = 0.80


def normalize_stem(text: str) -> str:
    text = re.sub(r"[^a-z0-9\s]", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def find_duplicates(candidate: BankEntry, bank: list[BankEntry]):
    """Returns (dups, near_dups). dup = same fact_key OR same normalized stem OR
    difflib ratio >= 0.87. near = 0.80 <= ratio < 0.87."""
    cand_fk = candidate.question.fact_key
    cand_stem = normalize_stem(candidate.question.question)
    dups: list[BankEntry] = []
    near: list[BankEntry] = []
    for e in bank:
        if e is candidate:
            continue
        e_stem = normalize_stem(e.question.question)
        if e.question.fact_key == cand_fk or e_stem == cand_stem:
            dups.append(e)
            continue
        ratio = difflib.SequenceMatcher(None, cand_stem, e_stem).ratio()
        if ratio >= DUP_THRESHOLD:
            dups.append(e)
        elif ratio >= NEAR_DUP_THRESHOLD:
            near.append(e)
    return dups, near
```

Make sure the top of the file reads `import difflib` then `import re`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_bank_dedup.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add daily-gk-quiz/selection/bank_qa.py daily-gk-quiz/tests/test_bank_dedup.py
git commit -m "feat(gk-bank): stdlib difflib dedup (exact + near-duplicate bands)"
```

---

### Task 4: Bank maintenance -- add / verify / retire / is_drawable

**Files:**
- Create: `selection/bank.py`
- Test: `tests/test_bank.py` (Create)

- [ ] **Step 1: Write the failing test**

Create `tests/test_bank.py`:

```python
from datetime import date

import pytest

from selection.models import BankEntry, Question
from selection.bank import add_entry, verify_entry, retire_entry, is_drawable, BankError


def _entry(fk="polity/a", static_class="permanent", **over):
    q = Question("polity", "basic", fk, "X", f"Stem for {fk} about something specific.",
                 "a", ["b", "c", "d"], ["SSC"], ["https://1", "https://2"],
                 explanation="e", source_citation="cite")
    return BankEntry(question=q, static_class=static_class, source_tier=2,
                     yield_weight=over.get("yield_weight", "high"))


TODAY = date(2026, 6, 12)


def test_add_entry_stamps_permanent_with_no_review_date():
    bank: list[BankEntry] = []
    stamped, warnings = add_entry(bank, _entry(), TODAY)
    assert stamped.status == "draft" and stamped.review_due_date is None
    assert bank == [stamped]


def test_add_entry_stamps_slowly_changing_plus_365():
    bank: list[BankEntry] = []
    stamped, _ = add_entry(bank, _entry(static_class="slowly-changing"), TODAY)
    assert stamped.review_due_date == "2027-06-12"


def test_add_entry_rejects_hard_qa_failure():
    bad = _entry()
    bad.question.explanation = "  "
    with pytest.raises(BankError):
        add_entry([], bad, TODAY)


def test_add_entry_rejects_duplicate():
    bank: list[BankEntry] = []
    add_entry(bank, _entry("polity/a"), TODAY)
    with pytest.raises(BankError):
        add_entry(bank, _entry("polity/a"), TODAY)


def test_verify_entry_flips_and_stamps():
    e = _entry(static_class="slowly-changing")
    v = verify_entry(e, TODAY)
    assert v.status == "verified" and v.verified_date == "2026-06-12"
    assert v.review_due_date == "2027-06-12"


def test_retire_entry():
    assert retire_entry(_entry()).status == "retired"


def test_is_drawable_rules():
    permanent = verify_entry(_entry(), TODAY)
    assert is_drawable(permanent, TODAY) is True
    assert is_drawable(_entry(), TODAY) is False  # draft, not verified
    expiring = verify_entry(_entry(static_class="slowly-changing"), TODAY)
    assert is_drawable(expiring, date(2027, 6, 12)) is True   # boundary == due date
    assert is_drawable(expiring, date(2027, 6, 13)) is False  # past due
    assert is_drawable(retire_entry(permanent), TODAY) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_bank.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'selection.bank'`).

- [ ] **Step 3: Write minimal implementation**

Create `selection/bank.py`:

```python
from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta
from typing import Optional

from selection.bank_qa import check_entry, find_duplicates
from selection.models import BankEntry

REVIEW_DAYS = 365


class BankError(ValueError):
    """Raised when an entry fails QA or is a duplicate at add time."""


def _review_due(static_class: str, today: date) -> Optional[str]:
    if static_class == "slowly-changing":
        return (today + timedelta(days=REVIEW_DAYS)).isoformat()
    return None  # permanent never expires


def add_entry(bank: list[BankEntry], entry: BankEntry, today: date) -> tuple[BankEntry, list[str]]:
    """Validate + dedup, then append a draft (stamped by static_class). Mutates `bank` on success.
    Returns (stamped_entry, warnings). Raises BankError on hard QA failure or duplicate."""
    hard, soft = check_entry(entry)
    if hard:
        raise BankError("; ".join(hard))
    dups, near = find_duplicates(entry, bank)
    if dups:
        raise BankError(f"duplicate of {[e.question.fact_key for e in dups]}")
    stamped = replace(entry, status="draft", verified_date=None,
                      review_due_date=_review_due(entry.static_class, today))
    bank.append(stamped)
    warnings = list(soft)
    if near:
        warnings.append(f"near-duplicate of {[e.question.fact_key for e in near]}")
    return stamped, warnings


def verify_entry(entry: BankEntry, today: date) -> BankEntry:
    """Flip draft -> verified, stamp verified_date and review_due_date. Returns a new entry."""
    return replace(entry, status="verified", verified_date=today.isoformat(),
                   review_due_date=_review_due(entry.static_class, today))


def retire_entry(entry: BankEntry) -> BankEntry:
    return replace(entry, status="retired")


def is_drawable(entry: BankEntry, today: date) -> bool:
    if entry.status != "verified":
        return False
    if entry.review_due_date is None:
        return True
    return today <= date.fromisoformat(entry.review_due_date)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_bank.py -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add daily-gk-quiz/selection/bank.py daily-gk-quiz/tests/test_bank.py
git commit -m "feat(gk-bank): bank maintenance (add/verify/retire/is_drawable) with static-vs-volatile expiry"
```

---

### Task 5: `bank_health`

**Files:**
- Modify: `selection/bank.py` (add `bank_health`)
- Test: `tests/test_bank.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_bank.py`:

```python
from selection.bank import bank_health


def test_bank_health_counts_and_low_stock():
    bank: list[BankEntry] = []
    # 1 drawable polity/basic
    add_entry(bank, _entry("polity/a"), TODAY)
    bank[-1] = verify_entry(bank[-1], TODAY)
    # 1 draft (not drawable, counted as draft)
    add_entry(bank, _entry("polity/b"), TODAY)
    # 1 retired
    add_entry(bank, _entry("polity/c"), TODAY)
    bank[-1] = retire_entry(verify_entry(bank[-1], TODAY))
    health = bank_health(bank, TODAY, low_stock=5)
    assert health["drawable"][("polity", "basic")] == 1
    assert health["drafts"] == 1
    assert health["retired"] == 1
    assert ("polity", "basic") in health["low_stock"]  # only 1 < 5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_bank.py::test_bank_health_counts_and_low_stock -v`
Expected: FAIL (`ImportError: cannot import name 'bank_health'`).

- [ ] **Step 3: Write minimal implementation**

Append to `selection/bank.py`:

```python
def bank_health(bank: list[BankEntry], today: date, low_stock: int = 5) -> dict:
    """Drawable counts per (domain, difficulty) + draft/expired/retired tallies + low-stock cells."""
    drawable: dict[tuple[str, str], int] = {}
    drafts = expired = retired = 0
    for e in bank:
        if e.status == "retired":
            retired += 1
        elif e.status == "draft":
            drafts += 1
        elif is_drawable(e, today):
            key = (e.question.domain, e.question.difficulty)
            drawable[key] = drawable.get(key, 0) + 1
        else:  # verified but past review_due_date
            expired += 1
    low = [k for k, n in drawable.items() if n < low_stock]
    return {"drawable": drawable, "drafts": drafts, "expired": expired,
            "retired": retired, "low_stock": low}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_bank.py -v`
Expected: PASS (8 tests).

- [ ] **Step 5: Commit**

```bash
git add daily-gk-quiz/selection/bank.py daily-gk-quiz/tests/test_bank.py
git commit -m "feat(gk-bank): bank_health drawable/draft/expired/retired + low-stock report"
```

---

### Task 6: `Store` load/save -> `BankEntry`

**Files:**
- Modify: `selection/store.py` (load_bank/save_bank + import)
- Modify: `tests/test_store.py` (update `_q`-based bank test to `BankEntry`)

- [ ] **Step 1: Update the failing test**

In `tests/test_store.py`, change the import line `from selection.models import Question, HistoryRecord` to:

```python
from selection.models import Question, HistoryRecord, BankEntry
```

Replace `test_save_bank_roundtrips` with:

```python
def _entry(fk):
    q = _q(fk)
    return BankEntry(question=q, static_class="permanent", source_tier=2,
                     yield_weight="high", status="verified", verified_date="2026-06-12")


def test_save_bank_roundtrips(tmp_path):
    s = Store(tmp_path / "hist.json", tmp_path / "bank.json")
    s.save_bank([_entry("history/a"), _entry("history/b")])
    loaded = s.load_bank()
    assert [e.question.fact_key for e in loaded] == ["history/a", "history/b"]
    assert all(isinstance(e, BankEntry) for e in loaded)
```

(Note: `_q` in this file lacks `explanation`/`source_citation`; that is fine here -- the store does not run QA, it only serialises. Leave `_q` as is.)

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_store.py -v`
Expected: FAIL (`load_bank` returns `Question` objects, so `e.question` raises `AttributeError`).

- [ ] **Step 3: Write minimal implementation**

In `selection/store.py`, change the import to include `BankEntry`:

```python
from selection.models import Question, HistoryRecord, BankEntry
```

Replace `load_bank` and `save_bank`:

```python
    def load_bank(self) -> list[BankEntry]:
        return [BankEntry.from_dict(d) for d in self._read(self._bank_path)]

    def save_bank(self, entries: list[BankEntry]) -> None:
        self._write(self._bank_path, [e.to_dict() for e in entries])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_store.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add daily-gk-quiz/selection/store.py daily-gk-quiz/tests/test_store.py
git commit -m "feat(gk-bank): Store reads/writes BankEntry"
```

---

### Task 7: `draw_from_bank` rewrite (yield-weighted random + anti-similarity)

**Files:**
- Modify: `selection/selection.py` (rewrite `draw_from_bank`, add imports)
- Modify: `tests/test_bank_draw.py` (rewrite for the new signature + behaviour)

- [ ] **Step 1: Rewrite the failing test**

Replace the entire contents of `tests/test_bank_draw.py` with:

```python
import random
from datetime import date

from selection.models import BankEntry, Question
from selection.selection import draw_from_bank

TODAY = date(2026, 6, 12)


def _entry(domain, diff, fk, stem="A neutral question stem about a topic.", yield_weight="high"):
    q = Question(domain, diff, fk, "X", stem, "a", ["b", "c", "d"], ["SSC"],
                 ["https://1", "https://2"], explanation="e", source_citation="cite")
    return BankEntry(question=q, static_class="permanent", source_tier=2,
                     yield_weight=yield_weight, status="verified", verified_date="2026-06-12")


def _bank():
    return [
        _entry("history", "basic", "history/plassey-1757", "Who won the Battle of Plassey?"),
        _entry("history", "advanced", "history/buxar-1764", "Who won the Battle of Buxar?"),
        _entry("polity", "basic", "polity/article-21", "Which Article protects life?"),
    ]


def test_draws_matching_domain_and_difficulty():
    got = draw_from_bank(_bank(), "history", "basic", set(), [], TODAY, random.Random(0))
    assert got is not None and got.fact_key == "history/plassey-1757"


def test_skips_already_used_fact_keys():
    got = draw_from_bank(_bank(), "history", "basic", {"history/plassey-1757"}, [],
                         TODAY, random.Random(0))
    assert got is None  # no other history+basic entry


def test_bank_miss_returns_none():
    assert draw_from_bank(_bank(), "economy", "basic", set(), [], TODAY, random.Random(0)) is None


def test_drafts_and_expired_are_excluded():
    bank = _bank()
    bank[0].status = "draft"  # the only history/basic entry is now a draft
    assert draw_from_bank(bank, "history", "basic", set(), [], TODAY, random.Random(0)) is None


def test_yield_weight_biases_frequency():
    # two eligible history/basic entries; the high-yield one should dominate over many draws
    bank = [
        _entry("history", "basic", "history/high", "Stem one about a thing.", yield_weight="high"),
        _entry("history", "basic", "history/low", "Different stem about another.", yield_weight="low"),
    ]
    rng = random.Random(42)
    picks = [draw_from_bank(bank, "history", "basic", set(), [], TODAY, rng).fact_key
             for _ in range(200)]
    assert picks.count("history/high") > picks.count("history/low")


def test_similar_stem_is_suppressed():
    bank = [
        _entry("history", "basic", "history/a", "Who was the 9th Prime Minister of India?"),
        _entry("history", "basic", "history/b", "What is the chemical symbol for gold?"),
    ]
    # recent question is shaped like history/a; it should be pushed away
    recent = ["Who was the 11th Prime Minister of India?"]
    rng = random.Random(1)
    picks = [draw_from_bank(bank, "history", "basic", set(), recent, TODAY, rng).fact_key
             for _ in range(50)]
    assert picks.count("history/b") > picks.count("history/a")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_bank_draw.py -v`
Expected: FAIL (old `draw_from_bank` signature has no `recent_stems`/`today`/`rng`).

- [ ] **Step 3: Write minimal implementation**

In `selection/selection.py`, add imports at the top (after the existing `from datetime import ...`):

```python
import difflib
import random

from selection.bank import is_drawable
from selection.bank_qa import normalize_stem
from selection.models import BankEntry, YIELD_WEIGHTS
```

(The file already imports `HistoryRecord, Question, DIFFICULTIES` from `selection.models`; keep that line and add the new `BankEntry, YIELD_WEIGHTS` import as shown -- duplicate `from selection.models import` lines are fine, or merge them.)

Replace the existing `draw_from_bank` function (the `for q in bank: ...` version) with:

```python
def draw_from_bank(bank: list[BankEntry], domain: str, difficulty: str,
                   used_fact_keys: set[str], recent_stems: list[str],
                   today: date, rng: random.Random) -> Optional[Question]:
    """Yield-weighted random pick among drawable, matching, unused entries, penalising
    candidates whose stem is similar to recently-asked stems. Returns the inner Question
    or None on a bank miss. `rng` makes it deterministic given a seed."""
    candidates = [
        e for e in bank
        if is_drawable(e, today)
        and e.question.domain == domain
        and e.question.difficulty == difficulty
        and e.question.fact_key not in used_fact_keys
    ]
    if not candidates:
        return None
    norm_recent = [normalize_stem(s) for s in recent_stems]
    weights: list[float] = []
    for e in candidates:
        base = YIELD_WEIGHTS[e.yield_weight]
        stem = normalize_stem(e.question.question)
        sim = max((difflib.SequenceMatcher(None, stem, r).ratio() for r in norm_recent),
                  default=0.0)
        weights.append(base * (1.0 - sim))
    if sum(weights) <= 0:  # all candidates fully penalised -> uniform fallback
        return rng.choice(candidates).question
    return rng.choices(candidates, weights=weights, k=1)[0].question
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_bank_draw.py -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add daily-gk-quiz/selection/selection.py daily-gk-quiz/tests/test_bank_draw.py
git commit -m "feat(gk-bank): yield-weighted random draw with anti-similarity penalty (kills list-order bias)"
```

---

### Task 8: `plan_today` integration

**Files:**
- Modify: `selection/planner.py` (bank type, pass recent_stems + rng)
- Modify: `tests/test_planner.py` (wrap bank fixtures in `BankEntry`, seed rng)

- [ ] **Step 1: Update the failing tests**

In `tests/test_planner.py`, update the imports and the two bank-using tests. Change the import line to:

```python
import random
from datetime import date
from selection.models import Question, HistoryRecord, BankEntry
from selection.planner import plan_today, DayPlan
```

Add a `BankEntry` helper after the existing `_q`:

```python
def _entry(domain, diff, fk):
    return BankEntry(question=_q(domain, diff, fk), static_class="permanent", source_tier=2,
                     yield_weight="high", status="verified", verified_date="2026-06-12")
```

Replace `test_plan_pulls_bank_candidate_when_static_match_exists` and
`test_current_affairs_never_pulls_from_bank` with:

```python
def test_plan_pulls_bank_candidate_when_static_match_exists():
    bank = [_entry("history", "basic", "history/plassey-1757")]
    plan = plan_today(history=[], bank=bank,
                      weights={"history": 100}, target_mix=MIX,
                      hooks=["h1"], ctas=["c1"], trick_hooks=[],
                      today=date(2026, 6, 10), window_days=120, rng=random.Random(0))
    assert plan.domain == "history" and plan.difficulty == "basic"
    assert plan.bank_candidate is not None
    assert plan.bank_candidate.fact_key == "history/plassey-1757"


def test_current_affairs_never_pulls_from_bank():
    bank = [_entry("current-affairs", "basic", "current-affairs/old-news")]
    plan = plan_today(history=[], bank=bank,
                      weights={"current-affairs": 100}, target_mix=MIX,
                      hooks=["h1"], ctas=["c1"], trick_hooks=[],
                      today=date(2026, 6, 10), window_days=120, rng=random.Random(0))
    assert plan.domain == "current-affairs"
    assert plan.bank_candidate is None  # CA is always generated live
```

(The other tests pass `bank=[]` and need no change. `test_plan_picks_domain_difficulty_and_recent_fact_keys` and `test_rotation_avoids_recently_used_hook_and_cta` stay as is -- `rng` defaults below make them valid.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_planner.py -v`
Expected: FAIL (`plan_today` has no `rng` kwarg / `draw_from_bank` gets wrong arg count).

- [ ] **Step 3: Write minimal implementation**

In `selection/planner.py`:

Update imports at the top:

```python
from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date
from typing import Optional

from selection.models import Question, HistoryRecord, BankEntry
from selection.selection import (
    pick_domain, pick_difficulty, draw_from_bank, pick_rotation, _recent,
    balance_answer_position,
)
```

Change the `plan_today` signature to take `bank: list[BankEntry]`, plus `rng` and `recent_window`:

```python
def plan_today(*, history: list[HistoryRecord], bank: list[BankEntry],
               weights: dict[str, float], target_mix: dict[str, float],
               hooks: list[str], ctas: list[str], trick_hooks: list[str],
               today: date, window_days: int = 120,
               rng: Optional[random.Random] = None, recent_window: int = 14) -> DayPlan:
    rng = rng or random.Random()
```

Replace the bank-draw block (currently `if domain != CURRENT_AFFAIRS: bank_candidate = draw_from_bank(bank, domain, difficulty, recent_fact_keys)`) with:

```python
    bank_candidate = None
    if domain != CURRENT_AFFAIRS:  # current affairs is always generated live
        recent_stems = [r.question.question for r in recent_records[-recent_window:]]
        bank_candidate = draw_from_bank(bank, domain, difficulty, recent_fact_keys,
                                        recent_stems, today, rng)
```

(`recent_records` is already computed earlier in the function; reuse it.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv\Scripts\python.exe -m pytest tests/test_planner.py tests/test_planner_render.py -v`
Expected: PASS. (`test_planner_render.py` uses `bank=[]`, so it is unaffected by the type change.)

- [ ] **Step 5: Run the FULL selection suite to catch any missed call site**

Run: `.venv\Scripts\python.exe -m pytest -q`
Expected: all PASS (every prior test + the new bank suites). If any test still constructs `draw_from_bank`/`plan_today`/`load_bank` with the old shapes, fix that test to the new signatures shown above.

- [ ] **Step 6: Commit**

```bash
git add daily-gk-quiz/selection/planner.py daily-gk-quiz/tests/test_planner.py
git commit -m "feat(gk-bank): plan_today draws from BankEntry bank with seeded rng + recent-stem variety"
```

---

### Task 9: Seed `state/question-bank.json` with verified anchor facts

**Files:**
- Create: `state/question-bank.json`
- Test: `tests/test_question_bank_seed.py` (Create)

**Context:** The seed is real verified content (research-derived), not code. Every entry below is a `BankEntry` dict with a nested `question`. The implementer transcribes the table into the JSON shape exactly; the test is the quality gate (every entry must pass `check_entry`, be `is_drawable`, and round-trip). The bank grows to thousands later via sub-project #2 -- this seed is the trustworthy starting set.

- [ ] **Step 1: Write the failing test**

Create `tests/test_question_bank_seed.py`:

```python
from datetime import date

from selection.store import Store
from selection.bank_qa import check_entry, find_duplicates
from selection.bank import is_drawable

SEED = "state/question-bank.json"
TODAY = date(2026, 6, 12)


def _bank():
    return Store("state/question-history.json", SEED).load_bank()


def test_seed_has_at_least_ten_entries():
    assert len(_bank()) >= 10


def test_every_seed_entry_passes_qa():
    for e in _bank():
        hard, _ = check_entry(e)
        assert hard == [], f"{e.question.fact_key}: {hard}"


def test_every_seed_entry_is_verified_and_drawable():
    for e in _bank():
        assert e.status == "verified", e.question.fact_key
        assert is_drawable(e, TODAY), e.question.fact_key


def test_seed_has_no_internal_duplicates():
    bank = _bank()
    for i, e in enumerate(bank):
        dups, _ = find_duplicates(e, bank[:i] + bank[i + 1:])
        assert not dups, f"{e.question.fact_key} duplicates {[d.question.fact_key for d in dups]}"


def test_no_current_affairs_in_seed():
    # the static bank must never contain the always-live current-affairs domain
    assert all(e.question.domain != "current-affairs" for e in _bank())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_question_bank_seed.py -v`
Expected: FAIL (`state/question-bank.json` missing or empty -> `< 10 entries`).

- [ ] **Step 3: Create the seed file**

Create `state/question-bank.json` as a JSON array. Each element has this exact shape (here is the first entry, fully worked -- replicate the structure for every row):

```json
[
  {
    "question": {
      "domain": "polity",
      "difficulty": "basic",
      "fact_key": "polity/article-21-right-to-life",
      "entity": "Article 21",
      "question": "Which Article of the Indian Constitution guarantees the Right to Life and Personal Liberty?",
      "answer": "Article 21",
      "distractors": ["Article 19", "Article 14", "Article 32"],
      "exam_relevance": ["SSC", "IBPS-SBI", "RRB"],
      "sources": ["https://www.constitutionofindia.net/articles/article-21-protection-of-life-and-personal-liberty/", "https://ncert.nic.in/textbook.php"],
      "explanation": "Article 21 guarantees that no person shall be deprived of life or personal liberty except by procedure established by law.",
      "mnemonic": null,
      "is_trick": false,
      "source_citation": "Constitution of India, Art. 21"
    },
    "static_class": "permanent",
    "source_tier": 2,
    "yield_weight": "high",
    "status": "verified",
    "verified_date": "2026-06-12",
    "review_due_date": null
  }
]
```

Add the following entries (transcribe each into the same shape; `exam_relevance` may be any non-empty subset of `["SSC","IBPS-SBI","RRB"]`; `mnemonic` null unless given; `is_trick` false; `status` "verified"; `verified_date` "2026-06-12"; `review_due_date` null for permanent, "2027-06-12" for slowly-changing). Every `sources` array must have >= 2 URLs.

| fact_key | domain | difficulty | question | answer | distractors | static_class | tier | yield | source_citation | sources |
|---|---|---|---|---|---|---|---|---|---|---|
| history/dandi-march-1930 | history | basic | In which year did Mahatma Gandhi begin the Dandi Salt March? | 1930 | [1920, 1942, 1857] | permanent | 2 | high | NCERT, Modern India | ["https://ncert.nic.in/textbook.php", "https://www.britannica.com/event/Salt-March"] |
| history/quit-india-1942 | history | intermediate | At which venue did Gandhi launch the Quit India Movement in 1942? | Gowalia Tank Maidan, Bombay | ["Sabarmati Ashram", "Red Fort, Delhi", "Jallianwala Bagh, Amritsar"] | permanent | 2 | medium | NCERT, Modern India | ["https://ncert.nic.in/textbook.php", "https://www.britannica.com/event/Quit-India-Movement"] |
| history/inc-founded-1885 | history | basic | In which year was the Indian National Congress founded? | 1885 | [1857, 1905, 1919] | permanent | 2 | high | NCERT, Modern India | ["https://ncert.nic.in/textbook.php", "https://www.britannica.com/topic/Indian-National-Congress"] |
| economy/rbi-founded-1935 | economy | basic | In which year was the Reserve Bank of India established? | 1935 | [1949, 1947, 1955] | permanent | 1 | high | RBI History, rbi.org.in | ["https://www.rbi.org.in/", "https://rbi.org.in/Scripts/briefhistory.aspx"] |
| economy/gst-2017 | economy | basic | In which year was the Goods and Services Tax (GST) implemented in India? | 2017 | [2014, 2016, 2019] | permanent | 1 | medium | PIB / GST Council | ["https://www.pib.gov.in/", "https://gstcouncil.gov.in/"] |
| geography/hirakud-longest-dam | geography | intermediate | On which river is the Hirakud Dam, the longest dam in India, built? | Mahanadi | ["Godavari", "Sutlej", "Narmada"] | permanent | 2 | medium | NCERT, Geography of India | ["https://ncert.nic.in/textbook.php", "https://www.britannica.com/place/Hirakud-Dam"] |
| geography/kanchenjunga-highest-india | geography | basic | What is the highest mountain peak located in India? | Kanchenjunga | ["Mount Everest", "Nanda Devi", "K2"] | permanent | 2 | medium | NCERT, Geography of India | ["https://ncert.nic.in/textbook.php", "https://www.britannica.com/place/Kanchenjunga"] |
| static-gk/bharatanatyam-tamil-nadu | static-gk | basic | The classical dance form Bharatanatyam originated in which Indian state? | Tamil Nadu | ["Kerala", "Odisha", "Andhra Pradesh"] | permanent | 1 | high | Ministry of Culture, indiaculture.gov.in | ["https://www.indiaculture.gov.in/dance", "https://www.sangeetnatak.gov.in/"] |
| static-gk/kathakali-kerala | static-gk | basic | The classical dance form Kathakali is associated with which Indian state? | Kerala | ["Tamil Nadu", "Manipur", "Assam"] | permanent | 1 | medium | Ministry of Culture, indiaculture.gov.in | ["https://www.indiaculture.gov.in/dance", "https://www.sangeetnatak.gov.in/"] |
| static-gk/wings-of-fire-kalam | static-gk | basic | Who is the author of the autobiography Wings of Fire? | A. P. J. Abdul Kalam | ["Jawaharlal Nehru", "Mahatma Gandhi", "Rabindranath Tagore"] | permanent | 3 | low | Wings of Fire (Universities Press) | ["https://en.wikipedia.org/wiki/Wings_of_Fire_(autobiography)", "https://www.britannica.com/biography/A-P-J-Abdul-Kalam"] |
| general-science/mitochondria-powerhouse | general-science | basic | Which cell organelle is known as the powerhouse of the cell? | Mitochondria | ["Nucleus", "Ribosome", "Chloroplast"] | permanent | 2 | high | NCERT Science, Class 9 | ["https://ncert.nic.in/textbook.php", "https://www.britannica.com/science/mitochondrion"] |
| general-science/gold-symbol-au | general-science | basic | What is the chemical symbol for gold? | Au | ["Ag", "Gd", "Go"] | permanent | 2 | medium | NCERT Science, Class 10 | ["https://ncert.nic.in/textbook.php", "https://www.britannica.com/science/gold-chemical-element"] |
| banking-financial-awareness/pmjdy-2014 | banking-financial-awareness | intermediate | In which year was the Pradhan Mantri Jan Dhan Yojana (PMJDY) launched? | 2014 | [2015, 2016, 2019] | permanent | 1 | medium | PIB / pmjdy.gov.in | ["https://www.pib.gov.in/", "https://pmjdy.gov.in/"] |
| sports-awards-misc/bharat-ratna-highest-civilian | sports-awards-misc | basic | Which is the highest civilian award of India? | Bharat Ratna | ["Padma Vibhushan", "Param Vir Chakra", "Padma Bhushan"] | permanent | 1 | medium | Ministry of Home Affairs, awards.gov.in | ["https://awards.gov.in/", "https://www.britannica.com/topic/Bharat-Ratna"] |
| polity/niti-aayog-2015 | polity | intermediate | NITI Aayog replaced which earlier body in 2015? | Planning Commission | ["Finance Commission", "Election Commission", "UPSC"] | permanent | 1 | medium | NITI Aayog, niti.gov.in | ["https://www.niti.gov.in/", "https://www.pib.gov.in/"] |

That is 15 entries + the worked first entry = 16 verified seeds (>= 10 required). All must be ASCII-quote-only JSON.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_question_bank_seed.py -v`
Expected: PASS (5 tests). If any entry fails QA (e.g. a non-distinct option or a missing source), fix that entry's data until green.

- [ ] **Step 5: Confirm the seed file is tracked (not gitignored), then commit**

Run: `git -C D:\Rewva\signal-lab check-ignore daily-gk-quiz/state/question-bank.json` (expected: no output = tracked).

```bash
git add daily-gk-quiz/state/question-bank.json daily-gk-quiz/tests/test_question_bank_seed.py
git commit -m "feat(gk-bank): seed question-bank.json with 16 verified anchor facts"
```

---

### Task 10: Thin operator CLI (`python -m selection.bank`)

**Files:**
- Modify: `selection/bank.py` (add `main` + `__main__` guard)
- Test: `tests/test_bank_cli.py` (Create)

- [ ] **Step 1: Write the failing test**

Create `tests/test_bank_cli.py`:

```python
import json

from selection.models import BankEntry, Question
from selection.bank import main


def _entry_dict(fk, status="draft"):
    q = Question("polity", "basic", fk, "X", "A specific stem about a topic here.", "a",
                 ["b", "c", "d"], ["SSC"], ["https://1", "https://2"],
                 explanation="e", source_citation="cite")
    e = BankEntry(question=q, static_class="permanent", source_tier=2,
                  yield_weight="high", status=status)
    return e.to_dict()


def _write_bank(path, entries):
    path.write_text(json.dumps(entries), encoding="utf-8")


def test_health_returns_zero(tmp_path, capsys):
    bank = tmp_path / "bank.json"
    _write_bank(bank, [_entry_dict("polity/a", status="verified")])
    rc = main(["--bank", str(bank), "--history", str(tmp_path / "h.json"), "health"])
    assert rc == 0
    assert "drawable" in capsys.readouterr().out.lower()


def test_verify_flips_status_and_persists(tmp_path):
    bank = tmp_path / "bank.json"
    _write_bank(bank, [_entry_dict("polity/a", status="draft")])
    rc = main(["--bank", str(bank), "--history", str(tmp_path / "h.json"),
               "verify", "polity/a"])
    assert rc == 0
    after = json.loads(bank.read_text(encoding="utf-8"))
    assert after[0]["status"] == "verified" and after[0]["verified_date"] is not None


def test_verify_unknown_fact_key_returns_one(tmp_path):
    bank = tmp_path / "bank.json"
    _write_bank(bank, [_entry_dict("polity/a")])
    rc = main(["--bank", str(bank), "--history", str(tmp_path / "h.json"),
               "verify", "polity/missing"])
    assert rc == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_bank_cli.py -v`
Expected: FAIL (`ImportError: cannot import name 'main'`).

- [ ] **Step 3: Write minimal implementation**

Append to `selection/bank.py` (add `import argparse`, `import sys` to the top imports):

```python
def main(argv=None) -> int:
    from selection.store import Store

    parser = argparse.ArgumentParser(prog="selection.bank")
    parser.add_argument("--bank", default="state/question-bank.json")
    parser.add_argument("--history", default="state/question-history.json")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("health")
    vp = sub.add_parser("verify")
    vp.add_argument("fact_key")
    args = parser.parse_args(argv)

    store = Store(args.history, args.bank)
    bank = store.load_bank()
    today = date.today()

    if args.cmd == "health":
        h = bank_health(bank, today)
        print(f"drawable cells: {dict(h['drawable'])}")
        print(f"drafts={h['drafts']} expired={h['expired']} retired={h['retired']}")
        print(f"low_stock: {h['low_stock']}")
        return 0

    if args.cmd == "verify":
        for i, e in enumerate(bank):
            if e.question.fact_key == args.fact_key:
                bank[i] = verify_entry(e, today)
                store.save_bank(bank)
                print(f"verified {args.fact_key}")
                return 0
        print(f"not found: {args.fact_key}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_bank_cli.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Run the FULL suite + commit**

Run: `.venv\Scripts\python.exe -m pytest -q`
Expected: all PASS (full daily-gk-quiz selection suite, no regressions).

```bash
git add daily-gk-quiz/selection/bank.py daily-gk-quiz/tests/test_bank_cli.py
git commit -m "feat(gk-bank): thin operator CLI -- bank health + verify"
```

---

## Self-Review notes (author)

- **Spec coverage:** SS2 BankEntry -> Task 1; SS3 QA gate -> Task 2; SS4 dedup -> Task 3; SS5
  maintenance (add/verify/retire/is_drawable) -> Task 4, bank_health -> Task 5; SS7 Store -> Task 6;
  SS6 draw rewrite -> Task 7; SS6 plan_today integration -> Task 8; SS8 seed -> Task 9; SS9 CLI ->
  Task 10; SS10 testing -> each task's tests. All covered.
- **Type consistency:** `draw_from_bank(bank, domain, difficulty, used_fact_keys, recent_stems,
  today, rng)` is identical in Task 7 (def), Task 8 (planner call), and all tests. `BankEntry`
  field order/names match across Tasks 1, 6, 7, 8, 9, 10. `bank_health` keys (`drawable`, `drafts`,
  `expired`, `retired`, `low_stock`) match between Task 5 def and Task 10 CLI usage.
- **Breakage covered:** every existing call site found via grep (`test_bank_draw.py`,
  `test_store.py`, `test_planner.py`, `planner.py`, `store.py`, `selection.py`) has an explicit
  update task; Task 8 Step 5 runs the whole suite as a backstop.
- **No placeholders:** every code + data step is concrete; the seed is a complete data table, not a
  "fill in later".
