from selection.models import Question, HistoryRecord
from selection.store import Store

def _q(fk="history/x"):
    return Question("history", "basic", fk, "X", "q?", "a",
                    ["b", "c", "d"], ["SSC"], ["https://1", "https://2"])

def test_load_missing_files_returns_empty(tmp_path):
    s = Store(tmp_path / "hist.json", tmp_path / "bank.json")
    assert s.load_history() == []
    assert s.load_bank() == []

def test_append_history_persists_and_reloads(tmp_path):
    s = Store(tmp_path / "hist.json", tmp_path / "bank.json")
    s.append_history(HistoryRecord("2026-06-10", _q()))
    again = Store(tmp_path / "hist.json", tmp_path / "bank.json")
    recs = again.load_history()
    assert len(recs) == 1 and recs[0].date == "2026-06-10"

def test_save_bank_roundtrips(tmp_path):
    s = Store(tmp_path / "hist.json", tmp_path / "bank.json")
    s.save_bank([_q("history/a"), _q("history/b")])
    assert [q.fact_key for q in s.load_bank()] == ["history/a", "history/b"]

def test_append_is_atomic_no_tmp_left(tmp_path):
    s = Store(tmp_path / "hist.json", tmp_path / "bank.json")
    s.append_history(HistoryRecord("2026-06-10", _q()))
    assert not (tmp_path / "hist.json.tmp").exists()
