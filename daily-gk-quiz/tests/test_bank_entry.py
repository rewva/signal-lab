from selection.models import BankEntry, Question, YIELD_WEIGHTS, STATIC_CLASSES, STATUSES


def _q(fk="polity/article-21"):
    return Question("polity", "basic", fk, "Article 21", "q?", "a",
                    ["b", "c", "d"], ["SSC"], ["https://1", "https://2"],
                    explanation="because", source_citation="Constitution of India, Art. 21")


def test_constants_present():
    assert STATIC_CLASSES == ("permanent", "slowly-changing")
    assert STATUSES == ("draft", "verified", "retired")
    assert YIELD_WEIGHTS == {"high": 3, "medium": 2, "low": 1}


def test_bankentry_roundtrips_with_nested_question():
    e = BankEntry(question=_q(), static_class="permanent", source_tier=2,
                  yield_weight="high", status="verified",
                  verified_date="2026-06-12", review_due_date=None)
    d = e.to_dict()
    assert d["question"]["fact_key"] == "polity/article-21"  # nested, not flattened
    assert d["static_class"] == "permanent" and d["source_tier"] == 2
    back = BankEntry.from_dict(d)
    assert back == e


def test_bankentry_defaults():
    e = BankEntry(question=_q(), static_class="permanent", source_tier=1, yield_weight="low")
    assert e.status == "draft" and e.verified_date is None and e.review_due_date is None
