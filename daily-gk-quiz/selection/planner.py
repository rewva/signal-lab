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
