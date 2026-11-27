"""Re-analyses on the v2 policy pass (Supplementary Note 1; codebook-policy-v2.2.md); no new coding. Same estimator as
twostage.py, with POLICY2_MEASURES.

- setters_by_parties: every paper with a primary parties code (codebook-parties.md), by its PARTIES code and the confirming
  coder's POLICY_SETTERS code, with the number in the policy cell. It shows how the papers that the v3.4 OWNERS cue list placed
  among several owners (formal-model players, bidders, abstract agents) sit under the question of who sets each policy; it
  replaces the keyword split of the deciding phrase that the v3.4 analysis used.
- partners: the two literatures built for partners that others train, by coded fields: DATA partitioned (codebook v3.4,
  "e.g. federated or cross-silo") and PARTNERS_FROM_OTHERS yes (codebook-policy-v2.2.md). For each, the 2025 main-track papers the
  first stage codes in it, the papers the confirming coder coded in it and where it placed them, and the cell share with the
  literature left out of the cell (estimated: the field is read from the confirming coder's code on every confirmed and slice paper),
  and the estimated share of each population with PARTNERS_FROM_OTHERS yes (table key partners-from-others).
Writes data/estimates-reanalyses-policy2.json (or argv[1]); data/estimates-reanalyses.json keeps the v3.4 analysis and
data/estimates-reanalyses-policy.json the v1 policy pass. setters_by_parties is written only once data/estimates-round2-policy2.json
exists (every v2 cell paper has a parties code).
"""
import json
import os
import sys

from round2 import PARTIES, POLICY2_PARTIES, POLICY_POPS, PRIMARY_PARTIES, load_parties
from twostage import POLICY2_MEASURES, POPS, load_policy2, table

GROUPS = {"partitioned-data": lambda r: r.get("data") == "partitioned", "partners-from-others": lambda r: r.get("partners_from_others") == "yes"}


def setters_by_parties(parties, claude):
    sev = POLICY2_MEASURES["several"]
    out = {c: {"n": 0, "one": 0, "several": 0, "na": 0, "cell": 0} for c in PARTIES}
    for i, c in parties.items():
        if i in claude:
            r = claude[i]
            out[c]["n"] += 1
            out[c][r["policy_setters"]] += 1
            out[c]["cell"] += int(sev(r))
    return out


def partners(data, pops=POPS):
    items, screen, part, claude = data
    sev, sim = POLICY2_MEASURES["several"], POLICY2_MEASURES["simulated"]
    t = table({"several": sev, **{f"without-{g}": (lambda r, f=f: sev(r) and not f(r)) for g, f in GROUPS.items()},
               "partners-from-others": GROUPS["partners-from-others"]}, pops, data)  # the last: its share of each population
    P25 = [i for i, x in items.items() if POPS["all-2025"](x, screen[i])]
    groups = {}
    for g, f in GROUPS.items():
        c = [i for i in P25 if i in part and f(claude[i])]
        groups[g] = {"screen_2025": sum(f(screen[i]) for i in P25), "confirmer_coded": len(c), "cell": sum(sev(claude[i]) for i in c), "simulated": sum(sim(claude[i]) for i in c)}
    return {"groups": groups, "table": {k: v for k, v in t.items() if k in pops}}


if __name__ == "__main__":
    data = load_policy2("full")
    res = {"partners": partners(data)}
    if os.path.exists(POLICY2_PARTIES):
        claude = {}
        for tag in POLICY_POPS:
            _, _, part, c = data if tag == "full" else load_policy2(tag)
            claude.update({i: c[i] for i in part})
        res["setters_by_parties"] = setters_by_parties(load_parties(PRIMARY_PARTIES), claude)
    json.dump(res, open(sys.argv[1] if len(sys.argv) > 1 else "data/estimates-reanalyses-policy2.json", "w"), indent=1)
    for c, v in res.get("setters_by_parties", {}).items():
        print("parties", c, v)
    print(json.dumps(res["partners"]["groups"]))
    for k, v in res["partners"]["table"].items():
        print(k, v["n"], "  ".join(f"{m} {100 * v[m]['share']:.2f} [{100 * v[m]['lo']:.2f}, {100 * v[m]['hi']:.2f}]" for m in ("several", *(f"without-{g}" for g in GROUPS))))
