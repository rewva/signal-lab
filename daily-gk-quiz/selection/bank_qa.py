from __future__ import annotations

import difflib
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
