"""Policy pass (codebook-policy.md): who sets each decision-maker's policy (POLICY_SETTERS), how many parties' interests the
decision-makers serve (PRINCIPALS), PARTNERS_FROM_OTHERS. Separate codebook, schema, calls and coded files; codebook v3.4 and
every v3.4 input, output and estimate key stay as they are."""
import hashlib
import json
import os
import re

import pytest

sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
POLICY = open("codebook-policy.md").read()
HAVE = all(os.path.exists(f"data/xfam/{f}") for f in ("items-full.jsonl", "items-ext.jsonl", "items-ext-ea.jsonl", "calls.jsonl", "calls-smoke100.jsonl"))


def test_codebooks_are_pinned_and_v34_is_untouched():
    from xfam_inputs import CODEBOOK_SHA, POLICY_SHA
    assert sha("codebook-v3.md") == CODEBOOK_SHA
    assert sha("codebook-policy.md") == POLICY_SHA


def test_policy_keys_follow_the_output_line_and_every_enum_value_is_a_defined_token():
    from xfam_inputs import POLICY_ENUMS, POLICY_KEYS
    line = next(l for l in POLICY.splitlines() if l.startswith("Output one JSON object"))
    assert POLICY_KEYS == re.findall(r'"(\w+)"', line.split("exactly these keys:")[1].split(".")[0])
    assert POLICY_KEYS == ["id", "policy_setters", "policy_quote", "principals", "principals_quote", "partners_from_others"]
    for k, vals in POLICY_ENUMS.items():
        para = next(l for l in POLICY.splitlines() if l.startswith(k.upper() + ":"))
        for v in vals:
            assert re.search(rf"[ (]{v}(:| if | otherwise)", para), (k, v)  # each value defined as a token, not a substring


def test_policy_schema_pins_the_id_and_has_no_v34_field():
    from xfam_inputs import KEYS, POLICY_KEYS, schema_policy
    s = schema_policy("y00042")
    assert s["required"] == POLICY_KEYS and s["additionalProperties"] is False
    assert s["properties"]["id"] == {"type": "string", "const": "y00042"}
    assert s["properties"]["policy_setters"]["enum"] == ["one", "several", "na"] == s["properties"]["principals"]["enum"]
    assert s["properties"]["partners_from_others"]["enum"] == ["yes", "no", "na"]
    assert s["properties"]["policy_quote"] == {"type": "string"} == s["properties"]["principals_quote"]
    assert not set(POLICY_KEYS[1:]) & set(KEYS)


def test_policy_call_has_the_policy_codebook_and_the_v34_user_message():
    from xfam_inputs import call, call_policy
    it = {"xid": "x00001", "venue": "neurips-2025", "main_track": True, "title": "T", "abstract": "A b.", "sample_id": "q1"}
    c = call_policy(it, POLICY)
    assert c["messages"][0]["content"].startswith(POLICY.rstrip("\n")) and "OWNERS" not in c["messages"][0]["content"]
    assert c["messages"][1] == call(it, "x")["messages"][1]
    assert c["schema"]["required"][1] == "policy_setters" and c["call_id"] == "x00001"


def test_client_parses_a_policy_record_without_the_v34_derivation():
    import sys
    sys.path.insert(0, "roihu")
    from xfam_client import parse_one
    from xfam_inputs import schema_policy
    raw = json.dumps({"id": "z00001", "policy_setters": "several", "policy_quote": "q", "principals": "several", "principals_quote": "", "partners_from_others": "no"})
    rec, err = parse_one(raw, schema_policy("z00001"))
    assert err is None and "has_decision_maker" not in rec
    assert parse_one(raw.replace('"no"}', '"maybe"}'), schema_policy("z00001"))[0] is None


def test_quote_check_reads_title_and_abstract():
    from xfam_inputs import quotes_verbatim
    it = {"title": "Two Owners", "abstract": "Agents of  different firms meet."}
    assert quotes_verbatim({"policy_quote": "different firms", "principals_quote": ""}, it)
    assert quotes_verbatim({"policy_quote": "Two Owners", "principals_quote": "agents of different firms"}, it)  # case and spacing
    assert not quotes_verbatim({"policy_quote": "several owners", "principals_quote": ""}, it)


@pytest.mark.skipif(not HAVE, reason="needs the local items and calls files (gitignored)")
def test_policy_calls_cover_every_item_once_in_items_order_with_the_v34_user_messages():
    from xfam_inputs import policy_items
    items = policy_items()
    want = [json.loads(l)["xid"] for f in ("items-full.jsonl", "items-ext.jsonl", "items-ext-ea.jsonl") for l in open(f"data/xfam/{f}")]
    assert [x["xid"] for x in items] == want and len(want) == len(set(want)) == 16511
    if os.path.exists("data/xfam/calls-policy.jsonl"):
        calls = [json.loads(l) for l in open("data/xfam/calls-policy.jsonl")]
        assert [c["call_id"] for c in calls] == want
        old = {c["call_id"]: c["messages"][1] for f in ("calls.jsonl", "calls-ext.jsonl", "calls-ext-ea.jsonl") for c in map(json.loads, open(f"data/xfam/{f}"))}
        assert all(c["messages"][1] == old[c["call_id"]] for c in calls)
        smoke = [json.loads(l)["call_id"] for l in open("data/xfam/calls-policy-smoke100.jsonl")]
        assert smoke == [json.loads(l)["call_id"] for l in open("data/xfam/calls-smoke100.jsonl")]


# ---- measures and the join ----

def rec(ps, pr, interests="one", focus="agent", **kw):
    return {"policy_setters": ps, "principals": pr, "interests": interests, "focus": focus, **kw}


def test_measures_follow_policy_setters_and_principals():
    from twostage import POLICY_MEASURES as M
    team = rec("one", "one", "several-aligned")  # one developer, one shared team reward
    lab_separate = rec("one", "one", "several-conflicting")  # separate rewards that serve the developer's goal
    lab_parties = rec("one", "several", "several-conflicting")  # one laboratory trains agents that stand for several parties
    bidders = rec("several", "several", "several-conflicting", "interaction")  # people acting for themselves
    assert not any(f(team) for f in M.values()) and not any(f(lab_separate) for f in M.values())
    assert M["simulated"](lab_parties) and not M["several"](lab_parties)
    assert M["several"](bidders) and M["conflicting"](bidders) and M["interaction"](bidders) and not M["simulated"](bidders)
    assert not M["several"](rec("several", "one")) and not M["several"](rec("na", "several")) and not M["simulated"](rec("na", "several"))


def test_measures_exclude_adversarial_interests_as_the_v34_cell_did():
    from twostage import POLICY_MEASURES as M
    attack = rec("several", "several", "adversarial", "interaction")  # attacker against a victim's model: a threat model, not owners' agents
    lab_attack = rec("one", "several", "adversarial")
    assert not any(f(attack) for f in M.values()) and not M["simulated"](lab_attack)


def test_join_keeps_v34_codes_and_adds_policy_codes_by_id():
    from twostage import join_policy
    v34 = {"x1": {"id": "x1", "interests": "one", "focus": "agent"}, "x2": {"id": "x2", "interests": "several-conflicting", "focus": "interaction"}}
    pol = {"x1": {"id": "x1", "policy_setters": "one", "principals": "one"}, "x2": {"id": "x2", "policy_setters": "several", "principals": "several"},
           "x3": {"id": "x3", "policy_setters": "na", "principals": "na"}}
    j = join_policy(v34, pol)
    assert j["x1"] == {"id": "x1", "interests": "one", "focus": "agent", "policy_setters": "one", "principals": "one"}
    assert j["x2"]["interests"] == "several-conflicting" and j["x2"]["principals"] == "several"
    assert j["x3"] == pol["x3"]  # a paper whose v3.4 code is not in yet carries no v3.4 field (policy_ready waits for it)
    assert v34["x1"] == {"id": "x1", "interests": "one", "focus": "agent"}
    with pytest.raises(AssertionError):
        join_policy(v34, {"x1": {"id": "x1", "interests": "several-aligned", "policy_setters": "one", "principals": "one"}})  # an addendum never recodes v3.4


def screen_pos(r):
    from twostage import policy_positive
    return policy_positive(r)


def test_screen_positive_is_either_field_several():
    assert screen_pos({"policy_setters": "several", "principals": "one"}) and screen_pos({"policy_setters": "one", "principals": "several"})
    assert not screen_pos({"policy_setters": "one", "principals": "one"}) and not screen_pos({"policy_setters": "na", "principals": "na"})


def test_policy_parts_confirm_new_positives_and_owners_na_and_restrict_slices_to_new_negatives():
    from twostage import policy_parts
    items = {i: {"venue": v, "main_track": m} for i, v, m in [("a1", "neurips-2025", True), ("c1", "neurips-2025", True), ("c2", "neurips-2025", True),
             ("c3", "icml-2025", False), ("d1", "neurips-2020", True), ("u1", "icml-2025", True), ("u2", "icml-2025", True), ("u3", "neurips-2020", True), ("u4", "icml-2025", False)]}
    part = {"a1": "a", "c1": "c", "c2": "c", "c3": "c", "d1": "d"}
    s34 = {i: {"owners_derived": "one"} for i in items} | {"u2": {"owners_derived": "na"}}
    neg, pos = {"policy_setters": "one", "principals": "one"}, {"policy_setters": "one", "principals": "several"}
    sp = {i: neg for i in items if i != "u3"} | {"c2": pos, "u1": pos}
    assert policy_parts(part, items, s34, sp)["u3"] == "n"  # a paper the screen failed to code is confirmed, never a negative
    sp["u3"] = neg
    p = policy_parts(part, items, s34, sp)
    assert p == {"a1": "a", "c1": "c", "c2": "n", "d1": "d", "u1": "n", "u2": "z"}  # c3: a non-main 2025 slice record leaves the slices
    assert "u4" not in p  # an uncoded 2025 paper outside the main track is in no population (the draw skips it too)
    assert "u3" not in p  # an uncoded new negative is estimated from the slices, never drawn


def test_policy_estimate_is_the_two_stage_estimate_on_the_new_parts():
    from twostage import POLICY_MEASURES, POPS, table
    items, screen, part, claude = {}, {}, {}, {}
    n = 0

    def add(venue, agent, p, code):
        nonlocal n
        n += 1
        i = f"x{n:05d}"
        items[i] = {"venue": venue, "main_track": True}
        screen[i] = {"agent": agent, "llm_basis": "no"}
        if p:
            part[i], claude[i] = p, code
    hit, miss = rec("several", "several", "several-conflicting", "interaction"), rec("one", "one")
    for _ in range(10):
        add("neurips-2025", "yes", "n", hit)  # confirmed new positives
    for k in range(40):
        add("neurips-2025", "yes", "c", hit if k < 4 else miss)  # slice of new negatives: rate 0.1
    for _ in range(50):
        add("neurips-2025", "yes", None, None)  # unsampled new negatives
    for _ in range(30):
        add("ec-2025", "no", "x", hit)
    t = table(POLICY_MEASURES, {"agent-2025": POPS["agent-2025"], "ec-2025": POPS["ec-2025"]}, (items, screen, part, claude))
    assert t["agent-2025"]["screened"] == 10 and t["agent-2025"]["several"]["confirmed"] == 10
    assert abs(t["agent-2025"]["several"]["share"] - (10 + 90 * 0.1) / 100) < 1e-12  # 90 new negatives at the slice's miss rate
    assert t["ec-2025"]["census"] and t["ec-2025"]["several"]["share"] == 1.0


DATA = all(os.path.exists(p) for p in ("data/xfam/items-full.jsonl", "data/estimates-twostage.json"))


@pytest.mark.skipif(not DATA, reason="needs the local full-run files (gitignored)")
def test_estimates_keep_every_existing_key_byte_identical_and_add_policy_keys_only_when_coded():
    from twostage import POLICY_TAGS, estimates, policy_ready
    old = json.loads(open("data/estimates-twostage.json").read())
    t = estimates()
    for k in old:
        if not k.startswith("policy"):
            assert json.dumps(t[k], indent=1) == json.dumps(old[k], indent=1), k
    assert set(t) - set(old) <= {f"{v}-{g}" if g != "full" else v for g in POLICY_TAGS for v in ("policy", "policy2")}
    for g in POLICY_TAGS:
        assert (("policy" if g == "full" else f"policy-{g}") in t) == policy_ready(g)


# ---- stage-2 draw and blind batches ----

def synth():
    """Three frames: 6 coded and 4 uncoded main papers, 2 coded EC papers, AAMAS 3 coded."""
    items = {f"x{i}": {"xid": f"x{i}", "venue": "neurips-2025", "main_track": True, "title": f"T{i}", "abstract": f"A{i}"} for i in range(10)}
    items |= {f"e{i}": {"xid": f"e{i}", "venue": "ec-2025", "main_track": True, "title": f"E{i}", "abstract": "e"} for i in range(2)}
    items |= {f"y{i}": {"xid": f"y{i}", "venue": "aamas-2025", "main_track": True, "title": f"Y{i}", "abstract": "y"} for i in range(3)}
    items["x10"] = {"xid": "x10", "venue": "icml-2025", "main_track": False, "title": "T10", "abstract": "A10"}  # outside every population
    coded = {f"x{i}" for i in range(6)} | {"e0", "e1", "y0", "y1", "y2"}
    s34 = {i: {"owners_derived": "na" if i == "x9" else "one"} for i in items}
    sp = {i: {"policy_setters": "one", "principals": "one"} for i in items} | {"x6": {"policy_setters": "several", "principals": "several"}, "x10": {"policy_setters": "several", "principals": "several"}, "x0": {"policy_setters": "several", "principals": "several"}}
    return items, coded, s34, sp


def test_stage2_draw_addendum_on_every_confirmed_paper_and_v34_on_uncoded_positives_and_owners_na():
    from xfam_full import stage2_policy
    items, coded, s34, sp = synth()
    d = stage2_policy(items, coded, s34, sp, dup_share=0.5, dup_venue_n=1, seed=1)
    assert sorted(d["v34"]) == ["x6", "x9"]  # x0 is a new positive the v3.4 confirmer already coded; x7, x8 are new negatives
    assert sorted(d["add"]) == sorted(coded | {"x6", "x9"}) and not coded & set(d["v34"])
    assert sum(items[i]["venue"] == "ec-2025" for i in d["dup"]) == 1 and sum(items[i]["venue"] == "aamas-2025" for i in d["dup"]) == 1
    rest = [i for i in d["add"] if items[i]["venue"] not in ("ec-2025", "aamas-2025")]
    assert sum(i in rest for i in d["dup"]) == round(0.5 * len(rest)) and set(d["dup"]) <= set(d["add"])
    assert stage2_policy(items, coded, s34, sp, dup_share=0.5, dup_venue_n=1, seed=1) == d
    del sp["x7"]  # a screen parse failure
    assert "x7" in stage2_policy(items, coded, s34, sp, dup_share=0.5, dup_venue_n=1, seed=1)["v34"]


def test_batches_are_blind_of_70_and_briefs_name_their_own_codebook_output_and_private_dir():
    from xfam_full import BRIEF, policy_batches, policy_brief
    items, coded, s34, sp = synth()
    items |= {f"q{i}": {"xid": f"q{i}", "venue": "icml-2025", "main_track": True, "title": "t", "abstract": "a"} for i in range(150)}
    bs = policy_batches("policy-add", sorted(items), items, seed=3)
    assert [len(b) for _, b in bs] == [70, 70, 26] and [n for n, _ in bs] == ["policy-add-00", "policy-add-01", "policy-add-02"]
    assert all(set(x) == {"id", "title", "abstract"} for _, b in bs for x in b)
    assert sorted(x["id"] for _, b in bs for x in b) == sorted(items) and policy_batches("policy-add", sorted(items), items, seed=3) == bs
    a, v, d = policy_brief("policy-add-01"), policy_brief("policy-v34-00"), policy_brief("policy-dup-02")
    assert "BASE/codebook-policy.md" in a and "codebook-v3.md" not in a and "BASE/data/coded/policy-add-01.jsonl" in a and "/private/tmp/policy-add-01/" in a
    assert v == BRIEF.format(b="policy-v34-00", t="policy-v34-00")  # the recorded v3.4 confirm brief, verbatim
    assert "BASE/data/coded/policy-dup-02.jsonl" in d and "codebook-v3.md" not in d and 'BASE = "BASE"' in a
    assert "policy-add-01" not in policy_brief("policy-add-02")


def test_parties_jobs_take_new_cell_papers_without_a_parties_code_and_the_split_uses_the_policy_cell():
    from round2 import new_cell, parties_measures
    from twostage import POLICY_MEASURES
    claude = {"a": rec("several", "several"), "b": rec("several", "several"), "c": rec("one", "several"), "d": rec("several", "one")}
    assert new_cell(claude, {"a"}) == ["b"]
    pm = parties_measures({"a": "humans", "b": "ai-agents"}, POLICY_MEASURES["several"])
    assert pm["parties_ai-agents"]({"id": "b", **claude["b"]}) and not pm["parties_ai-agents"]({"id": "c", **claude["c"]})
