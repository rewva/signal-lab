import random
from datetime import date

from selection.models import BankEntry, Question
from selection.selection import draw_from_bank

TODAY = date(2026, 6, 12)


def _entry(domain, diff, fk, stem="A neutral question stem about a topic.", yield_weight="high"):
    q = Question(domain, diff, fk, "X", stem, "a", ["b", "c", "d"], ["SSC"],
                 ["https://1", "https://2"], explanation="e", source_citation="cite")
    return BankEntry(question=q, static_class="permanent", source_tier=2,
                     yield_weight=yield_weight, status="verified", verified_date="2026-06-12")


def _bank():
    return [
        _entry("history", "basic", "history/plassey-1757", "Who won the Battle of Plassey?"),
        _entry("history", "advanced", "history/buxar-1764", "Who won the Battle of Buxar?"),
        _entry("polity", "basic", "polity/article-21", "Which Article protects life?"),
    ]


def test_draws_matching_domain_and_difficulty():
    got = draw_from_bank(_bank(), "history", "basic", set(), [], TODAY, random.Random(0))
    assert got is not None and got.fact_key == "history/plassey-1757"


def test_skips_already_used_fact_keys():
    got = draw_from_bank(_bank(), "history", "basic", {"history/plassey-1757"}, [],
                         TODAY, random.Random(0))
    assert got is None  # no other history+basic entry


def test_bank_miss_returns_none():
    assert draw_from_bank(_bank(), "economy", "basic", set(), [], TODAY, random.Random(0)) is None


def test_drafts_and_expired_are_excluded():
    bank = _bank()
    bank[0].status = "draft"  # the only history/basic entry is now a draft
    assert draw_from_bank(bank, "history", "basic", set(), [], TODAY, random.Random(0)) is None


def test_yield_weight_biases_frequency():
    bank = [
        _entry("history", "basic", "history/high", "Stem one about a thing.", yield_weight="high"),
        _entry("history", "basic", "history/low", "Different stem about another.", yield_weight="low"),
    ]
    rng = random.Random(42)
    picks = [draw_from_bank(bank, "history", "basic", set(), [], TODAY, rng).fact_key
             for _ in range(200)]
    assert picks.count("history/high") > picks.count("history/low")


def test_similar_stem_is_suppressed():
    bank = [
        _entry("history", "basic", "history/a", "Who was the 9th Prime Minister of India?"),
        _entry("history", "basic", "history/b", "What is the chemical symbol for gold?"),
    ]
    recent = ["Who was the 11th Prime Minister of India?"]
    rng = random.Random(1)
    picks = [draw_from_bank(bank, "history", "basic", set(), recent, TODAY, rng).fact_key
             for _ in range(50)]
    assert picks.count("history/b") > picks.count("history/a")
