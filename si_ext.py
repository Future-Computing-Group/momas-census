"""SI rows and fragments for the extension and the absolute cell counts, read from the estimate JSONs (no number typed by hand).
si_tables.py passes the v2 policy-pass view of estimates-twostage.json (keys policy2, policy2-ext, policy2-ext-ea); the count
table and the AAMAS fragment carry the parties split, so they are written only when it is passed (parties=True).

AAMAS 2025 enters the Perspective's share fragments as a comparison venue beside EC; ICLR 2025 and the AAMAS EA + Blue Sky papers
enter the count table only (Table S3), ICLR with its two-stage interval.
Counts are each population's share and conservative bounds times its N; a venue confirmed in full is a direct count.
"""
PERSPECTIVE_EXT = {"all-aamas-2025": "AAMAS 2025"}
COUNT_POPS = [("all-2020", "NeurIPS + ICML 2020", None), ("all-2025", "NeurIPS + ICML 2025", None), ("all-iclr-2025", "ICLR 2025", "ext"),
              ("all-aamas-2025", "AAMAS 2025", "ext"), ("all-aamas-2025-ea", "AAMAS 2025 EA + Blue Sky", "ext-ea"), ("ec-2025", "EC 2025", None)]
HELD = set()  # populations computed but kept out of the count table (none since the policy pass)
CELLS = ("several", "interaction", "simulated", "parties_ai-agents")


def ext_rows(tw):
    ext = tw.get("ext", {})
    return [(lab, ext[k]) for k, lab in PERSPECTIVE_EXT.items() if ext.get(k, {}).get("n")]


def counts(tw, r2, r2ext):
    """{pop: {"n": N, cell: {"count", "lo", "hi", "direct"}}} for the venue-year populations whose estimates exist."""
    out = {}
    for k, _, tag in COUNT_POPS:
        e = (tw.get(tag, {}) if tag else tw).get(k)
        if not e or not e.get("n"):
            continue
        parties = (r2ext.get(tag, {}).get("parties", {}) if tag else r2.get("parties", {})).get(k, {})
        n, direct = e["n"], bool(e.get("census"))
        out[k] = {"n": n}
        for c in CELLS:
            m = e.get(c) or parties.get(c)
            if m:
                out[k][c] = {"count": round(m["share"] * n), "lo": round(m["lo"] * n), "hi": round(m["hi"] * n), "direct": direct}
    return out


def count_rows(c, perspective=True):
    cell = lambda m: "--" if m is None else f"{m['count']}" if m["direct"] else f"{m['count']} ({m['lo']}--{m['hi']})"
    return [f"{lab} & {c[k]['n']:,} & " + " & ".join(cell(c[k].get(x)) for x in CELLS) + " \\\\"
            for k, lab, _ in COUNT_POPS if k in c and not (perspective and k in HELD)]


def _pct(m):
    return f"{100 * m['share']:.1f}\\%"


def aamas_fragment(tw, r2ext):
    a = tw["ext"]["all-aamas-2025"]
    s = f"{a['several']['confirmed']} of {a['n']} AAMAS 2025 papers ({_pct(a['several'])}) have several owners, {a['interaction']['confirmed']} ({_pct(a['interaction'])}) with the contribution about the interaction"
    p = r2ext.get("ext", {}).get("parties", {}).get("all-aamas-2025")
    if p:
        s += f"; {p['parties_ai-agents']['confirmed']} ({_pct(p['parties_ai-agents'])}) have AI agents of different owners on several sides"
    return s


def ea_fragment(tw):
    a = tw["ext-ea"]["all-aamas-2025-ea"]
    return f"{a['several']['confirmed']} of {a['n']} extended abstracts and Blue Sky papers ({_pct(a['several'])}) have several owners, {a['interaction']['confirmed']} ({_pct(a['interaction'])}) about the interaction"


def write(out, tw, r2, r2ext, counts_path="data/estimates-counts.json", parties=True):
    """Called by si_tables.py: AAMAS fragments once the extension is estimated, and the count table (all populations present).
    parties=False (the parties codes of the cell are not all in): only the fragments without a parties number."""
    import json
    if parties:
        c = counts(tw, r2, r2ext)
        json.dump(c, open(counts_path, "w"), indent=1)
        (out / "tab-counts.tex").write_text("\n".join(count_rows(c)) + "\n")
    if parties and ext_rows(tw):
        (out / "aamas-short.tex").write_text(aamas_fragment(tw, r2ext))
    if tw.get("ext-ea", {}).get("all-aamas-2025-ea", {}).get("n"):
        (out / "aamas-ea-short.tex").write_text(ea_fragment(tw))


# Section 4 of the main text states approximate proportions; the exact shares and bounds stay in Fig. 2a and the SI.
_FRACTIONS = [(1 / 2, "half"), (1 / 3, "a third"), (1 / 4, "a quarter"), (1 / 5, "a fifth"), (1 / 10, "a tenth")]


def rough_pct(ps):
    lo, hi = round(100 * min(ps)), round(100 * max(ps))
    return f"about {lo}\\%" if lo == hi else f"about {lo} to {hi}\\%"


def rough_fraction(p):
    if 0.5 < p < 2 / 3:
        return "more than half"
    return "about " + min(_FRACTIONS, key=lambda f: abs(f[0] - p))[1]


def rough_part(p):
    """A part of a whole in words: 'most' above 0.6, 'about half' from 0.4 to 0.6, else rough_fraction."""
    return "most" if p > 0.6 else "about half" if p >= 0.4 else rough_fraction(p)


def rough_rate(p):
    import math
    return f"about 1 in {10 ** round(math.log10(1 / p)):,}"


def rough_under(pairs):
    """'under N in 100' over (point, conservative upper bound) pairs: N/100 exceeds every upper bound, not only every point."""
    import math
    return f"under {math.floor(100 * max(hi for _, hi in pairs)) + 1} in 100"


def rough_change(before, after):
    r = after / before
    if r >= 3:
        return "more than tripled"
    if r >= 2:
        return "more than doubled"
    return f"rose by {'half' if r >= 1.5 else 'a third' if r >= 4 / 3 else 'a little'}"


def author_draw(recs):
    """The author's check set as drawn: how many it took among the papers the first stage then coded several owners, and from the rest
    (data/xfam/focus-check-20-draw.json: the ids with the first stage's OWNERS code at the draw, codebook v3.2)."""
    k = sum(r["owners"] == "several" for r in recs)
    return f"{k} drawn at random among the papers it then coded several owners and {len(recs) - k} from the rest"


def showcase_max(items):
    """The largest number of pages the deployment frame took from one vendor showcase (data/deploy-items.json)."""
    from collections import Counter
    return str(max(Counter(x["source"] for x in items).values()))
