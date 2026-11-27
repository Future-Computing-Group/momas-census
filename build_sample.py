"""Stage-2 sample: per venue-year, a random stratum, an agent-flagged stratum and (2025 only) every LLM-agent paper; the EC control corpus in full; a random overlap subset for the second coder."""
import json
import random
import sys

from census import flags, load, sample


def build(venues, n_random, n_agent, seed, overlap_frac):
    items = []
    for venue in sorted(venues):
        rows = venues[venue]
        text = {r["name"]: r["name"] + " " + (r.get("abstract") or "") for r in rows}
        strata = {}
        if venue.startswith("ec-"):
            strata["control"] = rows
        else:
            strata["random"] = sample(rows, n_random, seed)
            strata["agent"] = sample([r for r in rows if flags(text[r["name"]])["agent"]], n_agent, seed + 1)
            if venue.endswith("2025"):
                strata["llm_agent"] = [r for r in rows if flags(text[r["name"]])["llm_agent"]]
        member = {}
        for s, rs in strata.items():
            for r in rs:
                member.setdefault(r["name"], (r, []))[1].append(s)
        for name in sorted(member):
            r, ss = member[name]
            items.append({"venue": venue, "strata": sorted(ss), "title": r["name"], "abstract": r.get("abstract") or ""})
    # opaque ids: coders must not be able to read venue or year off the id
    random.Random(seed + 3).shuffle(items)
    items = [{"id": f"q{i:04d}", **x} for i, x in enumerate(items)]
    overlap = sorted(x["id"] for x in random.Random(seed + 2).sample(items, round(overlap_frac * len(items))))
    return items, overlap


if __name__ == "__main__":
    cells = sys.argv[1:] or ["neurips-2020", "icml-2020", "neurips-2025", "icml-2025", "ec-2025"]
    venues = {c: [r for r in load(f"data/raw/{c}.json") if r.get("type") != "paratext"] for c in cells}
    items, overlap = build(venues, n_random=300, n_agent=200, seed=2026, overlap_frac=0.2)
    json.dump(items, open("data/stage2-items.json", "w"), indent=0)
    json.dump(overlap, open("data/stage2-overlap.json", "w"))
    print(len(items), "items;", len(overlap), "overlap")
    for c in cells:
        v = [x for x in items if x["venue"] == c]
        print(c, len(v), {s: sum(s in x["strata"] for x in v) for s in ("random", "agent", "llm_agent", "control")})
