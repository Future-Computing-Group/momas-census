"""Control (C7) robustness: leave one C7 seed out at a time and report C7's links to C1-C5 (two-seed and one-seed corpora),
and the links of the system-identification seeds alone inside the run-4 data. No network calls. Writes results_c7_loo.json."""
import json, os
import analyse as A

AI = ["C1", "C2", "C3", "C4", "C5"]
s = lambda ref, a, b: max(ref[a][b] / ref[a][a], ref[b][a] / ref[b][b])
by = A.seedsets(set(A.MAIN))
out = {}
for k in (2, 1):
    rows = []
    for sd in [x for x in A.SEEDS if x["cluster"] == "C7"]:
        corp, _ = A.corpora(A.W["citers"], by, k, drop=sd["openalex"])
        ref = A.m1(corp, by)[0]
        rows.append({"left_out": sd["label"], "reach": {c: s(ref, "C7", c) for c in AI}, "n_ge_1pct": sum(s(ref, "C7", c) >= 0.01 for c in AI)})
    sysid = dict(by); sysid["C7"] = {x["openalex"] for x in A.SEEDS if x["cluster"] == "C7" and x.get("group", "base") == "base"}
    corp, _ = A.corpora(A.W["citers"], sysid, k)
    ref = A.m1(corp, sysid)[0]
    out[k] = {"loo": rows, "sysid_only": {c: s(ref, "C7", c) for c in AI}, "sysid_only_size": len(corp["C7"])}
    n = [r["n_ge_1pct"] for r in rows]
    print(f"{k}-seed: C7 reaches C1-C5 at >= 1% in {min(n)} to {max(n)} of 5 when one C7 seed is left out;",
          "weakest:", min(rows, key=lambda r: r["n_ge_1pct"])["left_out"])
    print(f"   system-identification seeds only (n={out[k]['sysid_only_size']}):", {c: round(v, 4) for c, v in out[k]["sysid_only"].items()})
json.dump(out, open(os.path.join(A.D, "results_c7_loo.json"), "w"), indent=1)
