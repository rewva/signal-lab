"""Orchestrate one daily quiz: verified Question + frozen plan -> props -> MP4 -> publisher job.

The two side effects (render subprocess, HTTP POST) are injected so build() is unit-testable;
main() wires the real implementations. See docs/specs/2026-06-11-gk-end-to-end-glue-design.md.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

from selection.assemble import RenderPlan, job_submission, quiz_props
from selection.models import Question


class RenderFailed(RuntimeError):
    pass


def slug_filename(fact_key: str) -> str:
    """fact_key contains '/', which is a path separator -> flatten it for the MP4 name."""
    return fact_key.replace("/", "__") + ".mp4"


def _real_render(props_path: str, out_path: str,
                 render_dir: str = "render", node: str = "node") -> int:
    """Run the Remotion CLI as a subprocess (cwd=render/, since render.mjs resolves
    src/index.ts relative to cwd). Returns the process exit code."""
    proc = subprocess.run(
        [node, "render.mjs", os.path.abspath(props_path), os.path.abspath(out_path)],
        cwd=render_dir,
    )
    return proc.returncode


def _real_post(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req) as resp:  # noqa: S310 (operator's own localhost publisher)
        return json.loads(resp.read().decode("utf-8"))


def build(request_path: str, *, labels: dict, publisher_url: str,
          out_dir: str = "out", props_path: str = "render/props.json",
          render=_real_render, post=_real_post) -> dict:
    """Assemble props, render the MP4, then POST the job. Returns the publisher's JobView dict."""
    request = json.loads(Path(request_path).read_text(encoding="utf-8"))
    question = Question.from_dict(request["question"]).validate()
    plan = RenderPlan(answer_position=request["answer_position"],
                      cta=request["cta"], trick_hook=request.get("trick_hook", ""))
    day_number = request["day_number"]

    props = quiz_props(question, plan, day_number, labels)
    Path(props_path).parent.mkdir(parents=True, exist_ok=True)
    Path(props_path).write_text(json.dumps(props, indent=2), encoding="utf-8")

    out_path = str(Path(out_dir) / slug_filename(question.fact_key))
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    code = render(props_path, out_path)
    if code != 0:
        raise RenderFailed(f"render exited {code}; not submitting a job for a missing video")

    body = job_submission(question, day_number, out_path, request["description"],
                          request["ai_disclosure"], labels)
    return post(publisher_url.rstrip("/") + "/api/jobs", body)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render + submit one daily GK quiz")
    parser.add_argument("--request", required=True, help="path to the render-request JSON")
    parser.add_argument("--publisher-url", default="http://127.0.0.1:8077")  # publisher config.py default
    parser.add_argument("--out", default="out")
    parser.add_argument("--domains", default="data/domains.json")
    args = parser.parse_args(argv)

    labels = json.loads(Path(args.domains).read_text(encoding="utf-8"))["labels"]
    result = build(args.request, labels=labels, publisher_url=args.publisher_url,
                   out_dir=args.out)
    print(f"submitted job {result.get('id')} ({result.get('status')})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
