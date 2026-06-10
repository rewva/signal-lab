from selection.models import Question
from selection.selection import draw_from_bank

def _q(domain, diff, fk):
    return Question(domain, diff, fk, "X", "q?", "a",
                    ["b", "c", "d"], ["SSC"], ["https://1", "https://2"])

BANK = [
    _q("history", "basic", "history/plassey-1757"),
    _q("history", "advanced", "history/buxar-1764"),
    _q("polity", "basic", "polity/article-21"),
]

def test_draws_matching_domain_and_difficulty():
    got = draw_from_bank(BANK, "history", "basic", used_fact_keys=set())
    assert got is not None and got.fact_key == "history/plassey-1757"

def test_skips_already_used_fact_keys():
    got = draw_from_bank(BANK, "history", "basic",
                         used_fact_keys={"history/plassey-1757"})
    assert got is None  # no other history+basic entry

def test_bank_miss_returns_none():
    assert draw_from_bank(BANK, "economy", "basic", used_fact_keys=set()) is None
