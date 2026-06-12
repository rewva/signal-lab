from selection.models import BankEntry, Question
from selection.bank_qa import check_entry


def _entry(**over):
    q_over = over.pop("q", {})
    base = dict(domain="polity", difficulty="basic", fact_key="polity/article-21",
                entity="Article 21", question="Which Article guarantees the right to life?",
                answer="Article 21", distractors=["Article 19", "Article 14", "Article 32"],
                exam_relevance=["SSC"], sources=["https://1", "https://2"],
                explanation="Art 21 protects life and liberty.",
                source_citation="Constitution of India, Art. 21")
    base.update(q_over)
    e = dict(static_class="permanent", source_tier=2, yield_weight="high")
    e.update(over)
    return BankEntry(question=Question(**base), **e)


def test_clean_entry_has_no_hard_errors():
    hard, soft = check_entry(_entry())
    assert hard == []


def test_duplicate_option_is_hard_error():
    hard, _ = check_entry(_entry(q={"distractors": ["Article 21", "Article 14", "Article 32"]}))
    assert any("distinct" in h for h in hard)


def test_blank_field_is_hard_error():
    hard, _ = check_entry(_entry(q={"explanation": "   "}))
    assert any("explanation" in h for h in hard)


def test_banned_phrase_is_hard_error():
    hard, _ = check_entry(_entry(q={"distractors": ["All of the above", "Article 14", "Article 32"]}))
    assert any("all/none of the above" in h for h in hard)


def test_bad_enums_are_hard_errors():
    hard, _ = check_entry(_entry(static_class="current-adjacent", source_tier=9, yield_weight="huge"))
    assert any("static_class" in h for h in hard)
    assert any("source_tier" in h for h in hard)
    assert any("yield_weight" in h for h in hard)


def test_answer_length_tell_is_soft_warning():
    long_ans = "Article 21 which guarantees the right to life and personal liberty to all persons"
    hard, soft = check_entry(_entry(q={"answer": long_ans}))
    assert hard == []  # not a hard failure
    assert any("answer-length" in s for s in soft)


def test_absolute_term_distractor_is_soft_warning():
    _, soft = check_entry(_entry(q={"distractors": ["Always Article 19", "Article 14", "Article 32"]}))
    assert any("absolute term" in s for s in soft)
