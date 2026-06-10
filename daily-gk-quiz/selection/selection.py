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
