import random

from round2 import interval, jeffreys_rate, resample_slice


def test_resample_slice_draws_within_strata_and_keeps_their_sizes():
    items = {f"p{i}": {"venue": "neurips-2020" if i < 6 else "icml-2025"} for i in range(10)}
    screen = {i: {"llm_basis": "no"} for i in items}
    ids = sorted(items)
    for seed in range(20):
        r = resample_slice(ids, items, screen, random.Random(seed))
        assert len(r) == 10
        assert sum(items[i]["venue"] == "neurips-2020" for i in r) == 6  # the 2020 stratum keeps its 6 draws


def test_jeffreys_rate_is_positive_on_zero_counts_and_pools_thin_strata():
    st = {"a": [0] * 179, "b": [1, 0]}
    rng = random.Random(0)
    draws = [jeffreys_rate(st, rng) for _ in range(4000)]
    ra = [d(st, "a") for d in draws]
    assert min(ra) > 0 and abs(sum(ra) / len(ra) - 0.5 / 180) < 0.001  # Jeffreys posterior mean (k + 1/2) / (n + 1)
    d = draws[0]
    assert d(st, "b") == d(st, "missing")  # thin and absent strata share the one pooled draw


def test_interval_is_the_central_95_percent_range():
    lo, hi = interval(list(range(1001)))
    assert lo == 25 and hi == 975


def test_paper_resampling_adds_population_variation_that_slice_resampling_lacks(monkeypatch):
    import round2
    items = {f"p{i:02d}": {"venue": "neurips-2020", "main_track": True} for i in range(40)}
    screen = {i: {"agent": "no", "llm_basis": "no"} for i in items}
    part = {i: ("a" if n < 10 else "d") for n, i in enumerate(sorted(items))}
    yes = {"faces_other_parties": "yes", "has_decision_maker": "yes", "interests": "several-conflicting"}
    claude = {i: (yes if n < 5 else {"has_decision_maker": "no"}) for n, i in enumerate(sorted(items))}
    monkeypatch.setattr(round2, "load", lambda: (items, screen, part, claude))
    pops = {"all": lambda x, s: True}
    m = {"several": round2.MEASURES["several"]}
    fixed = round2.replicates(pops, m, "bootstrap", reps=50)["all"]["several"]
    assert set(fixed) == {5 / 40}  # the slice has no paper of the cell, so only the population can move the share
    moving = round2.replicates(pops, m, "papers", reps=200)["all"]["several"]
    assert len(set(moving)) > 3 and abs(sum(moving) / len(moving) - 5 / 40) < 0.02


def test_parties_measures_split_the_cell_and_need_a_code_for_every_cell_paper():
    import pytest
    from round2 import MEASURES, parties_measures
    cell = {"id": "x1", "faces_other_parties": "yes", "has_decision_maker": "yes", "interests": "several-conflicting"}
    out = {"id": "x2", "faces_other_parties": "no", "has_decision_maker": "yes", "interests": "one"}
    m = parties_measures({"x1": "ai-agents"})
    assert m["parties_ai-agents"](cell) and not m["parties_humans"](cell)
    assert sum(f(cell) for f in m.values()) == 1 and sum(f(out) for f in m.values()) == 0
    with pytest.raises(KeyError):
        parties_measures({})["parties_ai-agents"](cell)


def _ext_data():
    sev = {"faces_other_parties": "yes", "has_decision_maker": "yes", "interests": "several-conflicting", "focus": "interaction"}
    one = {"faces_other_parties": "no", "has_decision_maker": "yes", "interests": "one", "focus": "agent"}
    items = {f"y{n:03d}": {"xid": f"y{n:03d}", "venue": "aamas-2025", "main_track": True, "title": f" T{n} ", "abstract": f"A{n}."} for n in range(250)}
    screen = {i: {"agent": "yes", "llm_basis": "no"} for i in items}
    part = {i: "a" if n < 230 else "c" for n, i in enumerate(sorted(items))}
    claude = {i: dict(sev if n < 230 else one, id=i) for n, i in enumerate(sorted(items))}
    return items, screen, part, claude


def test_jobs_ext_writes_blind_parties_batches_a_seeded_second_coder_slice_and_the_recorded_brief(tmp_path, monkeypatch):
    import json
    import round2
    data = _ext_data()
    recorded = [json.loads(l) for l in open("coding/briefs.jsonl") if '"r2-parties-01.jsonl"' in l][0]["brief"]
    assert round2.parties_brief("r2-parties-01") == recorded
    monkeypatch.setattr(round2, "load_ext", lambda tag="ext": data)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data" / "batches").mkdir(parents=True)
    round2.jobs_ext("ext")
    cell = [json.loads(l) for l in open("data/cell-parties-items-ext.jsonl")]
    assert len(cell) == 230 and all(set(x) == {"id", "title", "abstract"} for x in cell) and cell[0]["title"] == cell[0]["title"].strip()
    briefs = [json.loads(l) for l in open("data/batches/r2-parties-ext-briefs.jsonl")]
    main = [b for b in briefs if not b["batch"].endswith("dup")]
    assert [b["batch"] for b in main] == ["r2-parties-ext-01", "r2-parties-ext-02", "r2-parties-ext-03"] and all(b["n"] <= 100 for b in main)
    got = [x["id"] for b in main for x in json.load(open(f"data/batches/{b['batch']}.json"))]
    assert sorted(got) == sorted(x["id"] for x in cell)
    dup = json.load(open("data/batches/r2-parties-ext-dup.json"))
    assert len(dup) == 46 and set(x["id"] for x in dup) <= set(got)  # 20% of the cell, rounded
    assert briefs[-1]["brief"] == round2.parties_brief("r2-parties-ext-dup")


def test_parties_ext_splits_the_extension_cell_and_needs_every_code(monkeypatch):
    import pytest
    import round2
    data = _ext_data()
    monkeypatch.setattr(round2, "load_ext", lambda tag="ext": data)
    cell = [i for i, r in data[3].items() if r["interests"] == "several-conflicting"]
    codes = {i: ("ai-agents" if n < 30 else "formal-model") for n, i in enumerate(sorted(cell))}
    t = round2.parties_ext("ext", codes)
    a = t["all-aamas-2025"]
    assert a["parties_ai-agents"]["confirmed"] == 30 and a["parties_formal-model"]["confirmed"] == 200 and a["parties_ai-agents"]["lo"] == 30 / 250
    with pytest.raises(KeyError):
        round2.parties_ext("ext", dict(list(codes.items())[:-1]))


def test_ratio_of_replicates_takes_an_empty_denominator_as_infinite():
    import math
    from round2 import ratio_of
    assert ratio_of(1.0, 4.0) == 0.25 and ratio_of(0.5, 0.0) == math.inf and ratio_of(0.0, 0.0) == math.inf
    assert interval([ratio_of(x, 1.0) for x in range(99)] + [ratio_of(1.0, 0.0)]) == (2.0, 96.0)  # one empty replicate moves no percentile


def test_ratio_difference_carries_conservative_bounds_from_the_two_ratios():
    from round2 import contrasts
    m = lambda s, lo, hi: {"share": s, "lo": lo, "hi": hi}
    pop = lambda: {"several": m(0.2, 0.1, 0.4), "simulated": m(0.1, 0.05, 0.2), "interaction": m(0.1, 0.1, 0.1), "conflicting": m(0.1, 0.1, 0.1)}
    t = {k: pop() for k in ("all-2020", "all-2025", "agent-2020", "agent-2025", "llm-agent-2025", "other-agent-2025")}
    t["other-agent-2025"]["simulated"] = m(0.2, 0.1, 0.3)
    c = contrasts(t, {})
    l_, o_ = c["ratio-llm-agent-2025"]["conservative"], c["ratio-other-agent-2025"]["conservative"]
    assert l_ == (0.05 / 0.4, 0.2 / 0.1) and o_ == (0.1 / 0.4, 0.3 / 0.1)
    assert c["ratio-llm-minus-other"]["conservative"] == (l_[0] - o_[1], l_[1] - o_[0])
