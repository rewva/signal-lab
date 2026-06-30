"""Throwaway batch renderer: turn the verified bank questions into finished narrated MP4s
+ a ready-to-paste caption manifest, for MANUAL hand-posting (no publisher/OAuth needed).

Usage:  python batch_render.py [N]   (N = how many to render; default all verified)
Outputs: render/out/batch/NN-<slug>.mp4  +  render/out/batch/captions.md
Not committed -- operational tool, delete after use.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from selection.store import Store
from selection.assemble import RenderPlan, quiz_props, job_submission
from selection.selection import POSITIONS

HERE = Path(__file__).parent
RENDER_DIR = HERE / "render"
OUT_DIR = RENDER_DIR / "out" / "batch"
PROPS = RENDER_DIR / "_batch_props.json"

domains = json.loads((HERE / "data" / "domains.json").read_text(encoding="utf-8"))
prompts = json.loads((HERE / "data" / "prompts.json").read_text(encoding="utf-8"))
LABELS = domains.get("labels", {})
CTAS = prompts["ctas"]
HOOKS = prompts["hooks"]


def slug(fact_key: str) -> str:
    return fact_key.replace("/", "__")


def main() -> int:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    bank = Store(str(HERE / "state" / "question-history.json"),
                 str(HERE / "state" / "question-bank.json")).load_bank()
    verified = [e.question for e in bank if e.status == "verified"]
    verified.sort(key=lambda q: q.fact_key)  # stable order
    if limit:
        verified = verified[:limit]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = []
    for i, q in enumerate(verified):
        n = i + 1
        plan = RenderPlan(answer_position=POSITIONS[i % len(POSITIONS)],  # balance A/B/C/D
                          cta=CTAS[i % len(CTAS)], trick_hook="")
        props = quiz_props(q, plan, day_number=n, labels=LABELS)
        PROPS.write_text(json.dumps(props), encoding="utf-8")

        out_name = f"{n:02d}-{slug(q.fact_key)}.mp4"
        out_rel = f"out/batch/{out_name}"
        print(f"[{n}/{len(verified)}] rendering {out_name} ...", flush=True)
        r = subprocess.run(["node", "render.mjs", "_batch_props.json", out_rel],
                           cwd=str(RENDER_DIR))
        if r.returncode != 0:
            print(f"  FAILED on {q.fact_key} (rc={r.returncode})", file=sys.stderr)
            continue

        # ready-to-paste caption
        sub = job_submission(q, day_number=n, video_path=out_rel, description="",
                             ai_disclosure=True, labels=LABELS)
        category = sub["title"].split(" - ", 1)[1]
        hook = HOOKS[i % len(HOOKS)]
        tags = " ".join(sub["tags"])
        caption = (f"{hook}\n\n"
                   f"Pakka GK #{n}: {category} ({props['examPrefix']} level)\n\n"
                   f"{plan.cta}\n\n"
                   f"Source: {q.source_citation}\n\n{tags}")
        manifest.append(f"## {n:02d}. {out_name}\n\n{caption}\n")

    (OUT_DIR / "captions.md").write_text(
        "# Hand-post kit -- captions per video (paste when uploading)\n\n" +
        "\n---\n\n".join(manifest), encoding="utf-8")
    if PROPS.exists():
        PROPS.unlink()
    print(f"\nDone -> {OUT_DIR}  ({len(manifest)} videos + captions.md)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
