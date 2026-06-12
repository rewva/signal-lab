# Design: Question-bank foundation (trust machinery + unbiased draw)

**Date:** 2026-06-12
**Status:** Approved design (plan next -- no implementation in this phase)
**Owner:** sdevendran
**Relates to:** `docs/research/2026-06-12-static-question-bank-research.md` (the findings this
implements), `daily-gk-quiz/selection/` (the layer this extends in place), `SKILL.md` (bank prose
this makes concrete). This is **sub-project #1** of the question-bank build; the batch **generation
harness** (#2) and any further **draw/health tooling** are separate later specs that target this
contract.

---

## 1. What this is (and is not)

The selection layer already has a *bank concept*: `Store.load_bank/save_bank` read/write
`state/question-bank.json`, `draw_from_bank(domain, difficulty, used_fact_keys)` pulls a candidate,
and `plan_today` excludes `current-affairs` (always generated live). **What is missing** is the
*trust machinery* that makes a bank entry safe to publish at scale, plus an *unbiased pick order*.

This spec builds the foundation:
1. A **`BankEntry` wrapper** carrying lifecycle + trust metadata around the existing pure `Question`.
2. A **deterministic QA gate** (structural MCQ rules) + **stdlib dedup**.
3. **Bank maintenance** (add / verify / expiry / health) with a hard **static-vs-volatile** split.
4. A **principled draw strategy** (yield-weighted random + anti-similarity), replacing the current
   first-in-list match that causes alphabetical/position bias.
5. **Seed content**: ~30 research-anchor facts as verified entries.

**Out of scope (YAGNI):** the AI batch generator (#2); embeddings/ML dedup (stdlib `difflib`
suffices at a few thousand entries); a rich verification UI (a thin CLI only); changes to render or
publisher; current-affairs handling (already live, untouched).

---

## 2. Data model -- `BankEntry` wrapper (`selection/models.py`)

`Question` stays **unchanged** (it is shared by the bank, live current-affairs authoring, and
`HistoryRecord` -- bank-only fields would pollute those uses). A new wrapper holds bank concerns:

```python
@dataclass
class BankEntry:
    question: Question
    static_class: str          # "permanent" | "slowly-changing"
    source_tier: int           # 1 | 2 | 3  (from the research source map)
    yield_weight: str          # "high" | "medium" | "low"  (drives draw frequency)
    status: str = "draft"      # "draft" | "verified" | "retired"
    verified_date: str | None = None    # ISO date; set when flipped to verified
    review_due_date: str | None = None   # ISO date; None for permanent
```

- `to_dict` / `from_dict` nest the `Question` dict under a `"question"` key; round-trips losslessly.
- Module constants: `STATIC_CLASSES = ("permanent", "slowly-changing")`,
  `STATUSES = ("draft", "verified", "retired")`, `YIELD_WEIGHTS = {"high": 3, "medium": 2, "low": 1}`.
- `"current-adjacent"` is deliberately **not** a valid `static_class`: volatile facts (repo/CRR/SLR
  rates, current award winners, tiger-reserve counts, NH numbering) must never enter the static bank.
  They belong to the live current-affairs path. The QA gate (SS3) rejects any entry that names one.

---

## 3. Deterministic QA gate (`selection/bank_qa.py`, pure functions)

`check_entry(entry) -> QAResult` where `QAResult = (hard_errors: list[str], soft_warnings: list[str])`.
No I/O; fully unit-testable.

**HARD errors (entry is rejected -- cannot be added):**
- Options: exactly 4, all non-empty, all distinct (the 4 = correct answer + 3 distractors).
- The correct `answer` is non-empty and is one of the 4 options.
- `question`, `explanation`, `source_citation` are non-empty; `sources` is non-empty.
- No option text contains a banned phrase: "all of the above", "none of the above" (case-insensitive).
- `static_class` is in `STATIC_CLASSES` (not "current-adjacent" or anything else); `source_tier in
  {1,2,3}`; `yield_weight in YIELD_WEIGHTS`.

**SOFT warnings (allowed, surfaced for operator attention):**
- Correct answer length > 1.5x the average option length (the answer-length tell).
- A distractor contains an absolute term ("always", "never", "only", "all", "none").
- The stem is negatively phrased ("not", "except", "least") without capitalised emphasis.

Note: `Question.validate()` already enforces the required-field presence at the `Question` level; the
QA gate adds the *MCQ-quality* rules. The gate runs over a `BankEntry` so it can also check the
wrapper fields.

---

## 4. Dedup (`selection/bank_qa.py`, stdlib only -- no ML dependency)

`normalize_stem(text) -> str`: lowercase, strip punctuation, collapse whitespace.

`find_duplicates(candidate, bank) -> (exact_dups, near_dups)` using three signals:
1. **`fact_key`** exact match (already the upstream dedupe key).
2. **Normalized-stem** exact equality.
3. **`difflib.SequenceMatcher` ratio** on normalized stems:
   - ratio >= **0.87** -> treated as a **duplicate** (rejected by `add_entry`).
   - **0.80 <= ratio < 0.87** -> **near-duplicate**, flagged for operator review (added, but reported).

Brute-force pairwise over a few thousand entries is trivial and keeps the selection layer
dependency-free. (Embeddings can come later in #2 if the bank outgrows this.)

---

## 5. Bank maintenance (`selection/bank.py`)

Pure-ish helpers over a `list[BankEntry]` (I/O stays in `Store`):

- `add_entry(bank, entry, today) -> AddResult`: runs `check_entry` (reject on hard errors) and
  `find_duplicates` (reject on exact/near>=0.87). On pass, **stamps dates by `static_class`**
  (`permanent` -> `review_due_date = None`; `slowly-changing` -> `review_due_date = today + 365d`),
  leaves `status="draft"` (and `verified_date=None`), appends, returns the entry + any soft warnings /
  near-dup flags. Does not mutate on rejection.
- `verify_entry(entry, today) -> BankEntry`: flips `draft -> verified`, sets `verified_date = today`,
  and (re)stamps `review_due_date` from `static_class`. The operator's **accuracy gate #1** is this
  call.
- `retire_entry(entry) -> BankEntry`: flips to `retired` (kept for audit, never drawn).
- `is_drawable(entry, today) -> bool`: `status == "verified"` AND (`review_due_date is None` OR
  `today <= review_due_date`). Expired slowly-changing entries fall out of draws automatically until
  re-verified.
- `bank_health(bank, today) -> dict`: drawable counts per `(domain, difficulty)`, plus
  draft / expired / retired tallies and a `low_stock` list (domain/difficulty cells below a
  threshold) so the operator knows where to replenish.

---

## 6. Draw strategy (`selection/selection.py` -- `draw_from_bank` rewrite)

Replaces the current first-match (which pulls in file/alphabetical order and starves the tail).

`draw_from_bank(bank, domain, difficulty, used_fact_keys, recent_stems, today, rng) -> Optional[Question]`:

1. **Candidates** = entries where `is_drawable(e, today)` AND `e.question.domain == domain` AND
   `e.question.difficulty == difficulty` AND `e.question.fact_key not in used_fact_keys`.
2. **Base weight** = `YIELD_WEIGHTS[e.yield_weight]` (high=3, medium=2, low=1).
3. **Anti-similarity penalty**: `sim = max(difflib ratio(normalize_stem(e.stem),
   normalize_stem(s)) for s in recent_stems)` (0 if `recent_stems` empty); `weight *= (1 - sim)`. A
   "Who is the Nth <office> of India" candidate scores high `sim` against a recently-asked one of the
   same shape, so its weight collapses toward zero while that shape is fresh.
4. **Weighted-random choice** among candidates using an injected `rng: random.Random` (so a seed
   makes it deterministic and testable). Zero-weight candidates are excluded; if all candidates are
   penalised to ~0, fall back to uniform among candidates so a draw still happens.
5. Returns the inner `Question` (so `DayPlan.bank_candidate` / render are unchanged). `None` on a bank
   miss (planner then drafts live, exactly as today).

**`plan_today` change:** `bank` param becomes `list[BankEntry]`; it passes
`recent_stems = [r.question.question for r in recent_records[-K:]]` (K ~ 14) and an `rng` into
`draw_from_bank`. Everything downstream of `bank_candidate` is unchanged. `rng` is injected from the
caller (SKILL/build) -- seeded from the date for reproducible daily runs, or a fresh `Random()`.

**Why this fixes both reported problems:** (1) value (yield) drives frequency and the pick is
random, so file position / alphabetical order is irrelevant and the tail still surfaces; (2) the
stem-similarity penalty pushes same-shape questions apart across days, so consecutive questions feel
unrelated. Domain spread is already handled upstream by `pick_domain`'s weighted deficit balancing.

---

## 7. Persistence + integration (minimal, surgical)

- `Store.load_bank() -> list[BankEntry]` / `save_bank(list[BankEntry])` -- swap `Question` for
  `BankEntry` (the existing `question-bank.json` is empty, so no migration). Atomic-write helper
  unchanged; `ensure_ascii=True` stays (ASCII-only rule).
- `draw_from_bank` and `plan_today` signatures as in SS6.
- No other call sites change: `assemble.py` / `build.py` / render / publisher consume the drawn
  `Question` exactly as before.

---

## 8. Seed content (`state/question-bank.json`)

Populate with the **~30 high-confidence research-anchor facts** (8 classical dances -> states;
Gandhian chronology -- Champaran 1917, Non-Coop 1920-22, Dandi 1930, Quit India 1942; RBI founded
1935 / nationalised 1949 / first Indian governor C.D. Deshmukh; PMJDY 2014, PM-KISAN 2019; Article
21 = Right to Life; Hirakud = longest dam; etc.). Each as a `BankEntry` with `status="verified"`,
`verified_date` set, correct `static_class` (mostly "permanent"; e.g. scheme/anniversary facts that
could shift are "slowly-changing"), `source_tier`, `yield_weight`, and real `source_citation` +
`sources` (prefer the deep-linkable Tier-1/2 sources: constitutionofindia.net, ncert.nic.in,
ich/whc.unesco.org, pib.gov.in). These double as test fixtures and give a small, immediately drawable
bank. Each seed fact must pass the QA gate.

---

## 9. Operator surface (thin CLI -- `python -m selection.bank`)

- `health` -> prints `bank_health` (drawable per domain/difficulty, drafts, expired, low-stock).
- `verify <fact_key>` -> loads the bank, `verify_entry` the matching draft, saves.
- (Listing drafts / bulk verification is part of the generator sub-project #2, not here.)

The CLI is glue over the SS5 functions; the pure logic is what gets the heavy tests.

---

## 10. Testing (TDD throughout)

- **`bank_qa.check_entry`:** one test per HARD rule (4-distinct-options, answer-in-options,
  required-fields, banned-phrase, enum validity) and per SOFT rule (answer-length tell, absolute
  term, negative stem).
- **`bank_qa` dedup:** exact `fact_key`, normalized-stem exact, and the difflib bands (>=0.87
  reject, 0.80-0.87 flag, <0.80 clean).
- **`bank.add_entry`:** rejects on hard error / duplicate; on pass stamps dates per `static_class`
  (permanent -> None, slowly-changing -> +365d) and sets `status="draft"`.
- **`bank.verify_entry` / `is_drawable`:** status transitions; expiry boundary (today ==
  review_due_date drawable, +1 day not); permanent never expires.
- **`bank_health`:** correct per-cell counts and low-stock detection.
- **`draw_from_bank`:** excludes drafts/expired/retired/used fact_keys; with a seeded `rng`,
  yield-weighting biases frequency over many draws; a stem similar to `recent_stems` is suppressed;
  empty candidate set -> `None`; all-penalised -> uniform fallback still returns one.
- **`BankEntry` round-trip** (`to_dict`/`from_dict`) and a **load-the-seed-file** smoke test (all
  seed entries pass the QA gate and are drawable).

---

## 11. Open questions / locked defaults

Locked this round: dedup via stdlib `difflib` (no ML dep); slowly-changing re-verify cadence = 365
days; seed the ~30 anchor facts now as verified; `yield_weight` numeric map high=3/med=2/low=1 (a
tunable constant). Tunable constants fixed in the plan and revisited once real behaviour is observed:
the dedup difflib bands (0.87 reject / 0.80 flag), the draw's `recent_stems` window K (~14), and the
draw penalty curve (`weight *= (1 - sim)`, continuous -- no hard cutoff).
