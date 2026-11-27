"""Seed-candidate probe for the broadened R2 (one batched DOI filter call, cached in raw/): title, year, citations, 2015+ citations."""
import sys
from oa import get, sid, CALLS
dois = sys.argv[1:]
r = get("works", filter="doi:" + "|".join(dois), select="id,doi,title,publication_year,cited_by_count,counts_by_year", **{"per-page": 200})
for w in r["results"]:
    c15 = sum(c["cited_by_count"] for c in w["counts_by_year"] if c["year"] >= 2015)
    print(sid(w["id"]), w["publication_year"], w["cited_by_count"], c15, (w["doi"] or "").replace("https://doi.org/", ""), "|", w["title"])
print(len(r["results"]), "of", len(dois), CALLS)
