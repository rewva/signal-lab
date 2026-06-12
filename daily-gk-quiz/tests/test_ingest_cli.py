import json

from selection.models import BankEntry, Question
from selection.ingest import main


def _draft_dict(fk, stem):
    q = Question("polity", "basic", fk, "X", stem, "a", ["b", "c", "d"],
                 ["SSC"], ["https://a", "https://b"], explanation="why",
                 source_citation="cite")
    return BankEntry(question=q, static_class="permanent", source_tier=2,
                     yield_weight="high", status="draft").to_dict()


def test_ingest_cli_persists_drafts_and_returns_zero(tmp_path, capsys):
    batch = tmp_path / "batch.json"
    batch.write_text(json.dumps([_draft_dict("polity/a", "A distinct stem about a topic."),
                                 _draft_dict("polity/b", "Another stem on a separate matter.")]),
                     encoding="utf-8")
    bank = tmp_path / "bank.json"
    bank.write_text("[]", encoding="utf-8")
    rc = main(["--batch", str(batch), "--bank", str(bank), "--history", str(tmp_path / "h.json")])
    assert rc == 0
    saved = json.loads(bank.read_text(encoding="utf-8"))
    assert {e["question"]["fact_key"] for e in saved} == {"polity/a", "polity/b"}
    assert all(e["status"] == "draft" for e in saved)
    assert "accepted=2" in capsys.readouterr().out


def test_ingest_cli_all_rejected_returns_one(tmp_path):
    batch = tmp_path / "batch.json"
    q = Question("polity", "basic", "polity/x", "X", "stem here about things.", "a",
                 ["b", "c", "d"], ["SSC"], ["https://only"], explanation="w",
                 source_citation="c")
    bad = BankEntry(question=q, static_class="permanent", source_tier=2,
                    yield_weight="high", status="draft").to_dict()
    batch.write_text(json.dumps([bad]), encoding="utf-8")
    bank = tmp_path / "bank.json"
    bank.write_text("[]", encoding="utf-8")
    rc = main(["--batch", str(batch), "--bank", str(bank), "--history", str(tmp_path / "h.json")])
    assert rc == 1
