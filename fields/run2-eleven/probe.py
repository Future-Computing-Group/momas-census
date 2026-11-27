"""Seed-candidate probe: one batched DOI filter call; prints what OpenAlex resolves."""
import sys
from oa import get, sid, CALLS
dois = sys.argv[1:]
r = get("works", filter="doi:" + "|".join(dois), select="id,doi,title,publication_year,cited_by_count,referenced_works_count,type", **{"per-page": 200})
for w in r["results"]:
    print(sid(w["id"]), w["publication_year"], w["cited_by_count"], w["referenced_works_count"], w["type"], (w["doi"] or "").replace("https://doi.org/", ""), "|", w["title"])
print(len(r["results"]), "of", len(dois), CALLS)
