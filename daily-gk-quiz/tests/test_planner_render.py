from datetime import date
from selection.planner import plan_today, DayPlan

WEIGHTS = {"current-affairs": 30, "polity": 10}
MIX = {"basic": 0.5, "intermediate": 0.35, "advanced": 0.15}

def test_dayplan_has_answer_position_and_trick_hook():
    plan = plan_today(history=[], bank=[], weights=WEIGHTS, target_mix=MIX,
                      hooks=["h1"], ctas=["c1"], trick_hooks=["Common Exam Trap"],
                      today=date(2026, 6, 10), window_days=120)
    assert isinstance(plan, DayPlan)
    assert plan.answer_position == "A"            # empty history -> first slot
    assert plan.trick_hook == "Common Exam Trap"  # rotated from the pool
