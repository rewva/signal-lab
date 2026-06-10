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
