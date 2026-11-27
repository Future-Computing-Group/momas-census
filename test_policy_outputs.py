"""The v1 and v2 policy passes: the re-analyses, tipping points, SI fragments, Fig. 2a and attention read the policy pass,
now v2 (codebook-policy-v2.2.md; POLICY2_MEASURES, estimates-twostage.json keys policy2, policy2-ext, policy2-ext-ea). Fragments
that need parties codes for the v2 cell are written only once data/estimates-round2-policy2.json exists."""
import json
import os
import subprocess
import sys

import pytest


def rec(ps, pr, interests="several-conflicting", focus="interaction", **kw):
    # v2 fields default to an interacting setting without an outside attacker; the v1 measures ignore them
    return {"policy_setters": ps, "principals": pr, "interests": interests, "focus": focus, "outside_attacker": "no", "interacting": "yes", **kw}


# ---- reanalyses.py ----

def test_reanalyses_drop_the_keyword_rules():
    import reanalyses
    assert not any(hasattr(reanalyses, k) for k in ("NAMED", "owners_split", "abstract_cue", "PARTNERS"))


def test_setters_by_parties_cross_tabulates_the_confirmer_policy_setters_code_by_parties():
    from reanalyses import setters_by_parties
    parties = {"a": "formal-model", "b": "ai-agents", "c": "formal-model", "d": "humans", "e": "humans"}
    claude = {"a": rec("one", "several"), "b": rec("several", "several"), "c": rec("several", "several", outside_attacker="yes"), "d": rec("na", "na"),
              "e": rec("several", "several", "adversarial")}
    t = setters_by_parties(parties, claude)
    assert t["formal-model"] == {"n": 2, "one": 1, "several": 1, "na": 0, "cell": 0}  # c: an outside attacker stays out of the v2 cell
    assert t["ai-agents"] == {"n": 1, "one": 0, "several": 1, "na": 0, "cell": 1}
    assert t["humans"] == {"n": 2, "one": 0, "several": 1, "na": 1, "cell": 1}  # e: v3.4 adversarial, no outside attacker: in the cell (codebook v2)
    assert t["other"]["n"] == 0


def _partner_data():
    """40 confirmed 2025 agent papers: 10 in the cell, of which 4 DATA partitioned and 2 PARTNERS_FROM_OTHERS yes (1 both)."""
    items, screen, part, claude = {}, {}, {}, {}
    for n in range(40):
        i = f"x{n:03d}"
        items[i] = {"venue": "neurips-2025", "main_track": True}
        screen[i] = {"agent": "yes", "llm_basis": "no", "data": "partitioned" if n < 5 else "pooled", "partners_from_others": "no"}
        part[i] = "n"
        code = rec("several", "several") if n < 10 else rec("one", "several" if n < 13 else "one")
        code["data"] = "partitioned" if n < 4 or n == 12 else "pooled"
        code["partners_from_others"] = "yes" if n in (3, 4) else "no"
        claude[i] = code
    return items, screen, part, claude


def test_partners_use_the_coded_fields_and_leave_each_literature_out_of_the_cell():
    from reanalyses import partners
    from twostage import POPS
    pops = {k: POPS[k] for k in ("all-2025", "agent-2025")}
    r = partners(_partner_data(), pops)
    t = r["table"]["all-2025"]
    assert t["several"]["confirmed"] == 10 and t["without-partitioned-data"]["confirmed"] == 6 and t["without-partners-from-others"]["confirmed"] == 8
    g = r["groups"]
    assert g["partitioned-data"] == {"screen_2025": 5, "confirmer_coded": 5, "cell": 4, "simulated": 1}
    assert g["partners-from-others"] == {"screen_2025": 0, "confirmer_coded": 2, "cell": 2, "simulated": 0}
    s = r["table"]["agent-2025"]["partners-from-others"]  # the share of agent papers built for partners that others train or run
    assert s["confirmed"] == 2 and s["share"] == s["lo"] == s["hi"] == 2 / 40


def test_partners_simulated_is_the_v2_simulated_cell():
    from reanalyses import partners
    from twostage import POPS
    items, screen, part, claude = _partner_data()
    claude["x012"]["interacting"] = "no"  # a single learner serving several parties is not simulated (codebook v2)
    assert partners((items, screen, part, claude), {"all-2025": POPS["all-2025"]})["groups"]["partitioned-data"]["simulated"] == 0


# ---- tipping.py ----

def scr(ps, pr, interests="one", focus="interaction", attacker="no", interacting="yes"):
    return {"policy_setters": ps, "principals": pr, "interests": interests, "focus_derived": focus, "outside_attacker": attacker, "interacting": interacting}


def test_screen_cells_are_read_from_the_v2_fields():
    from tipping import SCREEN
    assert SCREEN["several"](scr("several", "several")) and SCREEN["interaction"](scr("several", "several")) and not SCREEN["simulated"](scr("several", "several"))
    assert SCREEN["simulated"](scr("one", "several")) and not SCREEN["several"](scr("one", "several"))
    assert not SCREEN["simulated"](scr("one", "several", interacting="no"))  # a single learner (codebook v2)
    assert not SCREEN["interaction"](scr("several", "several", focus="agent"))
    assert not any(f(scr("several", "several", attacker="yes")) for f in SCREEN.values())  # the exclusion is OUTSIDE_ATTACKER (codebook v2)
    assert SCREEN["several"](scr("several", "several", "adversarial"))  # v3.4 adversarial no longer excludes
    assert not any(f({"interests": "one", "focus_derived": "agent"}) for f in SCREEN.values())  # a screen parse failure codes nothing


def test_tipping_measures_are_the_v2_measures():
    import tipping
    from twostage import POLICY2_MEASURES
    assert tipping.MEASURES is POLICY2_MEASURES


def test_flips_are_counted_in_both_directions_across_the_policy_setters_boundary():
    from tipping import disagreement_measures
    screen = {"a": scr("several", "several"), "b": scr("one", "several")}
    dm = disagreement_measures(screen)
    assert dm["flip"]({"id": "a", **rec("one", "several")}) and not dm["flip"]({"id": "b", **rec("one", "several")})
    assert dm["flip_back"]({"id": "b", **rec("several", "several")}) and not dm["flip_back"]({"id": "a", **rec("several", "several")})


def test_ratio_observed_takes_the_larger_of_both_directions_as_direct_counts():
    from analyze import wilson
    from tipping import ratio_observed
    o = ratio_observed(2, 40, 3, 10)
    assert o["direction"] == "screen" and o["observed"] == (0.3, *wilson(3, 10))
    assert o["confirmer"] == (0.05, *wilson(2, 40))
    assert ratio_observed(15, 40, 1, 10)["direction"] == "confirmer"  # chosen by upper bound, as worst()


def test_rates_count_every_direction_directly_when_every_screen_positive_is_confirmed():
    from tipping import rates
    m = lambda share, k, lo, hi: {"share": share, "confirmed": k, "lo": lo, "hi": hi}
    t = {"p": {"n": 1000, "simulated": m(0.05, 40, 0.04, 0.08), "simulated:cn_sp": m(0.01, 10, 0.01, 0.03), "simulated:cp_sn": m(0.02, 10, 0.015, 0.05)}}
    r = rates(t, "p", 40, "simulated")
    assert abs(r["fp_screen"][0] - 10 / 40) < 1e-12 and r["fp_screen"][2] < 0.5  # direct: the policy confirmer coded every screen positive


def test_every_v2_screen_cell_paper_is_a_v2_screen_positive_so_it_is_confirmed():
    from tipping import SCREEN
    from twostage import policy2_positive
    import itertools
    full = lambda ps, pr, rb, it, oa: {**scr(ps, pr, attacker=oa, interacting=it), "rule_breaking": rb}
    for v in itertools.product(("one", "several", "na"), ("one", "several", "na"), ("yes", "no"), ("yes", "no", "na"), ("yes", "no")):
        s = full(*v)
        if any(f(s) for f in SCREEN.values()):
            assert policy2_positive(s), v


# ---- agreement of the two confirming coders ----

def test_coder_agreement_rows_compare_add_and_dup_by_id_on_fields_and_cells():
    from census import kappa
    from round2 import coder_agreement
    v34 = {i: {"id": i, "interests": "several-conflicting", "focus": "interaction"} for i in "abcd"}
    add = {"a": rec("several", "several", partners_from_others="no"), "b": rec("one", "several", partners_from_others="no"),
           "c": rec("one", "one", partners_from_others="yes"), "d": rec("several", "several", partners_from_others="no")}
    dup = {"a": rec("several", "several", partners_from_others="no"), "b": rec("several", "several", partners_from_others="no"),
           "c": rec("one", "one", partners_from_others="no")}
    for d in (add, dup):
        for r in d.values():
            del r["interests"], r["focus"]
    rows = coder_agreement(v34, add, dup)
    assert [r[0] for r in rows] == ["policy_setters", "principals", "partners_from_others", "several", "simulated"]
    ps = rows[0]
    assert ps[1:3] == (2, 3) and abs(ps[3] - kappa(["several", "one", "one"], ["several", "several", "one"])) < 1e-12
    assert rows[1][1:3] == (3, 3) and rows[2][1:3] == (2, 3)
    assert rows[3][1:3] == (2, 3) and rows[4][1:3] == (2, 3)  # b: simulated for one coder, several for the other


def test_coder_agreement_v2_rows_cover_the_v2_fields_the_derived_cell_and_both_cells():
    from round2 import V2_COMPARED, coder_agreement_v2
    v34 = {i: {"interests": "one"} for i in "abc"}
    add = {"a": rec("several", "several", behaviour="rational", rule_breaking="no", partners_from_others="no"),
           "b": rec("one", "several", behaviour="obedient", rule_breaking="no", partners_from_others="no"),
           "c": rec("several", "several", behaviour="rational", rule_breaking="yes", partners_from_others="no")}
    dup = {"a": rec("several", "several", behaviour="rational", rule_breaking="no", partners_from_others="no"),
           "b": rec("one", "several", behaviour="obedient", rule_breaking="no", partners_from_others="no", interacting="no"),
           "c": rec("several", "several", behaviour="rational", rule_breaking="no", partners_from_others="no")}
    rows = {r[0]: r[1:] for r in coder_agreement_v2(v34, add, dup)}
    assert list(rows) == [*V2_COMPARED, "cell", "several", "simulated"]
    assert V2_COMPARED == ("policy_setters", "principals", "behaviour", "rule_breaking", "interacting", "outside_attacker", "partners_from_others")
    assert rows["interacting"][:2] == (2, 3) and rows["rule_breaking"][:2] == (2, 3) and rows["policy_setters"][:2] == (3, 3)
    assert rows["cell"][:2] == (1, 3)  # b: simulated against single learner; c: rule-breaking against rational
    assert rows["several"][:2] == (3, 3) and rows["simulated"][:2] == (2, 3)


def test_policy2_extra_splits_the_cell_by_interests_and_counts_outside_attackers_apart():
    from round2 import POLICY2_EXTRA
    assert POLICY2_EXTRA["aligned"](rec("several", "several", "several-aligned"))
    assert not POLICY2_EXTRA["aligned"](rec("several", "several", "adversarial"))  # a gain-motivated deviator is conflicting
    assert POLICY2_EXTRA["adversarial"](rec("several", "several", outside_attacker="yes")) and not POLICY2_EXTRA["adversarial"](rec("several", "several", "adversarial"))
    assert POLICY2_EXTRA["adversarial_incl"](rec("several", "several", outside_attacker="yes")) and POLICY2_EXTRA["adversarial_incl"](rec("several", "several"))
    assert POLICY2_EXTRA["simulated_xvendor"](rec("one", "several", cross_vendor="yes")) and not POLICY2_EXTRA["simulated_xvendor"](rec("one", "several", cross_vendor="yes", interacting="no"))


# ---- round2.py: parties jobs for the v2 cell ----

def test_parties_jobs_take_v2_cell_papers_without_a_parties_code():
    from round2 import new_cell
    from twostage import POLICY2_MEASURES
    claude = {"a": rec("several", "several"), "b": rec("several", "several"), "c": rec("several", "several", outside_attacker="yes"),
              "d": rec("several", "several", "adversarial"), "e": rec("one", "several")}
    assert new_cell(claude, {"a"}, POLICY2_MEASURES["several"]) == ["b", "d"]


def test_parties_batches_are_blind_seeded_and_carry_a_20_percent_second_coder_draw():
    from round2 import parties_batches
    cell = [f"x{n:05d}" for n in range(234)]
    b = parties_batches(cell, "policy2", size=100, dup_share=0.2, seeds=(1, 2))
    assert list(b) == ["r2-parties-policy2-01", "r2-parties-policy2-02", "r2-parties-policy2-03", "r2-parties-policy2-dup"]
    prim = [i for k, v in b.items() if not k.endswith("dup") for i in v]
    assert sorted(prim) == cell and len(set(prim)) == 234 and max(len(v) for v in b.values()) <= 100
    assert prim != cell  # shuffled, so a batch is not a run of ids
    assert len(b["r2-parties-policy2-dup"]) == 47 and set(b["r2-parties-policy2-dup"]) <= set(cell)
    assert b == parties_batches(list(cell), "policy2", size=100, dup_share=0.2, seeds=(1, 2))
    assert parties_batches([], "policy2") == {}


# ---- the fragments read the v2 estimates ----

DATA = all(os.path.exists(p) for p in ("data/xfam/items-full.jsonl", "data/estimates-round2-policy2-core.json", "data/estimates-tipping-policy2.json",
                                       "data/estimates-reanalyses-policy2.json", "data/estimates-tipping-author-policy2.json"))
PARTIES2 = os.path.exists("data/estimates-round2-policy2.json")
HELD = ("parties-short.tex", "cell-composition.tex", "tab-parties.tex", "aamas-short.tex", "tab-counts.tex", "n-cell.tex", "parties-agreement.tex",
        "setters-parties.tex", "tab-tipping.tex", "tip-margins.tex")  # tab-attention.tex is attention.py's, gated there


@pytest.fixture(scope="module")
def frags(tmp_path_factory):
    out, doc, est = tmp_path_factory.mktemp("si"), tmp_path_factory.mktemp("doc"), tmp_path_factory.mktemp("est")
    before = os.stat("data/estimates-counts-policy2.json").st_mtime_ns
    r = subprocess.run([sys.executable, "si_tables.py", str(out), str(doc), str(est / "counts.json")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    assert os.stat("data/estimates-counts-policy2.json").st_mtime_ns == before  # the tracked estimates are not rewritten
    return lambda name: (out / name if (out / name).exists() else doc / name).read_text(), out  # SI fragment, else a docs/ fragment


P = lambda m: f"{100 * m['share']:.1f}"
B = lambda m: f"{P(m)}\\% (conservative bounds {100 * m['lo']:.1f} to {100 * m['hi']:.1f}\\%)"


@pytest.mark.skipif(not DATA, reason="needs the local full-run files and the policy2 estimates")
def test_fragments_read_their_numbers_from_the_policy2_estimates(frags):
    read, out = frags
    tw = json.load(open("data/estimates-twostage.json"))
    pw, pe, pea = tw["policy2"], tw["policy2-ext"], tw["policy2-ext-ea"]
    r2 = json.load(open("data/estimates-round2-policy2-core.json"))
    tp = json.load(open("data/estimates-tipping-policy2.json"))
    rx = json.load(open("data/estimates-reanalyses-policy2.json"))
    a = pw["all-2025"]["several"]
    assert read("headline-short.tex") == B(a)
    assert read("ec-share.tex") == f"{P(pw['ec-2025']['several'])}\\%"
    assert read("sim-agent-short.tex") == f"{P(pw['agent-2025']['simulated'])}\\%"
    assert read("iclr-short.tex") == B(pe["all-iclr-2025"]["several"])
    assert read("aamas-ea-short.tex").startswith(f"{pea['all-aamas-2025-ea']['several']['confirmed']} of 160")
    c = r2["contrasts"]
    ra, rd = c["ratio-agent-2025"], c["ratio-llm-minus-other"]
    assert read("ratio-agent.tex") == f"{ra['point']:.2f} (conservative bounds {ra['conservative'][0]:.2f} to {ra['conservative'][1]:.2f})" == "0.44 (conservative bounds 0.23 to 1.04)"
    lo, hi = (f"${x:.2f}$" if x < 0 else f"{x:.2f}" for x in rd["conservative"])
    assert read("ratio-llm-other.tex").endswith(f"(difference {rd['point']:.2f}, conservative bounds {lo} to {hi})")
    assert read("trend-several.tex").split(" points")[0].replace("$", "") == f"difference {c['all-several-2025-2020']['point']:.1f}".replace("-0.0", "0.0")
    rows = read("tab-twostage.tex").splitlines()
    assert rows[1].startswith(f"All papers 2025 & {pw['all-2025']['n']:,} & {pw['all-2025']['screened']} & {a['confirmed']} & {P(a)} (")
    assert any(r.startswith(f"AAMAS 2025 & 260 & {pe['all-aamas-2025']['screened']} & {pe['all-aamas-2025']['several']['confirmed']} &") for r in rows)
    mr = pw["miss_rates"]["several"]["agent"]
    assert all(f"{v[0]}/{v[1]}" in read("screen-misses.tex") for v in mr.values())
    pr = r2["screen_precision"]
    assert read("screen-precision.tex") == f"{pr['agent']['confirmed_several']} of {pr['agent']['screened']} agent papers and {pr['other']['confirmed_several']} of {pr['other']['screened']} other papers"
    assert read("n-confirm.tex") == f"{r2['n_confirm']:,}"
    pa = read("partners.tex")
    for g in ("partitioned-data", "partners-from-others"):
        assert f"{P(rx['partners']['table']['all-2025']['without-' + g])}\\%" in pa
    from tipping import ec_band
    lo, hi = ec_band(tp["ec"])
    assert read("ec-band.tex") == f"{100 * lo:.1f}\\% to {100 * hi:.1f}\\%"
    t2 = r2["table"]
    assert read("decomp-short.tex").startswith(f"all papers 2020, {P(t2['all-2020']['conflicting'])} of {P(t2['all-2020']['several'])}\\%")
    assert f"outside attacker raises the 2025 share to {P(t2['all-2025']['adversarial_incl'])}\\%" in read("decomp-short.tex")
    cvt = read("crossvendor.tex")
    cv = r2["cross_vendor"]
    assert cvt.startswith(f"{cv['yes']} of the {cv['n']} LLM-agent papers") and f"cross-vendor papers are {cv['several_stage2_yes']} of the {cv['several_stage2']}" in cvt
    sa = read("tab-screen-agreement.tex")
    for k, v in r2["screen_agreement"].items():
        assert f"{k.upper().replace('_', chr(92) + '_')} & {v['agree']}/{v['n']} & {v['kappa']:.2f} \\\\" in sa
    assert "BEHAVIOUR" in sa and "OUTSIDE\\_ATTACKER" in sa and "RULE\\_BREAKING" in sa
    assert not (out / "deploy-role-short.tex").exists() and not (out / "owners-split.tex").exists()


@pytest.mark.skipif(not DATA, reason="needs the local full-run files and the policy2 estimates")
def test_new_v2_fragments_read_the_policy2_cells(frags):
    read, _ = frags
    pw = json.load(open("data/estimates-twostage.json"))["policy2"]
    a = pw["all-2025"]
    assert read("several-rational-short.tex") == B(a["several_rational_within"])
    assert read("rule-breaking-short.tex") == B(a["several_rule_breaking"])
    assert read("single-learner-short.tex") == B(a["single_learner_several_principals"])
    rp = a["rational_prescribed"]
    assert read("rational-prescribed-n.tex") == f"{rp['confirmed']} confirmed papers of 2025, an estimated {P(rp)}\\% of all 2025 papers (conservative bounds {100 * rp['lo']:.1f} to {100 * rp['hi']:.1f}\\%)"
    v = read("v34-exclusion-sensitivity.tex")
    assert v.startswith(B(a["several_v34_exclusion"])) and B(a["several"]) in v
    assert f"{a['several_v34_exclusion']['confirmed']} confirmed papers against {a['several']['confirmed']}" in v
    assert read("setters-one-agent.tex") == B(pw["agent-2025"]["setters_one"])
    assert read("setters-one-all.tex") == B(a["setters_one"])
    assert read("principals-one-agent.tex") == B(pw["agent-2025"]["principals_one"])
    for f in ("several-rational-short.tex", "rule-breaking-short.tex", "single-learner-short.tex", "rational-prescribed-n.tex", "v34-exclusion-sensitivity.tex",
              "decomp-short.tex", "crossvendor.tex", "tip-author-policy.tex"):
        assert "—" not in read(f) and "–" not in read(f)


@pytest.mark.skipif(not DATA, reason="needs the local full-run files and the policy2 estimates")
def test_coder_agreement_table_has_the_v2_rows_from_the_add_dup_pairs(frags):
    read, _ = frags
    r2 = json.load(open("data/estimates-round2-policy2-core.json"))
    ca = read("tab-coder-agreement.tex").splitlines()
    ag = r2["coder_agreement"]
    assert list(ag) == ["policy_setters", "principals", "behaviour", "rule_breaking", "interacting", "outside_attacker", "partners_from_others", "cell", "several", "simulated"]
    assert all(v["n"] == 2210 for v in ag.values())
    for k, v in ag.items():
        assert any(r.endswith(f" & {v['agree']}/{v['n']} & {v['kappa']:.2f} \\\\") for r in ca), k
    assert ("PARTIES" in "".join(ca)) == PARTIES2  # the parties rows wait for the v2 parties codes


@pytest.mark.skipif(not DATA, reason="needs the local full-run files and the policy2 estimates")
def test_fragments_that_need_parties_codes_wait_for_the_v2_parties_split(frags):
    _, out = frags
    for f in HELD:
        assert (out / f).exists() == PARTIES2, f
    tp = json.load(open("data/estimates-tipping-policy2.json"))
    assert ("parties" in tp) == PARTIES2
    rx = json.load(open("data/estimates-reanalyses-policy2.json"))
    assert ("setters_by_parties" in rx) == PARTIES2


@pytest.mark.skipif(not DATA, reason="needs the local full-run files and the policy2 estimates")
def test_tipping_ratio_rows_and_author_shift_read_policy2(frags):
    read, _ = frags
    tp = json.load(open("data/estimates-tipping-policy2.json"))
    pw = json.load(open("data/estimates-twostage.json"))["policy2"]
    r = tp["ratio"]["agent-2025"]
    N = pw["agent-2025"]["n"]
    assert abs(r["S"] - pw["agent-2025"]["simulated"]["share"] * N) < 1e-9 and abs(r["V"] - pw["agent-2025"]["several"]["share"] * N) < 1e-9
    assert f"from {r['ratio']:.1f} to 1" in read("tip-ratio.tex")  # DOC fragment, written to the doc dir
    au = json.load(open("data/estimates-tipping-author-policy2.json"))
    assert read("tip-author-policy.tex").startswith(f"{au['raise']} of {au['m']} ")


@pytest.mark.skipif(not DATA, reason="needs the local full-run files and the policy2 estimates")
def test_v34_and_v1_estimate_files_stay_as_committed_and_the_v2_scripts_write_their_own():
    kept = ["data/estimates-tipping.json", "data/estimates-reanalyses.json", "data/estimates-counts.json", "data/estimates-attention.json", "data/estimates-round2.json",
            "data/estimates-tipping-policy.json", "data/estimates-reanalyses-policy.json", "data/estimates-counts-policy.json", "data/estimates-attention-policy.json",
            "data/estimates-round2-policy.json", "data/estimates-cell-composition.json", "data/estimates-tipping-author-policy.json"]
    r = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", *kept], capture_output=True)
    assert r.returncode == 0, "a v3.4 or v1 estimate file changed"


@pytest.mark.skipif(not DATA, reason="needs the local full-run files and the policy2 estimates")
def test_attention_cells_are_the_policy2_cell(tmp_path):
    import attention
    from twostage import POLICY2_MEASURES, load_policy2
    _, _, part, claude = load_policy2("full")
    items, cell, sub = attention.cells("main")
    assert cell == {i for i in part if POLICY2_MEASURES["several"](claude[i])}
    assert (sub is None) == (not PARTIES2)
    before = os.stat("data/estimates-attention-policy2.json").st_mtime_ns
    r = subprocess.run([sys.executable, "attention.py", str(tmp_path), str(tmp_path / "attention.json")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    assert os.stat("data/estimates-attention-policy2.json").st_mtime_ns == before  # the tracked estimates are not rewritten
    assert json.load(open(tmp_path / "attention.json")) == json.load(open("data/estimates-attention-policy2.json"))
    assert (tmp_path / "tab-attention.tex").exists() == PARTIES2
    assert (tmp_path / "attention-ratio.tex").exists()
    a = json.load(open("data/estimates-attention-policy2.json"))
    assert abs(a["neurips-2025"]["cell"]["paper_share"] - len([i for i in cell if items[i]["venue"] == "neurips-2025" and i in json.load(open("data/attention/neurips-2025.json"))["cites"]]) / a["neurips-2025"]["matched"]) < 1e-12


# ---- majority cells and the author's codes under the policy cells ----

def test_policy_shares_code_one_setter_and_one_principal_from_the_policy_fields_alone():
    from twostage import POLICY_SHARES
    assert set(POLICY_SHARES) == {"setters_one", "principals_one"}
    assert POLICY_SHARES["setters_one"](rec("one", "several", "adversarial")) and not POLICY_SHARES["setters_one"](rec("na", "one"))
    assert POLICY_SHARES["principals_one"](rec("several", "one")) and not POLICY_SHARES["principals_one"](rec("one", "several"))


def _restrict(cur, head):
    """cur cut down to the keys head has, recursively."""
    return {k: _restrict(cur[k], v) for k, v in head.items()} if isinstance(head, dict) else cur


def _head_json(path):
    r = subprocess.run(["git", "show", f"HEAD:{path}"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


@pytest.mark.skipif(not DATA, reason="needs the local full-run files and the policy2 estimates")
def test_twostage_keeps_every_committed_value_and_adds_the_majority_measures():
    head, cur = _head_json("data/estimates-twostage.json"), json.load(open("data/estimates-twostage.json"))
    assert json.dumps(_restrict(cur, head), sort_keys=True) == json.dumps(head, sort_keys=True)
    for k in ("all-2025", "agent-2025"):
        m = cur["policy2"][k]["setters_one"]
        assert 0.5 < m["lo"] <= m["share"] <= m["hi"] <= 1
    assert "principals_one" in cur["policy2"]["agent-2025"]


def test_author_policy_shift_substitutes_the_author_code_into_policy_setters():
    from tipping import author_policy_shift
    claude = {"a": rec("several", "several", "one"), "b": rec("one", "several", "one"), "c": rec("one", "one"), "d": rec("several", "several"), "e": rec("several", "several"), "f": rec("one", "one")}
    mine = {"a": "one", "b": "several", "c": "several", "d": "one", "e": "na", "f": "one"}
    in_pop = {"a", "b", "c", "e", "f"}  # d is outside the population
    r = author_policy_shift(mine, claude, in_pop)
    assert r["papers"] == {"a": "raise", "b": "lower", "c": "leave", "d": "leave", "e": "raise"}  # f agrees, so it is no disagreement
    assert (r["raise"], r["lower"], r["leave"], r["m"], r["n"]) == (2, 1, 2, 5, 6)


@pytest.mark.skipif(not (DATA and PARTIES2), reason="needs the v2 parties split (data/estimates-round2-policy2.json)")
def test_parties_fragments_read_the_policy2_split(frags):
    read, _ = frags
    pw = json.load(open("data/estimates-twostage.json"))["policy2"]
    r2 = json.load(open("data/estimates-round2-policy2.json"))
    pt = r2["full"]
    assert read("parties-short.tex").startswith(f"{P(pt['all-2025']['parties_ai-agents'])}\\% of 2025 papers")
    assert int(read("n-cell.tex").replace(",", "")) == r2["n_cell"]
    cc = r2["composition"]["all-2025"]
    assert read("cell-composition.tex").startswith(f"of the {P(pw['all-2025']['several'])}\\%, {P(pt['all-2025']['parties_formal-model'])} points")
    assert f"of which {P(cc['parties_other_partitioned'])} points" in read("cell-composition.tex")
    assert f"{r2['ext']['all-aamas-2025']['parties_ai-agents']['confirmed']} (" in read("aamas-short.tex")


@pytest.mark.skipif(not DATA or PARTIES2 or os.path.exists("data/coded/r2-parties-policy2-01.jsonl"), reason="only while the v2 parties codes are missing")
def test_policy2_split_refuses_while_a_v2_cell_paper_has_no_parties_code():
    from round2 import main_policy2
    with pytest.raises(AssertionError, match="v2 cell papers have no parties code"):
        main_policy2()
    assert not os.path.exists("data/estimates-round2-policy2.json")


@pytest.mark.skipif(not DATA, reason="needs the local full-run files")
def test_policy2_split_runs_on_stand_in_codes_and_writes_every_key_the_fragments_read(tmp_path, monkeypatch):
    import round2
    from twostage import POLICY2_MEASURES, load_policy2
    cell = sorted({i for t in round2.POLICY_POPS for d in [load_policy2(t)] for i in d[2] if POLICY2_MEASURES["several"](d[3][i])})
    fake = {i: round2.PARTIES[n % 4] for n, i in enumerate(cell)}
    monkeypatch.setattr(round2, "load_parties", lambda pattern=None: fake)
    monkeypatch.setattr(round2, "POLICY2_PARTIES", str(tmp_path / "r2p2.json"))
    round2.main_policy2()
    out = json.load(open(tmp_path / "r2p2.json"))
    assert out["n_cell"] == len(cell) and {"full", "ext", "ext-ea", "composition", "parties_agreement", "parties_agreement_policy2_dup"} <= set(out)
    m = out["full"]["all-2025"]
    assert abs(sum(m[f"parties_{c}"]["confirmed"] for c in round2.PARTIES) - json.load(open("data/estimates-twostage.json"))["policy2"]["all-2025"]["several"]["confirmed"]) == 0
    assert out["composition"]["all-2025"]["parties_other_partitioned"]["confirmed"] <= m["parties_other"]["confirmed"]
    assert "parties_ai-agents" in out["ext"]["all-aamas-2025"] and out["parties_agreement"]["agree"] == out["parties_agreement"]["n"]


@pytest.mark.skipif(not PARTIES2, reason="needs the v2 parties split")
def test_tipping_rows_never_print_a_share_above_all_papers(frags):
    import re
    read, _ = frags
    for m in re.finditer(r"([0-9.]+)\\% of other cell papers", read("tab-tipping.tex")):
        assert float(m.group(1)) <= 100, m.group(0)


@pytest.mark.skipif(not DATA, reason="needs the local full-run files and the policy2 estimates")
def test_pi_recon_is_in_the_first_person(frags):
    text = frags[0]("pi-recon.tex")
    assert "the author" not in text and "their own" not in text
    assert "I adopted" in text


MS = os.environ.get("NMI_MANUSCRIPT", "/nonexistent") + "/"  # the manuscript directory, local only
LITS = ("C1", "C2", "C3", "C4", "C5", "C6", "C7", "R1", "R2", "R3", "R4")


@pytest.mark.skipif(not DATA, reason="needs the local full-run files and the policy2 estimates")
def test_seeds_cited_fragment_counts_the_seed_to_citation_map(frags):
    cites = json.load(open("data/fields/seeds-main-cites.json"))
    ids = {x["openalex"] for x in json.load(open("data/fields/seeds-broad.json")) if x["cluster"] in LITS}
    assert set(cites) <= ids
    assert frags[0]("n3-seeds-cited.tex") == str(len(cites))


@pytest.mark.skipif(not os.path.exists(MS + "main.tex"), reason="needs the manuscript")
def test_seed_to_citation_map_matches_the_main_text():
    import re
    tex, bib = open(MS + "main.tex").read(), open(MS + "references.bib").read()
    keys = {k.strip() for c in re.findall(r"\\cite\w*\*?(?:\[[^]]*\])*\{([^}]*)\}", tex) for k in c.split(",")}
    ents = {k.strip(): b for k, b in re.findall(r"@\w+\s*\{([^,]+),(.*?)(?=\n@|\Z)", bib, re.S)}
    norm = lambda s: re.sub(r"[^a-z0-9]", "", (s or "").lower())
    title = {k: norm(m.group(1))[:30] for k in keys if (m := re.search(r"\btitle\s*=\s*[{\"](.+?)[}\"]\s*,\s*\n", ents[k], re.I | re.S))}
    doi = {k: norm(m.group(1)) for k in keys if (m := re.search(r"doi\s*=\s*[{\"]([^}\"]+)", ents[k], re.I))}
    found = {}
    for s in json.load(open("data/fields/seeds-broad.json")):
        if s["cluster"] not in LITS:
            continue
        d, t = norm((s.get("doi_tried") or "").replace("https://doi.org/", "")), norm(s["oa_title"])[:30]
        hit = [k for k in keys if (d and doi.get(k) == d) or title.get(k) == t]
        if hit:
            found[s["openalex"]] = hit[0]
    assert found == json.load(open("data/fields/seeds-main-cites.json"))


@pytest.mark.skipif(not DATA, reason="needs the local full-run files and the policy2 estimates")
def test_neurips_coverage_fragment_reads_the_coverage_file(frags):
    nc = json.load(open("data/fields/neurips-coverage.json"))
    sh = [nc["with_refs"][y] / nc["n"][y] for y in nc["n"]]
    assert frags[0]("n3-neurips-coverage.tex") == f"{100 * min(sh):.0f}\\% to {100 * max(sh):.0f}\\% of NeurIPS records from {min(nc['n'])} to {max(nc['n'])}"


@pytest.mark.skipif(not (DATA and PARTIES2), reason="needs the local full-run files and the policy2 parties estimates")
def test_section4_rough_fragments_round_the_same_estimates(frags):
    from si_ext import rough_pct, rough_fraction, rough_rate, rough_under
    read, _ = frags
    tw = json.load(open("data/estimates-twostage.json"))
    pw, pe = tw["policy2"], tw["policy2-ext"]
    pt = json.load(open("data/estimates-round2-policy2.json"))
    ai = lambda d, k: d[k]["parties_ai-agents"]["share"]
    assert read("sec4-ml-several.tex") == rough_pct([pw["all-2025"]["several"]["share"], pe["all-iclr-2025"]["several"]["share"]]) == "about 2\\%"
    assert read("sec4-ec-several.tex") == rough_fraction(pw["ec-2025"]["several"]["share"]) == "more than half"
    assert read("sec4-aamas-several.tex") == rough_fraction(pe["all-aamas-2025"]["several"]["share"]) == "about a fifth"
    assert read("sec4-ai-all.tex") == rough_rate(ai(pt["full"], "all-2025")) == "about 1 in 1,000"
    m = lambda d, k: d[k]["parties_ai-agents"]
    under = [(x["share"], x["hi"]) for x in [m(pt["full"], k) for k in ("agent-2025", "llm-agent-2025", "ec-2025")] + [m(pt["ext"], "all-aamas-2025")]]
    assert read("sec4-ai-under.tex") == rough_under(under) == "under 3 in 100"


@pytest.mark.skipif(not DATA, reason="needs the local full-run files and the policy2 estimates")
def test_control_robotics_fragment_reads_the_stored_topic_hits(frags):
    assert frags[0]("n3-control-robotics.tex") == "143 of 253"


@pytest.mark.skipif(not DATA, reason="needs the local full-run files and the policy2 estimates")
def test_partners_agent_share_fragment_reads_the_reanalyses(frags):
    m = json.load(open("data/estimates-reanalyses-policy2.json"))["partners"]["table"]["agent-2025"]["partners-from-others"]
    assert frags[0]("partners-agent-share.tex") == B(m)


@pytest.mark.skipif(not DATA, reason="needs the local full-run files and the policy2 estimates")
def test_deploy_gate_and_v2_v4_overlap_fragments(frags):
    read = frags[0]
    assert read("deploy-gate-agreement.tex") == "88 of 93 pages ($\\kappa = 0.64$)"
    assert read("deploy-v2v4-overlap.tex").startswith("75 of the 83 pages both code as live are among the 83 pages of the first coding")
    from deploy_layers import LABEL
    row = [r for r in read("tab-deploy-layers.tex").splitlines() if r.startswith(LABEL["agent_to_agent"] + " &")]
    assert len(row) == 1 and row[0].endswith("& -- \\\\")  # no page shows another organization's agent: kappa undefined


@pytest.mark.skipif(not (DATA and PARTIES2), reason="needs the local full-run files and the policy2 parties estimates")
def test_typed_census_numbers_have_fragments(frags):
    read = frags[0]
    tw = json.load(open("data/estimates-twostage.json"))
    assert read("sec4-ml-formal.tex") == "about half of them as parties in formal models"
    assert read("sec4-ec-formal.tex") == "mostly in formal models"
    assert read("n-iclr.tex") == f"{tw['policy2-ext']['all-iclr-2025']['n']:,}" == "3,708"
    assert read("n-deploy-pages.tex") == "156" and read("n-author-check.tex") == "20"
    assert read("dup-aamas.tex") == read("dup-ec.tex") == "70"
    assert read("author-draw.tex") == "13 drawn at random among the papers it then coded several owners and 7 from the rest"
    assert read("deploy-showcase-max.tex") == "71"
