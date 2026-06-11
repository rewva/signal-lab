import pytest
from selection.assemble import order_options


def test_answer_placed_in_each_position():
    answer = "Article 21"
    distractors = ["Article 19", "Article 14", "Article 32"]
    for pos in ("A", "B", "C", "D"):
        opts = order_options(answer, distractors, pos)
        assert [o["letter"] for o in opts] == ["A", "B", "C", "D"]
        by_letter = {o["letter"]: o["text"] for o in opts}
        assert by_letter[pos] == answer
        # the three distractors fill the other slots, in order
        others = [o["text"] for o in opts if o["letter"] != pos]
        assert others == distractors


def test_position_c_layout():
    opts = order_options("ANS", ["d0", "d1", "d2"], "C")
    assert opts == [
        {"letter": "A", "text": "d0"},
        {"letter": "B", "text": "d1"},
        {"letter": "C", "text": "ANS"},
        {"letter": "D", "text": "d2"},
    ]


def test_rejects_wrong_distractor_count():
    with pytest.raises(ValueError):
        order_options("ANS", ["only", "two"], "A")


from selection.assemble import quiz_props, RenderPlan
from selection.models import Question

LABELS = {"polity": "Polity", "current-affairs": "Current Affairs"}


def _question(**over):
    base = dict(
        domain="polity", difficulty="basic", fact_key="polity/article-21",
        entity="Article 21", question="Article 21 guarantees what?",
        answer="Life and personal liberty",
        distractors=["Equality", "Free speech", "Property"],
        exam_relevance=["SSC", "RRB"], sources=["https://a.gov.in", "https://b.org"],
        explanation="It protects life and personal liberty.",
        source_citation="Constitution of India, Art. 21",
    )
    base.update(over)
    return Question(**base)


EXPECTED_PROP_KEYS = {
    "dayNumber", "category", "difficulty", "examPrefix", "template", "question",
    "options", "correctLetter", "explanation", "sourceLine", "cta", "trickHook",
}


def test_quiz_props_full_mapping():
    plan = RenderPlan(answer_position="C", cta="Comment A or B", trick_hook="")
    props = quiz_props(_question(), plan, day_number=47, labels=LABELS)
    assert set(props.keys()) == EXPECTED_PROP_KEYS  # matches the zod QuizProps schema
    assert props["dayNumber"] == 47
    assert props["category"] == "Polity"
    assert props["difficulty"] == "basic"
    assert props["examPrefix"] == "SSC"
    assert props["template"] == "standard"
    assert props["correctLetter"] == "C"
    assert props["options"][2] == {"letter": "C", "text": "Life and personal liberty"}
    assert props["sourceLine"] == "Constitution of India, Art. 21"
    assert props["cta"] == "Comment A or B"
    assert props["trickHook"] == ""


def test_quiz_props_trick_template_and_hook():
    plan = RenderPlan(answer_position="A", cta="Comment A or B", trick_hook="Common Exam Trap")
    props = quiz_props(_question(is_trick=True), plan, day_number=5, labels=LABELS)
    assert props["template"] == "trick"
    assert props["trickHook"] == "Common Exam Trap"


def test_quiz_props_empty_exam_relevance_gives_blank_prefix():
    props = quiz_props(_question(exam_relevance=[]), RenderPlan("A", "cta", ""),
                       day_number=1, labels=LABELS)
    assert props["examPrefix"] == ""


def test_quiz_props_category_falls_back_to_titlecased_slug():
    props = quiz_props(_question(domain="general-science"), RenderPlan("A", "cta", ""),
                       day_number=1, labels=LABELS)
    assert props["category"] == "General Science"  # slug not in LABELS -> fallback


def test_order_options_rejects_invalid_position():
    from selection.assemble import order_options
    with pytest.raises(ValueError):
        order_options("ANS", ["a", "b", "c"], "E")


from selection.assemble import job_submission


def test_job_submission_full_body():
    body = job_submission(
        _question(), day_number=47, video_path="out/polity__article-21.mp4",
        description="Did you know Article 21 covers privacy?",
        ai_disclosure=True, labels=LABELS,
    )
    assert body["channel_id"] == "daily-gk-quiz"
    assert body["platforms"] == ["youtube", "facebook", "instagram"]
    assert body["video_path"] == "out/polity__article-21.mp4"
    assert body["title"] == "Daily GK #47 - Polity"
    assert body["description"].startswith("Did you know Article 21 covers privacy?")
    assert "Source: Constitution of India, Art. 21" in body["description"]
    assert body["tags"] == ["#SSC", "#RRB", "#Polity", "#DailyGK", "#GKQuiz"]
    assert body["per_platform"] == {"youtube": {"ai_disclosure": True}}
    # threaded for the future review dashboard
    assert body["source_citation"] == "Constitution of India, Art. 21"
    assert body["sources"] == ["https://a.gov.in", "https://b.org"]


def test_job_submission_compound_category_hashtag_is_alphanumeric():
    body = job_submission(
        _question(domain="banking-financial-awareness", exam_relevance=["IBPS-SBI"]),
        day_number=1, video_path="out/x.mp4", description="d",
        ai_disclosure=False, labels={"banking-financial-awareness": "Banking & Financial Awareness"},
    )
    assert body["tags"] == ["#IBPSSBI", "#BankingFinancialAwareness", "#DailyGK", "#GKQuiz"]
    assert body["per_platform"] == {"youtube": {"ai_disclosure": False}}
