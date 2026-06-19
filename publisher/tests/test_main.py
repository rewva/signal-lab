"""Unit tests for the live-runner scheduler loop helper."""

import threading

from publisher.__main__ import run_scheduler_loop


def test_loop_ticks_then_stops_on_event():
    calls = []
    stop = threading.Event()

    def tick():
        calls.append(1)
        stop.set()  # ask the loop to stop after the first tick

    run_scheduler_loop(tick, interval_seconds=0.0, stop=stop)
    assert calls == [1]


def test_loop_survives_a_failing_tick():
    calls = []
    stop = threading.Event()

    def tick():
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("boom")  # first tick blows up...
        stop.set()  # ...second tick still runs and then stops the loop

    run_scheduler_loop(tick, interval_seconds=0.0, stop=stop)
    assert calls == [1, 1]


def test_loop_does_not_tick_when_already_stopped():
    calls = []
    stop = threading.Event()
    stop.set()

    run_scheduler_loop(lambda: calls.append(1), interval_seconds=0.0, stop=stop)
    assert calls == []
