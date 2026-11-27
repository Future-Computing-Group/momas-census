"""Design-weighted shares over coded populations (agent papers = coded AGENT=yes; LLM-agent = AGENT=yes and LLM_BASIS=yes).

The keyword strata are the sampling frame, not the population: each coded item is weighted by the inverse of its
probability of entering the sample (Horvitz-Thompson), so keyword-missed agent papers enter through the random stratum.
"""
import json
import random

from analyze import category, final_codes, load_codes, strict, wilson
from census import flags, load, norm

N_RANDOM, N_AGENT = 300, 200  # build_sample.py quotas
ML = ("neurips-2020", "icml-2020", "neurips-2025", "icml-2025")


def inclusion(f, frame, llm_census):
    """Probability that a paper with keyword flags f enters the sample of its venue-year (strata drawn independently)."""
    if llm_census and f["llm_agent"]:
        return 1.0
    miss = 1 - frame["random"] / frame["n"]
    if f["agent"]:
        miss *= 1 - min(frame["agent"], frame["agent_hits"]) / frame["agent_hits"]
    return 1 - miss


def main_track(r):
    """Main-track record: 2025 records name their OpenReview group; the 2020 lists hold main-track proceedings only."""
    u = r.get("sourceurl")
    return u is None or u.rstrip("/").endswith("/Conference")


def ht_share(ys, pis):
    w = [1 / p for p in pis]
    return sum(y * x for y, x in zip(ys, w)) / sum(w)


def kish(pis):
    """Kish effective sample size of inverse-probability weights."""
    w = [1 / p for p in pis]
    return sum(w) ** 2 / sum(x * x for x in w)


def flip_leverage(ys, pis):
    """Absolute change in the weighted share if each item's indicator alone were flipped."""
    w = [1 / p for p in pis]
    return [x / sum(w) for x in w]  # flipping y_i moves the numerator by w_i, the share by w_i / sum(w)


def frames():
    out, main = {}, {}
    for c in ML:
        rows = [r for r in load(f"data/raw/{c}.json") if r.get("type") != "paratext"]
        hits = sum(flags(r["name"] + " " + (r.get("abstract") or ""))["agent"] for r in rows)
        out[c] = {"n": len(rows), "random": N_RANDOM, "agent_hits": hits, "agent": N_AGENT}
        main.update({(c, norm(r["name"])): main_track(r) for r in rows})
    return out, main


def table(seed=7, reps=2000, main_only=True, adjudicated=True):
    items = json.load(open("data/stage2-items.json"))
    codes = final_codes() if adjudicated else load_codes()
    llm = load_codes("data/coded/llm-0*.jsonl")
    fr, main = frames()
    rows = []
    for x in items:
        c = codes[x["id"]]
        if category(c) == "na" or (main_only and x["venue"] in ML and not main[(x["venue"], norm(x["title"]))]):
            continue
        # EC is coded in full (pi = 1)
        pi = 1.0 if x["venue"] == "ec-2025" else inclusion(flags(x["title"] + " " + x["abstract"]), fr[x["venue"]], x["venue"].endswith("2025"))
        rows.append({"id": x["id"], "venue": x["venue"], "year": x["venue"][-4:], "ec": x["venue"] == "ec-2025", "pi": pi, "c": c, "llm": llm.get(x["id"], {}).get("llm_basis")})
    pops = {
        "all-2020": lambda r: r["year"] == "2020",
        "all-2025": lambda r: r["year"] == "2025" and not r["ec"],
        "agent-2020": lambda r: r["year"] == "2020" and r["c"]["agent"] == "yes",
        "agent-2025": lambda r: r["year"] == "2025" and not r["ec"] and r["c"]["agent"] == "yes",
        "llm-agent-2025": lambda r: r["year"] == "2025" and not r["ec"] and r["c"]["agent"] == "yes" and r["llm"] == "yes",
        "other-agent-2025": lambda r: r["year"] == "2025" and not r["ec"] and r["c"]["agent"] == "yes" and r["llm"] != "yes",
        "ec-2025": lambda r: r["ec"],
    }
    simulated = lambda c: str(c["owners"]).lower() == "one" and str(c["interests"]).lower() in ("several-aligned", "several-conflicting")
    conflicting = lambda c: category(c) == "multi-principal" and str(c["interests"]).lower() == "several-conflicting"
    measures = {"several": lambda c: category(c) == "multi-principal", "conflicting": conflicting, "aligned": lambda c: category(c) == "multi-principal" and not conflicting(c),
                "strict": strict, "simulated": simulated, "adversarial": lambda c: category(c) == "adversarial",
                "default": lambda c: str(c["owners"]).lower() == "one" and str(c["interests"]).lower() == "one"}

    def est(rs):
        return {p: {m: ht_share([f(r["c"]) for r in rs if keep(r)], [r["pi"] for r in rs if keep(r)]) for m, f in measures.items()} for p, keep in pops.items()}

    point = est(rows)
    by_venue = {v: [r for r in rows if r["venue"] == v] for v in ML + ("ec-2025",)}
    rng = random.Random(seed)
    boots = []
    # ponytail: with-replacement bootstrap within venue-year, an approximation to the stratified design variance
    for _ in range(reps):
        boots.append(est([rng.choice(rs) for rs in by_venue.values() for _ in rs]))
    out = {}
    for p in pops:
        rs = [r for r in rows if pops[p](r)]
        pis = [r["pi"] for r in rs]
        ne = kish(pis)
        lev = flip_leverage([0] * len(rs), pis)
        out[p] = {"n": len(rs), "n_eff": ne, "k": {m: sum(f(r["c"]) for r in rs) for m, f in measures.items()},
                  "pivotal": sorted(r["id"] for r, l in zip(rs, lev) if l >= 0.01)}
        for m in measures:
            s = sorted(b[p][m] for b in boots)
            out[p][m] = (point[p][m], s[int(0.025 * reps)], s[int(0.975 * reps) - 1])
        # Wilson interval on the effective sample size, for rare proportions where the bootstrap degenerates
        out[p]["wilson_eff"] = {m: wilson(point[p][m] * ne, ne) for m in ("several", "simulated")}
    diff = sorted(b["agent-2025"]["several"] - b["agent-2020"]["several"] for b in boots)
    out["agent-diff-2025-2020"] = {"several": (point["agent-2025"]["several"] - point["agent-2020"]["several"], diff[int(0.025 * reps)], diff[int(0.975 * reps) - 1])}
    return out


if __name__ == "__main__":
    for main_only, adj, path in ((True, True, "data/estimates.json"), (False, True, "data/estimates-all-tracks.json"), (True, False, "data/estimates-coder-labels.json")):
        t = table(main_only=main_only, adjudicated=adj)
        json.dump(t, open(path, "w"), indent=1)
        print("##", path)
        for p, d in t.items():
            print(p, d.get("n", ""), "n_eff %.0f" % d["n_eff"] if "n_eff" in d else "", "k", d.get("k", {}).get("several"), "pivotal", len(d.get("pivotal", [])),
                  "  ".join(f"{m} {100 * d[m][0]:.1f} [{100 * d[m][1]:.1f}, {100 * d[m][2]:.1f}]" for m in ("several", "simulated") if m in d))
