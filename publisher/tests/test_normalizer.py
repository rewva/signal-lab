"""Tests for the FFmpeg normalizer.

Target spec confirmed by research to satisfy YouTube + Facebook + Instagram:
MP4 / H.264 / 1080x1920 / AAC-LC 128k / 48kHz / Fast Start, no edit lists.
The ffmpeg binary itself is never invoked here -- the runner and prober are injected.
"""

from publisher.normalizer import Normalizer, TargetSpec, build_command, is_conformant

SPEC = TargetSpec()  # defaults are the common baseline

CONFORMANT_PROBE = {
    "vcodec": "h264", "width": 1080, "height": 1920,
    "acodec": "aac", "sample_rate": 48000,
}


# --- command building -------------------------------------------------------

def test_full_reencode_command_has_expected_codecs_and_faststart():
    cmd = build_command("in.mp4", "out.mp4", SPEC, copy=False)
    joined = " ".join(cmd)
    assert cmd[0] == "ffmpeg"
    assert "libx264" in joined
    assert "-b:v" in cmd and "8M" in cmd
    assert "aac" in joined
    assert "-b:a" in cmd and "128k" in cmd
    assert "-ar" in cmd and "48000" in cmd
    assert "+faststart" in joined
    assert cmd[-1] == "out.mp4"


def test_full_reencode_scales_and_pads_to_1080x1920():
    joined = " ".join(build_command("in.mp4", "out.mp4", SPEC, copy=False))
    assert "1080:1920" in joined
    assert "pad=" in joined


def test_copy_command_remuxes_without_reencoding():
    cmd = build_command("in.mp4", "out.mp4", SPEC, copy=True)
    joined = " ".join(cmd)
    assert "-c" in cmd and "copy" in cmd
    assert "libx264" not in joined
    assert "+faststart" in joined  # still fix moov atom placement


def test_command_overwrites_output():
    assert "-y" in build_command("in.mp4", "out.mp4", SPEC)


# --- conformance decision ---------------------------------------------------

def test_is_conformant_true_for_matching_probe():
    assert is_conformant(CONFORMANT_PROBE, SPEC) is True


def test_is_conformant_false_for_wrong_video_codec():
    probe = {**CONFORMANT_PROBE, "vcodec": "hevc"}
    assert is_conformant(probe, SPEC) is False


def test_is_conformant_false_for_wrong_dimensions():
    probe = {**CONFORMANT_PROBE, "width": 720, "height": 1280}
    assert is_conformant(probe, SPEC) is False


def test_is_conformant_false_for_wrong_audio_sample_rate():
    probe = {**CONFORMANT_PROBE, "sample_rate": 44100}
    assert is_conformant(probe, SPEC) is False


# --- normalize orchestration ------------------------------------------------

def test_normalize_uses_copy_when_source_conformant():
    calls = []
    norm = Normalizer(
        runner=lambda cmd: calls.append(cmd),
        prober=lambda src: CONFORMANT_PROBE,
    )
    norm.normalize("in.mp4", "out.mp4")
    assert "copy" in calls[0]
    assert "libx264" not in " ".join(calls[0])


def test_normalize_reencodes_when_source_nonconformant():
    calls = []
    norm = Normalizer(
        runner=lambda cmd: calls.append(cmd),
        prober=lambda src: {**CONFORMANT_PROBE, "vcodec": "vp9"},
    )
    norm.normalize("in.webm", "out.mp4")
    assert "libx264" in " ".join(calls[0])


def test_normalize_returns_destination_path():
    norm = Normalizer(runner=lambda cmd: None, prober=lambda src: CONFORMANT_PROBE)
    assert norm.normalize("in.mp4", "out.mp4") == "out.mp4"
