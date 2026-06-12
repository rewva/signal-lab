from selection.models import BankEntry, Question
from selection.bank_qa import normalize_stem, find_duplicates


def _entry(fk, stem):
    q = Question("polity", "basic", fk, "X", stem, "a", ["b", "c", "d"],
                 ["SSC"], ["https://1", "https://2"],
                 explanation="e", source_citation="cite")
    return BankEntry(question=q, static_class="permanent", source_tier=2, yield_weight="high")


def test_normalize_stem_strips_punct_and_case():
    assert normalize_stem("Who is the 9th P.M.  of India?") == "who is the 9th p m of india"


def test_same_fact_key_is_duplicate():
    bank = [_entry("polity/a", "Totally different wording here about something else.")]
    cand = _entry("polity/a", "Another phrasing entirely unrelated to the above one.")
    dups, near = find_duplicates(cand, bank)
    assert len(dups) == 1 and not near


def test_high_similarity_is_duplicate():
    bank = [_entry("polity/a", "Which Article guarantees the right to life in India?")]
    cand = _entry("polity/b", "Which Article guarantees the right to life in India?")
    dups, near = find_duplicates(cand, bank)
    assert len(dups) == 1 and not near


def test_distinct_stems_are_clean():
    bank = [_entry("polity/a", "Who was the first President of India?")]
    cand = _entry("polity/b", "What is the chemical symbol for gold?")
    dups, near = find_duplicates(cand, bank)
    assert not dups and not near
