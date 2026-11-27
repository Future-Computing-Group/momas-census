"""Attention (C7b): OpenAlex cited_by_count per paper, against the cell's share of papers.

Inputs: data/attention/{venue}.json, written by fields/run5-attention/fetch.py ({"retrieved", "method", "cites": {xid: count}}).
Per venue: total and median citations of the matched papers, and the citation share of the several-owners cell and of its
AI-agents sub-cell against their paper share. Cells are the v2 policy pass (POLICY2_MEASURES on the confirmer's codes, Claude,
stage 2) on the papers that enter the estimates: the whole venue for AAMAS and EC, the confirmed set and slices for NeurIPS 2025
(screen-negatives it did not code count as outside the cell); the sub-cell takes every primary parties code. Citations accrue to
the retrieval date; the 2025 cohorts have had less than a year. Writes data/estimates-attention-policy2.json
(data/estimates-attention.json keeps the v3.4 cells, data/estimates-attention-policy.json the v1 policy cells) and
si/tab-attention.tex; the sub-cell and the table wait for data/estimates-round2-policy2.json (every v2 cell paper with a parties code). ICLR 2025 has no row: OpenAlex lists 3 of its
3,708 papers under the ICLR source (checked 2026-11-10), so it has no keyless route (fields/run5-attention/fetch.py).

  python3 attention.py [fragment dir, default si] [estimates file, default data/estimates-attention-policy2.json]
"""
import json
import os
import statistics
import sys


def squash(t):
    from fetch_frames import squash as sq
    return sq(t)


def by_title(items, works):
    """{xid: cited_by_count} for items whose space-free normalised title equals a work's; duplicates keep the larger count."""
    best = {}
    for w in works:
        k = squash(w.get("display_name") or "")
        best[k] = max(best.get(k, -1), w.get("cited_by_count") or 0)
    return {x["xid"]: best[squash(x["title"])] for x in items if squash(x["title"]) in best}


def venue_stats(ids, cites, cell, sub):
    m = [i for i in ids if i in cites]
    tot = sum(cites[i] for i in m)

    def part(s):
        p = [i for i in m if i in s]
        c = sum(cites[i] for i in p)
        return {"papers": len(p), "paper_share": len(p) / len(m), "citations": c, "citation_share": c / tot if tot else 0.0}
    return {"n": len(ids), "matched": len(m), "total": tot, "median": statistics.median(cites[i] for i in m) if m else None, "cell": part(cell), "sub": part(sub)}


VENUES = [("neurips-2025", "NeurIPS 2025", "main"), ("aamas-2025", "AAMAS 2025", "ext"), ("aamas-2025-ea", "AAMAS 2025 EA + Blue Sky", "ext-ea"),
          ("ec-2025", "EC 2025", "main"), ("iclr-2025", "ICLR 2025", "ext"), ("neurips-2020", "NeurIPS 2020", "main"),
          ("icml-2020", "ICML 2020", "main"), ("icml-2025", "ICML 2025", "main")]
HELD = {"iclr-2025"}


def cells(tag):
    """(items, v2 several-cell ids, AI-agents sub-cell ids or None until the v2 parties split exists) from the confirmer's codes
    and every primary parties code."""
    from round2 import POLICY2_PARTIES, PRIMARY_PARTIES, load_parties
    from twostage import POLICY2_MEASURES, load_policy2
    items, _, part, claude = load_policy2("full" if tag == "main" else tag)
    cell = {i for i in part if POLICY2_MEASURES["several"](claude[i])}
    if not os.path.exists(POLICY2_PARTIES):
        return items, cell, None
    parties = load_parties(PRIMARY_PARTIES)
    return items, cell, {i for i in cell if parties[i] == "ai-agents"}


def ratio_fragment(out, a, b):
    """Total citations of venue a over venue b, rounded, for the main-text sentence."""
    return f"{out[a]['total'] / out[b]['total']:.0f}"


def split_fragment(out, a, b):
    """The ratio of venue a over venue b split into matched papers and citations per matched paper."""
    x, y = out[a], out[b]
    return f"{x['matched'] / y['matched']:.0f} times as many papers matched in OpenAlex, each cited {(x['total'] / x['matched']) / (y['total'] / y['matched']):.1f} times as often on average"


def main():
    out, rows = {}, []
    for v, lab, tag in VENUES:
        f = f"data/attention/{v}.json"
        if not os.path.exists(f) or (tag != "main" and not os.path.exists(f"data/xfam/stage2-{tag}.json")):
            continue
        a = json.load(open(f))
        items, cell, sub = cells(tag)
        ids = [i for i, x in items.items() if x["venue"] == v and x["main_track"]]
        s = venue_stats(ids, a["cites"], cell, sub or set())
        if sub is None:
            del s["sub"]
        out[v] = {**s, "retrieved": a["retrieved"], "method": a["method"]}
        if v not in HELD and sub is not None:
            p = lambda d: f"{100 * d['paper_share']:.1f} / {100 * d['citation_share']:.1f}"
            rows.append(f"{lab} & {s['matched']:,} of {s['n']:,} & {s['total']:,} & {s['median']:g} & {p(s['cell'])} & {p(s['sub'])} \\\\")
    json.dump(out, open(sys.argv[2] if len(sys.argv) > 2 else "data/estimates-attention-policy2.json", "w"), indent=1)
    od = sys.argv[1] if len(sys.argv) > 1 else "si"
    os.makedirs(od, exist_ok=True)
    if rows:
        open(f"{od}/tab-attention.tex", "w").write("\n".join(rows) + "\n")
    if "neurips-2025" in out and "aamas-2025" in out:
        open(f"{od}/attention-ratio.tex", "w").write(ratio_fragment(out, "neurips-2025", "aamas-2025"))
        open(f"{od}/attention-split.tex", "w").write(split_fragment(out, "neurips-2025", "aamas-2025"))
    for v, s in out.items():
        print(v, {k: s[k] for k in ("n", "matched", "total", "median")}, "cell", s["cell"], "ai", s.get("sub"))


if __name__ == "__main__":
    main()
