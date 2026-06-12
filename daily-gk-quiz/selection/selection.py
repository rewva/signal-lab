from __future__ import annotations

import difflib
import random
from datetime import date, timedelta
from typing import Optional

from selection.bank import is_drawable
from selection.bank_qa import normalize_stem
from selection.models import HistoryRecord, Question, DIFFICULTIES
from selection.models import BankEntry, YIELD_WEIGHTS

def is_duplicate(fact_key: str, history: list[HistoryRecord],
                 today: date, window_days: int = 120) -> bool:
    cutoff = today - timedelta(days=window_days)
    for rec in history:
        if rec.question.fact_key == fact_key and date.fromisoformat(rec.date) >= cutoff:
            return True
    return False

def _recent(history: list[HistoryRecord], today: date, window_days: int) -> list[HistoryRecord]:
    cutoff = today - timedelta(days=window_days)
    return [r for r in history if date.fromisoformat(r.date) >= cutoff]

def recent_shares(values: list[str], universe) -> dict[str, float]:
    """Normalized frequency of each `universe` member among the in-universe values.
    Values not in `universe` are ignored entirely (not counted, not in the denominator)."""
    counts = {k: 0 for k in universe}
    in_universe = 0
    for v in values:
        if v in counts:
            counts[v] += 1
            in_universe += 1
    total = in_universe or 1
    return {k: counts[k] / total for k in counts}

def pick_domain(history: list[HistoryRecord], weights: dict[str, float],
                today: date, window_days: int = 120) -> str:
    targets = {k: w / sum(weights.values()) for k, w in weights.items()}
    seen = [r.question.domain for r in _recent(history, today, window_days)]
    shares = recent_shares(seen, weights.keys())
    deficits = {k: targets[k] - shares[k] for k in weights}
    return max(deficits, key=lambda k: (deficits[k], weights[k]))

def pick_difficulty(history: list[HistoryRecord], target_mix: dict[str, float],
                    today: date, window_days: int = 120) -> str:
    seen = [r.question.difficulty for r in _recent(history, today, window_days)]
    shares = recent_shares(seen, target_mix.keys())
    order = {d: len(DIFFICULTIES) - i for i, d in enumerate(DIFFICULTIES)}  # tie-break toward basic
    deficits = {k: target_mix[k] - shares[k] for k in target_mix}
    return max(deficits, key=lambda k: (deficits[k], order[k]))

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

def pick_rotation(pool: list[str], recent: list[str]) -> str:
    """Least-recently-used item in `pool`. `recent` is oldest-to-newest usage."""
    if not pool:
        raise ValueError("pick_rotation: pool must not be empty")
    if len(pool) == 1:
        return pool[0]
    def last_used(item: str) -> int:
        # higher index = used more recently; -1 = never used
        for i in range(len(recent) - 1, -1, -1):
            if recent[i] == item:
                return i
        return -1
    return min(pool, key=last_used)

POSITIONS = ("A", "B", "C", "D")

def balance_answer_position(history: list[HistoryRecord], today: date,
                            last_n: int = 30) -> str:
    """The A/B/C/D slot least used as the correct position over the last `last_n` posts.

    `today` is accepted for signature consistency with the other selectors (unused here:
    balancing is over the most recent posts, not a date window). Ties resolve A<B<C<D."""
    recent = [r.answer_position for r in history[-last_n:] if r.answer_position]
    counts = {p: recent.count(p) for p in POSITIONS}
    order = {p: i for i, p in enumerate(POSITIONS)}
    return min(POSITIONS, key=lambda p: (counts[p], order[p]))

def template_for(is_trick: bool) -> str:
    return "trick" if is_trick else "standard"
