"""Layer extension: relative-link matrices, H-layers, per-field question, leave-one-out for R1-R4, coverage.
Reads results_m1.json (from `analyse.py m1`) and works.json; network calls only via cached oa.get. Writes results_layers.json."""
import collections, itertools, json, os, statistics as st
import analyse as A
from oa import get, sid, CALLS

L1, L2 = [f"R{i}" for i in range(1, 5)], [f"C{i}" for i in range(1, 8)]
ORDER, AI = L1 + L2, L2[:5]
REC = {}


def rel(ref):
    return {i: {j: ref[i][j] / ref[i][i] for j in ORDER} for i in ORDER}


def s(ref, a, b):
    return max(ref[a][b] / ref[a][a], ref[b][a] / ref[b][b])


def layers(ref, l1=L1, l2=L2):
    between = [s(ref, a, b) for a in l1 for b in l2]
    within = [s(ref, a, b) for grp in (l1, l2) for a, b in itertools.combinations(grp, 2)]
    return {"n_between": len(between), "n_within": len(within), "median_between": st.median(between),
            "median_within": st.median(within), "ratio": st.median(between) / st.median(within)}


def talks(ref):
    return {r: {"reach": {c: s(ref, r, c) for c in AI}, "n_ge_1pct": sum(s(ref, r, c) >= 0.01 for c in AI)} for r in L1}


def show(name, mat, fmt="{:7.3f}"):
    print(f"\n{name}\n     " + "".join(f"{k:>7}" for k in ORDER))
    for i in ORDER:
        print(f"{i:>4} " + "".join(fmt.format(mat[i][j]) if i != j or "rel" not in name else "      -" for j in ORDER))


R = json.load(open(os.path.join(A.D, "results_m1.json")))["M1"]
for k in ("2", "1"):
    ref = R[k]["ref"]
    show(f"relative link (directed) ref[i][j]/ref[i][i], >= {k} seeds", rel(ref))
    sym = {i: {j: (s(ref, i, j) if i != j else 1.0) for j in ORDER} for i in ORDER}
    show(f"relative link s(i,j) larger direction, >= {k} seeds (rel)", sym)
    lay, lay_c6 = layers(ref), layers(ref, L1 + ["C6"], [c for c in L2 if c != "C6"])
    t = talks(ref)
    print(f"\n>= {k} seeds: H-layers {lay}\n   sensitivity, C6 moved to layer 1: {lay_c6}")
    for r, v in t.items():
        print(f"   {r} talks to AI (C1-C5) at >= 1%: {v['n_ge_1pct']} of 5;", {c: round(x, 4) for c, x in v["reach"].items()})
    print("   H-scatter", R[k]["summary"], "nonseed", R[k]["summary_nonseed"])
    REC[k] = {"rel": rel(ref), "sym": sym, "layers": lay, "layers_c6_in_l1": lay_c6, "talks": t,
              "overlap": R[k]["overlap"], "sizes": R[k]["sizes"]}
    if k == "2":
        print("   layer-1 pairs:", {f"{a}-{b}": round(s(ref, a, b), 4) for a, b in itertools.combinations(L1, 2)})
        print("   strongest between-layer pairs:", sorted(((round(s(ref, a, b), 4), a, b) for a in L1 for b in L2), reverse=True)[:8])

# leave one seed out, new literatures only (two-seed corpora)
by = A.seedsets(set(ORDER))
loo = []
for sd in A.SEEDS:
    if sd["cluster"] in L1:
        corp, _ = A.corpora(A.W["citers"], by, 2, drop=sd["openalex"])
        ref = A.m1(corp, by)[0]
        loo.append({"label": sd["label"], "scatter_ratio": A.summary(ref)["ratio"], "layers_ratio": layers(ref)["ratio"],
                    "talks": {r: v["n_ge_1pct"] for r, v in talks(ref).items()}, "size": len(corp[sd["cluster"]])})
for key in ("scatter_ratio", "layers_ratio"):
    v = [x[key] for x in loo]
    print(f"\nLOO (R seeds) {key}: {min(v):.4f} to {max(v):.4f}")
for r in L1:
    print("LOO", r, "talks-to-AI count range", min(x["talks"][r] for x in loo), max(x["talks"][r] for x in loo))
REC["loo"] = loo

# coverage: corpus works with non-empty referenced_works; seeds; dominant-subfield share of works with references
corp, _ = A.corpora(A.W["citers"], by, 2)
seed_ids = [sd["openalex"] for sd in A.SEEDS if sd["cluster"] in ORDER]
topic = {}
for i in range(0, len(seed_ids), 50):
    for w in get("works", filter="openalex:" + "|".join(seed_ids[i:i + 50]), select="id,primary_topic", **{"per-page": 200})["results"]:
        pt = w.get("primary_topic") or {}
        topic[sid(w["id"])] = ((pt.get("subfield") or {}).get("id"), (pt.get("subfield") or {}).get("display_name"))
cov = {}
for c in ORDER:
    ws = corp[c].values()
    sub = collections.Counter(topic.get(x) for x in by[c] if topic.get(x) and topic[x][0])
    (sf, sfname), _ = sub.most_common(1)[0]
    sf = sid(sf)
    f = f"primary_topic.subfield.id:{sf},publication_year:2015-2026"
    tot = get("works", filter=f, select="id", **{"per-page": 1})["meta"]["count"]
    withref = get("works", filter=f + ",referenced_works_count:>0", select="id", **{"per-page": 1})["meta"]["count"]
    cov[c] = {"corpus_nonempty": sum(bool(w["refs"]) for w in ws) / len(ws),
              "seeds_nonempty": sum(bool(A.W["seeds"][x]["refs"]) for x in by[c] if x in A.W["seeds"]) / len(by[c]),
              "subfield": sfname, "subfield_id": sf, "subfield_share_with_refs": withref / tot, "subfield_n": tot}
    print("coverage", c, {k: round(v, 3) if isinstance(v, float) else v for k, v in cov[c].items()})
REC["coverage"] = cov

# fairness baseline, same relative-link medians (one-seed sub-corpora as in the first run; unchanged)
F = json.load(open(os.path.join(A.D, "results.json")))["fairness"]
for p, v in F.items():
    pr = [s(v["ref"], a, b) for a, b in itertools.combinations(v["ref"], 2)]
    print(f"fairness {p}: relative links {[round(x, 3) for x in pr]}, median {st.median(pr):.3f}")
    REC[f"fairness_{p}"] = pr
json.dump(REC, open(os.path.join(A.D, "results_layers.json"), "w"), indent=1)
print("calls", CALLS)
