"""Policy pass v2 (codebook-policy-v2.md or a later revision, a parameter): output contract, schema, calls builder, quote
check, client parsing and the derived cells of the v2 pass. The v1 constants, calls, outputs and estimate keys stay as they are."""
import hashlib
import json
import os
import re
import subprocess
import sys

import pytest

sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
from xfam_inputs import POLICY2_CODEBOOK

V2 = open(POLICY2_CODEBOOK).read()  # the pinned revision (v2.2, rules R5 to R10)


def test_v2_keys_and_enums_follow_the_output_line_of_the_codebook():
    from xfam_inputs import QUOTES_V2, V2_ENUMS, V2_KEYS
    line = next(l for l in V2.splitlines() if l.startswith("Output one JSON object"))
    assert V2_KEYS == re.findall(r'"(\w+)"', line.split("exactly these keys:")[1].split(". Values")[0])
    assert V2_KEYS == ["id", "policy_setters", "policy_quote", "principals", "principals_quote", "behaviour", "behaviour_quote",
                       "rule_breaking", "interacting", "outside_attacker", "partners_from_others"]
    values = line.split("Values:")[1].split(". ")[0]
    for k, vals in V2_ENUMS.items():
        assert re.search(rf"\b{k} {' / '.join(map(re.escape, vals))}(;|$)", values), k  # same values, same order as the codebook
    assert set(V2_ENUMS) | set(QUOTES_V2) | {"id"} == set(V2_KEYS)
    assert V2_ENUMS["behaviour"] == ["obedient", "rational", "byzantine", "mixed", "not-stated", "na"] and V2_ENUMS["outside_attacker"] == ["yes", "no"]
    assert V2_ENUMS["rule_breaking"] == ["yes", "no", "na"]


def test_v2_schema_pins_the_id_requires_every_key_and_keeps_v1_untouched():
    from xfam_inputs import POLICY_KEYS, V2_ENUMS, V2_KEYS, schema_policy, schema_policy2
    s = schema_policy2("z00007")
    assert s["required"] == V2_KEYS == list(s["properties"]) and s["additionalProperties"] is False
    assert s["properties"]["id"] == {"type": "string", "const": "z00007"}
    assert all(s["properties"][k] == {"type": "string", "enum": v} for k, v in V2_ENUMS.items())
    assert all(s["properties"][k] == {"type": "string"} for k in ("policy_quote", "principals_quote", "behaviour_quote"))
    assert schema_policy("z00007")["required"] == POLICY_KEYS  # v1 schema unchanged


def test_v2_call_is_the_codebook_verbatim_with_the_v1_user_message():
    from xfam_inputs import INSTRUCTION, call_policy, call_policy2
    it = {"xid": "x00001", "venue": "neurips-2025", "main_track": True, "title": "T", "abstract": "A b.", "sample_id": "q1"}
    c = call_policy2(it, V2)
    assert c["messages"][0]["content"] == V2.rstrip("\n") + "\n\n" + INSTRUCTION
    assert c["messages"][1] == call_policy(it, "x")["messages"][1] and c["call_id"] == "x00001"
    assert c["schema"]["required"][5] == "behaviour"


def test_quote_check_covers_all_three_v2_quotes_and_v1_still_two():
    from xfam_inputs import QUOTES_V2, quotes_verbatim
    it = {"title": "Two Owners", "abstract": "Bidders  best respond to prices."}
    ok = {"policy_quote": "two owners", "principals_quote": "", "behaviour_quote": "bidders best respond"}
    assert quotes_verbatim(ok, it, QUOTES_V2)
    assert not quotes_verbatim({**ok, "behaviour_quote": "players are rational"}, it, QUOTES_V2)
    assert quotes_verbatim({**ok, "behaviour_quote": "players are rational"}, it)  # v1 default reads only its two quotes


def test_client_parses_a_v2_record_schema_driven_without_the_v34_derivation():
    sys.path.insert(0, "roihu")
    from xfam_client import parse_one
    from xfam_inputs import schema_policy2
    r = {"id": "y00003", "policy_setters": "several", "policy_quote": "q", "principals": "several", "principals_quote": "",
         "behaviour": "not-stated", "behaviour_quote": "", "rule_breaking": "no", "interacting": "yes", "outside_attacker": "no", "partners_from_others": "na"}
    assert parse_one(json.dumps(r), schema_policy2("y00003")) == (r, None)
    assert parse_one(json.dumps({**r, "behaviour": "selfish"}), schema_policy2("y00003"))[0] is None
    assert parse_one(json.dumps({**r, "outside_attacker": "na"}), schema_policy2("y00003"))[0] is None
    assert "missing behaviour_quote" in parse_one(json.dumps({k: v for k, v in r.items() if k != "behaviour_quote"}), schema_policy2("y00003"))[1]
    assert "missing rule_breaking" in parse_one(json.dumps({k: v for k, v in r.items() if k != "rule_breaking"}), schema_policy2("y00003"))[1]
    assert parse_one(json.dumps({**r, "rule_breaking": "maybe"}), schema_policy2("y00003"))[0] is None


V1_RUN = all(os.path.exists(p) for p in ("data/xfam/calls-policy.jsonl", "data/xfam/policy-v1/results-parsed.jsonl", "data/xfam/policy-v1/results"))


@pytest.mark.skipif(not V1_RUN, reason="needs the local v1 screen run (gitignored)")
def test_reparse_of_the_stored_v1_raw_output_is_byte_identical(tmp_path):
    sys.path.insert(0, "roihu")
    from xfam_client import parse
    d = "data/xfam/policy-v1"
    assert parse("data/xfam/calls-policy.jsonl", f"{d}/results", tmp_path / "p.jsonl", tmp_path / "f.jsonl") == (16507, 4)
    assert (tmp_path / "p.jsonl").read_bytes() == open(f"{d}/results-parsed.jsonl", "rb").read()
    assert (tmp_path / "f.jsonl").read_bytes() == open(f"{d}/failures.jsonl", "rb").read()


# ---- calls builder (synthetic frame, run in a temporary directory) ----

def frame(tmp_path, monkeypatch, codebook=V2):
    (tmp_path / "data/xfam").mkdir(parents=True)
    (tmp_path / "data/pilot").mkdir(parents=True)
    rows = {"items-full.jsonl": [f"x{i:05d}" for i in (3, 1, 2)], "items-ext.jsonl": ["y00002", "y00001"], "items-ext-ea.jsonl": ["z00001"]}
    for f, ids in rows.items():
        (tmp_path / "data/xfam" / f).write_text("".join(json.dumps({"xid": i, "title": f"T {i}", "abstract": f"A {i}."}) + "\n" for i in ids))
    (tmp_path / "data/xfam/calls-policy-smoke100.jsonl").write_text("".join(json.dumps({"call_id": i}) + "\n" for i in ("x00002", "y00001")))
    (tmp_path / "data/pilot/pilot-ids.json").write_text(json.dumps({"disputed": [{"id": "y00002", "clusters": ["K1"], "part": "a"}, {"id": "x00003", "clusters": ["K9"], "part": "n"}], "random": ["z00001", "x00001"], "codebook_sha256": "-"}))
    (tmp_path / "cb.md").write_text(codebook)
    monkeypatch.chdir(tmp_path)
    return [i for ids in rows.values() for i in ids]


def test_policy2_writes_calls_in_items_order_two_smokes_and_a_manifest(tmp_path, monkeypatch):
    import xfam_inputs
    order = frame(tmp_path, monkeypatch)
    xfam_inputs.main_policy2("cb.md", sha=sha("cb.md"), n_pilot=3)
    out = tmp_path / "data/xfam"
    calls = [json.loads(l) for l in open(out / "calls-policy2.jsonl")]
    assert [c["call_id"] for c in calls] == order
    assert all(c["messages"][0]["content"] == V2.rstrip("\n") + "\n\n" + xfam_inputs.INSTRUCTION for c in calls)
    assert all(c["schema"] == xfam_inputs.schema_policy2(c["call_id"]) for c in calls)
    by = {c["call_id"]: c for c in calls}
    smoke = [json.loads(l) for l in open(out / "calls-policy2-smoke100.jsonl")]
    assert [c["call_id"] for c in smoke] == ["x00002", "y00001"] and all(c == by[c["call_id"]] for c in smoke)
    pilot = [json.loads(l)["call_id"] for l in open(out / "calls-policy2-pilot100.jsonl")]
    assert pilot == ["x00001", "x00003", "y00002"]  # the first n in sorted order of disputed + random
    man = dict(reversed(l.split("  ")) for l in (out / "policy2-sha256.txt").read_text().splitlines())
    assert set(man) == {"calls-policy2.jsonl", "calls-policy2-smoke100.jsonl", "calls-policy2-pilot100.jsonl", "cb.md"}
    assert man["cb.md"] == sha("cb.md") and man["calls-policy2.jsonl"] == sha(out / "calls-policy2.jsonl")
    assert not (out / "calls-policy.jsonl").exists()  # the v1 calls are never rebuilt


def test_policy2_refuses_a_codebook_whose_sha_is_not_the_pinned_one(tmp_path, monkeypatch):
    import xfam_inputs
    frame(tmp_path, monkeypatch, V2 + "\nedited\n")
    with pytest.raises(AssertionError, match="pinned"):
        xfam_inputs.main_policy2("cb.md")
    assert not (tmp_path / "data/xfam/calls-policy2.jsonl").exists()


def test_the_pinned_codebook_is_the_pinned_sha():
    from xfam_inputs import POLICY2_CODEBOOK, POLICY2_SHA
    assert POLICY2_CODEBOOK == "codebook-policy-v2.2.md" and sha(POLICY2_CODEBOOK) == POLICY2_SHA
    man = dict(reversed(l.split("  ")) for l in open("data/xfam/policy2-sha256.txt").read().splitlines())
    assert man == {**{k: v for k, v in man.items() if k.startswith("calls-")}, "codebook-policy-v2.2.md": POLICY2_SHA}  # manifest rebuilt on v2.2


HAVE = os.path.exists("data/xfam/calls-policy2.jsonl") and os.path.exists("data/xfam/calls-policy.jsonl")


@pytest.mark.skipif(not HAVE, reason="needs the generated v1 and v2 calls (gitignored)")
def test_generated_v2_calls_match_v1_ids_and_messages_and_carry_the_v2_schema():
    from xfam_inputs import POLICY2_CODEBOOK, schema_policy2
    v1 = [json.loads(l) for l in open("data/xfam/calls-policy.jsonl")]
    v2 = [json.loads(l) for l in open("data/xfam/calls-policy2.jsonl")]
    assert [c["call_id"] for c in v2] == [c["call_id"] for c in v1] and len(v2) == 16511
    import re
    rules = lambda t: re.sub(r"\(20\d\d-\d\d-\d\d,[^)]*\)", "()", t)  # the dated provenance notes of the changelog lines were edited for release
    sysmsg = rules(open(POLICY2_CODEBOOK).read().rstrip("\n"))
    assert all(b["messages"][1] == a["messages"][1] and rules(b["messages"][0]["content"]).startswith(sysmsg) and b["schema"] == schema_policy2(b["call_id"])
               for a, b in zip(v1, v2))
    s1 = [json.loads(l)["call_id"] for l in open("data/xfam/calls-policy-smoke100.jsonl")]
    assert [json.loads(l)["call_id"] for l in open("data/xfam/calls-policy2-smoke100.jsonl")] == s1
    p = json.load(open("data/pilot/pilot-ids.json"))
    assert [json.loads(l)["call_id"] for l in open("data/xfam/calls-policy2-pilot100.jsonl")] == sorted([x["id"] for x in p["disputed"]] + p["random"])[:100]


# ---- derived cells of the v2 pass ----

def r2(ps="one", pr="one", behaviour="na", interacting="no", attacker="no", interests="one", focus="agent", rb="no"):
    return {"policy_setters": ps, "principals": pr, "behaviour": behaviour, "rule_breaking": rb, "interacting": interacting,
            "outside_attacker": attacker, "interests": interests, "focus": focus}


def test_policy2_measures_follow_the_design():
    from twostage import POLICY2_MEASURES as M
    assert set(M) == {"several", "several_rational_within", "several_rule_breaking", "simulated", "single_learner_several_principals",
                      "rational_prescribed", "several_v34_exclusion", "conflicting", "interaction", "setters_one", "principals_one"}
    bidders = r2("several", "several", "rational", "yes", interests="several-conflicting", focus="interaction")
    on = {k for k, f in M.items() if f(bidders)}
    assert on == {"several", "several_rational_within", "several_v34_exclusion", "conflicting", "interaction"}
    w = M["several_rational_within"]
    assert w(r2("several", "several", "mixed")) and not w(r2("several", "several", "not-stated"))
    # rule R5: a rule-breaker for gain stays in the several cell, outside the within-the-rules population of Box 2
    cheat = r2("several", "several", "rational", "yes", interests="adversarial", rb="yes")
    assert {k for k, f in M.items() if f(cheat)} == {"several", "several_rule_breaking", "conflicting"}
    assert not w(r2("several", "several", "rational", rb="na")) and not M["several_rule_breaking"](r2("several", "several", "rational", attacker="yes", rb="yes"))
    # rule R6: rational players all running the prescribed algorithm, counted beside (never in) the self-interested share
    assert {k for k, f in M.items() if f(r2("one", "several", "rational", "yes"))} == {"simulated", "rational_prescribed", "setters_one"}
    assert not M["rational_prescribed"](r2("one", "several", "rational", "no")) and not M["rational_prescribed"](r2("one", "several", "obedient", "yes"))
    side_by_side = r2("several", "several", "not-stated", "no")  # several vendors' models evaluated side by side: in the cell
    assert M["several"](side_by_side) and not M["interaction"](side_by_side)
    deviator = r2("several", "several", "rational", "yes", interests="adversarial")  # gain-motivated deviator: conflicting (codebook v2)
    assert M["several"](deviator) and M["conflicting"](deviator)
    assert not M["several_v34_exclusion"](deviator)  # codebook v2: the v3.4 exclusion drops it, reported as an SI sensitivity row
    attacker = r2("several", "several", "byzantine", "yes", "yes", "adversarial", "interaction")
    assert {k for k, f in M.items() if f(attacker)} == set()
    assert M["several_v34_exclusion"](r2("several", "several", "byzantine", attacker="yes", interests="several-conflicting"))
    lab = r2("one", "several", "obedient", "yes")
    fl = r2("one", "several", "na", "no")
    assert {k for k, f in M.items() if f(lab)} == {"simulated", "setters_one"}
    assert {k for k, f in M.items() if f(fl)} == {"single_learner_several_principals", "setters_one"}
    assert not any(M[k](r2("one", "several", interacting="na")) for k in ("simulated", "single_learner_several_principals"))  # G4 residual
    assert not M["simulated"](r2("one", "several", "obedient", "yes", "yes"))
    assert {k for k, f in M.items() if f(r2())} == {"setters_one", "principals_one"}


def test_join_accepts_the_v2_key_set_and_still_rejects_a_v34_field():
    from twostage import join_policy
    from xfam_inputs import V2_KEYS
    pol = {"x1": {**dict.fromkeys(V2_KEYS, "no"), "id": "x1"}}
    j = join_policy({"x1": {"id": "x1", "interests": "one"}}, pol, set(V2_KEYS))
    assert j["x1"]["interests"] == "one" and j["x1"]["behaviour"] == "no"
    with pytest.raises(AssertionError):
        join_policy({}, pol)  # the v1 key set refuses v2 records
    with pytest.raises(AssertionError):
        join_policy({}, {"x1": {"id": "x1", "focus": "agent"}}, set(V2_KEYS))


def test_load_policy2_reads_the_v2_screen_and_policy2_codes_never_dup(tmp_path, monkeypatch):
    import twostage
    items = {i: {"xid": i, "venue": "neurips-2025", "main_track": True} for i in ("x1", "x2", "x3", "x4")}
    s34 = {i: {"id": i, "owners_derived": "one", "agent": "yes", "llm_basis": "no"} for i in items}
    part = {"x1": "a", "x3": "c", "x4": "c"}
    claude = {i: {"id": i, "interests": "one", "focus": "agent"} for i in part}
    monkeypatch.setattr(twostage, "load", lambda: (items, s34, part, claude))
    (tmp_path / "data/xfam/policy-v2").mkdir(parents=True)
    (tmp_path / "data/coded").mkdir(parents=True)
    neg = r2()
    scr = {"x1": r2("several", "several"), "x2": neg, "x3": r2("one", "several"), "x4": neg, "y9": r2("several", "several")}
    (tmp_path / "data/xfam/policy-v2/results-parsed.jsonl").write_text("".join(json.dumps({"id": i, **r}) + "\n" for i, r in scr.items()))
    (tmp_path / "data/xfam/policy-v1").mkdir()  # the v1 screen: every paper negative, so the parts follow the v2 screen
    (tmp_path / "data/xfam/policy-v1/results-parsed.jsonl").write_text("".join(json.dumps({"id": i, "policy_setters": "one", "principals": "one"}) + "\n" for i in scr))
    code = lambda i, ps: json.dumps({"id": i, "policy_setters": ps, "policy_quote": "", "principals": "several", "principals_quote": "", "behaviour": "rational",
                                     "behaviour_quote": "", "rule_breaking": "no", "interacting": "yes", "outside_attacker": "no", "partners_from_others": "no"}) + "\n"
    (tmp_path / "data/coded/policy2-add-00.jsonl").write_text(code("x1", "several") + code("x3", "one") + code("x4", "one"))
    (tmp_path / "data/coded/policy2-dup-00.jsonl").write_text(code("x1", "one"))
    (tmp_path / "data/coded/policy-add-00.jsonl").write_text(json.dumps({"id": "x1", "policy_setters": "one", "principals": "one"}) + "\n")  # v1: never read
    (tmp_path / "data/coded/policy2-v34-00.jsonl").write_text(json.dumps({"id": "x9", "interests": "one", "focus": "agent"}) + "\n")
    monkeypatch.chdir(tmp_path)
    it, screen, p, codes = twostage.load_policy2("full")
    assert p == {"x1": "a", "x3": "n", "x4": "c"}  # x3 is a v2 screen positive; x2 an uncoded negative
    assert screen["x1"]["behaviour"] == "na" and screen["x1"]["policy_setters"] == "several" and "y9" not in screen
    assert codes["x1"]["policy_setters"] == "several" and codes["x1"]["interests"] == "one"  # the add code, never the dup or v1 code
    assert set(codes) == {"x1", "x3", "x4"}
    t = twostage.table(twostage.POLICY2_MEASURES, {"all-2025": twostage.POPS["all-2025"]}, (it, screen, p, codes))
    assert t["all-2025"]["several"]["confirmed"] == 1 and t["all-2025"]["simulated"]["confirmed"] == 1


GIT = subprocess.run(["git", "cat-file", "-e", "HEAD:data/estimates-twostage.json"], capture_output=True).returncode == 0
DATA = all(os.path.exists(p) for p in ("data/xfam/items-full.jsonl", "data/xfam/policy-v1/results-parsed.jsonl"))


@pytest.mark.skipif(not (GIT and DATA), reason="needs git and the local full-run files (gitignored)")
def test_every_estimate_key_at_git_head_is_reproduced_byte_for_byte():
    from twostage import estimates
    head = json.loads(subprocess.run(["git", "show", "HEAD:data/estimates-twostage.json"], capture_output=True, text=True, check=True).stdout)
    t = estimates()
    assert set(head) <= set(t)
    for k in head:
        assert json.dumps(t[k], indent=1) == json.dumps(head[k], indent=1), k
