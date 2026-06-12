from datetime import date

import pytest

from selection.models import BankEntry, Question
from selection.bank import add_entry, verify_entry, retire_entry, is_drawable, BankError


def _entry(fk="polity/a", static_class="permanent", **over):
    q = Question("polity", "basic", fk, "X", f"Stem for {fk} about something specific.",
                 "a", ["b", "c", "d"], ["SSC"], ["https://1", "https://2"],
                 explanation="e", source_citation="cite")
    return BankEntry(question=q, static_class=static_class, source_tier=2,
                     yield_weight=over.get("yield_weight", "high"))


TODAY = date(2026, 6, 12)


def test_add_entry_stamps_permanent_with_no_review_date():
    bank: list[BankEntry] = []
    stamped, warnings = add_entry(bank, _entry(), TODAY)
    assert stamped.status == "draft" and stamped.review_due_date is None
    assert bank == [stamped]


def test_add_entry_stamps_slowly_changing_plus_365():
    bank: list[BankEntry] = []
    stamped, _ = add_entry(bank, _entry(static_class="slowly-changing"), TODAY)
    assert stamped.review_due_date == "2027-06-12"


def test_add_entry_rejects_hard_qa_failure():
    bad = _entry()
    bad.question.explanation = "  "
    with pytest.raises(BankError):
        add_entry([], bad, TODAY)


def test_add_entry_rejects_duplicate():
    bank: list[BankEntry] = []
    add_entry(bank, _entry("polity/a"), TODAY)
    with pytest.raises(BankError):
        add_entry(bank, _entry("polity/a"), TODAY)


def test_verify_entry_flips_and_stamps():
    e = _entry(static_class="slowly-changing")
    v = verify_entry(e, TODAY)
    assert v.status == "verified" and v.verified_date == "2026-06-12"
    assert v.review_due_date == "2027-06-12"


def test_retire_entry():
    assert retire_entry(_entry()).status == "retired"


def test_is_drawable_rules():
    permanent = verify_entry(_entry(), TODAY)
    assert is_drawable(permanent, TODAY) is True
    assert is_drawable(_entry(), TODAY) is False  # draft, not verified
    expiring = verify_entry(_entry(static_class="slowly-changing"), TODAY)
    assert is_drawable(expiring, date(2027, 6, 12)) is True   # boundary == due date
    assert is_drawable(expiring, date(2027, 6, 13)) is False  # past due
    assert is_drawable(retire_entry(permanent), TODAY) is False


from selection.bank import bank_health


def test_bank_health_counts_and_low_stock():
    bank: list[BankEntry] = []
    # 1 drawable polity/basic
    add_entry(bank, _entry("polity/capital-of-india"), TODAY)
    bank[-1] = verify_entry(bank[-1], TODAY)
    # 1 draft (not drawable, counted as draft)
    add_entry(bank, _entry("polity/president-term-years"), TODAY)
    # 1 retired
    add_entry(bank, _entry("polity/rajya-sabha-total-seats"), TODAY)
    bank[-1] = retire_entry(verify_entry(bank[-1], TODAY))
    health = bank_health(bank, TODAY, low_stock=5)
    assert health["drawable"][("polity", "basic")] == 1
    assert health["drafts"] == 1
    assert health["retired"] == 1
    assert ("polity", "basic") in health["low_stock"]  # only 1 < 5
