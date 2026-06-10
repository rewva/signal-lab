from datetime import date
from selection.models import Question, HistoryRecord
from selection.selection import is_duplicate

def _rec(fk, d):
    q = Question("history", "basic", fk, "X", "q?", "a",
                 ["b", "c", "d"], ["SSC"], ["https://1", "https://2"])
    return HistoryRecord(d, q)

def test_recent_fact_key_is_duplicate():
    hist = [_rec("history/plassey-1757", "2026-06-01")]
    assert is_duplicate("history/plassey-1757", hist, date(2026, 6, 10), window_days=120)

def test_fact_key_outside_window_is_not_duplicate():
    hist = [_rec("history/plassey-1757", "2026-01-01")]  # >120 days before
    assert not is_duplicate("history/plassey-1757", hist, date(2026, 6, 10), window_days=120)

def test_unseen_fact_key_is_not_duplicate():
    hist = [_rec("history/plassey-1757", "2026-06-01")]
    assert not is_duplicate("polity/article-21", hist, date(2026, 6, 10), window_days=120)
