"""Fetch OpenAlex cited_by_count for the census frames (keyless, cached in raw/ by oa.py; stops at the credit floor, rerun resumes).

Matching per venue, by what the frame carries:
- AAMAS 2025 and its EA + Blue Sky sensitivity: the IFAAMAS DOI (filter doi:, 50 per call);
- EC 2025: the OpenAlex work id of the frame (filter openalex:, 50 per call);
- NeurIPS 2025: every 2025 work of OpenAlex source S4363606243 (neural information processing systems), matched by title.
NeurIPS 2020, ICML 2020 and 2025 and ICLR 2025 sit in OpenAlex mostly as arXiv works without a venue source (checked
2026-11-09: the NeurIPS source holds 242 works for 2020, the ICML source 180 for 2020 and none for 2025, the ICLR source none
for 2025), so they need one title search per paper, beyond the keyless allowance (1,000 credits a day, 10 per list call).

Run from the repository root: python3 fields/run5-attention/fetch.py [venue ...]. Writes data/attention/{venue}.json.
"""
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ".")
import oa  # noqa: E402
from attention import by_title  # noqa: E402
from census import norm  # noqa: E402

SEL = "id,doi,display_name,cited_by_count"


def items(venue):
    f = "data/xfam/items-full.jsonl" if venue in ("neurips-2025", "ec-2025") else "data/xfam/items-ext-ea.jsonl" if venue.endswith("-ea") else "data/xfam/items-ext.jsonl"
    return [x for x in map(json.loads, open(f)) if x["venue"] == venue and x["main_track"]]


def frame(venue):
    d = json.load(open(f"data/raw/{venue}.json"))
    return {norm(r["name"]): r for r in (d["results"] if isinstance(d, dict) else d)}


def by_key(its, venue, key, filt):
    """Batched id lookups: key is the frame field (doi or openalex), filt the OpenAlex filter name."""
    fr = frame(venue)
    want = {x["xid"]: fr[norm(x["title"])][key].lower().rsplit("/", 1)[-1] if key == "openalex" else fr[norm(x["title"])][key].lower() for x in its}
    vals = sorted(set(want.values()))
    got = {}
    for b in range(0, len(vals), 50):
        for w in oa.get("works", filter=f"{filt}:" + "|".join(vals[b:b + 50]), select=SEL, **{"per-page": 50})["results"]:
            k = (w.get("doi") or "").lower().replace("https://doi.org/", "") if key == "doi" else oa.sid(w["id"]).lower()
            got[k] = max(got.get(k, -1), w.get("cited_by_count") or 0)
    return {i: got[v] for i, v in want.items() if v in got}


def fetch(venue):
    its = items(venue)
    if venue.startswith("aamas-2025"):
        return by_key(its, venue, "doi", "doi"), "IFAAMAS DOI (filter doi:)"
    if venue == "ec-2025":
        return by_key(its, venue, "openalex", "openalex"), "frame OpenAlex id (filter openalex:)"
    if venue == "neurips-2025":
        works = oa.get_all("works", filter="primary_location.source.id:S4363606243,publication_year:2025", select=SEL)
        return by_title(its, works), "source S4363606243, publication_year 2025, matched by space-free normalised title"
    raise SystemExit(f"{venue}: no keyless route (one title search per paper)")


if __name__ == "__main__":
    os.makedirs("data/attention", exist_ok=True)
    for v in sys.argv[1:] or ["aamas-2025", "aamas-2025-ea", "ec-2025", "neurips-2025"]:
        cites, method = fetch(v)
        json.dump({"retrieved": datetime.date.today().isoformat(), "method": method, "cites": cites}, open(f"data/attention/{v}.json", "w"), indent=0)
        print(v, "matched", len(cites), "of", len(items(v)), oa.CALLS)
