"""Append the one EC 2025 research paper that OpenAlex types as paratext (build_sample.py drops paratext records) as item q2062."""
import json

from census import load

items = json.load(open("data/stage2-items.json"))
if not any(x["id"] == "q2062" for x in items):
    (r,) = [r for r in load("data/raw/ec-2025.json") if r.get("type") == "paratext"]
    items.append({"id": "q2062", "venue": "ec-2025", "strata": ["control"], "title": r["name"], "abstract": r.get("abstract") or ""})
    json.dump(items, open("data/stage2-items.json", "w"), indent=0)
    json.dump([{k: items[-1][k] for k in ("id", "title", "abstract")}], open("data/batches/primary-ec-addendum.json", "w"), indent=0)
print(len(items))
