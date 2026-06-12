from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

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
