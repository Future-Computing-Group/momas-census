"""Pilot agreement of the policy codebook (Supplementary Note 1): Krippendorff's alpha (nominal, two coders) and raw
agreement per field, per cluster (K1/K1m, K10, K9), on the derived cell (§2), coders' conformance with the adjudicator's
rule-implied codes, and agreement on the slice papers. Refuses to run if implied.jsonl does not match the sha
recorded in pilot-ids.json (the implied codes were fixed before any coder output existed).

Usage: python3 pilot_agreement.py [--round 2|3]
  round 2 (default): data/coded/pilot2-{A,B}-*.jsonl over the 177 pilot papers.
  round 3 (codebook v2.2, rules R5 to R10): data/coded/pilot3-{A,B}-*.jsonl over the fresh 40 (with
  implied-3.jsonl), the re-tested pilot papers (with implied-2b.jsonl), and the composite pilot (round-2 codes
  with the round-3 codes substituted for the re-tested papers), plus each coder against data/pilot/adjudicated-v2.2.jsonl
  on the re-tested papers. Round 3 adds RULE_BREAKING (compared only over papers whose codes carry it), the v2.2 cell with
  several-rule-breaking, and the R6 count (rational_prescribed)."""
import argparse
import collections
import glob
import hashlib
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
IDS = os.path.join(HERE, "data/pilot/pilot-ids.json")
IMPLIED = os.path.join(HERE, "data/pilot/implied.jsonl")
IDS3 = os.path.join(HERE, "data/pilot/pilot3-ids.json")
IMPLIED3 = os.path.join(HERE, "data/pilot/implied-3.jsonl")
IMPLIED2B = os.path.join(HERE, "data/pilot/implied-2b.jsonl")
ADJUDICATED = os.path.join(HERE, "data/pilot/adjudicated-v2.jsonl")  # v2 adjudication, kept as it was
ADJUDICATED22 = os.path.join(HERE, "data/pilot/adjudicated-v2.2.jsonl")  # with rules R5 to R10 applied
FIELDS = ["policy_setters", "principals", "behaviour", "interacting", "outside_attacker", "partners_from_others"]
FIELDS3 = FIELDS + ["rule_breaking"]  # codebook v2.2
CLUSTERS = {"K1/K1m": {"K1", "K1m"}, "K10": {"K10"}, "K9": {"K9"}}


def alpha(a, b):
    """Krippendorff's alpha, nominal, two coders, no missing values. nan when only one value occurs."""
    assert len(a) == len(b)
    o = collections.Counter()
    for x, y in zip(a, b):
        o[x, y] += 1
        o[y, x] += 1
    n_c = collections.Counter()
    for (x, _), v in o.items():
        n_c[x] += v
    n = sum(n_c.values())
    expected = sum(n_c[c] * n_c[k] for c in n_c for k in n_c if c != k)
    if expected == 0:
        return math.nan
    observed = sum(v for (x, y), v in o.items() if x != y)
    return 1 - (n - 1) * observed / expected


def raw(a, b):
    return sum(x == y for x, y in zip(a, b)) / len(a) if a else math.nan


# Derived cells, as 01-design.md §2 (POLICY_MEASURES_V2), restricted to the v2 fields.
def no_attacker(r):
    return r.get("outside_attacker") == "no"


def several(r):
    return r.get("policy_setters") == "several" and r.get("principals") == "several" and no_attacker(r)


def cell(r):
    """v2.2 (rule R5): several-rational is the within-the-rules share; a record without rule_breaking (v2) reads as before."""
    if several(r):
        if r.get("rule_breaking") == "yes":
            return "several-rule-breaking"
        return "several-rational" if r.get("behaviour") in ("rational", "mixed") else "several-other"
    if r.get("policy_setters") == "one" and r.get("principals") == "several" and no_attacker(r):
        return {"yes": "simulated", "no": "single-learner"}.get(r.get("interacting"), "rest")
    if r.get("outside_attacker") == "yes" and r.get("principals") == "several" and r.get("policy_setters") in ("one", "several"):
        return "excluded-attacker"
    return "rest"


def rational(r):
    return "rational-or-mixed" if r.get("behaviour") in ("rational", "mixed") else "other"


def rational_prescribed(r):
    """Rule R6 SI count: players modelled as rational who all run the paper's prescribed algorithm."""
    return "yes" if r.get("policy_setters") == "one" and r.get("behaviour") == "rational" and r.get("interacting") == "yes" else "no"


def compare(ids, A, B, fields=FIELDS, derived=(("behaviour_binary", rational), ("cell", cell))):
    """alpha, raw agreement, n and minority-value count for every field, the binary behaviour and the cell over ids. A field
    is compared over the ids whose code by either coder carries it (round-2 codes predate rule_breaking)."""
    out = {}
    for name, f in [(k, (lambda k: lambda r: r.get(k))(k)) for k in fields] + list(derived):
        sub = [i for i in ids if name not in fields or name in A[i] or name in B[i]]
        a, b = [f(A[i]) for i in sub], [f(B[i]) for i in sub]
        counts = collections.Counter(a + b)
        out[name] = {"alpha": alpha(a, b), "raw": raw(a, b), "n": len(sub),
                     "minority": min(counts.values()) // 2 if len(counts) > 1 else 0, "counts": dict(counts)}
    return out


def conformance(implied, coder):
    """Share of rule-implied codes the coder matches, overall and per rule. A code "one|na" accepts either value."""
    groups = collections.defaultdict(lambda: {"n": 0, "hits": 0, "misses": []})
    for r in implied:
        ok = coder[r["id"]].get(r["field"]) in r["code"].split("|")
        for g in ("all", r.get("rule", "?")):
            groups[g]["n"] += 1
            groups[g]["hits"] += ok
            if not ok:
                groups[g]["misses"].append(r["id"])
    return {k: {**v, "share": v["hits"] / v["n"]} for k, v in groups.items()}


def report(pilot, implied, A, B):
    disputed = {d["id"]: d for d in pilot["disputed"]}
    ids = list(disputed) + pilot["random"]
    missing = [i for i in ids if i not in A or i not in B]
    if missing:
        raise SystemExit(f"coder output missing {len(missing)} pilot ids, e.g. {missing[:5]}")
    rep = {"overall": compare(ids, A, B), "clusters": {}}
    for name, tags in CLUSTERS.items():
        sub = [i for i, d in disputed.items() if tags & set(d["clusters"])]
        rep["clusters"][name] = compare(sub, A, B)
    k10 = [i for i, d in disputed.items() if "K10" in d["clusters"]]
    rep["k10_interacting_no_both"] = sum(A[i].get("interacting") == B[i].get("interacting") == "no" for i in k10), len(k10)
    k9 = [i for i, d in disputed.items() if "K9" in d["clusters"]]
    rep["k9_outside_attacker_agreed"] = sum(A[i].get("outside_attacker") == B[i].get("outside_attacker") for i in k9), len(k9)
    rep["conformance"] = {"A": conformance(implied, A), "B": conformance(implied, B)}
    slices = [i for i, d in disputed.items() if d.get("part") in ("c", "d")]
    rep["slice"] = {i: {"agree_all": all(A[i].get(f) == B[i].get(f) for f in FIELDS), "cell_A": cell(A[i]), "cell_B": cell(B[i]),
                        "fields_disagreeing": [f for f in FIELDS if A[i].get(f) != B[i].get(f)]} for i in slices}
    return rep


def report3(p3, pilot, implied, implied3, A2, B2, A3, B3, adj=None, implied2b=()):
    """Round 3: agreement on the fresh papers, on the re-tested papers, and on the composite pilot (round-2 codes with the
    round-3 codes in place for the re-tested papers); conformance on each (implied2b: the rules R5 to R10 codes for pilot
    papers, on the re-tested papers and on the composite pilot); optionally each coder against the adjudication."""
    retest, fresh = [r["id"] for r in p3["retest"]], p3["fresh"]
    missing = [i for i in retest + fresh if i not in A3 or i not in B3]
    if missing:
        raise SystemExit(f"round-3 coder output missing {len(missing)} ids, e.g. {missing[:5]}")
    ids = [d["id"] for d in pilot["disputed"]] + pilot["random"]
    CA, CB = {**A2, **{i: A3[i] for i in retest}}, {**B2, **{i: B3[i] for i in retest}}
    derived = (("behaviour_binary", rational), ("cell", cell), ("rational_prescribed", rational_prescribed))
    cmp = lambda ids_, X, Y: compare(ids_, X, Y, FIELDS3, derived)
    rep = {"fresh": cmp(fresh, A3, B3), "fresh_conformance": {"A": conformance(implied3, A3), "B": conformance(implied3, B3)},
           "retest": cmp(retest, A3, B3), "pilot": cmp(ids, CA, CB),
           "pilot_conformance": {"A": conformance(implied, CA), "B": conformance(implied, CB)}}
    if implied2b:
        on_retest = [r for r in implied2b if r["id"] in set(retest)]
        on_pilot = [r for r in implied2b if r["id"] in CA and r["id"] in CB]
        rep["retest_conformance_2b"] = {"A": conformance(on_retest, A3), "B": conformance(on_retest, B3)}
        rep["pilot_conformance_2b"] = {"A": conformance(on_pilot, CA), "B": conformance(on_pilot, CB)}
    for part in ("fresh", "retest", "pilot"):
        rep[part]["n"] = len({"fresh": fresh, "retest": retest, "pilot": ids}[part])
    if adj:
        rep["retest_vs_adjudicated"] = {c: {**{f: raw([X[i].get(f) for i in retest], [adj[i].get(f) for i in retest]) for f in FIELDS3},
                                            "cell": raw([cell(X[i]) for i in retest], [cell(adj[i]) for i in retest])}
                                        for c, X in (("A", A3), ("B", B3))}
    return rep


def check_sha(pilot, path=IMPLIED, key="implied_sha256"):
    sha = hashlib.sha256(open(path, "rb").read()).hexdigest()
    if sha != pilot.get(key):
        raise SystemExit(f"{os.path.basename(path)} sha {sha} differs from the ids file's {key} {pilot.get(key)}: refusing to run")


def load_coder(pattern):
    return {r["id"]: r for f in sorted(glob.glob(pattern)) for r in map(json.loads, filter(str.strip, open(f)))}


def load_jsonl(path):
    return [json.loads(l) for l in open(path) if l.strip()]


def fragments(pilot, p3, rep):
    """{file name: LaTeX fragment} for the pilot paragraph of Supplementary Note 1: the pilot's sizes and, on the fresh and on the
    re-tested papers of round 3, the range of alpha over the coded fields (undefined alphas left out) and the cell's raw agreement."""
    def agree(part):
        a = [rep[part][f]["alpha"] for f in FIELDS3 if not math.isnan(rep[part][f]["alpha"])]
        return f"$\\alpha$ from {min(a):.2f} to {max(a):.2f}; cell agreement {100 * rep[part]['cell']['raw']:.1f}\\%"
    n_d, n_r, n_t, n_f = len(pilot["disputed"]), len(pilot["random"]), len(p3["retest"]), len(p3["fresh"])
    return {"pilot-n.tex": str(n_d + n_r), "pilot-disputed.tex": str(n_d), "pilot-random.tex": str(n_r), "pilot-retest-n.tex": str(n_t),
            "pilot-fresh-n.tex": str(n_f), "pilot-round3-n.tex": str(n_t + n_f), "pilot-fresh.tex": agree("fresh"), "pilot-retest.tex": agree("retest")}


def round2():
    pilot = json.load(open(IDS))
    check_sha(pilot)
    A = load_coder(os.path.join(HERE, "data/coded/pilot2-A-*.jsonl"))
    B = load_coder(os.path.join(HERE, "data/coded/pilot2-B-*.jsonl"))
    return pilot, load_jsonl(IMPLIED), A, B


def round3():
    """(pilot, p3, round-3 report) after the sha checks."""
    pilot, implied, A, B = round2()
    p3 = json.load(open(IDS3))
    check_sha(p3)
    check_sha(p3, IMPLIED3, "implied_3_sha256")
    check_sha(p3, IMPLIED2B, "implied_2b_sha256")
    sha = hashlib.sha256(open(os.path.join(HERE, p3["codebook"]), "rb").read()).hexdigest()
    if sha != p3["codebook_sha256"]:
        raise SystemExit(f"{p3['codebook']} sha {sha} differs from pilot3-ids.json: refusing to run")
    adj = {r["id"]: r for r in load_jsonl(ADJUDICATED22)}
    rep = report3(p3, pilot, implied, load_jsonl(IMPLIED3), A, B, load_coder(os.path.join(HERE, "data/coded/pilot3-A-*.jsonl")),
                  load_coder(os.path.join(HERE, "data/coded/pilot3-B-*.jsonl")), adj, load_jsonl(IMPLIED2B))
    return pilot, p3, rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", type=int, choices=(2, 3), default=2)
    args = ap.parse_args()
    rep = report(*round2()) if args.round == 2 else round3()[2]
    json.dump(rep, sys.stdout, indent=1, default=str)
    print()


if __name__ == "__main__":
    main()
