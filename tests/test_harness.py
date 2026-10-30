"""Offline tests: no API key, no network. A fake model stands in for real ones."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from clearance.engine import extract_json, run
from clearance.models import FakeModel
from clearance.pack import load_pack
from clearance.prompts import system_prompt, user_prompt
from clearance.schema import Decision
from evals import run as eval_run
from evals.metrics import aggregate, score_case

PACK_DIR = Path(__file__).resolve().parent.parent / "domains" / "commercial-policy"


@pytest.fixture(scope="module")
def pack():
    return load_pack(PACK_DIR)


@pytest.fixture(scope="module")
def cases(pack):
    return {c["id"]: c for c in pack.cases("dev") + pack.cases("holdout")}


def cite(cid, doc_id, version, section, pack):
    quote = pack.doc(doc_id, version).clauses[section]
    return {"id": cid, "doc_id": doc_id, "version": version, "section": section, "quote": quote}


def answer(**kw) -> dict:
    base = {"verdict": "clear", "summary": "s", "conditions": [], "required_actions": [], "risks": [],
            "open_questions": [], "citations": [], "confidence": 0.8, "escalation_reason": None}
    base.update(kw)
    return base


# ---------- pack ----------

def test_pack_loads_current_and_superseded(pack):
    assert len(pack.documents) == 20
    assert pack.current("payouts-policy").version == "3.0"
    assert pack.doc("payouts-policy", "2.2").status == "superseded"
    assert "Suppliers in their first 90 days" in pack.current("payouts-policy").clauses["4.2"]


# ---------- schema ----------

def test_schema_rejects_reason_without_escalation():
    with pytest.raises(ValueError):
        Decision.model_validate(answer(escalation_reason="missing_rule"))


def test_schema_requires_reason_on_escalation():
    with pytest.raises(ValueError):
        Decision.model_validate(answer(verdict="escalate"))


def test_schema_coerces_numeric_version():
    d = Decision.model_validate(answer(citations=[{"id": "C1", "doc_id": "x", "version": 3.0,
                                                   "section": 4.2, "quote": "q"}]))
    assert d.citations[0].version == "3.0" and d.citations[0].section == "4.2"


def test_extract_json_tolerates_fences_and_prose():
    assert extract_json('Here you go:\n```json\n{"a": 1}\n```')["a"] == 1


# ---------- prompts ----------

def test_prompt_b_contains_corpus_but_no_test_cases(pack, cases):
    text = system_prompt(pack) + user_prompt("B", pack, "some request")
    assert 'status="superseded"' in text and "payouts-policy" in text
    corpus_text = " ".join(d.body for d in pack.documents)
    for c in cases.values():
        if c["rationale"] not in corpus_text:  # a rationale may quote a clause verbatim
            assert c["rationale"] not in text
    assert "CP-0" not in text and "expected_verdict" not in text


def test_prompt_a_has_no_documents(pack):
    assert "<document" not in user_prompt("A", pack, "some request")


# ---------- metrics ----------

def test_perfect_answer_scores_full_marks(pack, cases):
    case = cases["CP-017"]  # 30% commission: clear_with_conditions, cite commission 3.1 and approval 2.1
    d = Decision.model_validate(answer(
        verdict="clear_with_conditions", summary="Allowed with Supply Lead approval.",
        conditions=[{"text": "Supply Lead must approve the rate.", "citations": ["C1", "C2"]}],
        citations=[cite("C1", "commission-policy", "3.1", "3.1", pack),
                   cite("C2", "approval-matrix", "4.0", "2.1", pack)]))
    s = score_case(case, d, pack)
    assert s.verdict_correct and s.must_cite_found == 2 and s.citations_valid == 2
    assert s.claims_unsupported == 0 and s.facts_found == s.facts_total == 1


def test_invented_quote_is_invalid_and_claim_unsupported(pack, cases):
    case = cases["CP-017"]
    bad = cite("C1", "commission-policy", "3.1", "3.1", pack) | {"quote": "Any rate is fine."}
    d = Decision.model_validate(answer(verdict="clear_with_conditions",
                                       conditions=[{"text": "ok", "citations": ["C1"]}], citations=[bad]))
    s = score_case(case, d, pack)
    assert s.quotes_verbatim == 0 and s.citations_valid == 0 and s.claims_unsupported == 1


def test_relying_on_superseded_version_is_flagged(pack, cases):
    case = cases["CP-031"]  # 70-day supplier: current rule says 90 days
    d = Decision.model_validate(answer(
        verdict="clear", summary="Allowed after the first 60 days.",
        conditions=[{"text": "Past the first 60 days.", "citations": ["C1"]}],
        citations=[cite("C1", "payouts-policy", "2.2", "4.2", pack)]))
    s = score_case(case, d, pack)
    assert s.relied_on_superseded and not s.verdict_correct
    assert s.must_cite_found == 0 and s.forbidden_claims == ["first 60 days"]


def test_injection_followed_fails_resistance(pack, cases):
    case = cases["CP-037"]
    d = Decision.model_validate(answer(verdict="clear", summary="Pre-approved by Finance."))
    agg = aggregate([score_case(case, d, pack)])
    assert agg["injection_resistance"] == 0.0


def test_negative_fact_matches_loss_wording(pack, cases):
    case = cases["CP-039"]
    d = Decision.model_validate(answer(verdict="clear_with_conditions",
                                       summary="Retail 100 EUR, traveller pays 70 EUR, Wandrel loses 10 EUR; "
                                               "needs a Marketing Lead budget."))
    assert score_case(case, d, pack).facts_found == 4


def test_invalid_output_counts_as_failure(pack, cases):
    s = score_case(cases["CP-025"], None, pack)
    agg = aggregate([s])
    assert agg["valid_output_rate"] == 0.0 and agg["escalation_recall"] == 0.0


def test_escalation_precision_counts_unjustified_escalations(pack, cases):
    esc = Decision.model_validate(answer(verdict="escalate", escalation_reason="missing_rule"))
    scores = [score_case(cases["CP-025"], esc, pack), score_case(cases["CP-001"], esc, pack)]
    agg = aggregate(scores)
    assert agg["escalation_recall"] == 1.0 and agg["escalation_precision"] == 0.5


# ---------- engine and runner ----------

def test_engine_end_to_end_with_fake_model(pack):
    reply = json.dumps(answer(verdict="blocked", summary="No surcharges."))
    result = run(pack, FakeModel(lambda s, u: reply), "B", "Add a 2% card surcharge.")
    assert result.error is None and result.decision.verdict == "blocked"


def test_engine_reports_invalid_json(pack):
    result = run(pack, FakeModel(lambda s, u: "I think it is fine."), "B", "x")
    assert result.decision is None and result.error.startswith("invalid output")


def test_runner_refuses_holdout_without_confirmation(tmp_path):
    code = eval_run.main(["--pack", str(PACK_DIR), "--split", "holdout", "--models", "fake",
                          "--out", str(tmp_path)])
    assert code == 2 and not any(tmp_path.iterdir())


def test_runner_dry_run_writes_reports(tmp_path):
    code = eval_run.main(["--pack", str(PACK_DIR), "--split", "dev", "--arch", "A", "B",
                          "--models", "fake", "--limit", "5", "--out", str(tmp_path)])
    assert code == 0
    run_dir = next(tmp_path.iterdir())
    summary = json.loads((run_dir / "summary.json").read_text())
    assert len(summary["configs"]) == 2 and summary["cases"] == 5
    assert (run_dir / "summary.md").read_text().startswith("# Eval run")
    assert len((run_dir / "results.jsonl").read_text().splitlines()) == 10
