from __future__ import annotations

import argparse
import sys
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


def bank_health(bank: list[BankEntry], today: date, low_stock: int = 5) -> dict:
    """Drawable counts per (domain, difficulty) + draft/expired/retired tallies + low-stock cells."""
    drawable: dict[tuple[str, str], int] = {}
    drafts = expired = retired = 0
    for e in bank:
        if e.status == "retired":
            retired += 1
        elif e.status == "draft":
            drafts += 1
        elif is_drawable(e, today):
            key = (e.question.domain, e.question.difficulty)
            drawable[key] = drawable.get(key, 0) + 1
        else:  # verified but past review_due_date
            expired += 1
    low = [k for k, n in drawable.items() if n < low_stock]
    return {"drawable": drawable, "drafts": drafts, "expired": expired,
            "retired": retired, "low_stock": low}


def main(argv=None) -> int:
    from selection.store import Store

    parser = argparse.ArgumentParser(prog="selection.bank")
    parser.add_argument("--bank", default="state/question-bank.json")
    parser.add_argument("--history", default="state/question-history.json")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("health")
    vp = sub.add_parser("verify")
    vp.add_argument("fact_key")
    sub.add_parser("drafts")
    args = parser.parse_args(argv)

    store = Store(args.history, args.bank)
    bank = store.load_bank()
    today = date.today()

    if args.cmd == "health":
        h = bank_health(bank, today)
        print(f"drawable cells: {dict(h['drawable'])}")
        print(f"drafts={h['drafts']} expired={h['expired']} retired={h['retired']}")
        print(f"low_stock: {h['low_stock']}")
        return 0

    if args.cmd == "verify":
        for i, e in enumerate(bank):
            if e.question.fact_key == args.fact_key:
                bank[i] = verify_entry(e, today)
                store.save_bank(bank)
                print(f"verified {args.fact_key}")
                return 0
        print(f"not found: {args.fact_key}", file=sys.stderr)
        return 1

    if args.cmd == "drafts":
        for e in bank:
            if e.status == "draft":
                print(f"{e.question.fact_key}\t{e.question.question}")
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
