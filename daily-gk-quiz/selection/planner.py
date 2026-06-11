from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from selection.models import Question, HistoryRecord
from selection.selection import (
    pick_domain, pick_difficulty, draw_from_bank, pick_rotation, _recent,
    balance_answer_position,
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
    answer_position: str = "A"
    trick_hook: str = ""

def plan_today(*, history: list[HistoryRecord], bank: list[Question],
               weights: dict[str, float], target_mix: dict[str, float],
               hooks: list[str], ctas: list[str], trick_hooks: list[str],
               today: date, window_days: int = 120) -> DayPlan:
    domain = pick_domain(history, weights, today, window_days)
    difficulty = pick_difficulty(history, target_mix, today, window_days)
    recent_records = _recent(history, today, window_days)
    recent_fact_keys = {r.question.fact_key for r in recent_records}

    bank_candidate = None
    if domain != CURRENT_AFFAIRS:  # current affairs is always generated live
        bank_candidate = draw_from_bank(bank, domain, difficulty, recent_fact_keys)

    recent_hooks = [r.hook for r in recent_records if r.hook]
    recent_ctas = [r.cta for r in recent_records if r.cta]
    hook = pick_rotation(hooks, recent_hooks)
    cta = pick_rotation(ctas, recent_ctas)
    answer_position = balance_answer_position(history, today)
    recent_trick = [r.hook for r in recent_records if r.hook]
    trick_hook = pick_rotation(trick_hooks, recent_trick) if trick_hooks else ""
    return DayPlan(domain, difficulty, recent_fact_keys, bank_candidate, hook, cta,
                   answer_position=answer_position, trick_hook=trick_hook)
