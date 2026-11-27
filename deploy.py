"""D3: share of documented agent deployments by reach (internal / customer / cross-owner), per page and per organization."""
import json
import sys

from analyze import fmt, load_codes

ORDER = {"internal": 0, "customer": 1, "cross-owner": 2}


def shares(coded):
    rows = [c for c in coded if str(c.get("agent")).lower() == "yes" and c.get("reach") in ORDER]
    out = {k: sum(c["reach"] == k for c in rows) for k in ORDER}
    out["n"] = len(rows)
    return out


def crosstab(v2, v3):
    """Counter of (v2 reach, v3 reach) over the pages both versions coded; v3's counterparty is v2's customer."""
    from collections import Counter
    lab = lambda r: {"counterparty": "customer"}.get(r["reach"], r["reach"])
    return Counter((v2[i]["reach"], lab(v3[i])) for i in v3 if i in v2)


def org_level(pairs):
    """Per organization, the widest reach among its coded agent cases (na dropped)."""
    best = {}
    for org, reach in pairs:
        if reach in ORDER:
            k = org.strip().lower()
            if k not in best or ORDER[reach] > ORDER[best[k]]:
                best[k] = reach
    return best


def main(pattern="data/coded/deploy-[0-9]*.jsonl"):
    items = {x["id"]: x for x in json.load(open("data/deploy-items.json"))}
    codes = load_codes(pattern)
    coded = [c for i, c in codes.items() if i in items]
    s = shares(coded)
    print(f"cases coded {len(coded)}; agent deployments with known reach {s['n']}")
    for k in ORDER:
        print(f"  per page {k:12s} {fmt(s[k], s['n'])}")
    lvl = org_level((items[c['id']]['org'], c["reach"]) for c in coded if str(c.get("agent")).lower() == "yes")
    n = len(lvl)
    for k in ORDER:
        print(f"  per org  {k:12s} {fmt(sum(v == k for v in lvl.values()), n)}")
    print(f"  a2a mentioned {sum(str(c.get('a2a')).lower() == 'yes' for c in coded)}")


if __name__ == "__main__":
    main(*sys.argv[1:])
