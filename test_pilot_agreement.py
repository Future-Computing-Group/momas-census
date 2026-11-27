import hashlib
import json
import math

import pytest

import pilot_agreement as pa


def test_alpha_perfect_agreement_is_one():
    assert pa.alpha(list("aabbc"), list("aabbc")) == 1.0


def test_alpha_hand_computed_2x2():
    # pairs (a,a) (a,b) (b,b) (b,b): o_aa=2, o_ab=o_ba=1, o_bb=4; n_a=3, n_b=5, n=8; alpha = 1 - 7*2/(2*3*5) = 8/15
    assert pa.alpha(list("aabb"), list("abbb")) == pytest.approx(8 / 15)


def test_alpha_systematic_disagreement_negative():
    # pairs (a,b) (b,a): o_ab=o_ba=2; n_a=n_b=2, n=4; alpha = 1 - 3*4/8 = -0.5
    assert pa.alpha(list("ab"), list("ba")) == pytest.approx(-0.5)


def test_alpha_single_value_is_undefined():
    assert math.isnan(pa.alpha(list("aaa"), list("aaa")))


def rec(s, p, beh="rational", inter="yes", att="no", rb=None):
    r = {"policy_setters": s, "principals": p, "behaviour": beh, "interacting": inter, "outside_attacker": att,
         "partners_from_others": "no"}
    return r if rb is None else {**r, "rule_breaking": rb}


def test_cells():
    assert pa.cell(rec("several", "several")) == "several-rational"
    assert pa.cell(rec("several", "several", beh="mixed")) == "several-rational"
    assert pa.cell(rec("several", "several", beh="not-stated")) == "several-other"
    assert pa.cell(rec("one", "several")) == "simulated"
    assert pa.cell(rec("one", "several", inter="no")) == "single-learner"
    assert pa.cell(rec("several", "several", att="yes")) == "excluded-attacker"
    assert pa.cell(rec("one", "one", inter="no")) == "rest"


def test_cells_v22_rule_breaking_splits_the_several_cell():
    # rule R5: a rule-breaker for gain stays in the several cell, apart from the within-the-rules rational share
    assert pa.cell(rec("several", "several", rb="yes")) == "several-rule-breaking"
    assert pa.cell(rec("several", "several", beh="byzantine", rb="yes")) == "several-rule-breaking"
    assert pa.cell(rec("several", "several", rb="no")) == "several-rational"
    assert pa.cell(rec("several", "several", beh="not-stated", rb="no")) == "several-other"
    assert pa.cell(rec("several", "several", att="yes", rb="yes")) == "excluded-attacker"
    # rule R6 SI count: setters one, behaviour rational, interacting yes
    assert pa.rational_prescribed(rec("one", "several")) == "yes"
    assert pa.rational_prescribed(rec("one", "one")) == "yes"
    assert pa.rational_prescribed(rec("one", "several", inter="no")) == "no"
    assert pa.rational_prescribed(rec("several", "several")) == "no"
    assert pa.rational_prescribed(rec("one", "several", beh="obedient")) == "no"


def pilot_fixture():
    pilot = {"disputed": [{"id": "p1", "clusters": ["K1"], "part": "a"}, {"id": "p2", "clusters": ["K10"], "part": "d"},
                          {"id": "p3", "clusters": ["K9"], "part": "n"}], "random": ["r1"]}
    implied = [{"id": "p1", "field": "policy_setters", "code": "one", "rule": "dyn"},
               {"id": "p2", "field": "interacting", "code": "no", "rule": "k10"},
               {"id": "p3", "field": "policy_setters", "code": "one|na", "rule": "k4"}]
    A = {"p1": rec("one", "several"), "p2": rec("one", "several", inter="no"), "p3": rec("na", "na", att="yes"), "r1": rec("one", "one")}
    B = {**A, "p1": rec("several", "several")}
    return pilot, implied, A, B


def test_report_conformance_and_slice():
    pilot, implied, A, B = pilot_fixture()
    rep = pa.report(pilot, implied, A, B)
    assert rep["conformance"]["A"]["all"]["share"] == 1.0
    assert rep["conformance"]["B"]["all"]["misses"] == ["p1"]
    assert rep["conformance"]["B"]["dyn"]["share"] == 0.0
    assert rep["k10_interacting_no_both"] == (1, 1)
    assert rep["slice"]["p2"]["agree_all"] is True
    assert rep["overall"]["policy_setters"]["raw"] == 0.75
    assert rep["clusters"]["K1/K1m"]["cell"]["raw"] == 0.0


def test_report_refuses_missing_coder_ids():
    pilot, implied, A, B = pilot_fixture()
    del B["r1"]
    with pytest.raises(SystemExit):
        pa.report(pilot, implied, A, B)


def test_sha_mismatch_refuses(tmp_path):
    p = tmp_path / "implied.jsonl"
    p.write_text(json.dumps({"id": "p1"}) + "\n")
    good = {"implied_sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
    pa.check_sha(good, str(p))
    p.write_text(json.dumps({"id": "p2"}) + "\n")
    with pytest.raises(SystemExit):
        pa.check_sha(good, str(p))


def test_shipped_files_match():
    pilot = json.load(open(pa.IDS))
    pa.check_sha(pilot)
    assert len(pilot["disputed"]) == 137 and len(pilot["random"]) == 40
    assert pilot["codebook_sha256"] == hashlib.sha256(open(pa.HERE + "/codebook-policy-v2.md", "rb").read()).hexdigest()


# Round 3 (01-design.md §5.4 step 3): fresh 40 plus the re-tested pilot disagreements, on codebook v2.1.
def round3_fixture():
    pilot, implied, A2, B2 = pilot_fixture()
    p3 = {"retest": [{"id": "p1", "reason": "x"}], "fresh": ["f1", "f2"]}
    implied3 = [{"id": "f1", "field": "policy_setters", "code": "several", "rule": "eq"}]
    A3 = {"p1": rec("one", "several"), "f1": rec("several", "several"), "f2": rec("one", "one")}
    B3 = {**A3, "f2": rec("one", "several", inter="no")}
    return p3, pilot, implied, implied3, A2, B2, A3, B3


def test_report3_fresh_retest_and_composite_pilot():
    p3, pilot, implied, implied3, A2, B2, A3, B3 = round3_fixture()
    rep = pa.report3(p3, pilot, implied, implied3, A2, B2, A3, B3)
    assert rep["fresh"]["cell"]["raw"] == 0.5 and rep["fresh"]["n"] == 2
    assert rep["fresh_conformance"]["A"]["all"]["share"] == 1.0
    assert rep["retest"]["policy_setters"]["raw"] == 1.0
    # p1 disagreed in round 2 (B2 several); round-3 codes replace it, so the composite pilot agrees on all four papers
    assert rep["pilot"]["policy_setters"]["raw"] == 1.0 and rep["pilot"]["n"] == 4
    assert rep["pilot_conformance"]["B"]["all"]["misses"] == []


def test_report3_v22_rule_breaking_fields_and_implied_2b():
    p3, pilot, implied, implied3, A2, B2, A3, B3 = round3_fixture()
    A3 = {k: {**v, "rule_breaking": "no"} for k, v in A3.items()}
    B3 = {k: {**v, "rule_breaking": "no"} for k, v in B3.items()}
    B3["f1"] = {**B3["f1"], "rule_breaking": "yes"}
    implied2b = [{"id": "p1", "field": "rule_breaking", "code": "no", "rule": "R5"},
                 {"id": "p3", "field": "outside_attacker", "code": "no", "rule": "R5"}]
    rep = pa.report3(p3, pilot, implied, implied3, A2, B2, A3, B3, implied2b=implied2b)
    assert rep["fresh"]["rule_breaking"]["raw"] == 0.5 and rep["fresh"]["rule_breaking"]["n"] == 2
    assert rep["fresh"]["cell"]["raw"] == 0.0  # f1: several-rational vs several-rule-breaking; f2 as before
    assert rep["fresh"]["rational_prescribed"]["raw"] == 0.5
    # the composite pilot has rule_breaking only on the re-tested p1 (round-2 codes predate the field)
    assert rep["pilot"]["rule_breaking"]["n"] == 1 and rep["pilot"]["policy_setters"]["n"] == 4
    assert rep["retest_conformance_2b"]["A"]["all"] == {"n": 1, "hits": 1, "misses": [], "share": 1.0}
    assert rep["pilot_conformance_2b"]["A"]["all"]["misses"] == ["p3"]  # p3 kept its round-2 code, attacker yes


def test_round2_compare_has_no_rule_breaking_key():
    pilot, implied, A, B = pilot_fixture()
    assert "rule_breaking" not in pa.report(pilot, implied, A, B)["overall"]


def test_report3_against_adjudicated():
    p3, pilot, implied, implied3, A2, B2, A3, B3 = round3_fixture()
    adj = {"p1": rec("several", "several")}
    rep = pa.report3(p3, pilot, implied, implied3, A2, B2, A3, B3, adj)
    assert rep["retest_vs_adjudicated"]["A"]["policy_setters"] == 0.0
    assert rep["retest_vs_adjudicated"]["A"]["principals"] == 1.0
    assert rep["retest_vs_adjudicated"]["A"]["cell"] == 0.0


def test_report3_refuses_missing_ids():
    p3, pilot, implied, implied3, A2, B2, A3, B3 = round3_fixture()
    del A3["f2"]
    with pytest.raises(SystemExit):
        pa.report3(p3, pilot, implied, implied3, A2, B2, A3, B3)


def test_check_sha3_refuses_mismatch(tmp_path):
    p = tmp_path / "implied3.jsonl"
    p.write_text(json.dumps({"id": "f1"}) + "\n")
    good = {"implied_3_sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
    pa.check_sha(good, str(p), "implied_3_sha256")
    p.write_text(json.dumps({"id": "f2"}) + "\n")
    with pytest.raises(SystemExit):
        pa.check_sha(good, str(p), "implied_3_sha256")


def test_shipped_round3_files_match():
    p3 = json.load(open(pa.IDS3))
    pilot = json.load(open(pa.IDS))
    pa.check_sha(p3)
    pa.check_sha(p3, pa.IMPLIED3, "implied_3_sha256")
    assert len(p3["fresh"]) == 40 and len(p3["retest"]) == 24
    old = {d["id"] for d in pilot["disputed"]} | set(pilot["random"])
    assert not set(p3["fresh"]) & old and {r["id"] for r in p3["retest"]} <= old
    pa.check_sha(p3, pa.IMPLIED2B, "implied_2b_sha256")
    assert p3["codebook"] == "codebook-policy-v2.2.md"
    assert p3["codebook_sha256"] == hashlib.sha256(open(pa.HERE + "/codebook-policy-v2.2.md", "rb").read()).hexdigest()
    implied3 = [json.loads(l) for l in open(pa.IMPLIED3) if l.strip()]
    assert {r["id"] for r in implied3} <= set(p3["fresh"])
    implied2b = [json.loads(l) for l in open(pa.IMPLIED2B) if l.strip()]
    assert {r["id"] for r in implied2b} <= {r["id"] for r in p3["retest"]} | {"x04926", "x01284", "x04296"}
    adj = {r["id"]: r for r in map(json.loads, open(pa.ADJUDICATED22))}
    assert set(adj) == old and all(r.get("rule_breaking") in ("yes", "no", "na") for r in adj.values())
    # the adjudicated v2.2 codes conform to every implied code they cover (2b on the pilot papers)
    assert all(adj[r["id"]][r["field"]] in r["code"].split("|") for r in implied2b)
    briefs = [json.loads(l) for l in open(pa.HERE + "/data/batches/pilot3-briefs.jsonl")]
    assert len(briefs) == 4 and all("codebook-policy-v2.2.md" in b["brief"] and "v2.1" not in b["brief"] for b in briefs)
    batches = {x["id"] for c in "AB" for f in sorted(__import__("glob").glob(pa.HERE + f"/data/batches/pilot3-{c}-*.json")) for x in json.load(open(f))}
    assert batches == set(p3["fresh"]) | {r["id"] for r in p3["retest"]}


def test_pilot_fragments_carry_the_sizes_and_the_round3_agreement():
    F = lambda a, raw_cell: {**{f: {"alpha": a.get(f, 1.0), "raw": 1.0, "n": 2} for f in pa.FIELDS3}, "cell": {"alpha": 0.9, "raw": raw_cell, "n": 2}}
    pilot = {"disputed": [{"id": f"d{n}"} for n in range(5)], "random": ["r1", "r2"]}
    p3 = {"retest": [{"id": "d1"}, {"id": "d2"}], "fresh": ["f1", "f2", "f3"]}
    rep = {"fresh": F({"principals": 0.8454, "outside_attacker": math.nan}, 0.975), "retest": F({"partners_from_others": 0.6519}, 0.875)}
    fr = pa.fragments(pilot, p3, rep)
    assert fr["pilot-n.tex"] == "7" and fr["pilot-disputed.tex"] == "5" and fr["pilot-random.tex"] == "2"
    assert fr["pilot-retest-n.tex"] == "2" and fr["pilot-fresh-n.tex"] == "3" and fr["pilot-round3-n.tex"] == "5"
    assert fr["pilot-fresh.tex"] == "$\\alpha$ from 0.85 to 1.00; cell agreement 97.5\\%"  # an undefined alpha is left out
    assert fr["pilot-retest.tex"] == "$\\alpha$ from 0.65 to 1.00; cell agreement 87.5\\%"


@pytest.mark.skipif(not __import__("os").path.exists(pa.IDS3), reason="needs the local pilot files")
def test_pilot_fragments_on_the_stored_pilot():
    fr = pa.fragments(*pa.round3())
    assert (fr["pilot-n.tex"], fr["pilot-disputed.tex"], fr["pilot-random.tex"], fr["pilot-retest-n.tex"], fr["pilot-round3-n.tex"]) == ("177", "137", "40", "24", "64")
    assert fr["pilot-fresh.tex"] == "$\\alpha$ from 0.85 to 1.00; cell agreement 97.5\\%"
