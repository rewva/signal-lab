import json
import os
import pytest
from selection import build


def _request():
    return {
        "question": {
            "domain": "polity", "difficulty": "basic", "fact_key": "polity/article-21",
            "entity": "Article 21", "question": "Article 21 guarantees what?",
            "answer": "Life and personal liberty",
            "distractors": ["Equality", "Free speech", "Property"],
            "exam_relevance": ["SSC", "RRB"], "sources": ["https://a.gov.in", "https://b.org"],
            "explanation": "Protects life and liberty.",
            "source_citation": "Constitution of India, Art. 21",
        },
        "answer_position": "C", "hook": "h", "cta": "Comment A or B",
        "trick_hook": "", "day_number": 47,
        "description": "Did you know?", "ai_disclosure": True,
    }


def _setup(tmp_path, request):
    req_path = tmp_path / "approved.json"
    req_path.write_text(json.dumps(request), encoding="utf-8")
    labels = {"polity": "Polity"}
    return req_path, labels


def test_fact_key_slugged_into_output_path(tmp_path):
    assert build.slug_filename("polity/article-21") == "polity__article-21.mp4"


def test_build_writes_props_renders_then_posts(tmp_path):
    req_path, labels = _setup(tmp_path, _request())
    calls = {"render": None, "post": None}

    def fake_render(props_path, out_path):
        calls["render"] = (props_path, out_path)
        return 0  # success

    def fake_post(url, payload):
        calls["post"] = (url, payload)
        return {"id": 99, "status": "PENDING_APPROVAL"}

    out_dir = tmp_path / "out"
    result = build.build(str(req_path), labels=labels, publisher_url="http://pub",
                         out_dir=str(out_dir), props_path=str(tmp_path / "props.json"),
                         render=fake_render, post=fake_post)

    props = json.loads((tmp_path / "props.json").read_text(encoding="utf-8"))
    assert props["correctLetter"] == "C"
    assert props["category"] == "Polity"
    assert calls["render"][0] == str(tmp_path / "props.json")
    assert calls["render"][1].endswith("polity__article-21.mp4")
    assert calls["post"][0] == "http://pub/api/jobs"
    assert calls["post"][1]["source_citation"] == "Constitution of India, Art. 21"
    assert calls["post"][1]["video_path"].endswith("polity__article-21.mp4")
    assert result["id"] == 99


def test_build_aborts_post_when_render_fails(tmp_path):
    req_path, labels = _setup(tmp_path, _request())
    posted = []

    def failing_render(props_path, out_path):
        return 1  # non-zero -> render failed

    def fake_post(url, payload):
        posted.append(payload)
        return {}

    with pytest.raises(build.RenderFailed):
        build.build(str(req_path), labels=labels, publisher_url="http://pub",
                    out_dir=str(tmp_path / "out"), props_path=str(tmp_path / "props.json"),
                    render=failing_render, post=fake_post)
    assert posted == []  # never POSTed a job for a missing video


def test_build_video_path_is_absolute(tmp_path, monkeypatch):
    """video_path stored in the publisher job must be absolute so a separate publisher
    process (with its own cwd) can resolve it."""
    monkeypatch.chdir(tmp_path)
    req_path, labels = _setup(tmp_path, _request())
    calls = {"render": None, "post": None}

    def fake_render(props_path, out_path):
        calls["render"] = (props_path, out_path)
        return 0

    def fake_post(url, payload):
        calls["post"] = (url, payload)
        return {"id": 42, "status": "PENDING_APPROVAL"}

    build.build(str(req_path), labels=labels, publisher_url="http://pub",
                out_dir="out", props_path="props.json",
                render=fake_render, post=fake_post)

    assert os.path.isabs(calls["post"][1]["video_path"]), (
        "video_path must be absolute; got: " + calls["post"][1]["video_path"]
    )
    assert calls["post"][1]["video_path"].endswith("polity__article-21.mp4")


def test_build_rejects_unverified_question(tmp_path):
    bad = _request()
    bad["question"]["source_citation"] = ""
    req_path, labels = _setup(tmp_path, bad)
    with pytest.raises(ValueError, match="source_citation is required"):
        build.build(str(req_path), labels=labels, publisher_url="http://pub",
                    out_dir=str(tmp_path / "out"), props_path=str(tmp_path / "props.json"),
                    render=lambda p, o: 0, post=lambda u, p: {})
