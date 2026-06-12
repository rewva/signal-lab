import json

from selection.models import BankEntry, Question
from selection.bank import main


def _entry_dict(fk, status="draft"):
    q = Question("polity", "basic", fk, "X", "A specific stem about a topic here.", "a",
                 ["b", "c", "d"], ["SSC"], ["https://1", "https://2"],
                 explanation="e", source_citation="cite")
    e = BankEntry(question=q, static_class="permanent", source_tier=2,
                  yield_weight="high", status=status)
    return e.to_dict()


def _write_bank(path, entries):
    path.write_text(json.dumps(entries), encoding="utf-8")


def test_health_returns_zero(tmp_path, capsys):
    bank = tmp_path / "bank.json"
    _write_bank(bank, [_entry_dict("polity/a", status="verified")])
    rc = main(["--bank", str(bank), "--history", str(tmp_path / "h.json"), "health"])
    assert rc == 0
    assert "drawable" in capsys.readouterr().out.lower()


def test_verify_flips_status_and_persists(tmp_path):
    bank = tmp_path / "bank.json"
    _write_bank(bank, [_entry_dict("polity/a", status="draft")])
    rc = main(["--bank", str(bank), "--history", str(tmp_path / "h.json"),
               "verify", "polity/a"])
    assert rc == 0
    after = json.loads(bank.read_text(encoding="utf-8"))
    assert after[0]["status"] == "verified" and after[0]["verified_date"] is not None


def test_verify_unknown_fact_key_returns_one(tmp_path):
    bank = tmp_path / "bank.json"
    _write_bank(bank, [_entry_dict("polity/a")])
    rc = main(["--bank", str(bank), "--history", str(tmp_path / "h.json"),
               "verify", "polity/missing"])
    assert rc == 1
