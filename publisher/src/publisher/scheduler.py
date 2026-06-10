"""Scheduling logic (pure functions + value objects).

The live APScheduler job wakes every 60s and runs ``select_due`` over the SCHEDULED jobs;
``next_free_slot`` picks the next per-account posting window not already occupied within a
+/-30min buffer. Both are pure so they unit-test without a clock or a scheduler thread.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from typing import Optional

from publisher.models import Job

HORIZON_DAYS = 14  # how far ahead to look for a free posting slot
DEFAULT_BUFFER_MINUTES = 30


@dataclass(frozen=True)
class PostingWindow:
    time_slot: str  # "HH:MM"
    days_of_week: list[int] = field(default_factory=list)  # 0=Mon .. 6=Sun (Python weekday)

    @property
    def parsed_time(self) -> time:
        hh, mm = self.time_slot.split(":")
        return time(int(hh), int(mm))


def select_due(jobs: list[Job], now: datetime) -> list[Job]:
    """Jobs that are SCHEDULED with scheduled_for at or before now."""
    due = []
    for job in jobs:
        if job.status != "SCHEDULED" or not job.scheduled_for:
            continue
        if datetime.fromisoformat(job.scheduled_for) <= now:
            due.append(job)
    return due


def next_free_slot(
    windows: list[PostingWindow],
    now: datetime,
    occupied: list[datetime],
    buffer_minutes: int = DEFAULT_BUFFER_MINUTES,
) -> Optional[datetime]:
    """Earliest future window datetime not within +/-buffer of any occupied time."""
    if not windows:
        return None
    buffer = timedelta(minutes=buffer_minutes)
    candidates: list[datetime] = []
    for day_offset in range(HORIZON_DAYS):
        day = now.date() + timedelta(days=day_offset)
        for window in windows:
            if day.weekday() not in window.days_of_week:
                continue
            slot = datetime.combine(day, window.parsed_time, tzinfo=now.tzinfo)
            if slot > now:
                candidates.append(slot)
    for slot in sorted(candidates):
        if all(abs(slot - occ) >= buffer for occ in occupied):
            return slot
    return None
