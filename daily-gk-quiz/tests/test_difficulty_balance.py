from datetime import date
from selection.models import Question, HistoryRecord
from selection.selection import pick_difficulty

DEFAULT_MIX = {"basic": 0.50, "intermediate": 0.35, "advanced": 0.15}

def _rec(diff, d):
    q = Question("history", diff, f"history/x-{d}", "X", "q?", "a",
                 ["b", "c", "d"], ["SSC"], ["https://1", "https://2"])
    return HistoryRecord(d, q)

def test_empty_history_picks_basic():
    assert pick_difficulty([], DEFAULT_MIX, date(2026, 6, 10), window_days=120) == "basic"

def test_picks_level_furthest_below_target():
    # all-basic recent history -> intermediate (target 0.35, share 0) is the largest deficit,
    # ahead of advanced (target 0.15)
    hist = [_rec("basic", f"2026-06-0{n}") for n in range(1, 6)]
    assert pick_difficulty(hist, DEFAULT_MIX, date(2026, 6, 10), window_days=120) == "intermediate"
