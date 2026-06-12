from datetime import date

from selection.store import Store
from selection.bank_qa import check_entry, find_duplicates
from selection.bank import is_drawable

SEED = "state/question-bank.json"
TODAY = date(2026, 6, 12)


def _bank():
    return Store("state/question-history.json", SEED).load_bank()


def test_seed_has_at_least_ten_entries():
    assert len(_bank()) >= 10


def test_every_seed_entry_passes_qa():
    for e in _bank():
        hard, _ = check_entry(e)
        assert hard == [], f"{e.question.fact_key}: {hard}"


def test_every_seed_entry_is_verified_and_drawable():
    for e in _bank():
        assert e.status == "verified", e.question.fact_key
        assert is_drawable(e, TODAY), e.question.fact_key


def test_seed_has_no_internal_duplicates():
    bank = _bank()
    for i, e in enumerate(bank):
        dups, _ = find_duplicates(e, bank[:i] + bank[i + 1:])
        assert not dups, f"{e.question.fact_key} duplicates {[d.question.fact_key for d in dups]}"


def test_no_current_affairs_in_seed():
    assert all(e.question.domain != "current-affairs" for e in _bank())
