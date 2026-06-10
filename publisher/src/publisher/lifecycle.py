r"""Job lifecycle state machine (pure logic, no I/O).

    SUBMITTED -> PENDING_APPROVAL -> APPROVED -> SCHEDULED -> POSTING -> POSTED
                                 \-> REJECTED               POSTING -> FAILED (after retries)
                                                            POSTING -> SCHEDULED (re-queue for retry)

Terminal states (POSTED / FAILED / REJECTED) have no outgoing transitions; recovering from
a terminal state means creating a new job, never mutating the old one.
"""

from __future__ import annotations

MAX_ATTEMPTS = 3  # retry up to 3 times, then mark FAILED + alert

TERMINAL = frozenset({"POSTED", "FAILED", "REJECTED"})

ALLOWED: dict[str, frozenset[str]] = {
    "SUBMITTED": frozenset({"PENDING_APPROVAL"}),
    "PENDING_APPROVAL": frozenset({"APPROVED", "REJECTED"}),
    "APPROVED": frozenset({"SCHEDULED"}),
    "SCHEDULED": frozenset({"POSTING"}),
    "POSTING": frozenset({"POSTED", "FAILED", "SCHEDULED"}),
    "POSTED": frozenset(),
    "FAILED": frozenset(),
    "REJECTED": frozenset(),
}


class InvalidTransition(Exception):
    """Raised when a status transition is not permitted by the state machine."""


def can_transition(src: str, dst: str) -> bool:
    return dst in ALLOWED.get(src, frozenset())


def validate_transition(src: str, dst: str) -> None:
    if not can_transition(src, dst):
        raise InvalidTransition(f"{src} -> {dst} is not a permitted transition")


def is_terminal(status: str) -> bool:
    return status in TERMINAL


def outcome_after_failure(attempts_made: int) -> str:
    """Given how many posting attempts have been made, decide the next status.

    Below the cap -> re-queue (SCHEDULED) for another attempt; at/above -> FAILED.
    """
    return "SCHEDULED" if attempts_made < MAX_ATTEMPTS else "FAILED"
