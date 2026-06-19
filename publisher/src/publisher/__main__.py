"""Run the publisher live: serve the FastAPI app + drive the scheduler tick.

    python -m publisher

Wiring lives in ``build_runtime`` (db + vault + adapters + orchestrator + app + tick). This
module adds the two long-running pieces that production needs but tests don't: a background
thread that calls ``tick`` every ``poll_interval_seconds`` (so SCHEDULED jobs get posted) and
the uvicorn server for the intake + review API. The loop helper is pure enough to unit-test
without a real clock or server.
"""

from __future__ import annotations

import threading
from typing import Callable

from publisher.bootstrap import Runtime, build_runtime
from publisher.config import Settings


def run_scheduler_loop(
    tick: Callable[[], None],
    interval_seconds: float,
    stop: threading.Event,
) -> None:
    """Call ``tick`` immediately, then once per ``interval_seconds`` until ``stop`` is set.

    A failing tick is swallowed (logged) so one bad posting attempt never kills the loop --
    the orchestrator already records the per-job failure. ``stop.wait`` makes the sleep
    interruptible, so shutdown is immediate rather than up to one interval late.
    """
    while not stop.is_set():
        try:
            tick()
        except Exception as exc:  # noqa: BLE001 -- a loop must outlive one bad tick
            print(f"[scheduler] tick error: {exc}", flush=True)
        stop.wait(interval_seconds)


def _start_scheduler(runtime: Runtime, interval_seconds: float) -> threading.Event:
    stop = threading.Event()
    thread = threading.Thread(
        target=run_scheduler_loop,
        args=(runtime.tick, interval_seconds, stop),
        name="publisher-scheduler",
        daemon=True,
    )
    thread.start()
    return stop


def main() -> None:
    import uvicorn

    settings = Settings()
    runtime = build_runtime(settings)
    _start_scheduler(runtime, settings.poll_interval_seconds)
    print(f"[publisher] serving on http://{settings.host}:{settings.port} "
          f"(review queue at /)", flush=True)
    uvicorn.run(runtime.app, host=settings.host, port=settings.port, log_level="info")


if __name__ == "__main__":
    main()
