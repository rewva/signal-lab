"""FFmpeg pre-processor: normalise any source video to the cross-platform spec.

Target (research-confirmed to satisfy YouTube + Facebook + Instagram):
MP4 / H.264 / 1080x1920 / 8 Mbps / AAC-LC 128k / 48kHz / Fast Start (moov atom at front),
no edit lists. If the source already conforms, remux with ``-c copy`` (no re-encode).

The ffmpeg binary is invoked through an injected ``runner`` and metadata read through an
injected ``prober`` so the command-building and conformance logic are unit-tested without
the binary present.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Any, Callable, Optional

Runner = Callable[[list[str]], Any]
Prober = Callable[[str], dict[str, Any]]


@dataclass(frozen=True)
class TargetSpec:
    vcodec: str = "h264"
    width: int = 1080
    height: int = 1920
    vbitrate: str = "8M"
    acodec: str = "aac"
    abitrate: str = "128k"
    sample_rate: int = 48000


def build_command(src: str, dst: str, spec: TargetSpec, copy: bool = False) -> list[str]:
    """Build the ffmpeg argv to produce ``dst`` from ``src`` per ``spec``."""
    cmd = ["ffmpeg", "-y", "-i", src]
    if copy:
        cmd += ["-c", "copy"]
    else:
        vf = (
            f"scale={spec.width}:{spec.height}:force_original_aspect_ratio=decrease,"
            f"pad={spec.width}:{spec.height}:(ow-iw)/2:(oh-ih)/2,setsar=1"
        )
        cmd += [
            "-vf", vf,
            "-c:v", "libx264", "-b:v", spec.vbitrate, "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", spec.abitrate, "-ar", str(spec.sample_rate),
        ]
    cmd += ["-movflags", "+faststart", dst]
    return cmd


def is_conformant(probe: dict[str, Any], spec: TargetSpec) -> bool:
    """True if the probed source already matches the spec (so we can remux, not re-encode)."""
    return (
        probe.get("vcodec") == spec.vcodec
        and probe.get("width") == spec.width
        and probe.get("height") == spec.height
        and probe.get("acodec") == spec.acodec
        and probe.get("sample_rate") == spec.sample_rate
    )


def _default_runner(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True)


def _default_prober(src: str) -> dict[str, Any]:
    """Probe a file with ffprobe into the flat dict ``is_conformant`` expects."""
    out = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", src],
        check=True, capture_output=True, text=True,
    ).stdout
    streams = json.loads(out).get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), {})
    audio = next((s for s in streams if s.get("codec_type") == "audio"), {})
    return {
        "vcodec": video.get("codec_name"),
        "width": video.get("width"),
        "height": video.get("height"),
        "acodec": audio.get("codec_name"),
        "sample_rate": int(audio["sample_rate"]) if audio.get("sample_rate") else None,
    }


class Normalizer:
    def __init__(
        self,
        spec: Optional[TargetSpec] = None,
        runner: Runner = _default_runner,
        prober: Prober = _default_prober,
    ):
        self._spec = spec or TargetSpec()
        self._runner = runner
        self._prober = prober

    def normalize(self, src: str, dst: str) -> str:
        copy = is_conformant(self._prober(src), self._spec)
        self._runner(build_command(src, dst, self._spec, copy=copy))
        return dst
