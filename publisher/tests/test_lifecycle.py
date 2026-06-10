"""Tests for the job lifecycle state machine (pure transition logic)."""

import pytest

from publisher.lifecycle import (
    MAX_ATTEMPTS,
    InvalidTransition,
    can_transition,
    is_terminal,
    outcome_after_failure,
    validate_transition,
)


@pytest.mark.parametrize("src,dst", [
    ("SUBMITTED", "PENDING_APPROVAL"),
    ("PENDING_APPROVAL", "APPROVED"),
    ("PENDING_APPROVAL", "REJECTED"),
    ("APPROVED", "SCHEDULED"),
    ("SCHEDULED", "POSTING"),
    ("POSTING", "POSTED"),
    ("POSTING", "FAILED"),
    ("POSTING", "SCHEDULED"),  # re-queue for retry
])
def test_allowed_transitions(src, dst):
    assert can_transition(src, dst) is True


@pytest.mark.parametrize("src,dst", [
    ("SUBMITTED", "POSTED"),        # cannot skip approval
    ("PENDING_APPROVAL", "POSTING"),
    ("APPROVED", "POSTED"),
    ("POSTED", "POSTING"),          # terminal, no exit
    ("FAILED", "SCHEDULED"),        # terminal, no exit (a NEW job is required)
    ("REJECTED", "APPROVED"),
])
def test_disallowed_transitions(src, dst):
    assert can_transition(src, dst) is False


def test_validate_transition_passes_silently_when_allowed():
    validate_transition("APPROVED", "SCHEDULED")  # must not raise


def test_validate_transition_raises_when_disallowed():
    with pytest.raises(InvalidTransition):
        validate_transition("POSTED", "POSTING")


@pytest.mark.parametrize("status", ["POSTED", "FAILED", "REJECTED"])
def test_terminal_statuses(status):
    assert is_terminal(status) is True


@pytest.mark.parametrize("status", ["SUBMITTED", "PENDING_APPROVAL", "APPROVED",
                                    "SCHEDULED", "POSTING"])
def test_non_terminal_statuses(status):
    assert is_terminal(status) is False


def test_failure_before_max_attempts_requeues():
    # one or two attempts made so far -> retry by going back to SCHEDULED
    assert outcome_after_failure(1) == "SCHEDULED"
    assert outcome_after_failure(MAX_ATTEMPTS - 1) == "SCHEDULED"


def test_failure_at_max_attempts_is_terminal():
    assert outcome_after_failure(MAX_ATTEMPTS) == "FAILED"


def test_max_attempts_is_three():
    assert MAX_ATTEMPTS == 3
