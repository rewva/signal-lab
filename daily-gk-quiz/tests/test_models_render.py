from selection.models import Question, HistoryRecord

def _q(**over):
    base = dict(domain="polity", difficulty="basic", fact_key="polity/art-21",
                entity="Article 21", question="Q?", answer="Article 21",
                distractors=["a", "b", "c"], exam_relevance=["SSC"],
                sources=["https://1", "https://2"], explanation="why")
    base.update(over)
    return Question(**base)

def test_question_defaults_is_trick_false():
    assert _q().is_trick is False

def test_question_is_trick_roundtrips():
    q = _q(is_trick=True)
    assert Question.from_dict(q.to_dict()).is_trick is True

def test_history_record_carries_answer_position():
    rec = HistoryRecord("2026-06-10", _q(), hook="h", cta="c", answer_position="B")
    d = rec.to_dict()
    assert d["answer_position"] == "B"
    assert HistoryRecord.from_dict(d).answer_position == "B"
