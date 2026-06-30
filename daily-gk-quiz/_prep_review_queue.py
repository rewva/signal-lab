"""Ops prep: render every DRAFT bank entry to a Short and submit it to the publisher review
portal (PENDING_APPROVAL), so the operator can review+approve the whole pool at the laptop.

Idempotent: tracks submitted fact_keys in render/out/review/_submitted.json so re-runs skip
already-queued items. Renders are skipped if the MP4 already exists. Requires the publisher
running at 127.0.0.1:8077. Throwaway ops tool -- not committed.
"""
from __future__ import annotations
import json, subprocess, sys, urllib.request, urllib.error
from pathlib import Path

from selection.store import Store
from selection.assemble import RenderPlan, quiz_props, job_submission
from selection.selection import POSITIONS

HERE = Path(__file__).parent
RENDER_DIR = HERE / "render"
OUT_DIR = RENDER_DIR / "out" / "review"
PROPS = RENDER_DIR / "_prep_props.json"
SUBMITTED = OUT_DIR / "_submitted.json"
PUB = "http://127.0.0.1:8077/api/jobs"

domains = json.loads((HERE / "data" / "domains.json").read_text(encoding="utf-8"))
prompts = json.loads((HERE / "data" / "prompts.json").read_text(encoding="utf-8"))
LABELS = domains.get("labels", {})
CTAS = prompts["ctas"]

OUT_DIR.mkdir(parents=True, exist_ok=True)
# Seed: the 5 already submitted in this session (jobs 3-7) so we never double-queue them.
SEED = [
    "polity/42nd-amendment-mini-constitution",
    "history/champaran-satyagraha-1917",
    "economy/nabard-established-1982",
    "geography/godavari-second-longest-river-india",
    "sports-awards-misc/ranji-trophy-cricket",
]
submitted = set(json.loads(SUBMITTED.read_text(encoding="utf-8"))) if SUBMITTED.exists() else set(SEED)

bank = Store(str(HERE / "state" / "question-history.json"),
             str(HERE / "state" / "question-bank.json")).load_bank()
drafts = [e.question for e in bank if e.status == "draft"]
drafts.sort(key=lambda q: q.fact_key)
todo = [q for q in drafts if q.fact_key not in submitted]
print(f"{len(drafts)} drafts, {len(submitted)} already queued, {len(todo)} to do", flush=True)


def render(q, i) -> str | None:
    plan = RenderPlan(answer_position=POSITIONS[i % len(POSITIONS)], cta=CTAS[i % len(CTAS)], trick_hook="")
    PROPS.write_text(json.dumps(quiz_props(q, plan, day_number=i + 1, labels=LABELS)), encoding="utf-8")
    slug = q.fact_key.replace("/", "__")
    out_rel = f"out/review/{slug}.mp4"
    out_abs = RENDER_DIR / out_rel
    if not out_abs.is_file():
        r = subprocess.run(["node", "render.mjs", "_prep_props.json", out_rel], cwd=str(RENDER_DIR))
        if r.returncode != 0:
            print(f"  RENDER FAIL {q.fact_key} rc={r.returncode}", file=sys.stderr, flush=True)
            return None
    return str(out_abs.resolve())


def submit(q, video_abs, i):
    body = job_submission(q, day_number=i + 1, video_path=video_abs,
                          description="", ai_disclosure=True, labels=LABELS)
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(PUB, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


for i, q in enumerate(todo):
    print(f"[{i+1}/{len(todo)}] {q.fact_key}", flush=True)
    video_abs = render(q, i)
    if not video_abs:
        continue
    try:
        view = submit(q, video_abs, i)
    except (urllib.error.URLError, OSError) as exc:
        print(f"  SUBMIT FAIL {q.fact_key}: {exc}", file=sys.stderr, flush=True)
        continue
    submitted.add(q.fact_key)
    SUBMITTED.write_text(json.dumps(sorted(submitted), indent=1), encoding="utf-8")
    print(f"  queued job {view.get('id')} ({view.get('status')})", flush=True)

PROPS.unlink(missing_ok=True)
print(f"\nDONE. {len(submitted)} total fact_keys queued in the portal.", flush=True)
