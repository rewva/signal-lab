from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from selection.models import HistoryRecord, Question

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

def pick_difficulty(history: list[HistoryRecord], target_mix: dict[str, float],
                    today: date, window_days: int = 120) -> str:
    seen = [r.question.difficulty for r in _recent(history, today, window_days)]
    shares = recent_shares(seen, target_mix.keys())
    order = {"basic": 3, "intermediate": 2, "advanced": 1}  # tie-break toward basic
    deficits = {k: target_mix[k] - shares[k] for k in target_mix}
    return max(deficits, key=lambda k: (deficits[k], order[k]))

def draw_from_bank(bank: list[Question], domain: str, difficulty: str,
                   used_fact_keys: set[str]) -> Optional[Question]:
    for q in bank:
        if (q.domain == domain and q.difficulty == difficulty
                and q.fact_key not in used_fact_keys):
            return q
    return None

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
