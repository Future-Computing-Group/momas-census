"""Stage 2 of the v2 policy pass : the v2 screen-positive rule, the stage-2 draw
(add, v34, dup), the blind batches and briefs, the output validation, and the policy2 estimate keys. Synthetic screen data only."""
import json

import pytest

V2NEG = {"policy_setters": "one", "principals": "one", "behaviour": "na", "rule_breaking": "no", "interacting": "no", "outside_attacker": "no"}


def test_policy2_positive_is_setters_or_principals_several_or_rule_breaking_or_interacting_or_a_parse_failure():
    from twostage import policy2_positive
    assert policy2_positive(None)
    assert not policy2_positive(V2NEG)
    for k, v in (("policy_setters", "several"), ("principals", "several"), ("rule_breaking", "yes"), ("interacting", "yes")):
        assert policy2_positive({**V2NEG, k: v}), k
    for k, v in (("behaviour", "rational"), ("outside_attacker", "yes"), ("policy_setters", "na"), ("interacting", "na"), ("rule_breaking", "na")):
        assert not policy2_positive({**V2NEG, k: v}), k


def test_policy2_parts_confirm_v1_and_v2_positives_and_slice_only_papers_negative_on_both():
    from twostage import policy2_parts, policy_parts
    ids = ["a1", "c1", "c2", "c3", "c4", "d1", "u1", "u2", "u3", "u4", "u5"]
    items = {i: {"venue": "neurips-2025", "main_track": True} for i in ids} | {"c4": {"venue": "icml-2025", "main_track": False}, "u5": {"venue": "icml-2025", "main_track": False}}
    part = {"a1": "a", "c1": "c", "c2": "c", "c3": "c", "c4": "c", "d1": "d"}
    s34 = {i: {"owners_derived": "one"} for i in ids} | {"u4": {"owners_derived": "na"}}
    n1, p1 = {"policy_setters": "one", "principals": "one"}, {"policy_setters": "several", "principals": "one"}
    sp1 = {i: n1 for i in ids} | {"c1": p1, "u1": p1}
    sp2 = {i: V2NEG for i in ids} | {"c2": {**V2NEG, "interacting": "yes"}, "u2": {**V2NEG, "rule_breaking": "yes"}, "u5": {**V2NEG, "interacting": "yes"}}
    del sp2["u3"]  # a v2 parse failure
    p = policy2_parts(part, items, s34, sp1, sp2)
    assert p == {"a1": "a", "c1": "n", "c2": "n", "c3": "c", "d1": "d", "u1": "n", "u2": "n", "u3": "n", "u4": "z"}
    from twostage import policy2_positive
    assert p == policy_parts(policy_parts(part, items, s34, sp1), items, s34, sp2, policy2_positive)  # v1 parts, then the v2 rule


# ---- stage-2 draw ----

def synth():
    """Main frame: 2025 main papers (coded: confirmed m0..m4, slices s0..s19; uncoded u0..u9), one non-main 2025 slice paper and
    one non-main uncoded positive; 2020: slice t0..t4, uncoded v0..v2; EC 3 coded; AAMAS 4 coded, two of them slices (a census venue)."""
    it = lambda i, v, m=True: {"xid": i, "venue": v, "main_track": m, "title": f"T {i}", "abstract": f"A {i} abstract."}
    items = {}
    for i in [f"m{k}" for k in range(5)] + [f"s{k}" for k in range(20)] + [f"u{k}" for k in range(10)]:
        items[i] = it(i, "neurips-2025")
    items |= {"sn": it("sn", "icml-2025", False), "un": it("un", "icml-2025", False)}
    items |= {f"t{k}": it(f"t{k}", "neurips-2020") for k in range(5)}
    items |= {f"v{k}": it(f"v{k}", "neurips-2020") for k in range(3)}  # uncoded 2020 negatives: 2020 is estimated, not a census
    items |= {f"e{k}": it(f"e{k}", "ec-2025") for k in range(3)}
    items |= {f"y{k}": it(f"y{k}", "aamas-2025") for k in range(4)}
    slices = {f"s{k}" for k in range(20)} | {"sn", "y0", "y1"} | {f"t{k}" for k in range(5)}
    coded = {f"m{k}" for k in range(5)} | slices | {f"e{k}" for k in range(3)} | {f"y{k}" for k in range(4)}
    s34 = {i: {"owners_derived": "one"} for i in items} | {"u9": {"owners_derived": "na"}}
    sp = {i: V2NEG for i in items} | {"u0": {**V2NEG, "principals": "several"}, "u1": {**V2NEG, "interacting": "yes"},
                                      "m0": {**V2NEG, "policy_setters": "several"}, "un": {**V2NEG, "policy_setters": "several"}}
    del sp["u2"]  # parse failure
    return items, coded, s34, sp, slices, ["m1", "u5", "un", "s3"]


def test_stage2_policy2_adds_every_coded_paper_new_v2_positives_failures_and_owners_na_and_gives_new_papers_a_v34_code():
    from xfam_full import stage2_policy2
    items, coded, s34, sp, slices, disputed = synth()
    d = stage2_policy2(items, coded, s34, sp, slices, disputed, dup_share=0.5, dup_venue_n=2, seed=7)
    assert d["v34"] == ["u0", "u1", "u2", "u9"]  # un: a non-main 2025 paper enters no population; m0 is coded already
    assert d["add"] == sorted(coded) + d["v34"] and not coded & set(d["v34"])
    assert stage2_policy2(items, coded, s34, sp, slices, disputed, dup_share=0.5, dup_venue_n=2, seed=7) == d


def test_dup_takes_every_weighted_slice_paper_and_every_disputed_paper_in_the_population_beside_the_seeded_draw():
    from xfam_full import stage2_policy2
    items, coded, s34, sp, slices, disputed = synth()
    d = stage2_policy2(items, coded, s34, sp, slices, disputed, dup_share=0.0, dup_venue_n=2, seed=7)
    weighted = {f"s{k}" for k in range(20)} | {f"t{k}" for k in range(5)}  # sn: non-main 2025; y0, y1: AAMAS is a census venue
    assert weighted | {"m1"} <= set(d["dup"]) and not {"sn", "un", "u5"} & set(d["dup"])  # u5: not drawn, so not in add
    assert sum(items[i]["venue"] == "ec-2025" for i in d["dup"]) == 2 and sum(items[i]["venue"] == "aamas-2025" for i in d["dup"]) == 2
    assert set(d["dup"]) == weighted | {"m1"} | {i for i in d["dup"] if items[i]["venue"] in ("ec-2025", "aamas-2025")}
    assert set(d["dup"]) <= set(d["add"]) and d["dup"] == sorted(d["dup"])
    d5 = stage2_policy2(items, coded, s34, sp, slices, disputed, dup_share=0.5, dup_venue_n=2, seed=7)
    rest = [i for i in d5["add"] if items[i]["venue"] not in ("ec-2025", "aamas-2025")]
    assert set(d["dup"]) <= set(d5["dup"]) and len(set(d5["dup"]) - set(d["dup"])) <= round(0.5 * len(rest))


# ---- batches, briefs, files ----

def test_policy2_briefs_are_the_pilot3_template_and_the_recorded_v34_brief():
    from xfam_full import ADD2_BRIEF, BRIEF, POLICY_BATCH_SEEDS, policy_brief
    from xfam_inputs import POLICY2_CODEBOOK
    pilot = json.loads(open("data/batches/pilot3-briefs.jsonl").readline())
    assert ADD2_BRIEF.format(b=pilot["batch"]) == pilot["brief"]
    a, v, d = policy_brief("policy2-add-03"), policy_brief("policy2-v34-00"), policy_brief("policy2-dup-12")
    assert f"BASE/{POLICY2_CODEBOOK} in full" in a and "/private/tmp/policy2-add-03/" in a and "BASE/data/coded/policy2-add-03.jsonl" in a
    assert "BASE/data/batches/policy2-dup-12.json" in d and "/private/tmp/policy2-dup-12/" in d and "codebook-v3.md" not in a + d
    assert v == BRIEF.format(b="policy2-v34-00", t="policy2-v34-00") and "/private/tmp/conf-policy2-v34-00/" in v
    assert {k: POLICY_BATCH_SEEDS[k] for k in ("policy2-add", "policy2-v34", "policy2-dup")} == {"policy2-add": 93, "policy2-v34": 94, "policy2-dup": 95}
    assert policy_brief("policy-add-01").count("codebook-policy.md (v1)") == 1  # v1 briefs unchanged


def frame(tmp_path, monkeypatch, n_new=150):
    """A synthetic BASE: three frames for twostage.load / load_ext, the v1 addendum ids, pilot ids, v1 and v2 screens."""
    import twostage
    items, coded, s34, sp, slices, disputed = synth()
    items |= {f"w{k:03d}": {"xid": f"w{k:03d}", "venue": "icml-2025", "main_track": True, "title": f"W{k:03d}", "abstract": f"Players {k} bid."} for k in range(n_new)}
    s34 |= {i: {"owners_derived": "one"} for i in items if i[0] == "w"}
    sp |= {i: {**V2NEG, "interacting": "yes"} for i in items if i[0] == "w"}
    x = lambda i: i if i[0] == "y" else "x" + i  # the loaders keep a frame's screen records by xid prefix (x main, y extension)
    items = {x(i): {**v, "xid": x(i)} for i, v in items.items()}
    coded, slices, disputed = {x(i) for i in coded}, {x(i) for i in slices}, [x(i) for i in disputed]
    s34, sp = {x(i): dict(v) for i, v in s34.items()}, {x(i): v for i, v in sp.items()}
    for s in s34.values():
        s.setdefault("agent", "yes"), s.setdefault("llm_basis", "no")
    part = {i: ("c" if i in slices else "a") for i in coded}
    full = {i: x for i, x in items.items() if x["venue"] != "aamas-2025"}
    ext = {i: x for i, x in items.items() if x["venue"] == "aamas-2025"}
    claude = {i: {"id": i, "interests": "one", "focus": "agent", "has_decision_maker": "yes", "faces_other_parties": "no"} for i in coded}
    sub = lambda d, keep: {i: v for i, v in d.items() if i in keep}
    monkeypatch.setattr(twostage, "load", lambda: (full, sub(s34, full), sub(part, full), sub(claude, full)))
    monkeypatch.setattr(twostage, "load_ext", lambda tag="ext": (ext, sub(s34, ext), sub(part, ext), sub(claude, ext)) if tag == "ext" else ({}, {}, {}, {}))
    for d in ("data/xfam/policy-v2", "data/xfam/policy-v1", "data/coded", "data/batches", "data/pilot"):
        (tmp_path / d).mkdir(parents=True)
    w = lambda p, rows: (tmp_path / p).write_text("".join(json.dumps(r) + "\n" for r in rows))
    w("data/xfam/items-full.jsonl", full.values()), w("data/xfam/items-ext.jsonl", ext.values()), w("data/xfam/items-ext-ea.jsonl", [])
    w("data/xfam/policy-v2/results-parsed.jsonl", [{"id": i, **r} for i, r in sp.items()])
    w("data/xfam/policy-v2/failures.jsonl", [{"call_id": i, "error": "x"} for i in items if i not in sp])
    w("data/xfam/policy-v1/results-parsed.jsonl", [{"id": i, "policy_setters": "one", "principals": "one"} for i in items])
    w("data/coded/policy-add-00.jsonl", [{"id": i} for i in sorted(coded)])
    w("data/coded/confirm-00.jsonl", claude.values())
    (tmp_path / "data/pilot/pilot-ids.json").write_text(json.dumps({"disputed": [{"id": i, "clusters": ["K1"], "part": "a"} for i in disputed], "random": []}))
    monkeypatch.chdir(tmp_path)
    return items


def test_main_policy2_writes_the_draw_blind_batches_of_70_and_one_brief_per_batch(tmp_path, monkeypatch):
    import xfam_full
    items = frame(tmp_path, monkeypatch)
    xfam_full.main_policy2()
    d = json.load(open("data/xfam/stage2-policy2.json"))
    assert set(d) == {"add", "v34", "dup"} and len(d["v34"]) == 154  # xu0 xu1 xu2 xu9 and the 150 interacting w papers
    briefs = [json.loads(l) for l in open("data/batches/policy2-briefs.jsonl")]
    for prefix, key in (("policy2-add", "add"), ("policy2-v34", "v34"), ("policy2-dup", "dup")):
        bs = [b for b in briefs if b["batch"].startswith(prefix + "-")]
        assert [b["batch"] for b in bs] == [f"{prefix}-{n:02d}" for n in range(-(-len(d[key]) // 70))]
        rows = [x for b in bs for x in json.load(open(f"data/batches/{b['batch']}.json"))]
        assert sorted(x["id"] for x in rows) == sorted(d[key]) and all(list(x) == ["id", "title", "abstract"] for x in rows)
        assert all(b["n"] == len(json.load(open(f"data/batches/{b['batch']}.json"))) <= 70 and b["brief"] == xfam_full.policy_brief(b["batch"]) for b in bs)
    first = [x["id"] for x in json.load(open("data/batches/policy2-v34-00.json"))]
    assert first == [x["id"] for x in xfam_full.policy_batches("policy2-v34", d["v34"], items)[0][1]] and first != sorted(first)  # shuffled, seed 94


def test_main_policy2_refuses_a_screen_that_does_not_cover_every_item(tmp_path, monkeypatch):
    import xfam_full
    frame(tmp_path, monkeypatch)
    (tmp_path / "data/xfam/policy-v2/failures.jsonl").write_text("")
    with pytest.raises(AssertionError, match="every item"):
        xfam_full.main_policy2()
    assert not (tmp_path / "data/xfam/stage2-policy2.json").exists()


def outputs(tmp_path):
    """Synthetic coder outputs for every policy2 batch: valid v2 records (add, dup) and v3.4 records (v34)."""
    from xfam_inputs import KEYS, V2_KEYS
    for l in open("data/batches/policy2-briefs.jsonl"):
        b = json.loads(l)["batch"]
        ids = [x["id"] for x in json.load(open(f"data/batches/{b}.json"))]
        title = {x["id"]: x["title"] for x in json.load(open(f"data/batches/{b}.json"))}
        if b.startswith("policy2-v34-"):
            rec = lambda i: {**{k: "na" for k in KEYS}, "id": i, "has_decision_maker": "yes", "faces_other_parties": "no", "one_party_runs_all": "yes",
                             "confidence": "high", "faces_quote": "", "quote": ""}
        else:
            rec = lambda i: {**{k: "no" for k in V2_KEYS}, "id": i, "policy_setters": "several", "principals": "one", "behaviour": "rational",
                             "policy_quote": "", "principals_quote": "", "behaviour_quote": title[i].upper()}
        (tmp_path / f"data/coded/{b}.jsonl").write_text("".join(json.dumps(rec(i)) + "\n" for i in ids))


def test_validate_policy2_outputs_passes_valid_files_and_catches_key_enum_order_quotes_and_missing(tmp_path, monkeypatch):
    import xfam_full
    frame(tmp_path, monkeypatch)
    xfam_full.main_policy2()
    n = sum(1 for _ in open("data/batches/policy2-briefs.jsonl"))
    outputs(tmp_path)
    v = xfam_full.validate_policy2_outputs()
    assert v == {"valid": n, "missing": [], "nonverbatim": []}  # quotes in upper case: the check folds case
    f = tmp_path / "data/coded/policy2-add-00.jsonl"
    good = f.read_text()
    rows = [json.loads(l) for l in good.splitlines()]
    for bad, msg in ((rows[::-1], "order"), ([{**rows[0], "behaviour": "selfish"}, *rows[1:]], "policy2-add-00"),
                     ([{k: v for k, v in r.items() if k != "rule_breaking"} for r in rows], "policy2-add-00")):
        f.write_text("".join(json.dumps(r) + "\n" for r in bad))
        with pytest.raises(AssertionError, match=msg):
            xfam_full.validate_policy2_outputs()
    f.write_text("".join(json.dumps({**r, "behaviour_quote": "not in the abstract"}) + "\n" for r in rows[:1]) + "".join(json.dumps(r) + "\n" for r in rows[1:]))
    assert xfam_full.validate_policy2_outputs()["nonverbatim"] == [("policy2-add-00", rows[0]["id"])]
    v34 = tmp_path / "data/coded/policy2-v34-00.jsonl"
    v34.write_text("".join(json.dumps({**json.loads(l), "owners": "two"}) + "\n" for l in v34.read_text().splitlines()))
    with pytest.raises(AssertionError, match="policy2-v34-00"):
        xfam_full.validate_policy2_outputs()
    v34.unlink(), f.write_text(good)
    assert xfam_full.validate_policy2_outputs()["missing"] == ["policy2-v34-00"]


# ---- estimator ----

def test_policy2_keys_appear_only_once_every_part_has_a_policy2_add_and_a_v34_code_and_old_keys_do_not_move(tmp_path, monkeypatch):
    import twostage
    import xfam_full
    frame(tmp_path, monkeypatch)
    monkeypatch.setattr(twostage, "ext_ready", lambda tag="ext": False)
    monkeypatch.setattr(twostage, "policy_ready", lambda tag="full": False)
    assert not twostage.policy2_ready("full")  # no policy2 codes yet
    base = twostage.estimates()
    assert not any(k.startswith("policy2") for k in base)
    xfam_full.main_policy2()
    outputs(tmp_path)
    items, screen, p, codes = twostage.load_policy2("full")
    assert set(p) - set(codes) == set() and all("interests" in codes[i] for i in p)  # v3.4 codes of new papers: policy2-v34-*
    assert twostage.policy2_ready("full")
    t = twostage.estimates()
    assert "policy2" in t and "policy2-ext" not in t and {k: t[k] for k in base} == base
    assert set(t["policy2"]["all-2025"]) >= set(twostage.POLICY2_MEASURES)
    v34 = tmp_path / "data/coded/policy2-v34-00.jsonl"
    keep = v34.read_text()
    v34.unlink()
    assert not twostage.policy2_ready("full") and "policy2" not in twostage.estimates()  # a new paper without its v3.4 code
    v34.write_text(keep)
    (tmp_path / "data/coded/policy2-add-00.jsonl").write_text("")
    assert not twostage.policy2_ready("full") and "policy2" not in twostage.estimates()  # the dup codes never stand in
