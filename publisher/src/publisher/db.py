"""SQLite data layer for the publisher.

Thin hand-rolled repository over stdlib sqlite3 -- no ORM, to keep memory and start-up
cost minimal. List/dict columns are stored as JSON text; timestamps as ISO-8601 UTC.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from publisher.models import Account, Job, PostResult

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    brand           TEXT NOT NULL,
    platform        TEXT NOT NULL,
    account_id      TEXT NOT NULL,
    token_key_ref   TEXT NOT NULL,
    token_broken    INTEGER NOT NULL DEFAULT 0,
    expires_at      TEXT
);

CREATE TABLE IF NOT EXISTS jobs (
    -- NOTE: CREATE TABLE IF NOT EXISTS won't add columns to a pre-existing DB; drop publisher.db if you hit "no column named source_citation".
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id      TEXT NOT NULL,
    video_path      TEXT NOT NULL,
    title           TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    tags            TEXT NOT NULL DEFAULT '[]',
    platforms       TEXT NOT NULL DEFAULT '[]',
    per_platform    TEXT NOT NULL DEFAULT '{}',
    status          TEXT NOT NULL,
    submitted_at    TEXT,
    scheduled_for   TEXT,
    posted_at       TEXT,
    deleted_at      TEXT,
    attempts        INTEGER NOT NULL DEFAULT 0,
    source_citation TEXT NOT NULL DEFAULT '',
    sources         TEXT NOT NULL DEFAULT '[]',
    reject_reason   TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS post_results (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id              INTEGER NOT NULL REFERENCES jobs(id),
    platform            TEXT NOT NULL,
    account_id          TEXT NOT NULL,
    external_post_id    TEXT,
    post_url            TEXT,
    error               TEXT,
    created_at          TEXT
);

CREATE TABLE IF NOT EXISTS posting_windows (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id      INTEGER NOT NULL REFERENCES accounts(id),
    time_slot       TEXT NOT NULL,      -- HH:MM
    days_of_week    TEXT NOT NULL DEFAULT '[]'
);
"""


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, path: str | Path, clock: Callable[[], str] = _utcnow_iso):
        # check_same_thread=False: FastAPI runs sync endpoints in a threadpool, so the
        # connection is shared across threads. _lock serialises access (fine at this
        # monolith's 1-5 posts/day volume).
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._lock = threading.Lock()
        self._now = clock

    def init_schema(self) -> None:
        with self._lock:
            self._conn.executescript(SCHEMA)
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # All connection access funnels through these two locked helpers so the API
    # threadpool and the scheduler thread never touch the shared connection concurrently.

    def _write(self, sql: str, params: tuple) -> int:
        with self._lock:
            cur = self._conn.execute(sql, params)
            self._conn.commit()
            return cur.lastrowid

    def _query(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        with self._lock:
            return self._conn.execute(sql, params).fetchall()

    # --- accounts -----------------------------------------------------------

    def add_account(self, account: Account) -> Account:
        account.id = self._write(
            "INSERT INTO accounts (brand, platform, account_id, token_key_ref, "
            "token_broken, expires_at) VALUES (?, ?, ?, ?, ?, ?)",
            (account.brand, account.platform, account.account_id, account.token_key_ref,
             int(account.token_broken), account.expires_at),
        )
        return account

    def get_account(self, account_pk: int) -> Optional[Account]:
        rows = self._query("SELECT * FROM accounts WHERE id = ?", (account_pk,))
        return self._row_to_account(rows[0]) if rows else None

    def list_accounts(self, brand: Optional[str] = None,
                      platform: Optional[str] = None) -> list[Account]:
        sql, params = "SELECT * FROM accounts", []
        clauses = []
        if brand is not None:
            clauses.append("brand = ?"); params.append(brand)
        if platform is not None:
            clauses.append("platform = ?"); params.append(platform)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY id"
        return [self._row_to_account(r) for r in self._query(sql, tuple(params))]

    def mark_token_broken(self, account_pk: int, broken: bool) -> None:
        self._write(
            "UPDATE accounts SET token_broken = ? WHERE id = ?", (int(broken), account_pk)
        )

    @staticmethod
    def _row_to_account(row: sqlite3.Row) -> Account:
        return Account(
            id=row["id"], brand=row["brand"], platform=row["platform"],
            account_id=row["account_id"], token_key_ref=row["token_key_ref"],
            token_broken=bool(row["token_broken"]), expires_at=row["expires_at"],
        )

    # --- jobs ---------------------------------------------------------------

    def create_job(self, job: Job) -> Job:
        if job.submitted_at is None:
            job.submitted_at = self._now()
        job.id = self._write(
            "INSERT INTO jobs (channel_id, video_path, title, description, tags, "
            "platforms, per_platform, status, submitted_at, scheduled_for, posted_at, "
            "deleted_at, attempts, source_citation, sources, reject_reason) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (job.channel_id, job.video_path, job.title, job.description,
             json.dumps(job.tags), json.dumps(job.platforms),
             json.dumps(job.per_platform), job.status, job.submitted_at,
             job.scheduled_for, job.posted_at, job.deleted_at, job.attempts,
             job.source_citation, json.dumps(job.sources), job.reject_reason),
        )
        return job

    def get_job(self, job_pk: int, include_deleted: bool = False) -> Optional[Job]:
        rows = self._query("SELECT * FROM jobs WHERE id = ?", (job_pk,))
        if not rows:
            return None
        row = rows[0]
        if row["deleted_at"] is not None and not include_deleted:
            return None
        return self._row_to_job(row)

    def list_jobs(self, status: Optional[str] = None,
                 include_deleted: bool = False) -> list[Job]:
        sql, params = "SELECT * FROM jobs", []
        clauses = []
        if not include_deleted:
            clauses.append("deleted_at IS NULL")
        if status is not None:
            clauses.append("status = ?"); params.append(status)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY id"
        return [self._row_to_job(r) for r in self._query(sql, tuple(params))]

    def update_job_status(self, job_pk: int, status: str) -> None:
        self._write("UPDATE jobs SET status = ? WHERE id = ?", (status, job_pk))

    def increment_attempts(self, job_pk: int) -> int:
        self._write("UPDATE jobs SET attempts = attempts + 1 WHERE id = ?", (job_pk,))
        return self._query("SELECT attempts FROM jobs WHERE id = ?", (job_pk,))[0]["attempts"]

    def set_scheduled_for(self, job_pk: int, when_iso: str) -> None:
        self._write("UPDATE jobs SET scheduled_for = ? WHERE id = ?", (when_iso, job_pk))

    def set_posted_at(self, job_pk: int, when_iso: str) -> None:
        self._write("UPDATE jobs SET posted_at = ? WHERE id = ?", (when_iso, job_pk))

    def set_reject_reason(self, job_pk: int, reason: str) -> None:
        self._write("UPDATE jobs SET reject_reason = ? WHERE id = ?", (reason, job_pk))

    def soft_delete_job(self, job_pk: int) -> None:
        self._write(
            "UPDATE jobs SET deleted_at = ? WHERE id = ?", (self._now(), job_pk)
        )

    @staticmethod
    def _row_to_job(row: sqlite3.Row) -> Job:
        return Job(
            id=row["id"], channel_id=row["channel_id"], video_path=row["video_path"],
            title=row["title"], description=row["description"],
            tags=json.loads(row["tags"]), platforms=json.loads(row["platforms"]),
            per_platform=json.loads(row["per_platform"]), status=row["status"],
            submitted_at=row["submitted_at"], scheduled_for=row["scheduled_for"],
            posted_at=row["posted_at"], deleted_at=row["deleted_at"],
            attempts=row["attempts"],
            source_citation=row["source_citation"],
            sources=json.loads(row["sources"]),
            reject_reason=row["reject_reason"],
        )

    # --- post_results -------------------------------------------------------

    def record_post_result(self, result: PostResult) -> PostResult:
        if result.created_at is None:
            result.created_at = self._now()
        result.id = self._write(
            "INSERT INTO post_results (job_id, platform, account_id, external_post_id, "
            "post_url, error, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (result.job_id, result.platform, result.account_id, result.external_post_id,
             result.post_url, result.error, result.created_at),
        )
        return result

    # --- posting_windows ----------------------------------------------------

    def add_posting_window(self, account_pk: int, time_slot: str,
                           days_of_week: list[int]) -> int:
        return self._write(
            "INSERT INTO posting_windows (account_id, time_slot, days_of_week) "
            "VALUES (?, ?, ?)",
            (account_pk, time_slot, json.dumps(days_of_week)),
        )

    def list_posting_windows(self, account_pk: int) -> list["PostingWindow"]:
        from publisher.scheduler import PostingWindow

        rows = self._query(
            "SELECT * FROM posting_windows WHERE account_id = ? ORDER BY time_slot",
            (account_pk,),
        )
        return [
            PostingWindow(time_slot=r["time_slot"],
                          days_of_week=json.loads(r["days_of_week"]))
            for r in rows
        ]

    def list_post_results(self, job_pk: int) -> list[PostResult]:
        rows = self._query(
            "SELECT * FROM post_results WHERE job_id = ? ORDER BY id", (job_pk,)
        )
        return [
            PostResult(
                id=r["id"], job_id=r["job_id"], platform=r["platform"],
                account_id=r["account_id"], external_post_id=r["external_post_id"],
                post_url=r["post_url"], error=r["error"], created_at=r["created_at"],
            )
            for r in rows
        ]
