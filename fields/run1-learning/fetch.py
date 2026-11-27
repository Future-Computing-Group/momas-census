"""Step 2: fetch every work citing any seed of a cluster (union cites: filter), seeds themselves, fairness periods.
Corpus membership (>=2 seeds) is decided later in analyse.py from referenced_works, so one fetch per cluster suffices."""
import json, os
from oa import get, get_all, sid, CALLS

D = os.path.dirname(os.path.abspath(__file__))
SEL = "id,title,publication_year,cited_by_count,referenced_works,primary_location,citation_normalized_percentile"
seeds = json.load(open(os.path.join(D, "seeds.json")))
by = {}
for s in seeds:
    by.setdefault(s["cluster"], []).append(s["openalex"])


def slim(w):
    src = ((w.get("primary_location") or {}).get("source") or {})
    cnp = w.get("citation_normalized_percentile") or {}
    return {"id": sid(w["id"]), "year": w["publication_year"], "cites": w["cited_by_count"],
            "refs": [sid(r) for r in w.get("referenced_works") or []], "src": sid(src.get("id")),
            "src_name": src.get("display_name"), "cnp": cnp.get("value"), "top1": cnp.get("is_in_top_1_percent"),
            "title": w.get("title")}


out = {"citers": {}, "seeds": {}}
for c, ids in by.items():
    years = "2015-2026" if c.startswith("C") else None
    if years:
        out["citers"][c] = [slim(w) for w in get_all("works", filter=f"cites:{'|'.join(ids)},publication_year:{years}", select=SEL)]
    else:  # fairness: two periods
        for p in ("2012-2016", "2019-2023"):
            out["citers"][f"{c}:{p}"] = [slim(w) for w in get_all("works", filter=f"cites:{'|'.join(ids)},publication_year:{p}", select=SEL)]
    print(c, {k: len(v) for k, v in out["citers"].items() if k.startswith(c)}, CALLS, flush=True)
allids = [s["openalex"] for s in seeds]
for i in range(0, len(allids), 50):
    for w in get("works", filter="openalex:" + "|".join(allids[i:i + 50]), select=SEL, **{"per-page": 200})["results"]:
        out["seeds"][sid(w["id"])] = slim(w)
json.dump(out, open(os.path.join(D, "works.json"), "w"))
print("done", CALLS)
