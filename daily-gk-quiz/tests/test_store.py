from selection.models import Question, HistoryRecord, BankEntry
from selection.store import Store

def _q(fk="history/x"):
    return Question("history", "basic", fk, "X", "q?", "a",
                    ["b", "c", "d"], ["SSC"], ["https://1", "https://2"])

def _entry(fk):
    q = _q(fk)
    return BankEntry(question=q, static_class="permanent", source_tier=2,
                     yield_weight="high", status="verified", verified_date="2026-06-12")


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
    s.save_bank([_entry("history/a"), _entry("history/b")])
    loaded = s.load_bank()
    assert [e.question.fact_key for e in loaded] == ["history/a", "history/b"]
    assert all(isinstance(e, BankEntry) for e in loaded)

def test_append_is_atomic_no_tmp_left(tmp_path):
    s = Store(tmp_path / "hist.json", tmp_path / "bank.json")
    s.append_history(HistoryRecord("2026-06-10", _q()))
    assert not (tmp_path / "hist.json.tmp").exists()
