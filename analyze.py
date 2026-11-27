"""Stage-2 analysis: share of single-principal vs multi-principal settings per venue-year and stratum."""
import glob
import json
import math
import os
import sys
from collections import Counter

from census import flags


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, (c - m) / d), min(1.0, (c + m) / d))


def category(r):
    """multi-principal: several owners with modelled distinct-or-shared interests; adversarial: several owners via an attacker only."""
    owners, interests = str(r["owners"]).lower(), str(r["interests"]).lower()
    if owners == "na":
        return "na"
    if owners == "several" and interests in ("several-aligned", "several-conflicting"):
        return "multi-principal"
    if owners == "several" and interests == "adversarial":
        return "adversarial"
    return "single"


def strict(r):
    """multi-principal with no single party controlling every decision-maker (excludes federated learning with a central server)."""
    return category(r) == "multi-principal" and str(r.get("control")).lower() == "decentralized"


def agreement(primary, second, key, ids):
    """(n, agreements, kappa) between two coders on the given ids."""
    from census import kappa

    a = [str(primary[i][key]).lower() for i in ids]
    b = [str(second[i][key]).lower() for i in ids]
    return len(ids), sum(x == y for x, y in zip(a, b)), (kappa(a, b) if ids else float("nan"))


def load_codes(pattern="data/coded/primary-*.jsonl"):
    codes = {}
    for f in sorted(glob.glob(pattern)):
        for line in open(f):
            if line.strip():
                r = json.loads(line)
                codes[r["id"]] = r
    return codes


def final_codes(pattern="data/coded/primary-*.jsonl", adjudicated="data/adjudicated.json"):
    """Coder codes with the author's adjudicated codes applied (agreement statistics use load_codes instead)."""
    codes = load_codes(pattern)
    for i, fields in (json.load(open(adjudicated)) if os.path.exists(adjudicated) else {}).items():
        codes[i] = {**codes[i], **fields}
    return codes


def fmt(k, n):
    lo, hi = wilson(k, n)
    return f"{k}/{n} = {100 * k / n:.1f}% [{100 * lo:.1f}, {100 * hi:.1f}]" if n else "0/0"


def main():
    items = json.load(open("data/stage2-items.json"))
    codes = load_codes()
    print(f"coded {len(codes)} of {len(items)} items")
    rows = [(x, codes[x["id"]]) for x in items if x["id"] in codes]
    print("\n## Multi-principal share (several owners with modelled interests), adversarial-only reported separately")
    for venue in sorted({x["venue"] for x in items}):
        for stratum in ("random", "agent", "llm_agent", "control"):
            sub = [(x, c) for x, c in rows if x["venue"] == venue and stratum in x["strata"]]
            if not sub:
                continue
            cats = Counter(category(c) for _, c in sub)
            n = sum(v for k, v in cats.items() if k != "na")
            print(f"{venue:13s} {stratum:9s} n={len(sub):3d}  multi-principal {fmt(cats['multi-principal'], n)}  adversarial {fmt(cats['adversarial'], n)}")
        agent_coded = [(x, c) for x, c in rows if x["venue"] == venue and "random" in x["strata"] and c["agent"] == "yes"]
        if agent_coded:
            ag = [(x, c) for x, c in agent_coded]
            k = sum(category(c) == "multi-principal" for _, c in ag)
            print(f"{venue:13s} coded-agent papers in random stratum: multi-principal {fmt(k, len(ag))}")
    print("\n## Strict multi-principal (several owners, modelled interests, decentralized control)")
    for venue in sorted({x["venue"] for x in items}):
        for stratum in ("random", "agent", "llm_agent", "control"):
            sub = [c for x, c in rows if x["venue"] == venue and stratum in x["strata"] and category(c) != "na"]
            if sub:
                print(f"{venue:13s} {stratum:9s} strict {fmt(sum(strict(c) for c in sub), len(sub))}")
    second = load_codes("data/coded/overlap-*.jsonl")
    if second:
        ids = sorted(i for i in second if i in codes)
        length = {x["id"]: len(x["abstract"]) for x in items}
        print(f"\n## Inter-coder agreement on {len(ids)} double-coded items (kappa)")
        for key in ("agent", "interests", "owners", "control", "boundary"):
            n, k, kap = agreement(codes, second, key, ids)
            ln = [i for i in ids if length[i] > 900]
            sh = [i for i in ids if length[i] <= 900]
            _, kl, kapl = agreement(codes, second, key, ln)
            _, ks, kaps = agreement(codes, second, key, sh)
            print(f"{key:10s} all {k}/{n} k={kap:.2f} | abstract>900 {kl}/{len(ln)} k={kapl:.2f} | <=900 {ks}/{len(sh)} k={kaps:.2f}")
        cp = [category(codes[i]) for i in ids]
        cs = [category(second[i]) for i in ids]
        from census import kappa
        print(f"category  all {sum(a == b for a, b in zip(cp, cs))}/{len(ids)} k={kappa(cp, cs):.2f}")
    print("\n## Keyword-flag recall for agent papers (random strata)")
    for venue in sorted({x["venue"] for x in items if not x["venue"].startswith("ec-")}):
        sub = [(x, c) for x, c in rows if x["venue"] == venue and "random" in x["strata"] and c["agent"] == "yes"]
        hit = sum(flags(x["title"] + " " + x["abstract"])["agent"] for x, _ in sub)
        print(f"{venue:13s} agent flag catches {fmt(hit, len(sub))} of coded agent papers")


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    main(*sys.argv[1:])
