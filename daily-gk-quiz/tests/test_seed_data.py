import json
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
STATE = Path(__file__).resolve().parent.parent / "state"

def test_domain_weights_sum_to_100():
    weights = json.loads((DATA / "domains.json").read_text(encoding="utf-8"))["weights"]
    assert sum(weights.values()) == 100

def test_domains_include_the_blueprint_set():
    weights = json.loads((DATA / "domains.json").read_text(encoding="utf-8"))["weights"]
    assert "current-affairs" in weights and "banking-financial-awareness" in weights

def test_prompts_have_hooks_and_ctas():
    p = json.loads((DATA / "prompts.json").read_text(encoding="utf-8"))
    assert len(p["hooks"]) >= 3 and len(p["ctas"]) >= 3

def test_state_files_seed():
    # question-history starts empty; question-bank is pre-seeded with verified anchor facts
    assert json.loads((STATE / "question-history.json").read_text(encoding="utf-8")) == []
    bank = json.loads((STATE / "question-bank.json").read_text(encoding="utf-8"))
    assert isinstance(bank, list) and len(bank) >= 16

def test_every_weighted_domain_has_a_label():
    data = json.loads((DATA / "domains.json").read_text(encoding="utf-8"))
    assert "labels" in data, "domains.json must carry a display-label map"
    for slug in data["weights"]:
        assert slug in data["labels"], f"missing label for domain {slug}"
        assert data["labels"][slug].strip(), f"empty label for domain {slug}"
