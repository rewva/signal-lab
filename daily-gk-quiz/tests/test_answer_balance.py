from datetime import date
from selection.models import Question, HistoryRecord
from selection.selection import balance_answer_position, template_for

def _rec(pos, d):
    q = Question("polity", "basic", f"polity/x-{d}", "X", "q?", "a",
                 ["b", "c", "d"], ["SSC"], ["https://1", "https://2"])
    return HistoryRecord(d, q, answer_position=pos)

def test_empty_history_returns_A():
    assert balance_answer_position([], date(2026, 6, 10)) == "A"

def test_picks_least_used_position_over_last_30():
    # A used 3x, B 2x, C 2x, D 0x -> D is least used
    hist = ([_rec("A", f"2026-05-{d:02d}") for d in (1, 2, 3)]
            + [_rec("B", f"2026-05-{d:02d}") for d in (4, 5)]
            + [_rec("C", f"2026-05-{d:02d}") for d in (6, 7)])
    assert balance_answer_position(hist, date(2026, 6, 10)) == "D"

def test_only_counts_last_30_records():
    hist = [_rec("A", f"2026-04-{(d % 28) + 1:02d}") for d in range(31)]
    assert balance_answer_position(hist, date(2026, 6, 10)) in ("B", "C", "D")

def test_template_for_maps_is_trick():
    assert template_for(True) == "trick"
    assert template_for(False) == "standard"
