"""Tests for scheduler logic: due-job selection and next-free-slot picking (pure)."""

from datetime import datetime, timedelta, timezone

from publisher.models import Job
from publisher.scheduler import PostingWindow, next_free_slot, select_due

UTC = timezone.utc
ALL_DAYS = [0, 1, 2, 3, 4, 5, 6]


def _job(status, scheduled_for):
    return Job(channel_id="c", video_path="v", title="t", status=status,
               scheduled_for=scheduled_for, id=1)


# --- select_due -------------------------------------------------------------

def test_select_due_includes_scheduled_in_the_past():
    now = datetime(2026, 6, 8, 12, 0, tzinfo=UTC)
    jobs = [_job("SCHEDULED", (now - timedelta(minutes=1)).isoformat())]
    assert len(select_due(jobs, now)) == 1


def test_select_due_excludes_future_scheduled():
    now = datetime(2026, 6, 8, 12, 0, tzinfo=UTC)
    jobs = [_job("SCHEDULED", (now + timedelta(minutes=1)).isoformat())]
    assert select_due(jobs, now) == []


def test_select_due_excludes_non_scheduled_status():
    now = datetime(2026, 6, 8, 12, 0, tzinfo=UTC)
    jobs = [_job("APPROVED", (now - timedelta(hours=1)).isoformat())]
    assert select_due(jobs, now) == []


def test_select_due_ignores_jobs_without_scheduled_for():
    now = datetime(2026, 6, 8, 12, 0, tzinfo=UTC)
    assert select_due([_job("SCHEDULED", None)], now) == []


# --- next_free_slot ---------------------------------------------------------

def test_picks_todays_window_when_still_upcoming():
    now = datetime(2026, 6, 8, 8, 0, tzinfo=UTC)
    windows = [PostingWindow(time_slot="09:00", days_of_week=ALL_DAYS)]
    assert next_free_slot(windows, now, occupied=[]) == datetime(2026, 6, 8, 9, 0, tzinfo=UTC)


def test_rolls_to_next_day_when_todays_slot_passed():
    now = datetime(2026, 6, 8, 10, 0, tzinfo=UTC)
    windows = [PostingWindow(time_slot="09:00", days_of_week=ALL_DAYS)]
    assert next_free_slot(windows, now, occupied=[]) == datetime(2026, 6, 9, 9, 0, tzinfo=UTC)


def test_respects_days_of_week():
    now = datetime(2026, 6, 8, 8, 0, tzinfo=UTC)
    tomorrow_weekday = (now.weekday() + 1) % 7
    windows = [PostingWindow(time_slot="09:00", days_of_week=[tomorrow_weekday])]
    assert next_free_slot(windows, now, occupied=[]) == datetime(2026, 6, 9, 9, 0, tzinfo=UTC)


def test_picks_earliest_of_multiple_windows():
    now = datetime(2026, 6, 8, 8, 0, tzinfo=UTC)
    windows = [
        PostingWindow(time_slot="12:00", days_of_week=ALL_DAYS),
        PostingWindow(time_slot="09:00", days_of_week=ALL_DAYS),
    ]
    assert next_free_slot(windows, now, occupied=[]) == datetime(2026, 6, 8, 9, 0, tzinfo=UTC)


def test_skips_slot_occupied_within_30_minutes():
    now = datetime(2026, 6, 8, 8, 0, tzinfo=UTC)
    windows = [
        PostingWindow(time_slot="09:00", days_of_week=ALL_DAYS),
        PostingWindow(time_slot="12:00", days_of_week=ALL_DAYS),
    ]
    occupied = [datetime(2026, 6, 8, 9, 10, tzinfo=UTC)]  # within 30 min of 09:00
    assert next_free_slot(windows, now, occupied=occupied) == datetime(2026, 6, 8, 12, 0, tzinfo=UTC)


def test_returns_none_when_no_window_within_horizon():
    now = datetime(2026, 6, 8, 8, 0, tzinfo=UTC)
    assert next_free_slot([], now, occupied=[]) is None
