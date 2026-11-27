import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "roihu"))
from xfam_client import derive, parse, parse_one  # noqa: E402

from xfam_inputs import schema  # noqa: E402

GOOD = {"id": "x00001", "agent": "yes", "data": "pooled", "objective": "multiple", "control": "decentralized", "interests": "several-conflicting",
        "has_decision_maker": "yes", "faces_other_parties": "yes", "faces_quote": "different users", "one_party_runs_all": "no", "owners": "several", "eval_run": "one", "cross_vendor": "no", "focus": "interaction", "boundary": "yes", "llm_basis": "yes", "confidence": "high", "quote": "agents representing different users"}
S = schema("x00001")


def test_valid_response_parses():
    assert parse_one(json.dumps(GOOD), S) == (GOOD, None)


def test_derive_owners_and_focus_from_the_three_answers():
    assert derive({**GOOD, "faces_other_parties": "yes", "has_decision_maker": "no"}) == {"owners_derived": "several", "focus_derived": "na"}
    assert derive({**GOOD, "faces_other_parties": "no", "has_decision_maker": "yes", "focus": "agent"}) == {"owners_derived": "one", "focus_derived": "agent"}
    assert derive({**GOOD, "faces_other_parties": "no", "has_decision_maker": "no"}) == {"owners_derived": "na", "focus_derived": "na"}
    assert derive({**GOOD, "faces_other_parties": "yes", "has_decision_maker": "yes", "focus": "na"})["focus_derived"] == "na"  # model's own na kept


def test_invalid_json_is_a_failure():
    rec, err = parse_one('{"id": "x00001", "agent": ', S)
    assert rec is None and err.startswith("invalid json")


def test_missing_key_is_a_failure():
    rec, err = parse_one(json.dumps({k: v for k, v in GOOD.items() if k != "eval_run"}), S)
    assert rec is None and "missing eval_run" in err


def test_enum_violation_and_wrong_id_are_failures():
    assert "owners='two'" in parse_one(json.dumps({**GOOD, "owners": "two"}), S)[1]
    assert "id='x00002'" in parse_one(json.dumps({**GOOD, "id": "x00002"}), S)[1]
    assert "unexpected note" in parse_one(json.dumps({**GOOD, "note": "x"}), S)[1]


def test_parse_pass_writes_records_and_failures(tmp_path):
    calls = tmp_path / "calls.jsonl"
    calls.write_text("".join(json.dumps({"call_id": x, "schema": schema(x)}) + "\n" for x in ("x00001", "x00002", "x00003")))
    res = tmp_path / "results"
    res.mkdir()
    (res / "x00001.json").write_text(json.dumps({"call_id": "x00001", "raw": json.dumps(GOOD)}))
    (res / "x00002.json").write_text(json.dumps({"call_id": "x00002", "raw": "not json"}))
    ok, bad = parse(calls, res, tmp_path / "results-parsed.jsonl", tmp_path / "failures.jsonl")
    assert (ok, bad) == (1, 2)
    assert [json.loads(l) for l in open(tmp_path / "results-parsed.jsonl")] == [{**GOOD, **derive(GOOD)}]
    fails = {f["call_id"]: f["error"] for f in map(json.loads, open(tmp_path / "failures.jsonl"))}
    assert fails["x00003"] == "no result" and fails["x00002"].startswith("invalid json")
