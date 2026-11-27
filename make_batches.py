"""Blind coder batches: shuffled across venues, carrying only id, title and abstract."""
import json
import random
from pathlib import Path

SIZE = 70
items = {x["id"]: x for x in json.load(open("data/stage2-items.json"))}
overlap = json.load(open("data/stage2-overlap.json"))
out = Path("data/batches")
out.mkdir(exist_ok=True)
for kind, ids, seed in (("primary", sorted(items), 31), ("overlap", overlap, 32)):
    ids = list(ids)
    random.Random(seed).shuffle(ids)
    for b in range(0, len(ids), SIZE):
        chunk = [{k: items[i][k] for k in ("id", "title", "abstract")} for i in ids[b : b + SIZE]]
        json.dump(chunk, open(out / f"{kind}-{b // SIZE:02d}.json", "w"), indent=0)
print(sorted(p.name for p in out.glob("*.json"))[-1], len(list(out.glob("primary-*"))), len(list(out.glob("overlap-*"))))
