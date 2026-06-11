import pytest
from selection.models import Question, HistoryRecord

def _q(**over):
    base = dict(
        domain="polity", difficulty="basic",
        fact_key="polity/article-21-right-to-life", entity="Article 21",
        question="Article 21 guarantees the right to what?",
        answer="Life and personal liberty",
        distractors=["Equality", "Freedom of speech", "Property"],
        exam_relevance=["SSC", "RRB"],
        sources=["https://a.gov.in", "https://b.org"],
        explanation="Article 21 protects life and personal liberty.",
        source_citation="Constitution of India, Art. 21",
        mnemonic=None,
    )
    base.update(over)
    return Question(**base)

def test_question_roundtrips_through_dict():
    q = _q()
    assert Question.from_dict(q.to_dict()) == q

def test_question_rejects_wrong_distractor_count():
    with pytest.raises(ValueError, match="exactly 3 distractors"):
        _q(distractors=["only", "two"]).validate()

def test_question_rejects_too_few_sources():
    with pytest.raises(ValueError, match="at least 2 sources"):
        _q(sources=["https://only-one"]).validate()

def test_question_rejects_bad_difficulty():
    with pytest.raises(ValueError, match="difficulty"):
        _q(difficulty="impossible").validate()

def test_question_requires_explanation():
    with pytest.raises(ValueError, match="explanation is required"):
        _q(explanation="").validate()

def test_question_keeps_explanation_and_mnemonic_through_dict():
    q = _q(explanation="Article 21 covers life and liberty.", mnemonic="21 = to-live")
    back = Question.from_dict(q.to_dict())
    assert back.explanation == "Article 21 covers life and liberty."
    assert back.mnemonic == "21 = to-live"

def test_history_record_roundtrips_flat():
    rec = HistoryRecord(date="2026-06-10", question=_q())
    d = rec.to_dict()
    assert d["date"] == "2026-06-10"
    assert d["fact_key"] == "polity/article-21-right-to-life"  # flattened, not nested
    assert HistoryRecord.from_dict(d) == rec


def test_question_requires_source_citation():
    with pytest.raises(ValueError, match="source_citation is required"):
        _q(source_citation="").validate()


def test_question_keeps_source_citation_through_dict():
    q = _q(source_citation="RBI Monetary Policy, Feb 2026")
    assert Question.from_dict(q.to_dict()).source_citation == "RBI Monetary Policy, Feb 2026"
