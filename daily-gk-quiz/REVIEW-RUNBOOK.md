# Laptop runbook — review & release the GK quiz queue

Everything to pick up at the laptop. The draft pool has been pre-rendered into Shorts and
loaded into the publisher review portal, ready for you to approve.

## 1. Start the portal

```
cd D:\Rewva\signal-lab\publisher
.venv\Scripts\python.exe -m publisher
```

Then open **http://127.0.0.1:8077** in a browser. This serves the review queue AND runs a
background scheduler that posts SCHEDULED jobs when they come due.

## 2. Review & approve (the single gate)

Each card in the queue is one quiz Short:

- **Watch** the video (plays inline).
- **Verify** the fact by clicking the source chip(s) — opens the authoritative source in a new tab.
- **Approve** → the job goes to `SCHEDULED` (next free posting slot) and will auto-post once
  accounts are connected (step 3).
- **Reject** → reveals a reason box; the job is rejected + soft-deleted.

That's it — approve in the portal = scheduled to release. No separate fact-verify step.

## 3. Connect accounts (one-time, required before anything actually posts)

Approving only *schedules*. Real posting needs OAuth, done once at this laptop:

```
cd D:\Rewva\signal-lab\publisher
.venv\Scripts\python.exe -m publisher.connect youtube
.venv\Scripts\python.exe -m publisher.connect meta
```

Full browser steps (GCP OAuth desktop client + YouTube Data API enable; Meta app + token +
role-holders) are in `publisher\docs\connect-accounts.md`. After connecting, set posting
windows per account (also covered there). Then SCHEDULED jobs fire automatically.

## What was prepped (2026-06-30 session)

- Question bank grown +49 verified-survivor drafts (committed `5c313e2`); bank = 16 verified + 72 drafts.
- All 72 drafts rendered to Shorts and queued in the portal as PENDING_APPROVAL via
  `_prep_review_queue.py` (idempotent; tracks `render\out\review\_submitted.json`). Re-run it
  anytime to queue any newly-added drafts.

## Known follow-up (not blocking your review)

Approving in the portal schedules the post but does NOT yet flip the source fact in the bank
from `draft` -> `verified`. That bank status only matters for the *automated daily planner*
draw (a separate path you are not using while hand-approving the pre-queued pool). When you
want the daily automation, we wire a small decoupled sync: poll the portal for approved jobs
and `bank verify` their fact_keys. Until then it has zero effect on the portal review flow.
