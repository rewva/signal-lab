from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta
from typing import Optional

from selection.bank_qa import check_entry, find_duplicates
from selection.models import BankEntry

REVIEW_DAYS = 365


class BankError(ValueError):
    """Raised when an entry fails QA or is a duplicate at add time."""


def _review_due(static_class: str, today: date) -> Optional[str]:
    if static_class == "slowly-changing":
        return (today + timedelta(days=REVIEW_DAYS)).isoformat()
    return None  # permanent never expires


def add_entry(bank: list[BankEntry], entry: BankEntry, today: date) -> tuple[BankEntry, list[str]]:
    """Validate + dedup, then append a draft (stamped by static_class). Mutates `bank` on success.
    Returns (stamped_entry, warnings). Raises BankError on hard QA failure or duplicate."""
    hard, soft = check_entry(entry)
    if hard:
        raise BankError("; ".join(hard))
    dups, near = find_duplicates(entry, bank)
    if dups:
        raise BankError(f"duplicate of {[e.question.fact_key for e in dups]}")
    stamped = replace(entry, status="draft", verified_date=None,
                      review_due_date=_review_due(entry.static_class, today))
    bank.append(stamped)
    warnings = list(soft)
    if near:
        warnings.append(f"near-duplicate of {[e.question.fact_key for e in near]}")
    return stamped, warnings


def verify_entry(entry: BankEntry, today: date) -> BankEntry:
    """Flip draft -> verified, stamp verified_date and review_due_date. Returns a new entry."""
    return replace(entry, status="verified", verified_date=today.isoformat(),
                   review_due_date=_review_due(entry.static_class, today))


def retire_entry(entry: BankEntry) -> BankEntry:
    return replace(entry, status="retired")


def is_drawable(entry: BankEntry, today: date) -> bool:
    if entry.status != "verified":
        return False
    if entry.review_due_date is None:
        return True
    return today <= date.fromisoformat(entry.review_due_date)
