from datetime import date

from selection.models import BankEntry, Question
from selection.ingest import ingest_batch, IngestReport

TODAY = date(2026, 6, 12)


def _draft(fk, stem, sources=("https://a", "https://b"), distractors=("b", "c", "d"),
           explanation="why", source_citation="cite"):
    q = Question("polity", "basic", fk, "X", stem, "a", list(distractors),
                 ["SSC"], list(sources), explanation=explanation,
                 source_citation=source_citation)
    return BankEntry(question=q, static_class="permanent", source_tier=2,
                     yield_weight="high", status="draft")


def test_clean_batch_all_accepted_and_landed_as_drafts():
    bank: list[BankEntry] = []
    drafts = [_draft("polity/a", "First distinct stem about one topic."),
              _draft("polity/b", "Second different stem on another matter.")]
    report = ingest_batch(bank, drafts, TODAY)
    assert set(report.accepted) == {"polity/a", "polity/b"}
    assert report.rejected == []
    assert len(bank) == 2
    assert all(e.status == "draft" for e in bank)


def test_too_few_sources_rejected_by_validate():
    bank: list[BankEntry] = []
    report = ingest_batch(bank, [_draft("polity/a", "A stem here about things.",
                                        sources=("https://only-one",))], TODAY)
    assert report.accepted == []
    assert report.rejected[0][0] == "polity/a"
    assert "source" in report.rejected[0][1].lower()
    assert len(bank) == 0  # nothing appended


def test_hard_qa_failure_rejected_others_accepted():
    bank: list[BankEntry] = []
    bad = _draft("polity/bad", "Bad item with a blank distractor.", distractors=("b", "c", ""))
    good = _draft("polity/good", "A perfectly fine stem about a subject.")
    report = ingest_batch(bank, [bad, good], TODAY)
    assert "polity/good" in report.accepted
    assert any(fk == "polity/bad" for fk, _ in report.rejected)
    assert len(bank) == 1


def test_duplicate_rejected():
    bank: list[BankEntry] = []
    first = _draft("polity/a", "A unique stem about one specific topic.")
    dup = _draft("polity/a", "Completely different wording but same fact key.")
    report = ingest_batch(bank, [first, dup], TODAY)
    assert report.accepted == ["polity/a"]
    assert any(fk == "polity/a" and "duplicate" in reason.lower()
               for fk, reason in report.rejected)
    assert len(bank) == 1


def test_near_duplicate_accepted_with_warning():
    bank: list[BankEntry] = []
    first = _draft("polity/a", "Which Article ensures citizens the right to free speech in India?")
    near = _draft("polity/b", "Which Article guarantees citizens the right to free expression in India?")
    report = ingest_batch(bank, [first, near], TODAY)
    assert set(report.accepted) == {"polity/a", "polity/b"}
    assert any(fk == "polity/b" and any("near-duplicate" in w for w in warns)
               for fk, warns in report.warnings)


def test_report_is_ingestreport_instance():
    assert isinstance(ingest_batch([], [], TODAY), IngestReport)
