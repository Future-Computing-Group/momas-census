"""Two-stage census estimates: the open-weight screen codes every paper; Claude confirms every paper the screen codes owners
several (parts a, b, e) and codes random slices of screen-negatives (part c: agent papers, part d: other papers) to estimate misses.

Populations are defined on the screen's codes (venue, main track, AGENT, LLM_BASIS). Writes data/estimates-twostage.json.
The ICLR 2025 / AAMAS 2025 extension (items-ext.jsonl, its own screen run, stage-2 draw and confirmation codes) is estimated
the same way, from its own slices and strata, under the key "ext" once data/xfam/stage2-ext.json exists; the main census
keys do not depend on it.
"""
import glob
import json
import os

SEVERAL = ("several-aligned", "several-conflicting")


def claude_owners(r):
    if r.get("faces_other_parties") == "yes":
        return "several"
    return "one" if r.get("has_decision_maker") == "yes" else "na"


MIN_STRATUM = 30


def stratum_rate(strata, key):
    """Miss rate in one stratum of a random slice (0/1 outcomes), pooled over strata when the stratum has < MIN_STRATUM papers."""
    v = strata.get(key, [])
    if len(v) >= MIN_STRATUM:
        return sum(v) / len(v)
    allv = [y for w in strata.values() for y in w]
    return sum(allv) / len(allv)


def miss_bounds(negs, strata):
    """95% bounds on expected misses: each stratum's negatives times the Wilson bounds of its (pooled if thin) miss rate."""
    from analyze import wilson
    lo = hi = 0.0
    allv = [y for w in strata.values() for y in w]
    for k, n in negs.items():
        v = strata.get(k, [])
        v = v if len(v) >= MIN_STRATUM else allv
        a, b = wilson(sum(v), len(v))
        lo, hi = lo + n * a, hi + n * b
    return lo, hi


def stratum(x, s):
    yr = "2020" if x["venue"].endswith("2020") else {"ec-2025": "ec", "iclr-2025": "iclr", "aamas-2025": "aamas", "aamas-2025-ea": "aamas-ea"}.get(x["venue"], "2025")
    return (yr, s.get("llm_basis") == "yes")


def two_stage_count(confirmed, neg_agent, rate_agent, neg_other, rate_other):
    return confirmed + neg_agent * rate_agent + neg_other * rate_other


MEASURES = {
    "several": lambda r: claude_owners(r) == "several" and r.get("interests") in SEVERAL,
    "conflicting": lambda r: claude_owners(r) == "several" and r.get("interests") == "several-conflicting",
    "interaction": lambda r: claude_owners(r) == "several" and r.get("interests") in SEVERAL and r.get("focus") == "interaction",
    "simulated": lambda r: claude_owners(r) == "one" and r.get("interests") in SEVERAL,
}


# Policy pass (codebook-policy.md, v1): the cells from who sets each decision-maker's policy and how many
# parties' interests they serve. INTERESTS and FOCUS stay v3.4 codes and enter only the conflicting and interaction splits.
POLICY_MEASURES = {
    "several": lambda r: r.get("policy_setters") == "several" and r.get("principals") == "several" and r.get("interests") != "adversarial",
    "conflicting": lambda r: r.get("policy_setters") == "several" and r.get("principals") == "several" and r.get("interests") == "several-conflicting",
    "interaction": lambda r: r.get("policy_setters") == "several" and r.get("principals") == "several" and r.get("interests") != "adversarial" and r.get("focus") == "interaction",
    "simulated": lambda r: r.get("policy_setters") == "one" and r.get("principals") == "several" and r.get("interests") != "adversarial",
}
# Adversarial v3.4 INTERESTS (an attacker against a victim's model) stay out of every cell, as in the v3.4 MEASURES.
# Majority cells (POLICY_SETTERS one, PRINCIPALS one), estimated beside the cells under the policy keys only. The estimator holds
# for them as for the rare cells: the unconfirmed papers of a population are the policy screen's negatives (one or na on both
# fields), the slices c and d are simple random samples of those negatives within each stratum, and k + sum over strata of
# negatives x slice rate is the stratified estimate of any 0/1 measure, whatever its prevalence; the bounds add each stratum's
# Wilson bounds, which stays conservative. Prevalence changes only the width: for a majority cell most of the share comes from
# the negatives, so its bounds are wider than a rare cell's. The one assumption that weighs more here is the pooling
# of a stratum with < MIN_STRATUM slice papers (stratum_rate), which takes the rate as equal across strata; in the 2025
# main-track populations every stratum that holds negatives has its own slice (agent papers 130 and 200, other papers 566), so
# no pooled rate enters their majority shares.
POLICY_SHARES = {
    "setters_one": lambda r: r.get("policy_setters") == "one",
    "principals_one": lambda r: r.get("principals") == "one",
}
POLICY_TAGS = ("full", "ext", "ext-ea")
POLICY_RUN = "data/xfam/policy-v1/results-parsed.jsonl"
PREFIX = {"full": "x", "ext": "y", "ext-ea": "z"}


def policy_positive(r):
    """A screen code that can place a paper in either cell; a paper the screen failed to code (None) counts as positive."""
    return r is None or "several" in (r["policy_setters"], r["principals"])


def policy_parts(part, items, s34, sp, positive=policy_positive):
    """Stage-2 parts for the policy estimate. Confirmed: the old confirmed parts, every screen-positive (n, coded in full if
    the v3.4 confirmer had not coded it) and every v3.4 owners-na paper (z, outside the old slice frames). Slices: the old
    random slices c and d restricted to the new negatives; a slice of the old negatives that are new negatives is a simple
    random sample of the new negatives in its stratum. 2025 slice papers outside the main track leave the slices. A paper
    the screen failed to code (a parse failure) is confirmed like a positive. positive: the screen's rule (v1 by default)."""
    out = {}
    for i, x in items.items():
        p = part.get(i)
        non_main_2025 = x["venue"] in ("neurips-2025", "icml-2025") and not x["main_track"]
        if p is None and non_main_2025:  # in no population, never drawn
            continue
        if p is None or p in "cd":
            if positive(sp.get(i)):
                p = "n"
            elif s34[i]["owners_derived"] == "na":
                p = "z"
            elif p is not None and non_main_2025:
                p = None
        if p is not None:
            out[i] = p
    return out


def join_policy(v34, pol, keys=frozenset({"id", "policy_setters", "policy_quote", "principals", "principals_quote", "partners_from_others"})):
    """Confirmer codes by id: the v3.4 record (data/coded/*confirm-* or, for a paper the v3.4 confirmer had not coded,
    data/coded/policy-v34-*) with the policy addendum (data/coded/policy-add-*). An addendum never carries a v3.4 field.
    keys: the addendum's key set (v1 by default; the v2 pass passes xfam_inputs.V2_KEYS)."""
    for i, r in pol.items():
        assert set(r) <= keys, i
    return {i: {**v34.get(i, {}), **r} for i, r in pol.items()}


def load_codes(pattern):
    return {r["id"]: r for f in sorted(glob.glob(pattern)) for r in map(json.loads, filter(str.strip, open(f)))}


def load_policy(tag="full"):
    """Items, screen codes (v3.4 with the policy screen's fields merged in, where it parsed), policy parts and joined confirmer
    codes. The second-coder files (policy-dup-*) never enter."""
    items, s34, part, claude = load() if tag == "full" else load_ext(tag)
    sp = {r["id"]: r for r in map(json.loads, open(POLICY_RUN)) if r["id"][0] == PREFIX[tag]}
    p = policy_parts(part, items, s34, sp)
    v34 = {**load_codes("data/coded/policy-v34-*.jsonl"), **claude}
    screen = {i: {**s, **sp.get(i, {})} for i, s in s34.items()}
    return items, screen, p, join_policy(v34, {i: r for i, r in load_codes("data/coded/policy-add-*.jsonl").items() if i in items})


# Policy pass v2 (codebook-policy-v2.md or its revision, now v2.2). OUTSIDE_ATTACKER replaces v3.4 INTERESTS
# adversarial as the exclusion; a v3.4 adversarial paper that passes it is a gain-motivated deviator and counts as conflicting.
POLICY2_RUN = "data/xfam/policy-v2/results-parsed.jsonl"


def _no_attacker(r):
    return r.get("outside_attacker") == "no"


def _several2(r):
    return r.get("policy_setters") == "several" and r.get("principals") == "several" and _no_attacker(r)


def _one_several(r, interacting):
    return r.get("policy_setters") == "one" and r.get("principals") == "several" and r.get("interacting") == interacting and _no_attacker(r)


POLICY2_MEASURES = {
    "several": _several2,
    # rule R5: Box 2's population is the rational share within the rules; rule-breakers for gain stay in the cell (Argument 2)
    "several_rational_within": lambda r: _several2(r) and r.get("behaviour") in ("rational", "mixed") and r.get("rule_breaking") == "no",
    "several_rule_breaking": lambda r: _several2(r) and r.get("rule_breaking") == "yes",
    "conflicting": lambda r: _several2(r) and r.get("interests") in ("several-conflicting", "adversarial"),
    "interaction": lambda r: _several2(r) and r.get("focus") == "interaction",
    "simulated": lambda r: _one_several(r, "yes"),
    "single_learner_several_principals": lambda r: _one_several(r, "no"),
    # rule R6: rational players who all run the prescribed algorithm; one SI sentence beside the self-interested share
    "rational_prescribed": lambda r: r.get("policy_setters") == "one" and r.get("behaviour") == "rational" and r.get("interacting") == "yes",
    # codebook v2: SI sensitivity row, the v3.4 INTERESTS adversarial exclusion in place of OUTSIDE_ATTACKER
    "several_v34_exclusion": lambda r: r.get("policy_setters") == "several" and r.get("principals") == "several" and r.get("interests") != "adversarial",
    **POLICY_SHARES,
}


def policy2_positive(r):
    """v2 screen positive (codebook-policy-v2.2.md): POLICY_SETTERS several, or PRINCIPALS several, or RULE_BREAKING yes, or
    INTERACTING yes; a paper the screen failed to code (None) counts as positive. Every v2 cell needs setters or principals
    several; RULE_BREAKING yes and INTERACTING yes add the papers whose setters or principals the screen may have read one."""
    return r is None or r["policy_setters"] == "several" or r["principals"] == "several" or r["rule_breaking"] == "yes" or r["interacting"] == "yes"


def policy2_parts(part, items, s34, sp1, sp2):
    """Stage-2 parts for the v2 estimate: the v1 policy parts (policy_parts on the v1 screen sp1), then every v2 screen-positive
    or v2 parse failure that is not yet confirmed joins part n. Confirmed: the v3.4 parts a, b, e, x, the v1 positives and
    every v3.4 owners-na paper (all coded by the v1 addendum) plus the new v2 positives. Slices: the old slices c and d
    restricted to papers negative on both screens (and, as in the v1 pass, to the 2025 main track), so each slice stays a simple
    random sample of the remaining negatives in its stratum."""
    return policy_parts(policy_parts(part, items, s34, sp1), items, s34, sp2, policy2_positive)


def screen_run(path, tag):
    return {r["id"]: r for r in map(json.loads, open(path)) if r["id"][0] == PREFIX[tag]}


def load_policy2(tag="full"):
    """As load_policy, from the v1 and v2 screens (POLICY_RUN, POLICY2_RUN; parts by policy2_parts) and the v2 confirmer codes
    data/coded/policy2-add-*.jsonl; the second-coder files (policy2-dup-*) never enter, and policy2-v34-* files carry v3.4
    codes for papers no v3.4 confirmer coded."""
    from xfam_inputs import V2_KEYS
    items, s34, part, claude = load() if tag == "full" else load_ext(tag)
    sp = screen_run(POLICY2_RUN, tag)
    p = policy2_parts(part, items, s34, screen_run(POLICY_RUN, tag), sp)
    v34 = {**load_codes("data/coded/policy-v34-*.jsonl"), **load_codes("data/coded/policy2-v34-*.jsonl"), **claude}
    pol = {i: r for i, r in load_codes("data/coded/policy2-add-*.jsonl").items() if i in items}
    screen = {i: {**s, **sp.get(i, {})} for i, s in s34.items()}
    return items, screen, p, join_policy(v34, pol, set(V2_KEYS))


def policy2_ready(tag="full"):
    """Every paper in the tag's v2 parts has a policy2-add code and a v3.4 code (until then estimates() emits no policy2 key)."""
    if not os.path.exists(POLICY2_RUN) or (tag != "full" and not ext_ready(tag)):
        return False
    items, s34, part, claude = load_policy2(tag)
    return all(i in claude and "policy_setters" in claude[i] and "interests" in claude[i] for i in part)


def policy_ready(tag="full"):
    if not os.path.exists(POLICY_RUN) or (tag != "full" and not ext_ready(tag)):
        return False
    items, s34, part, claude = load_policy(tag)
    return all(i in claude and "policy_setters" in claude[i] and "interests" in claude[i] for i in part)


def load():
    items = {json.loads(l)["xid"]: json.loads(l) for l in open("data/xfam/items-full.jsonl")}
    screen = {}
    for l in open("data/xfam/full-v34/results-parsed.jsonl"):
        r = json.loads(l)
        screen[r["id"]] = r
    part = {x["xid"]: x["part"] for x in json.load(open("data/xfam/stage2-confirm.json"))}
    part.update({i: "e" for i in json.load(open("data/xfam/stage2-part-e.json"))})
    # parts f and g are further random draws within strata of screen-negatives: f joins slice d (non-agent), g slice c (2025 LLM-agent)
    fg = json.load(open("data/xfam/stage2-parts-fg.json"))
    part.update({i: "d" for i in fg["f"]})
    part.update({i: "c" for i in fg["g"]})
    if os.path.exists("data/xfam/stage2-part-ec.json"):
        part.update({i: "x" for i in json.load(open("data/xfam/stage2-part-ec.json"))})
    claude = {}
    for f in sorted(glob.glob("data/coded/confirm-*.jsonl")):
        for l in open(f):
            if l.strip():
                r = json.loads(l)
                claude[r["id"]] = r
    return items, screen, part, claude


def ext_files(tag="ext"):
    """Items, screen codes and stage-2 draw of an extension run: "ext" (ICLR + AAMAS) or "ext-ea" (AAMAS EA + Blue Sky)."""
    return (f"data/xfam/items-{tag}.jsonl", f"data/xfam/{tag}-v34/results-parsed.jsonl", f"data/xfam/stage2-{tag}.json")


EXT_FILES = ext_files()


def ext_ready(tag="ext"):
    """The run's files exist and the confirmer has coded its whole stage-2 draw (until then the estimates keep to the main census)."""
    if not all(os.path.exists(p) for p in ext_files(tag)):
        return False
    coded = {r["id"] for f in glob.glob(f"data/coded/{tag}-confirm-*.jsonl") for r in map(json.loads, filter(str.strip, open(f)))}
    return all(x["xid"] in coded for x in json.load(open(ext_files(tag)[2])))


def load_ext(tag="ext"):
    """The extension's items, screen codes, stage-2 parts and confirmation codes (data/coded/{tag}-confirm-*.jsonl)."""
    f_items, f_screen, f_part = ext_files(tag)
    items = {x["xid"]: x for x in map(json.loads, open(f_items))}
    screen = {r["id"]: r for r in map(json.loads, open(f_screen))}
    part = {x["xid"]: x["part"] for x in json.load(open(f_part))}
    claude = {r["id"]: r for f in sorted(glob.glob(f"data/coded/{tag}-confirm-*.jsonl")) for r in map(json.loads, filter(str.strip, open(f)))}
    return items, screen, part, claude


MAIN_2025 = lambda x: x["venue"] in ("neurips-2025", "icml-2025") and x["main_track"]
POPS = {
    "all-2020": lambda x, s: x["venue"].endswith("2020"),
    "all-2025": lambda x, s: MAIN_2025(x),
    "agent-2020": lambda x, s: x["venue"].endswith("2020") and s["agent"] == "yes",
    "agent-2025": lambda x, s: MAIN_2025(x) and s["agent"] == "yes",
    "llm-agent-2025": lambda x, s: MAIN_2025(x) and s["agent"] == "yes" and s["llm_basis"] == "yes",
    "other-agent-2025": lambda x, s: MAIN_2025(x) and s["agent"] == "yes" and s["llm_basis"] != "yes",
    "ec-2025": lambda x, s: x["venue"] == "ec-2025",
}
def venue_pops(v):
    """All, agent, LLM-agent and other-agent main papers of one extension venue (AGENT and LLM_BASIS from the screen)."""
    return {f"all-{v}": lambda x, s: x["venue"] == v and x["main_track"],
            f"agent-{v}": lambda x, s: x["venue"] == v and x["main_track"] and s["agent"] == "yes",
            f"llm-agent-{v}": lambda x, s: x["venue"] == v and x["main_track"] and s["agent"] == "yes" and s["llm_basis"] == "yes",
            f"other-agent-{v}": lambda x, s: x["venue"] == v and x["main_track"] and s["agent"] == "yes" and s["llm_basis"] != "yes"}


POPS_EXT = {**venue_pops("iclr-2025"), **venue_pops("aamas-2025")}
POPS_EA = venue_pops("aamas-2025-ea")


def strata_of(ids, f, items, screen, claude):
    """0/1 outcomes of measure f in a slice, grouped by stratum."""
    st = {}
    for i in ids:
        st.setdefault(stratum(items[i], screen[i]), []).append(int(f(claude[i])))
    return st


def negatives(P, confirmed, items, screen):
    """Counts per stratum of the population's papers outside the confirmed set, for agent and other papers."""
    neg_a, neg_o = {}, {}
    for i in P:
        if i not in confirmed:
            d_ = neg_a if screen[i]["agent"] == "yes" else neg_o
            k_ = stratum(items[i], screen[i])
            d_[k_] = d_.get(k_, 0) + 1
    return neg_a, neg_o


def expected(negs, st, rate=stratum_rate):
    return sum(rate(st, k) * n for k, n in negs.items())


def slices(part):
    """Confirmed set (parts a, b, e) and the random slices of screen-negatives (c: agent papers, d: other papers)."""
    return ({i for i, p in part.items() if p in "abenz"}, [i for i, p in part.items() if p == "c"], [i for i, p in part.items() if p == "d"])


def table(measures=MEASURES, pops=POPS, data=None):
    items, screen, part, claude = data or load()
    assert all(i in claude for i in part), "stage-2 coding incomplete"
    # misses are estimated per stratum (year group x LLM basis) of screen-negative papers, from the random slices c and d
    confirmed, slice_c, slice_d = slices(part)
    out = {}
    for name, keep in pops.items():
        P = [i for i, x in items.items() if keep(x, screen[i])]
        pos = [i for i in P if i in confirmed]
        neg_a, neg_o = negatives(P, confirmed, items, screen)
        out[name] = {"n": len(P), "screened": len(pos), "neg_agent": sum(neg_a.values()), "neg_other": sum(neg_o.values())}
        if not P:  # an empty population (possible in a small extension venue) has no share
            continue
        if all(i in claude for i in P):  # the confirmer coded the whole population (EC): a direct count, no estimated misses
            for m, f in measures.items():
                k = sum(f(claude[i]) for i in P)
                out[name][m] = {"confirmed": k, "share": k / len(P), "lo": k / len(P), "hi": k / len(P)}
            out[name]["census"] = True
            continue
        for m, f in measures.items():
            k = sum(f(claude[i]) for i in pos)
            st_c, st_d = strata_of(slice_c, f, items, screen, claude), strata_of(slice_d, f, items, screen, claude)
            est = (k + expected(neg_a, st_c) + expected(neg_o, st_d)) / len(P)
            la, ha = miss_bounds(neg_a, st_c)
            lo_, ho = miss_bounds(neg_o, st_d)
            out[name][m] = {"confirmed": k, "share": est, "lo": (k + la + lo_) / len(P), "hi": (k + ha + ho) / len(P)}
    out["miss_rates"] = {m: {"agent": {str(k): (sum(v), len(v)) for k, v in strata_of(slice_c, f, items, screen, claude).items()}, "other": {str(k): (sum(v), len(v)) for k, v in strata_of(slice_d, f, items, screen, claude).items()}} for m, f in measures.items()}
    out["precision"] = {p: {"screened": sum(1 for i, q in part.items() if q == p), "confirmed_several": sum(measures.get("several", MEASURES["several"])(claude[i]) for i, q in part.items() if q == p)} for p in sorted(set("abe") | set(part.values()) & set("nz"))}
    return out


def estimates():
    t = table()
    if ext_ready():
        t["ext"] = table(MEASURES, POPS_EXT, load_ext())
    if ext_ready("ext-ea"):  # sensitivity population, outside the headline
        t["ext-ea"] = table(MEASURES, POPS_EA, load_ext("ext-ea"))
    for tag, pops in (("full", POPS), ("ext", POPS_EXT), ("ext-ea", POPS_EA)):  # new keys; every key above is unchanged
        if policy_ready(tag):
            t["policy" if tag == "full" else f"policy-{tag}"] = table({**POLICY_MEASURES, **POLICY_SHARES}, pops, load_policy(tag))
    for tag, pops in (("full", POPS), ("ext", POPS_EXT), ("ext-ea", POPS_EA)):  # v2 keys, likewise new
        if policy2_ready(tag):
            t["policy2" if tag == "full" else f"policy2-{tag}"] = table(POLICY2_MEASURES, pops, load_policy2(tag))
    return t


if __name__ == "__main__":
    t = estimates()
    json.dump(t, open("data/estimates-twostage.json", "w"), indent=1)
    for k, v in [*t.get("ext", {}).items(), *t.get("ext-ea", {}).items()]:
        if isinstance(v, dict) and v.get("n"):
            print(k, v["n"], "screened", v["screened"], "  ".join(f"{m} {v[m]['confirmed']} {100 * v[m]['share']:.1f} [{100 * v[m]['lo']:.1f}, {100 * v[m]['hi']:.1f}]" for m in MEASURES))
    for k, v in t.items():
        if "n" in v:
            print(k, v["n"], "screened", v["screened"], "  ".join(f"{m} {v[m]['confirmed']} {100 * v[m]['share']:.1f} [{100 * v[m]['lo']:.1f}, {100 * v[m]['hi']:.1f}]" for m in MEASURES))
    print(t["miss_rates"], t["precision"])
