"""Agreement of open-weight (xfam) codes with the Claude primary codes, mapped through sample_id.

  python3 xfam_compare.py data/xfam/smoke/results-parsed.jsonl
"""
import json
import random
import sys

from analyze import category, load_codes
from census import kappa

FIELDS = ("agent", "interests", "owners", "boundary")


def compare(smoke, items, primary, llm):
    """{field: (n, agree, kappa)} incl. category and llm_basis, and the owners disagreements."""
    pairs = [(r, primary[items[r["id"]]["sample_id"]]) for r in smoke if items[r["id"]]["sample_id"] in primary]
    low = lambda v: str(v).lower()

    def stat(a, b):
        return (len(a), sum(x == y for x, y in zip(a, b)), kappa(a, b) if a else float("nan"))

    rows = {f: stat([low(c[f]) for _, c in pairs], [low(m[f]) for m, _ in pairs]) for f in FIELDS}
    rows["category"] = stat([category(c) for _, c in pairs], [category(m) for m, _ in pairs])
    lp = [(m, llm[items[m["id"]]["sample_id"]]) for m, _ in pairs if items[m["id"]]["sample_id"] in llm]
    rows["llm_basis"] = stat([low(c["llm_basis"]) for _, c in lp], [low(m["llm_basis"]) for m, _ in lp])
    owners = [{"sample_id": items[m["id"]]["sample_id"], "title": items[m["id"]]["title"], "claude": low(c["owners"]), "model": low(m["owners"]),
               "interests": low(m["interests"]), "quote": m.get("quote")} for m, c in pairs if low(c["owners"]) != low(m["owners"])]
    return rows, owners


def focus_check(smoke, items, seed=20261106, n=20, cap=12):
    """Author check set: every owners-several paper (up to cap), the rest drawn at random; shuffled so order hides the draw."""
    rng = random.Random(seed)
    sev = [r for r in smoke if r["owners"] == "several"]
    take = rng.sample(sev, min(cap, len(sev)))
    take += rng.sample([r for r in smoke if r not in take], n - len(take))
    rng.shuffle(take)
    return [{"id": items[r["id"]]["sample_id"], "title": items[r["id"]]["title"], "abstract": items[r["id"]]["abstract"],
             **{k: r[k] for k in ("focus", "owners", "interests", "eval_run", "quote")}} for r in take]


def recode_check(prev, smoke, items):
    """The same check set (q-ids, order) with the codes of a later smoke run."""
    by = {items[r["id"]]["sample_id"]: r for r in smoke}
    return [{"id": p["id"], "title": items[by[p["id"]]["id"]]["title"], "abstract": items[by[p["id"]]["id"]]["abstract"],
             **{k: by[p["id"]][k] for k in ("focus", "owners", "interests", "eval_run", "quote")}} for p in prev]


def main(path, halves=None, derived=None):
    from collections import Counter
    smoke = [json.loads(l) for l in open(path)]
    if derived:  # compare on the owners and focus derived from the decomposition (codebook v3.4)
        smoke = [{**r, "owners": r["owners_derived"], "focus": r["focus_derived"]} for r in smoke]
    items = {x["xid"]: x for x in map(json.loads, open("data/xfam/items-full.jsonl"))}
    groups = json.load(open(halves)) if halves else {"all": [r["id"] for r in smoke]}
    for g, ids in groups.items():
        sub = [r for r in smoke if r["id"] in set(ids)]
        rows, owners = compare(sub, items, load_codes(), load_codes("data/coded/llm-0*.jsonl"))
        print(f"\n## {g} ({len(sub)})\n| field | n | agree | kappa |\n|---|---|---|---|")
        for f, (n, k, kap) in rows.items():
            print(f"| {f} | {n} | {k} | {kap:.2f} |")
        both = lambda r: r["owners"] == "several" and r["interests"] in ("several-aligned", "several-conflicting")
        print("focus x (owners several & interests several):", dict(Counter((r.get("focus"), both(r)) for r in sub)))
        for f in ("owners", "eval_run", "cross_vendor", "confidence", "focus"):
            print(f, dict(Counter(r[f] for r in sub)))
        print("quotes verbatim", sum(bool(r["quote"]) and r["quote"] in items[r["id"]]["abstract"] for r in sub), "empty", sum(not r["quote"] for r in sub))
        print(f"owners disagreements: {len(owners)}")
        for o in owners:
            print(json.dumps(o, ensure_ascii=False))
        for r in sub:
            if r["owners"] == "several":
                print("SEVERAL", items[r["id"]]["sample_id"], r.get("focus"), r["eval_run"], r["interests"], "|", items[r["id"]]["title"], "|", r["quote"])


if __name__ == "__main__":
    main(*sys.argv[1:])
