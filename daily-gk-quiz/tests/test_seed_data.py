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

def test_state_files_seed_empty_lists():
    assert json.loads((STATE / "question-history.json").read_text(encoding="utf-8")) == []
    assert json.loads((STATE / "question-bank.json").read_text(encoding="utf-8")) == []
