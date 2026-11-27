from twostage import two_stage_count, claude_owners


def test_claude_owners_is_derived_from_the_decision_questions():
    assert claude_owners({"faces_other_parties": "yes", "has_decision_maker": "yes"}) == "several"
    assert claude_owners({"faces_other_parties": "no", "has_decision_maker": "yes"}) == "one"
    assert claude_owners({"faces_other_parties": "no", "has_decision_maker": "no"}) == "na"


def test_two_stage_count_adds_confirmed_positives_and_expected_misses():
    # 3 confirmed positives among screened papers, 100 screen-negative agent papers at miss rate 0.02,
    # 50 screen-negative non-agent papers at miss rate 0.0
    assert abs(two_stage_count(3, 100, 0.02, 50, 0.0) - 5.0) < 1e-12


def test_stratum_rate_falls_back_to_pooled_when_thin():
    from twostage import stratum_rate
    strata = {"a": [1] * 3 + [0] * 27, "b": [1, 0]}
    assert abs(stratum_rate(strata, "a") - 0.1) < 1e-12
    # 'b' has fewer than 30 sampled papers: use the pooled rate 4/32
    assert abs(stratum_rate(strata, "b") - 4 / 32) < 1e-12


def test_bounds_use_wilson_per_stratum_and_never_collapse_on_zero_misses():
    from twostage import miss_bounds
    lo, hi = miss_bounds({"a": 100}, {"a": [0] * 50})
    assert lo == 0 and hi > 5  # Wilson upper bound of 0/50 is about 7.1%


import json
import os

import pytest

DATA = all(os.path.exists(p) for p in ("data/xfam/items-full.jsonl", "data/xfam/full-v34/results-parsed.jsonl", "data/estimates-twostage.json"))


@pytest.mark.skipif(not DATA, reason="needs the local full-run files (gitignored)")
def test_existing_estimates_are_reproduced_value_for_value_and_byte_for_byte_until_the_extension_lands():
    from twostage import ext_ready, estimates, table
    text = open("data/estimates-twostage.json").read()
    t = json.loads(json.dumps(table()))
    assert {k: json.loads(text)[k] for k in t} == t
    if not ext_ready():
        assert json.dumps(estimates(), indent=1) == text


def test_extension_venues_get_their_own_strata_and_existing_strata_keep_their_keys():
    from twostage import stratum
    s = {"llm_basis": "yes"}
    assert [stratum({"venue": v}, s)[0] for v in ("neurips-2020", "icml-2025", "ec-2025", "iclr-2025", "aamas-2025")] == ["2020", "2025", "ec", "iclr", "aamas"]


def test_extension_populations_are_estimated_like_the_existing_ones():
    from twostage import MEASURES, POPS_EXT, table
    sev = {"faces_other_parties": "yes", "has_decision_maker": "yes", "interests": "several-conflicting", "focus": "interaction"}
    one = {"faces_other_parties": "no", "has_decision_maker": "yes", "interests": "one", "focus": "agent"}
    items, screen, part, claude = {}, {}, {}, {}

    def add(i, venue, agent, p=None, code=None):
        items[i] = {"xid": i, "venue": venue, "main_track": True}
        screen[i] = {"agent": agent, "llm_basis": "no"}
        if p:
            part[i], claude[i] = p, code
    # ICLR: 10 confirmed (6 in the cell); 100 agent negatives, slice of 40 with 2 misses; 200 other negatives, slice of 50 with none
    for n in range(10):
        add(f"i{n}", "iclr-2025", "yes", "a", sev if n < 6 else one)
    for n in range(100):
        add(f"j{n}", "iclr-2025", "yes", *(("c", sev if n < 2 else one) if n < 40 else ()))
    for n in range(200):
        add(f"k{n}", "iclr-2025", "no", *(("d", one) if n < 50 else ()))
    # AAMAS: every paper confirmed, so a direct count
    for n in range(20):
        add(f"m{n}", "aamas-2025", "yes", "a" if n < 5 else "c", sev if n < 5 else one)
    t = table(MEASURES, POPS_EXT, (items, screen, part, claude))
    assert abs(t["all-iclr-2025"]["several"]["share"] - (6 + 100 * 2 / 40) / 310) < 1e-12
    assert abs(t["agent-iclr-2025"]["several"]["share"] - (6 + 5) / 110) < 1e-12 and t["agent-iclr-2025"]["n"] == 110
    assert t["all-iclr-2025"]["several"]["hi"] > t["all-iclr-2025"]["several"]["share"] > t["all-iclr-2025"]["several"]["lo"]
    assert t["all-aamas-2025"].get("census") and t["all-aamas-2025"]["several"]["share"] == 5 / 20
    assert t["llm-agent-iclr-2025"]["n"] == 0 or "several" in t["llm-agent-iclr-2025"]


def test_ea_sensitivity_is_its_own_venue_stratum_and_population_with_files_of_its_own():
    from twostage import MEASURES, POPS_EA, ext_files, stratum, table
    assert stratum({"venue": "aamas-2025-ea"}, {})[0] == "aamas-ea"
    assert ext_files("ext-ea") == ("data/xfam/items-ext-ea.jsonl", "data/xfam/ext-ea-v34/results-parsed.jsonl", "data/xfam/stage2-ext-ea.json")
    assert set(POPS_EA) == {"all-aamas-2025-ea", "agent-aamas-2025-ea", "llm-agent-aamas-2025-ea", "other-agent-aamas-2025-ea"}
    sev = {"faces_other_parties": "yes", "has_decision_maker": "yes", "interests": "several-aligned", "focus": "agent"}
    one = {"faces_other_parties": "no", "has_decision_maker": "yes", "interests": "one", "focus": "agent"}
    items = {f"z{n}": {"xid": f"z{n}", "venue": "aamas-2025-ea", "main_track": True} for n in range(8)}
    screen = {i: {"agent": "yes", "llm_basis": "no"} for i in items}
    part = {i: "a" if n < 3 else "c" for n, i in enumerate(sorted(items))}
    claude = {i: sev if n < 3 else one for n, i in enumerate(sorted(items))}
    t = table(MEASURES, POPS_EA, (items, screen, part, claude))
    assert t["all-aamas-2025-ea"]["census"] and t["all-aamas-2025-ea"]["several"]["share"] == 3 / 8


def test_an_extension_counts_as_ready_only_once_its_whole_draw_is_coded(tmp_path, monkeypatch):
    from twostage import ext_files, ext_ready
    monkeypatch.chdir(tmp_path)
    for f in ext_files("ext-ea"):
        (tmp_path / f).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / "data/coded").mkdir()
    a, b, c = ext_files("ext-ea")
    (tmp_path / a).write_text(json.dumps({"xid": "z1"}) + "\n" + json.dumps({"xid": "z2"}) + "\n")
    (tmp_path / b).write_text("")
    (tmp_path / c).write_text(json.dumps([{"xid": "z1", "part": "a"}, {"xid": "z2", "part": "c"}]))
    assert not ext_ready("ext-ea")  # drawn, not coded: the estimates keep to the main census
    (tmp_path / "data/coded/ext-ea-confirm-00.jsonl").write_text(json.dumps({"id": "z1"}) + "\n")
    assert not ext_ready("ext-ea")
    (tmp_path / "data/coded/ext-ea-confirm-01.jsonl").write_text(json.dumps({"id": "z2"}) + "\n")
    assert ext_ready("ext-ea")
