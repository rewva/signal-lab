from datetime import date
from selection.models import Question, HistoryRecord
from selection.planner import plan_today, DayPlan

WEIGHTS = {"current-affairs": 30, "general-science": 18, "static-gk": 12, "history": 10}
MIX = {"basic": 0.50, "intermediate": 0.35, "advanced": 0.15}

def _q(domain, diff, fk):
    return Question(domain, diff, fk, "X", "q?", "a",
                    ["b", "c", "d"], ["SSC"], ["https://1", "https://2"])

def test_plan_picks_domain_difficulty_and_recent_fact_keys():
    plan = plan_today(history=[], bank=[], weights=WEIGHTS, target_mix=MIX,
                      hooks=["h1", "h2"], ctas=["c1", "c2"], trick_hooks=[],
                      today=date(2026, 6, 10), window_days=120)
    assert isinstance(plan, DayPlan)
    assert plan.domain == "current-affairs"   # highest weight, empty history
    assert plan.difficulty == "basic"          # empty history
    assert plan.recent_fact_keys == set()
    assert plan.hook == "h1" and plan.cta == "c1"
    assert plan.bank_candidate is None         # empty bank -> live generation

def test_plan_pulls_bank_candidate_when_static_match_exists():
    bank = [_q("history", "basic", "history/plassey-1757")]
    plan = plan_today(history=[], bank=bank,
                      weights={"history": 100}, target_mix=MIX,
                      hooks=["h1"], ctas=["c1"], trick_hooks=[],
                      today=date(2026, 6, 10), window_days=120)
    assert plan.domain == "history" and plan.difficulty == "basic"
    assert plan.bank_candidate is not None
    assert plan.bank_candidate.fact_key == "history/plassey-1757"

def test_current_affairs_never_pulls_from_bank():
    bank = [_q("current-affairs", "basic", "current-affairs/old-news")]
    plan = plan_today(history=[], bank=bank,
                      weights={"current-affairs": 100}, target_mix=MIX,
                      hooks=["h1"], ctas=["c1"], trick_hooks=[],
                      today=date(2026, 6, 10), window_days=120)
    assert plan.domain == "current-affairs"
    assert plan.bank_candidate is None  # CA is always generated live

def test_rotation_avoids_recently_used_hook_and_cta():
    rec = HistoryRecord("2026-06-09", _q("history", "basic", "history/x"),
                        hook="h1", cta="c1")
    plan = plan_today(history=[rec], bank=[], weights=WEIGHTS, target_mix=MIX,
                      hooks=["h1", "h2"], ctas=["c1", "c2"], trick_hooks=[],
                      today=date(2026, 6, 10), window_days=120)
    assert plan.hook == "h2" and plan.cta == "c2"
