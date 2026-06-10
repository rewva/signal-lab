"""Entry point: `python main.py` starts the publisher monolith.

Runs the FastAPI app (job intake + read API) and an APScheduler background job that fires
every poll_interval_seconds, posting any due SCHEDULED jobs through the orchestrator.
"""

from __future__ import annotations

import uvicorn
from apscheduler.schedulers.background import BackgroundScheduler

from publisher.bootstrap import build_runtime
from publisher.config import Settings


def main() -> None:
    settings = Settings()
    runtime = build_runtime(settings)

    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        runtime.tick, "interval", seconds=settings.poll_interval_seconds,
        id="post-due-jobs", max_instances=1, coalesce=True,
    )
    scheduler.start()
    try:
        uvicorn.run(runtime.app, host=settings.host, port=settings.port)
    finally:
        scheduler.shutdown(wait=False)


if __name__ == "__main__":
    main()
