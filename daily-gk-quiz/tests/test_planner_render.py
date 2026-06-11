from datetime import date
from selection.planner import plan_today, DayPlan
from selection.models import Question, HistoryRecord

WEIGHTS = {"current-affairs": 30, "polity": 10}
MIX = {"basic": 0.5, "intermediate": 0.35, "advanced": 0.15}

def test_dayplan_has_answer_position_and_trick_hook():
    plan = plan_today(history=[], bank=[], weights=WEIGHTS, target_mix=MIX,
                      hooks=["h1"], ctas=["c1"], trick_hooks=["Common Exam Trap"],
                      today=date(2026, 6, 10), window_days=120)
    assert isinstance(plan, DayPlan)
    assert plan.answer_position == "A"            # empty history -> first slot
    assert plan.trick_hook == "Common Exam Trap"  # rotated from the pool


def _q(d):
    return Question("polity", "basic", f"polity/x-{d}", "X", "q?", "a",
                    ["b", "c", "d"], ["SSC"], ["https://1", "https://2"])


def test_trick_hook_rotates_away_from_recent():
    rec = HistoryRecord("2026-06-09", _q("1"), trick_hook="Common Exam Trap")
    plan = plan_today(history=[rec], bank=[], weights=WEIGHTS, target_mix=MIX,
                      hooks=["h1"], ctas=["c1"],
                      trick_hooks=["Common Exam Trap", "SSC Favourite Trap"],
                      today=date(2026, 6, 10), window_days=120)
    assert plan.trick_hook == "SSC Favourite Trap"   # avoids the recently-used one
