"""Seed-candidate probe for the broadened R1, R3, R4 and C7 (one batched DOI filter call, cached in raw/): title, year, citations, 2016+ citations."""
import sys
from oa import get, sid, CALLS
dois = sys.argv[1:]
r = get("works", filter="doi:" + "|".join(dois), select="id,doi,title,publication_year,cited_by_count,counts_by_year,type", **{"per-page": 200})
for w in sorted(r["results"], key=lambda w: (w["doi"] or "")):
    c16 = sum(c["cited_by_count"] for c in w["counts_by_year"] if c["year"] >= 2015)
    print(sid(w["id"]), w["publication_year"], w["cited_by_count"], c16, w["type"], (w["doi"] or "").replace("https://doi.org/", ""), "|", w["title"])
print(len(r["results"]), "of", len(dois), CALLS)
