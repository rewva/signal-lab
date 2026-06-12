from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from selection.bank import BankError, add_entry
from selection.models import BankEntry


@dataclass
class IngestReport:
    accepted: list[str] = field(default_factory=list)              # fact_keys
    rejected: list[tuple[str, str]] = field(default_factory=list)  # (fact_key, reason)
    warnings: list[tuple[str, list[str]]] = field(default_factory=list)  # (fact_key, warnings)


def ingest_batch(bank: list[BankEntry], drafts: list[BankEntry], today: date) -> IngestReport:
    """Validate + add each draft through the single QA+dedup path (add_entry). Mutates `bank`,
    appending only accepted drafts. Returns a per-item report. add_entry owns check_entry +
    find_duplicates, so we do NOT call check_entry separately here."""
    report = IngestReport()
    for entry in drafts:
        fk = entry.question.fact_key
        try:
            entry.question.validate()  # enforces >= 2 sources, 3 distractors, required fields
        except ValueError as exc:
            report.rejected.append((fk, str(exc)))
            continue
        try:
            _stamped, warnings = add_entry(bank, entry, today)
        except BankError as exc:
            report.rejected.append((fk, str(exc)))
            continue
        report.accepted.append(fk)
        if warnings:
            report.warnings.append((fk, warnings))
    return report


def main(argv=None) -> int:
    from selection.store import Store

    parser = argparse.ArgumentParser(prog="selection.ingest")
    parser.add_argument("--batch", required=True)
    parser.add_argument("--bank", default="state/question-bank.json")
    parser.add_argument("--history", default="state/question-history.json")  # unused by ingest; required to construct Store
    args = parser.parse_args(argv)

    raw = json.loads(Path(args.batch).read_text(encoding="utf-8"))
    drafts = [BankEntry.from_dict(d) for d in raw]

    store = Store(args.history, args.bank)
    bank = store.load_bank()
    report = ingest_batch(bank, drafts, date.today())
    store.save_bank(bank)

    for fk in report.accepted:
        print(f"ACCEPT {fk}")
    for fk, warns in report.warnings:
        print(f"  WARN {fk}: {warns}")
    for fk, reason in report.rejected:
        print(f"REJECT {fk}: {reason}")
    print(f"accepted={len(report.accepted)} rejected={len(report.rejected)}")
    return 0 if report.accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
