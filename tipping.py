"""Tipping-point analysis of the census claims (Supplementary Note 1), on the v2 policy pass (codebook-policy-v2.2.md,
POLICY2_MEASURES): for each claim, the smallest systematic coder error that would overturn it, against the error rates actually
observed between coders. Writes data/estimates-tipping-policy2.json (data/estimates-tipping.json keeps the v3.4 analysis and
data/estimates-tipping-policy.json the v1 policy pass); si_tables.py writes si/tip-*.tex. The parties claim (section 2) is
computed only once data/estimates-round2-policy2.json exists, that is once every v2 cell paper has a parties code.

Observed errors are disagreements between the two stages, estimated over the whole population with the two-stage estimator (the
confirmer coded every v2 screen positive, which includes every paper of a first-stage cell, and random slices of the rest, so every
first-stage positive is a direct count), with the conservative upper bound of twostage.py (Wilson for direct counts); the parties
second coders; and, reported but not used, the author's 20- and 13-paper checks (v3.4 FOCUS and OWNERS; the author's policy
check is not yet coded).
"""
import json
import os
import random
import sys

from analyze import wilson
from census import kappa
from round2 import POLICY2_PARTIES, PRIMARY_PARTIES, authors_by_title, interval, load_parties, sector_pops
from twostage import POLICY2_MEASURES as MEASURES, POPS, claude_owners, load, load_policy2, table

lift_rate = lambda s, t: (t - s) / (1 - s)  # miss rate among papers coded negative that lifts share s to t
drop_rate = lambda s, t: (s - t) / s  # false-positive rate among papers coded positive that lowers share s to t
flip_to_ratio = lambda S, V, r=1.0: (S - r * V) / (1 + r)  # papers moved from S to V so that (S - x) / (V + x) = r
verdict = lambda need, seen_hi: "robust" if need > seen_hi else "sensitive"


def null_seen(d):
    """A null row's observed differential (point, bound), both from the direction whose interval sets the bound d["observed"]."""
    p, lo, hi = max(d["observed_diff"].values(), key=lambda v: max(abs(v[1]), abs(v[2])))
    return p, max(abs(lo), abs(hi))


def ec_band(ec):
    """EC is counted in full, so its bounds are degenerate. The band the observed disagreement allows: the confirmer's share with its
    false positives at the upper bound of the observed rate (confirmer in the cell, first stage not) removed, and with its misses at
    the upper bound of the observed rate (first stage in the cell, confirmer not) added. ec: the 'ec' entry of estimates-tipping.json."""
    s, r = ec["share"], ec["rates"]
    return s * (1 - r["fp_confirmer"][2]), s + (1 - s) * r["miss_confirmer"][2]


def diff_bound(a, b):
    """Newcombe interval for a - b from (point, lo, hi) of each."""
    d = a[0] - b[0]
    return d - ((a[0] - a[1]) ** 2 + (b[2] - b[0]) ** 2) ** 0.5, d + ((a[2] - a[0]) ** 2 + (b[0] - b[1]) ** 2) ** 0.5


def kappa_interval(a, b, rng, reps=2000):
    n = len(a)
    ks = []
    for _ in range(reps):
        ix = [rng.randrange(n) for _ in range(n)]
        ks.append(kappa([a[i] for i in ix], [b[i] for i in ix]))
    return interval([k for k in ks if k is not None])  # a draw where both coders give one value has no kappa


# the first stage's cells, as POLICY2_MEASURES on the screen's v2 fields and its v3.4 FOCUS; a paper whose v2 screen failed to
# parse has no v2 field and is in no screen cell (it was confirmed in full)
_s_sev = lambda s: s.get("policy_setters") == "several" and s.get("principals") == "several" and s.get("outside_attacker") == "no"
SCREEN = {
    "several": _s_sev,
    "interaction": lambda s: _s_sev(s) and s.get("focus_derived") == "interaction",
    "simulated": lambda s: s.get("policy_setters") == "one" and s.get("principals") == "several" and s.get("interacting") == "yes" and s.get("outside_attacker") == "no",
}


def disagreement_measures(screen):
    """Per measure: the confirmer positive where the first stage is negative (cp_sn) and the reverse (cn_sp); and the POLICY_SETTERS
    boundary flips between the two cells in both directions: confirmer simulated where the first stage is in the several cell
    (flip), and confirmer several where the first stage is simulated (flip_back)."""
    out = {}
    for m in SCREEN:
        out[m] = MEASURES[m]
        out[f"{m}:cp_sn"] = lambda r, m=m: MEASURES[m](r) and not SCREEN[m](screen[r["id"]])
        out[f"{m}:cn_sp"] = lambda r, m=m: not MEASURES[m](r) and SCREEN[m](screen[r["id"]])
    out["flip"] = lambda r: MEASURES["simulated"](r) and SCREEN["several"](screen[r["id"]])
    out["flip_back"] = lambda r: MEASURES["several"](r) and SCREEN["simulated"](screen[r["id"]])
    return out


def ratio_observed(k_conf, n_conf, k_screen, n_screen):
    """Observed flip rate for a ratio row, the larger (by upper bound, as worst()) of the two directions, both direct counts:
    of the confirmer's simulated papers, those the first stage put in the several cell; of the first stage's simulated papers,
    those the confirmer put in the several cell."""
    c, s = (k_conf / n_conf, *wilson(k_conf, n_conf)), (k_screen / n_screen, *wilson(k_screen, n_screen))
    return {"confirmer": c, "screen": s, "direction": "screen" if s[2] > c[2] else "confirmer", "observed": max(c, s, key=lambda x: x[2])}


def rates(t, pop, n_sp, m):
    """Disagreement rates (point, lo, hi) for measure m in one population: misses (positives among one coder's negatives, either
    coder) and false positives (negatives among one coder's positives, either coder)."""
    v, N = t[pop], t[pop]["n"]
    cpos = v[m]["share"] * N

    def r(key, den):
        x = v[f"{m}:{key}"]
        # a direct count: the whole population was confirmed (EC), or the first stage's positive, which the policy confirmer coded
        # for every cell (cn_sp outside the confirmed set is impossible; slices would only add a spurious upper bound)
        if v.get("census") or key == "cn_sp":
            x = {"share": x["confirmed"] / N}
            k = round(x["share"] * N)
            lo, hi = wilson(k, round(den))
            return (k / den, lo, hi)
        return (x["share"] * N / den, x["lo"] * N / den, x["hi"] * N / den)
    return {"miss_confirmer": r("cn_sp", N - cpos), "miss_screen": r("cp_sn", N - n_sp), "fp_confirmer": r("cp_sn", cpos), "fp_screen": r("cn_sp", n_sp)}


worst = lambda rs, keys: max((rs[k] for k in keys), key=lambda x: x[2])


def parties_claim(out, t, R, data, n_sp, s):
    """2. AI agents of separate owners: miscoded parties within the cell, or hidden settings outside it."""
    items, screen, part, claude = data
    parties = load_parties(PRIMARY_PARTIES)
    pm = {"ai": lambda r: MEASURES["several"](r) and parties[r["id"]] == "ai-agents",
          "ai:cp_sn": lambda r: MEASURES["several"](r) and parties[r["id"]] == "ai-agents" and not SCREEN["several"](screen[r["id"]])}
    tp = table(pm, {"all-2025": POPS["all-2025"]}, data)
    a_, b_ = parties, load_parties("data/coded/r2-parties-*dup.jsonl")  # every second parties coder, against the primary codes
    ids = sorted(b_)
    dis = []
    for x, y in ((a_, b_), (b_, a_)):
        neg = [i for i in ids if x[i] != "ai-agents"]
        k = sum(y[i] == "ai-agents" for i in neg)
        dis.append((k / len(neg), *wilson(k, len(neg)), k, len(neg)))
    sa, sc = tp["all-2025"]["ai"]["share"], s("all-2025", "several")
    N = t["all-2025"]["n"]
    # hidden outside the cell: AI-agents settings the confirmer found among the first stage's negatives, or the first stage's cell
    # papers the confirmer rejected (whose parties are uncoded, so all are counted as possible AI-agents settings)
    x_ = tp["all-2025"]["ai:cp_sn"]
    n_neg = N - n_sp("all-2025", "several")
    ai_seen = (x_["share"] * N / n_neg, x_["lo"] * N / n_neg, x_["hi"] * N / n_neg)
    out["parties"] = {"share": sa, "cell": sc, "n": N, "observed_within": max(dis, key=lambda z: z[2]), "observed_ai_screen": ai_seen,
                      "observed_outside": max((ai_seen, R[("all-2025", "several")]["miss_confirmer"]), key=lambda z: z[2]),
                      "need_within": {str(g): (g - sa) / (sc - sa) for g in (0.01, 0.02)}, "need_outside": {str(g): (g - sa) / (1 - sc) for g in (0.01, 0.02)},
                      "papers": {str(g): (g - sa) * N for g in (0.01, 0.02)}, "within_n": (sc - sa) * N, "outside_n": (1 - sc) * N}


def main():
    data = load_policy2("full")
    items, screen, part, claude = data
    dm = disagreement_measures(screen)
    t = table(dm, POPS, data)
    n_sp = lambda pop, m, pops=POPS: sum(SCREEN[m](screen[i]) for i, x in items.items() if pops[pop](x, screen[i]))
    R = {(p, m): rates(t, p, n_sp(p, m), m) for p in ("all-2020", "all-2025", "agent-2025", "llm-agent-2025", "other-agent-2025", "ec-2025") for m in SCREEN}
    MISS = ("miss_confirmer", "miss_screen")
    out = {}
    s = lambda p, m: t[p][m]["share"]

    # 1. level and known-groups contrast
    obs = worst(R[("all-2025", "several")], MISS)
    out["level"] = {"share": s("all-2025", "several"), "n": t["all-2025"]["n"], "observed": obs, "rates": R[("all-2025", "several")],
                    "need": {str(g): lift_rate(s("all-2025", "several"), g) for g in (0.10, 0.20)}}
    obs = worst(R[("ec-2025", "several")], ("fp_confirmer", "fp_screen"))
    out["ec"] = {"share": s("ec-2025", "several"), "n": t["ec-2025"]["n"], "observed": obs, "rates": R[("ec-2025", "several")], "need": drop_rate(s("ec-2025", "several"), 0.20)}

    N = t["all-2025"]["n"]
    if os.path.exists(POLICY2_PARTIES):
        parties_claim(out, t, R, data, n_sp, s)

    # 3. interaction focus
    obs = worst(R[("all-2025", "interaction")], MISS)
    out["interaction"] = {"share": s("all-2025", "interaction"), "n": N, "observed": obs, "need": lift_rate(s("all-2025", "interaction"), 0.05)}

    # 4 and 6. nulls: differential miss rate between two groups against the observed differential
    def null(t_, a, b, gap_points=(0.01, 0.02)):
        sa_, sb_ = t_[a]["several"]["share"], t_[b]["several"]["share"]
        d = sa_ - sb_
        ra = rates(t_, a, n_sp_(a), "several")
        rb = rates(t_, b, n_sp_(b), "several")
        db = [diff_bound(ra[k], rb[k]) for k in MISS]
        seen = max(max(abs(lo), abs(hi)) for lo, hi in db)
        need = {str(g): min(lift_rate(sa_, sb_ + g), lift_rate(sb_, sa_ + g)) for g in gap_points}
        need["hide-rise" if a == "all-2025" else "gap"] = {str(g): lift_rate(sa_, sa_ + g - d) for g in gap_points}
        return {"diff": d, "a": sa_, "b": sb_, "observed_diff": {k: (ra[k][0] - rb[k][0], *v) for k, v in zip(MISS, db)}, "observed": seen, "need": need,
                "manufacture": lift_rate(sb_, sa_) if d > 0 else lift_rate(sa_, sb_)}
    n_sp_ = lambda p: n_sp(p, "several")
    out["trend"] = null(t, "all-2025", "all-2020")
    sp = sector_pops(authors_by_title())
    sp = {k: v for k, v in sp.items() if k.startswith("all-")}
    ts = table({m: f for m, f in dm.items() if m.startswith("several")}, sp, data)
    n_sp_ = lambda p: sum(SCREEN["several"](screen[i]) for i, x in items.items() if sp[p](x, screen[i]))
    out["sector"] = null(ts, "all-industry", "all-academic")

    # 5. simulate versus assume: POLICY_SETTERS boundary flips from the simulated cell to the several cell, observed in both directions
    out["ratio"] = {}
    for p in ("agent-2025", "llm-agent-2025", "other-agent-2025"):
        N_ = t[p]["n"]
        S, V = s(p, "simulated") * N_, s(p, "several") * N_
        x = flip_to_ratio(S, V)
        k, kb = t[p]["flip"]["confirmed"], t[p]["flip_back"]["confirmed"]  # every first-stage cell paper was confirmed: direct counts
        # the claim is the side of 1 the ratio lies on; it is overturned by flips out of the larger cell, observed in both directions
        if x >= 0:  # simulate more than assume: simulated papers that are several-cell papers
            o = ratio_observed(k, t[p]["simulated"]["confirmed"], kb, n_sp(p, "simulated"))
        else:  # assume more than simulate: several-cell papers that are simulated papers
            o = ratio_observed(kb, t[p]["several"]["confirmed"], k, n_sp(p, "several"))
        out["ratio"][p] = {"S": S, "V": V, "ratio": S / V, "claim": "simulated" if x >= 0 else "several", "flip_papers": abs(x), "flip_share": abs(x) / (S if x >= 0 else V),
                           "flip_seen": k, "flip_back_seen": kb, **o}
    L, O = out["ratio"]["llm-agent-2025"], out["ratio"]["other-agent-2025"]
    x = flip_to_ratio(L["S"], L["V"], O["ratio"])
    out["ratio"]["llm-minus-other"] = {"flip_papers": abs(x), "flip_share": abs(x) / (L["S"] if x >= 0 else L["V"]), "observed": L["observed"]}

    # the author's checks (reported, not used as an estimate): kappa intervals and where the disagreements fall, against the v3.4 codes
    _, screen, _, claude = load()
    fl = json.load(open("data/focus-check-labels.json"))
    fids = [x["id"] for x in json.load(open("data/xfam/focus-check-20.json"))]
    xs = {json.loads(l)["sample_id"]: json.loads(l)["xid"] for l in open("data/xfam/items-full.jsonl") if json.loads(l).get("sample_id")}
    mine = lambda i, k: fl["adjudication"].get(i, {}).get("fields", {}).get(k, {}).get("mine", fl["validation"][i][k])
    rng = random.Random(20261107)
    out["author"] = {}
    for against, ids_, code in (("screen", fids, lambda i, k: str(screen[xs[i]][f"{k}_derived"])),
                                ("confirmer", [i for i in fids if xs[i] in claude], lambda i, k: claude_owners(claude[xs[i]]) if k == "owners" else (claude[xs[i]]["focus"] if claude[xs[i]].get("has_decision_maker") == "yes" else "na"))):
        for k in ("focus", "owners"):
            a, b = [mine(i, k) for i in ids_], [code(i, k) for i in ids_]
            pairs = {}
            for x_, y_ in zip(a, b):
                if x_ != y_:
                    pairs[f"{x_}>{y_}"] = pairs.get(f"{x_}>{y_}", 0) + 1
            out["author"][f"{against}-{k}"] = {"n": len(ids_), "agree": sum(x_ == y_ for x_, y_ in zip(a, b)), "kappa": kappa(a, b), "ci": kappa_interval(a, b, rng), "pairs": pairs}
    return out


def author_policy_shift(mine, claude, in_pop, cells=MEASURES):
    """The author's blind OWNERS code (one / several / na) put in place of the confirmer's POLICY_SETTERS, one paper at a time, on
    the papers where the two differ: whether the simulated-over-several ratio of the population rises, falls or stays. A paper
    outside the population (in_pop) leaves it. A move into the simulated cell or out of the several cell raises it, the reverse
    lowers it; the paper's weight in the estimator (1 if confirmed, its stratum's negatives over the slice if a slice paper) sets
    the size, not the sign. mine, claude: by paper id, over the papers both coded."""
    out = {"n": len(mine), "papers": {}}
    for i, o in mine.items():
        r = claude[i]
        if o == r.get("policy_setters"):
            continue
        r2 = {**r, "policy_setters": o}
        d = (cells["simulated"](r2) - cells["simulated"](r)) - (cells["several"](r2) - cells["several"](r))
        out["papers"][i] = "leave" if i not in in_pop or d == 0 else ("raise" if d > 0 else "lower")
    out["m"] = len(out["papers"])
    out.update({k: sum(v == k for v in out["papers"].values()) for k in ("raise", "lower", "leave")})
    return out


def author_policy(pop="agent-2025"):
    """data/estimates-tipping-author-policy2.json: author_policy_shift on the 20-paper check (data/focus-check-labels.json, the
    blind code as in main()) against the v2 policy confirmer, over the papers it coded in the main census, for the 2025 agent-paper
    ratio."""
    items, screen, part, claude = load_policy2("full")
    fl = json.load(open("data/focus-check-labels.json"))
    fids = [x["id"] for x in json.load(open("data/xfam/focus-check-20.json"))]
    xs = {json.loads(l)["sample_id"]: json.loads(l)["xid"] for l in open("data/xfam/items-full.jsonl") if json.loads(l).get("sample_id")}
    mine = {xs[i]: fl["adjudication"].get(i, {}).get("fields", {}).get("owners", {}).get("mine", fl["validation"][i]["owners"]) for i in fids if xs[i] in part}
    in_pop = {i for i in mine if POPS[pop](items[i], screen[i])}
    return {"population": pop, **author_policy_shift(mine, claude, in_pop)}


if __name__ == "__main__" and sys.argv[1:] == ["author-policy"]:
    res = author_policy()
    json.dump(res, open("data/estimates-tipping-author-policy2.json", "w"), indent=1)
    print(res)
elif __name__ == "__main__":
    res = main()
    json.dump(res, open("data/estimates-tipping-policy2.json", "w"), indent=1)
    print(json.dumps(res, indent=1))
