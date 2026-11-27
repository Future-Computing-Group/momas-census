"""Supplementary: M1 block medians, OpenAlex AI-subfield share (deviation: ICML/ICLR absent as venues), fairness whole-corpus attention."""
import json, statistics as st, collections
import analyse as A
from oa import get
R = json.load(open(A.os.path.join(A.D, "results_m1.json")))["M1"]
for k in ("2", "1"):
    ref = R[k]["ref"]; AI, EX = A.AI, ["C6", "C7"]
    ai_off = [ref[i][j] for i in AI for j in AI if i != j]
    cross = [ref[i][j] for i in AI for j in EX] + [ref[i][j] for i in EX for j in AI] + [ref["C6"]["C7"], ref["C7"]["C6"]]
    print(f">= {k} seeds: median within-AI-block off-diag {st.median(ai_off):.4f}; median AI<->econ/control and econ<->control {st.median(cross):.5f}; median diag {st.median(ref[i][i] for i in ref):.4f}")
by = A.seedsets(A.MAIN); corp, _ = A.corpora(A.W["citers"], by, 2)
tot = {int(g["key"]): g["count"] for g in get("works", filter="primary_topic.subfield.id:1702", group_by="publication_year")["group_by"]}
uni = {k: w for c in A.AI for k, w in corp[c].items()}
yrs = collections.Counter(w["year"] for w in uni.values())
print("AI union / OpenAlex AI subfield:", {y: f"{yrs[y]}/{tot[y]} = {100*yrs[y]/tot[y]:.4f}%" for y in range(2015, 2026)})
# fairness union (>=2 of 6), same normalisation and attention table
fb = A.seedsets({"F1", "F2", "F3"}); allf = set().union(*fb.values())
for p in ("2012-2016", "2019-2023"):
    u = {w["id"]: w for c in fb for w in A.W["citers"][f"{c}:{p}"] if len(allf & set(w["refs"])) >= 2}
    fy = collections.Counter(w["year"] for w in u.values())
    print("fairness", p, {y: f"{fy[y]}/{tot[y]} = {100*fy[y]/tot[y]:.4f}%" for y in sorted(fy)})
    print("   attention", end=" "); A.cnp_table({"FAIR" + p: u}, ["FAIR" + p])
