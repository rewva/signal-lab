from datetime import date
from selection.models import Question, HistoryRecord
from selection.selection import pick_domain, recent_shares

def _rec(domain, d):
    q = Question(domain, "basic", f"{domain}/x-{d}", "X", "q?", "a",
                 ["b", "c", "d"], ["SSC"], ["https://1", "https://2"])
    return HistoryRecord(d, q)

WEIGHTS = {"current-affairs": 30, "general-science": 18, "static-gk": 12}

def test_empty_history_picks_highest_weight():
    assert pick_domain([], WEIGHTS, date(2026, 6, 10), window_days=120) == "current-affairs"

def test_picks_domain_furthest_below_its_weight():
    hist = [_rec("current-affairs", "2026-06-08"), _rec("current-affairs", "2026-06-09")]
    assert pick_domain(hist, WEIGHTS, date(2026, 6, 10), window_days=120) == "general-science"

def test_ignores_history_outside_window():
    hist = [_rec("current-affairs", "2025-01-01")]  # stale, ignored
    assert pick_domain(hist, WEIGHTS, date(2026, 6, 10), window_days=120) == "current-affairs"

def test_recent_shares_ignores_out_of_universe_values():
    shares = recent_shares(["a", "a", "unknown"], ["a", "b"])
    assert shares["a"] == 1.0
    assert shares["b"] == 0.0
