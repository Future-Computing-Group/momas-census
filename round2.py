"""Round-2 re-analyses of the two-stage census (Supplementary Note 1): the headline cell by interests with an adversarial-inclusive
row, intervals for the 2025-2020 differences and the simulated/several ratios, CROSS_VENDOR counts, and the sector comparison.
Writes data/estimates-round2.json; si_tables.py turns it into si/*.tex.

Intervals, all with the confirmed counts held fixed (the confirmer coded every screened paper):
- conservative: differences and ratios of the per-population bounds of twostage.py;
- bootstrap: slice papers resampled with replacement within strata (keeps the correlation between measures and populations);
- jeffreys: each stratum's rate drawn from its Jeffreys posterior, a sensitivity for strata whose slice holds no paper of the cell,
  where the bootstrap cannot move. Draws are independent across measures, so it is used for differences only, not for ratios.
"""
import json
import math
import random
import sys

from affil import alphabetical, sector
from census import norm
from twostage import load_codes, MAIN_2025, MEASURES, POLICY_MEASURES, POLICY2_MEASURES, load_policy, load_policy2, policy_ready, policy2_ready, MIN_STRATUM, POPS, POPS_EA, POPS_EXT, SEVERAL, claude_owners, expected, load, load_ext, slices, strata_of, stratum, stratum_rate, table

EXTRA = {
    "aligned": lambda r: claude_owners(r) == "several" and r.get("interests") == "several-aligned",
    "adversarial": lambda r: claude_owners(r) == "several" and r.get("interests") == "adversarial",
    "adversarial_incl": lambda r: claude_owners(r) == "several" and r.get("interests") in SEVERAL + ("adversarial",),
    "simulated_xvendor": lambda r: MEASURES["simulated"](r) and r.get("cross_vendor") == "yes",
}
ALL = {**MEASURES, **EXTRA}


PARTIES = ("ai-agents", "humans", "formal-model", "other")


def parties_measures(parties, cell=MEASURES["several"]):
    """The cell split by who the other parties are (codebook-parties.md); every cell paper must have a code (KeyError otherwise)."""
    return {f"parties_{c}": (lambda r, c=c: cell(r) and parties[r["id"]] == c) for c in PARTIES}


def load_parties(pattern="data/coded/r2-parties-0*.jsonl"):
    import glob
    return {r["id"]: r["parties"] for f in sorted(glob.glob(pattern)) for r in map(json.loads, filter(str.strip, open(f)))}


def parties_agreement(first="data/coded/r2-parties-0*.jsonl", second="data/coded/r2-parties-dup.jsonl"):
    from census import kappa
    a, b = load_parties(first), load_parties(second)
    ids = sorted(b)
    x, y = [a[i] for i in ids], [b[i] for i in ids]
    bx, by = [v == "ai-agents" for v in x], [v == "ai-agents" for v in y]
    return {"n": len(ids), "agree": sum(u == v for u, v in zip(x, y)), "kappa": kappa(x, y), "agree_ai": sum(u == v for u, v in zip(bx, by)), "kappa_ai": kappa(bx, by)}


def resample_slice(ids, items, screen, rng):
    """One bootstrap draw of a random slice: each stratum resampled with replacement to its own size."""
    by = {}
    for i in ids:
        by.setdefault(stratum(items[i], screen[i]), []).append(i)
    return [rng.choice(v) for v in by.values() for _ in v]


def jeffreys_rate(st, rng):
    """A rate function (as twostage.stratum_rate) whose rates are one Jeffreys-posterior draw per stratum; thin or absent strata
    share one draw of the pooled rate."""
    beta = lambda v: rng.betavariate(sum(v) + 0.5, len(v) - sum(v) + 0.5)
    pooled = beta([y for v in st.values() for y in v])
    d = {k: beta(v) for k, v in st.items() if len(v) >= MIN_STRATUM}
    return lambda _st, k: d.get(k, pooled)


def ratio_of(x, y):
    """A replicate's ratio; a replicate with no paper in the denominator cell has an unbounded ratio (sorts above every finite one)."""
    return x / y if y else math.inf


def interval(xs):
    s = sorted(xs)
    return s[int(0.025 * (len(s) - 1))], s[int(0.975 * (len(s) - 1))]


def replicates(pops, measures, method, reps=2000, seed=12, data=None):
    """{pop: {measure: [share per replicate]}}. method: 'bootstrap' resamples the slices within strata; 'jeffreys' draws the
    stratum rates instead; a 'papers' prefix ('papers' = with the bootstrap, 'papers-jeffreys') also resamples each population's
    papers with replacement, treating the census as one draw from the venues' output."""
    import numpy as np
    items, screen, part, claude = data or load()
    confirmed, sc, sd = slices(part)
    rng, nrng = random.Random(seed), np.random.default_rng(seed)
    jeff, pop_draw = method.endswith("jeffreys"), method.startswith("papers")
    base = {}
    for name, keep in pops.items():
        P = [i for i, x in items.items() if keep(x, screen[i])]
        keys = sorted({(screen[i]["agent"] == "yes", stratum(items[i], screen[i])) for i in P if i not in confirmed})
        code = np.array([-1 if i in confirmed else keys.index((screen[i]["agent"] == "yes", stratum(items[i], screen[i]))) for i in P])
        val = {m: np.array([int(i in confirmed and f(claude[i])) for i in P]) for m, f in measures.items()}
        base[name] = (len(P), keys, code, val)
    out = {n: {m: [] for m in measures} for n in pops}
    for _ in range(reps):
        c_, d_ = (sc, sd) if jeff else (resample_slice(sc, items, screen, rng), resample_slice(sd, items, screen, rng))
        draws = {}
        for name, (n, keys, code, val) in base.items():
            ix = nrng.integers(0, n, n) if pop_draw else np.arange(n)
            cnt = np.bincount(code[ix][code[ix] >= 0], minlength=len(keys))
            draws[name] = (n, {k: int(c) for k, c in zip(keys, cnt)}, {m: int(v[ix].sum()) for m, v in val.items()})
        for m, f in measures.items():
            st_c, st_d = strata_of(c_, f, items, screen, claude), strata_of(d_, f, items, screen, claude)
            rc, rd = (jeffreys_rate(st_c, rng), jeffreys_rate(st_d, rng)) if jeff else (stratum_rate, stratum_rate)
            for name, (n, cnt, k) in draws.items():
                na = {s_: c for (a, s_), c in cnt.items() if a}
                no = {s_: c for (a, s_), c in cnt.items() if not a}
                out[name][m].append((k[m] + expected(na, st_c, rc) + expected(no, st_d, rd)) / n)
    return out


def authors_by_title():
    raw = {}
    for v in ("neurips-2020", "icml-2020", "neurips-2025", "icml-2025"):
        for r in json.load(open(f"data/raw/{v}.json"))["results"]:
            raw.setdefault((v, norm(r["name"])), r.get("authors") or [])
    return raw


def last_sector(x, raw, dual="industry"):
    """Last author's sector for a main-track paper with at least two authors in non-alphabetical order, else None."""
    a = raw.get((x["venue"], norm(x["title"])))
    if not a or len(a) < 2 or alphabetical([y.get("fullname", "") for y in a]):
        return None
    return sector(a[-1].get("institution"), dual=dual)


MAIN = lambda x: x["venue"].endswith("2020") or MAIN_2025(x)


def sector_pops(raw, dual="industry", unknown=None):
    """Main-track papers of 2020 and 2025 by the last author's sector (see last_sector). unknown: None drops papers whose last
    author is unclassified; 'academic' or 'industry' assigns them there."""
    def last(x):
        s = last_sector(x, raw, dual)
        return unknown if s == "unknown" else s
    pops = {}
    for g in ("industry", "academic"):
        pops[f"all-{g}"] = lambda x, s, g=g: MAIN(x) and last(x) == g
        pops[f"agent-{g}"] = lambda x, s, g=g: MAIN(x) and s["agent"] == "yes" and last(x) == g
    return pops


def contrasts(t, reps):
    """Differences (points) and ratios with conservative intervals and one interval per replicate scheme in reps
    ({method: replicates}); Jeffreys draws are independent across measures, so ratios use the resampling schemes only."""
    out = {}

    def diff(name, a, b, m):
        out[name] = {"point": 100 * (t[a][m]["share"] - t[b][m]["share"]), "conservative": (100 * (t[a][m]["lo"] - t[b][m]["hi"]), 100 * (t[a][m]["hi"] - t[b][m]["lo"]))}
        for meth, r in reps.items():
            out[name][meth] = tuple(100 * x for x in interval([x - y for x, y in zip(r[a][m], r[b][m])]))

    def ratio(name, p, num="simulated", den="several"):
        out[name] = {"point": t[p][num]["share"] / t[p][den]["share"], "conservative": (t[p][num]["lo"] / t[p][den]["hi"], t[p][num]["hi"] / t[p][den]["lo"])}
        for meth, r in reps.items():
            if not meth.endswith("jeffreys"):
                out[name][meth] = interval([ratio_of(x, y) for x, y in zip(r[p][num], r[p][den])])
    for m in ("several", "interaction", "conflicting"):
        diff(f"all-{m}-2025-2020", "all-2025", "all-2020", m)
    for m in ("several", "simulated"):
        diff(f"agent-{m}-2025-2020", "agent-2025", "agent-2020", m)
    for p in ("agent-2025", "llm-agent-2025", "other-agent-2025"):
        ratio(f"ratio-{p}", p)
    l_c, o_c = out["ratio-llm-agent-2025"]["conservative"], out["ratio-other-agent-2025"]["conservative"]
    out["ratio-llm-minus-other"] = {"point": out["ratio-llm-agent-2025"]["point"] - out["ratio-other-agent-2025"]["point"],
                                    "conservative": (l_c[0] - o_c[1], l_c[1] - o_c[0])}
    for meth, r in reps.items():
        if not meth.endswith("jeffreys"):
            l_, o_ = r["llm-agent-2025"], r["other-agent-2025"]
            out["ratio-llm-minus-other"][meth] = interval([ratio_of(a, b) - ratio_of(c, d) for a, b, c, d in zip(l_["simulated"], l_["several"], o_["simulated"], o_["several"])])
    return out


def cross_vendor(data=None, measures=MEASURES, screen_simulated=lambda s: s["owners_derived"] == "one" and s["interests"] in SEVERAL):
    """CROSS_VENDOR among the 2025 main-track LLM-agent papers: the confirmer's code where it coded the paper, else the screen's.
    data, measures, screen_simulated: the policy pass passes load_policy(), POLICY_MEASURES and the screen's policy simulated cell."""
    items, screen, part, claude = data or load()
    P = [i for i, x in items.items() if POPS["llm-agent-2025"](x, screen[i])]
    claude = {i: r for i, r in claude.items() if "cross_vendor" in r}  # papers with a v3.4 confirmer code
    cv = lambda i: (claude[i] if i in claude else screen[i]).get("cross_vendor")
    s2 = [i for i in P if i in claude]
    sim2 = [i for i in s2 if measures["simulated"](claude[i])]
    sim1 = [i for i in P if i not in claude and screen_simulated(screen[i])]
    sev2 = [i for i in s2 if measures["several"](claude[i])]
    return {"n": len(P), "n_stage2": len(s2), "yes": sum(cv(i) == "yes" for i in P), "yes_stage2": sum(cv(i) == "yes" for i in s2),
            "simulated_stage2": len(sim2), "simulated_stage2_yes": sum(cv(i) == "yes" for i in sim2),
            "simulated_stage1_only": len(sim1), "simulated_stage1_only_yes": sum(cv(i) == "yes" for i in sim1),
            "several_stage2": len(sev2), "several_stage2_yes": sum(cv(i) == "yes" for i in sev2)}


def sector_comparison(reps=2000, data=None, several=MEASURES["several"]):
    raw = authors_by_title()
    items, _, _, _ = data or load()
    secs = [last_sector(x, raw) for x in items.values() if MAIN(x)]
    out = {"eligible": sum(s is not None for s in secs), "unclassified": secs.count("unknown"), "main_track": len(secs)}
    for label, kw in (("primary", {}), ("dual-academic", {"dual": "academic"}), ("dual-excluded", {"dual": "unknown"}),
                      ("unknown-academic", {"unknown": "academic"}), ("unknown-industry", {"unknown": "industry"})):
        pops = sector_pops(raw, **kw)
        m = {"several": several}
        t = table(m, pops, data)
        b = replicates(pops, m, "papers-jeffreys", reps=reps, data=data)
        for pop in ("all", "agent"):
            i, a = t[f"{pop}-industry"], t[f"{pop}-academic"]
            d = [x - y for x, y in zip(b[f"{pop}-industry"]["several"], b[f"{pop}-academic"]["several"])]
            out[f"{label}-{pop}"] = {"industry": {"n": i["n"], **i["several"]}, "academic": {"n": a["n"], **a["several"]},
                                    "diff": 100 * (i["several"]["share"] - a["several"]["share"]), "bootstrap": tuple(100 * x for x in interval(d)),
                                    "conservative": (100 * (i["several"]["lo"] - a["several"]["hi"]), 100 * (i["several"]["hi"] - a["several"]["lo"]))}
    return out


def jobs():
    """Coding jobs (dispatched to the coders outside this repository): who the other parties are, for every paper the confirmer placed in the
    cell (codebook-parties.md); and the role-independent REACH re-code of the 83 live agent deployments with a stated reach
    (codebook-deploy-roleindep.md). Coders see the id and the text only; the deployment file holds vendor page text (gitignored)."""
    import glob
    from pathlib import Path
    items, _, part, claude = load()
    cell = sorted(i for i in claude if MEASURES["several"](claude[i]))
    rng = random.Random(20261107)
    rng.shuffle(cell)
    with open("data/cell-parties-items.jsonl", "w") as f:
        for i in cell:
            f.write(json.dumps({"id": i, "title": items[i]["title"].strip(), "abstract": items[i]["abstract"]}, ensure_ascii=False) + "\n")
    P = {}
    for fn in sorted(glob.glob("data/coded/deploy-0[0-9].jsonl")):
        for line in open(fn):
            if line.strip():
                r = json.loads(line)
                P[r["id"]] = r
    known = sorted(i for i, r in P.items() if str(r.get("status")).lower() == "ok" and str(r.get("agent")).lower() == "yes" and str(r.get("reach")).lower() in ("internal", "customer", "cross-owner"))
    org = {x["id"]: x["org"] for x in json.load(open("data/deploy-items.json"))}
    with open("data/deploy-recode-items.jsonl", "w") as f:
        for i in known:
            f.write(json.dumps({"id": i, "org": org[i], "text": Path(f"data/raw/deploy-pages/{i}.txt").read_text()}, ensure_ascii=False) + "\n")
    print(f"cell papers {len(cell)}; deployment pages {len(known)}")


# The dispatched parties brief (coding/briefs.jsonl, template b9eb78723f81); BASE and <scratch-path> are filled at dispatch.
PARTIES_BRIEF = 'You are a careful research coder. Do the work yourself: spawn no agents, run nothing in the background, fetch no web pages, use no scripts or keyword rules to assign codes (a helper script only to serialize your hand-assigned codes is fine, kept in your private directory <scratch-path>).\n\nBASE = "BASE"\nRead BASE/codebook-parties.md and the papers in BASE/data/batches/{b}.json (each has id, title, abstract). Open no other file. Code every paper by hand from its title and abstract, reading each abstract to its end. Write BASE/data/coded/{b}.jsonl with exactly one JSON object per line per paper, in the output format the codebook specifies, ids copied exactly. Return only: the number of papers coded and the count per PARTIES category.'
EXT_POPS = {"ext": POPS_EXT, "ext-ea": POPS_EA}


def parties_brief(batch):
    return PARTIES_BRIEF.format(b=batch)


def jobs_ext(tag="ext", size=100, dup_share=0.2):
    """Parties coding jobs for an extension run: every cell paper of its confirmation (data/cell-parties-items-{tag}.jsonl),
    cut into blind batches r2-parties-{tag}-01.. of at most `size`, plus a seeded second-coder slice r2-parties-{tag}-dup."""
    import math
    items, _, part, claude = load_ext(tag)
    assert all(i in claude for i in part), f"{tag}: stage-2 coding incomplete"
    cell = sorted(i for i in claude if MEASURES["several"](claude[i]))
    random.Random(20261107).shuffle(cell)
    rec = lambda i: {"id": i, "title": items[i]["title"].strip(), "abstract": items[i]["abstract"]}
    with open(f"data/cell-parties-items-{tag}.jsonl", "w") as f:
        f.writelines(json.dumps(rec(i), ensure_ascii=False) + "\n" for i in cell)
    k = math.ceil(len(cell) / size)
    step = math.ceil(len(cell) / k)
    batches = {f"r2-parties-{tag}-{n + 1:02d}": cell[n * step:(n + 1) * step] for n in range(k)}
    batches[f"r2-parties-{tag}-dup"] = random.Random(20261110).sample(cell, round(dup_share * len(cell)))
    with open(f"data/batches/r2-parties-{tag}-briefs.jsonl", "w") as f:
        for name, ids in batches.items():
            json.dump([rec(i) for i in ids], open(f"data/batches/{name}.json", "w"), indent=0, ensure_ascii=False)
            f.write(json.dumps({"batch": name, "n": len(ids), "brief": parties_brief(name)}) + "\n")
    print(f"{tag}: cell papers {len(cell)}; batches", {n: len(v) for n, v in batches.items()})


def parties_ext(tag="ext", parties=None):
    """The extension cell split by parties, per population of the run (direct counts where the venue is confirmed in full)."""
    parties = load_parties(f"data/coded/r2-parties-{tag}-0*.jsonl") if parties is None else parties
    pm = parties_measures(parties)
    t = table(pm, EXT_POPS[tag], load_ext(tag))
    return {k: {m: v[m] for m in pm} for k, v in t.items() if k in EXT_POPS[tag] and v.get("n")}


def new_cell(claude, have, cell=POLICY_MEASURES["several"]):
    """Papers in the policy several-owner cell (v1 by default; the v2 pass passes POLICY2_MEASURES["several"]) that no parties
    coder has coded."""
    return sorted(i for i, r in claude.items() if cell(r) and i not in have)


POLICY_POPS = {"full": POPS, "ext": POPS_EXT, "ext-ea": POPS_EA}


def parties_batches(cell, tag, size=100, dup_share=0.2, seeds=(20261111, 20261112)):
    """{batch name: ids}: the cell papers shuffled (seeds[0]) and cut into blind batches r2-parties-{tag}-NN of at most `size`,
    plus a second-coder draw r2-parties-{tag}-dup of dup_share of them (seeds[1]). An empty cell gives no batch."""
    import math
    if not cell:
        return {}
    cell = list(cell)
    random.Random(seeds[0]).shuffle(cell)
    k = math.ceil(len(cell) / size)
    step = math.ceil(len(cell) / k)
    batches = {f"r2-parties-{tag}-{n + 1:02d}": cell[n * step:(n + 1) * step] for n in range(k)}
    batches[f"r2-parties-{tag}-dup"] = random.Random(seeds[1]).sample(cell, round(dup_share * len(cell)))
    return batches


def jobs_policy(size=100, dup_share=0.2, tag="policy", load=load_policy, ready=policy_ready, cell=POLICY_MEASURES["several"],
                have="data/coded/r2-parties-[0e]*[0-9].jsonl", seeds=(20261111, 20261112)):
    """Parties jobs for the policy cell: every cell paper of the three frames without a primary parties code (glob `have`), in
    blind batches r2-parties-{tag}-NN of at most `size` plus a seeded second-coder slice r2-parties-{tag}-dup, with the recorded
    parties brief per batch in data/batches/r2-parties-{tag}-briefs.jsonl. Defaults: the v1 pass; jobs_policy2 is the v2 pass."""
    assert all(ready(t) for t in POLICY_POPS), f"{tag} stage 2 incomplete"
    have = set(load_parties(have))
    items, ids = {}, []
    for t in POLICY_POPS:
        it, _, part, claude = load(t)
        items.update(it)
        ids += new_cell({i: {"id": i, **claude[i]} for i in part}, have, cell)
    rec = lambda i: {"id": i, "title": items[i]["title"].strip(), "abstract": items[i]["abstract"]}
    batches = parties_batches(ids, tag, size, dup_share, seeds)
    with open(f"data/batches/r2-parties-{tag}-briefs.jsonl", "w") as f:
        for name, b in batches.items():
            json.dump([rec(i) for i in b], open(f"data/batches/{name}.json", "w"), indent=0, ensure_ascii=False)
            f.write(json.dumps({"batch": name, "n": len(b), "brief": parties_brief(name)}) + "\n")
    print(f"{tag}: new cell papers {len(ids)}; batches", {n: len(v) for n, v in batches.items()})


PRIMARY_PARTIES = "data/coded/r2-parties-[0ep]*[0-9].jsonl"  # every primary parties code (main, ext, ext-ea, policy, policy2)
POLICY2_PARTIES = "data/estimates-round2-policy2.json"  # written by `round2.py policy2` once every v2 cell paper has a parties code


def jobs_policy2(size=100, dup_share=0.2):
    """Parties jobs for the v2 several cell (codebook-policy-v2.2.md): cell papers of the three frames without a primary parties
    code, in batches r2-parties-policy2-NN and r2-parties-policy2-dup (20%, seeded)."""
    jobs_policy(size, dup_share, "policy2", load_policy2, policy2_ready, POLICY2_MEASURES["several"], PRIMARY_PARTIES, (20261113, 20261114))


POLICY_EXTRA = {
    "aligned": lambda r: POLICY_MEASURES["several"](r) and r.get("interests") == "several-aligned",
    "adversarial": lambda r: r.get("policy_setters") == "several" and r.get("principals") == "several" and r.get("interests") == "adversarial",
    "adversarial_incl": lambda r: r.get("policy_setters") == "several" and r.get("principals") == "several",
    "simulated_xvendor": lambda r: POLICY_MEASURES["simulated"](r) and r.get("cross_vendor") == "yes",
}
POLICY_ALL = {**POLICY_MEASURES, **POLICY_EXTRA}
COMPARED = ("policy_setters", "principals", "partners_from_others")


def coder_agreement(v34, add, dup):
    """Agreement of the two confirming coders on the policy pass (policy-add against policy-dup, by id): each policy field, and the
    several and simulated cells with the paper's v3.4 INTERESTS and FOCUS joined in. Rows (name, agree, n, kappa)."""
    from census import kappa
    ids = sorted(i for i in dup if i in add)
    rows = []
    for k in COMPARED:
        a, b = [add[i][k] for i in ids], [dup[i][k] for i in ids]
        rows.append((k, sum(x == y for x, y in zip(a, b)), len(ids), kappa(a, b)))
    for m in ("several", "simulated"):
        f = POLICY_MEASURES[m]
        a, b = [f({**v34.get(i, {}), **add[i]}) for i in ids], [f({**v34.get(i, {}), **dup[i]}) for i in ids]
        rows.append((m, sum(x == y for x, y in zip(a, b)), len(ids), kappa(a, b)))
    return rows


def screen_agreement(screen, claude, fields=COMPARED):
    """The first stage's policy codes against the confirming coder's, on every paper both coded. Rows (field, agree, n, kappa)."""
    from census import kappa
    ids = sorted(i for i in claude if "policy_setters" in claude[i] and "policy_setters" in screen.get(i, {}))
    out = []
    for k in fields:
        a, b = [screen[i][k] for i in ids], [claude[i][k] for i in ids]
        out.append((k, sum(x == y for x, y in zip(a, b)), len(ids), kappa(a, b)))
    return out


def main_policy(reps=2000):
    """data/estimates-round2-policy.json: the policy cell split by parties per population (keys full, ext, ext-ea), from every
    primary parties code; and, for the main census, the round-2 analyses of the v3.4 file on the policy cells: table (with the
    interests split), contrasts, cross_vendor, sector, parties agreement on the cell (every second parties coder), the second
    confirming coder's agreement (coder_agreement), and n_cell (cell papers of the three frames, all with a parties code)."""
    import glob
    parties = load_parties("data/coded/r2-parties-[0ep]*[0-9].jsonl")
    pm = parties_measures(parties, POLICY_MEASURES["several"])
    out, cell = {}, set()
    for tag, pops in POLICY_POPS.items():
        data = load_policy(tag)
        t = table(pm, pops, data)
        out[tag] = {k: {m: v[m] for m in pm} for k, v in t.items() if k in pops and v.get("n")}
        cell |= {i for i in data[2] if POLICY_MEASURES["several"](data[3][i])}
    data = load_policy("full")
    t = table(POLICY_ALL, POPS, data)
    pops = {k: v for k, v in POPS.items() if k != "ec-2025"}
    core = {m: POLICY_ALL[m] for m in ("several", "interaction", "conflicting", "simulated")}
    rp = {meth: replicates(pops, core, meth, reps=reps, data=data) for meth in ("bootstrap", "jeffreys", "papers", "papers-jeffreys")}
    out["table"] = t
    out["contrasts"] = contrasts(t, rp)
    sim_screen = lambda s: s.get("policy_setters") == "one" and s.get("principals") == "several" and s["interests"] != "adversarial"
    out["cross_vendor"] = cross_vendor(data, POLICY_MEASURES, sim_screen)
    out["sector"] = sector_comparison(reps, data, POLICY_MEASURES["several"])
    second = load_parties("data/coded/r2-parties-*dup.jsonl")
    ids = sorted(i for i in second if i in cell)
    from census import kappa
    x, y = [parties[i] for i in ids], [second[i] for i in ids]
    bx, by = [v == "ai-agents" for v in x], [v == "ai-agents" for v in y]
    out["parties_agreement"] = {"n": len(ids), "agree": sum(u == v for u, v in zip(x, y)), "kappa": kappa(x, y), "agree_ai": sum(u == v for u, v in zip(bx, by)), "kappa_ai": kappa(bx, by)}
    out["parties_agreement_policy_dup"] = parties_agreement("data/coded/r2-parties-[0ep]*[0-9].jsonl", "data/coded/r2-parties-policy-dup.jsonl")
    v34 = {}
    for tag in POLICY_POPS:
        v34.update(load_policy(tag)[3])
    rows = coder_agreement(v34, load_codes("data/coded/policy-add-*.jsonl"), load_codes("data/coded/policy-dup-*.jsonl"))
    out["coder_agreement"] = {k: {"agree": a, "n": n, "kappa": kp} for k, a, n, kp in rows}
    _, s_, p_, c_ = data  # the main census, as the v3.4 rows of Table S6
    out["screen_agreement"] = {k: {"agree": a, "n": n, "kappa": kp} for k, a, n, kp in screen_agreement(s_, {i: c_[i] for i in p_})}
    out["n_cell"] = len(cell)
    out["n_confirm"] = len(p_)  # main-census papers the confirming coder coded that enter the estimates (confirmed set and slices)
    # the first stage's several cell, all confirmed: how many the confirming coder kept, for agent and other papers
    sev_screen = lambda x: x.get("policy_setters") == "several" and x.get("principals") == "several" and x["interests"] != "adversarial"
    out["screen_precision"] = {g: {"screened": sum(1 for i in p_ if sev_screen(s_[i]) and (s_[i]["agent"] == "yes") == (g == "agent")),
                                   "confirmed_several": sum(1 for i in p_ if sev_screen(s_[i]) and (s_[i]["agent"] == "yes") == (g == "agent") and POLICY_MEASURES["several"](c_[i]))}
                               for g in ("agent", "other")}
    assert all(i in parties for i in cell), "a policy cell paper has no parties code"
    json.dump(out, open("data/estimates-round2-policy.json", "w"), indent=1)
    for tag in POLICY_POPS:
        for k, m in out[tag].items():
            print(tag, k, "  ".join(f"{c} {x['confirmed']} {100 * x['share']:.1f} [{100 * x['lo']:.1f}, {100 * x['hi']:.1f}]" for c, x in m.items()))


def main_composition():
    """data/estimates-cell-composition.json: the 2025 main-track policy cell by PARTIES (as main_policy) and, within PARTIES other,
    the papers whose v3.4 DATA code (confirmer) is partitioned (several owners hold data they do not pool, such as federated or
    cross-silo clients), with the two-stage estimator."""
    pm = parties_measures(load_parties("data/coded/r2-parties-[0ep]*[0-9].jsonl"), POLICY_MEASURES["several"])
    pm["parties_other_partitioned"] = lambda r: pm["parties_other"](r) and r.get("data") == "partitioned"
    pops = {"all-2025": POPS["all-2025"]}
    t = table(pm, pops, load_policy("full"))
    out = {k: {m: t[k][m] for m in pm} for k in pops}
    json.dump(out, open("data/estimates-cell-composition.json", "w"), indent=1)
    print(out)


def main_ext():
    """data/estimates-round2-ext.json: the parties split and coder agreement for each extension run whose codes are in."""
    import glob
    out = {}
    for tag in EXT_POPS:
        if glob.glob(f"data/coded/r2-parties-{tag}-0*.jsonl"):
            out[tag] = {"parties": parties_ext(tag)}
            if glob.glob(f"data/coded/r2-parties-{tag}-dup.jsonl"):
                out[tag]["parties_agreement"] = parties_agreement(f"data/coded/r2-parties-{tag}-0*.jsonl", f"data/coded/r2-parties-{tag}-dup.jsonl")
    json.dump(out, open("data/estimates-round2-ext.json", "w"), indent=1)
    for tag, v in out.items():
        for k, m in v["parties"].items():
            print(tag, k, "  ".join(f"{c} {x['confirmed']} {100 * x['share']:.1f} [{100 * x['lo']:.1f}, {100 * x['hi']:.1f}]" for c, x in m.items()))
        print(tag, v.get("parties_agreement", "no second coder yet"))


# ---- the v2 pass (codebook-policy-v2.2.md) ----
_ss = lambda r: r.get("policy_setters") == "several" and r.get("principals") == "several"
POLICY2_EXTRA = {
    "aligned": lambda r: POLICY2_MEASURES["several"](r) and not POLICY2_MEASURES["conflicting"](r),  # several minus conflicting
    "adversarial": lambda r: _ss(r) and r.get("outside_attacker") == "yes",  # the exclusion (codebook v2)
    "adversarial_incl": _ss,
    "simulated_xvendor": lambda r: POLICY2_MEASURES["simulated"](r) and r.get("cross_vendor") == "yes",
}
POLICY2_ALL = {**POLICY2_MEASURES, **POLICY2_EXTRA}
V2_COMPARED = ("policy_setters", "principals", "behaviour", "rule_breaking", "interacting", "outside_attacker", "partners_from_others")


def coder_agreement_v2(v34, add, dup):
    """The two v2 confirming coders (policy2-add against policy2-dup, by id): each v2 field, the derived cell of the pilot
    (pilot_agreement.cell: several within the rules, several rule-breaking, several other, simulated, single learner, excluded
    by attacker, rest), and the several and simulated cells with the paper's v3.4 codes joined in. Rows (name, agree, n, kappa)."""
    from census import kappa
    from pilot_agreement import cell
    ids = sorted(i for i in dup if i in add)
    rows = []
    for name, f in [(k, (lambda k: lambda r: r[k])(k)) for k in V2_COMPARED] + [("cell", cell), ("several", POLICY2_MEASURES["several"]), ("simulated", POLICY2_MEASURES["simulated"])]:
        a, b = [f({**v34.get(i, {}), **add[i]}) for i in ids], [f({**v34.get(i, {}), **dup[i]}) for i in ids]
        rows.append((name, sum(x == y for x, y in zip(a, b)), len(ids), kappa(a, b)))
    return rows


def screen_several2(s):
    return s.get("policy_setters") == "several" and s.get("principals") == "several" and s.get("outside_attacker") == "no"


def main_policy2_core(reps=2000):
    """data/estimates-round2-policy2-core.json: the round-2 analyses that need no parties code, on the v2 cells of the main census:
    table (POLICY2_ALL, with the interests split and the outside-attacker rows), contrasts, cross_vendor, sector, the second
    confirming coder's agreement (coder_agreement_v2 on every policy2-dup paper), the first stage's v2 codes against the
    confirmer's (screen_agreement), n_confirm and the first stage's several-cell precision."""
    data = load_policy2("full")
    t = table(POLICY2_ALL, POPS, data)
    pops = {k: v for k, v in POPS.items() if k != "ec-2025"}
    core = {m: POLICY2_ALL[m] for m in ("several", "interaction", "conflicting", "simulated")}
    rp = {meth: replicates(pops, core, meth, reps=reps, data=data) for meth in ("bootstrap", "jeffreys", "papers", "papers-jeffreys")}
    out = {"table": t, "contrasts": contrasts(t, rp)}
    sim_screen = lambda s: s.get("policy_setters") == "one" and s.get("principals") == "several" and s.get("interacting") == "yes" and s.get("outside_attacker") == "no"
    out["cross_vendor"] = cross_vendor(data, POLICY2_MEASURES, sim_screen)
    out["sector"] = sector_comparison(reps, data, POLICY2_MEASURES["several"])
    v34 = {}
    for tag in POLICY_POPS:
        v34.update(load_policy2(tag)[3])
    rows = coder_agreement_v2(v34, load_codes("data/coded/policy2-add-*.jsonl"), load_codes("data/coded/policy2-dup-*.jsonl"))
    out["coder_agreement"] = {k: {"agree": a, "n": n, "kappa": kp} for k, a, n, kp in rows}
    _, s_, p_, c_ = data
    out["screen_agreement"] = {k: {"agree": a, "n": n, "kappa": kp} for k, a, n, kp in screen_agreement(s_, {i: c_[i] for i in p_}, V2_COMPARED)}
    out["n_confirm"] = len(p_)
    out["screen_precision"] = {g: {"screened": sum(1 for i in p_ if screen_several2(s_[i]) and (s_[i]["agent"] == "yes") == (g == "agent")),
                                   "confirmed_several": sum(1 for i in p_ if screen_several2(s_[i]) and (s_[i]["agent"] == "yes") == (g == "agent") and POLICY2_MEASURES["several"](c_[i]))}
                               for g in ("agent", "other")}
    json.dump(out, open("data/estimates-round2-policy2-core.json", "w"), indent=1)
    r_ = lambda b: round(b, 2) if isinstance(b, float) else tuple(round(x, 2) for x in b)
    for k, v in out["contrasts"].items():
        print(k, {a: r_(b) for a, b in v.items()})
    print(out["coder_agreement"], out["screen_precision"], out["n_confirm"])


def main_policy2():
    """data/estimates-round2-policy2.json, once every v2 cell paper of the three frames has a primary parties code: the v2 cell
    split by parties per population (keys full, ext, ext-ea), its composition (PARTIES other with v3.4 DATA partitioned, 2025
    main track), parties agreement on the cell (every second parties coder) and on the policy2 dup batch, and n_cell."""
    from census import kappa
    sev = POLICY2_MEASURES["several"]
    parties = load_parties(PRIMARY_PARTIES)
    datas = {tag: load_policy2(tag) for tag in POLICY_POPS}
    cell = {i for d in datas.values() for i in d[2] if sev(d[3][i])}
    missing = sorted(cell - set(parties))
    assert not missing, f"{len(missing)} v2 cell papers have no parties code (round2.py jobs-policy2), e.g. {missing[:5]}"
    pm = parties_measures(parties, sev)
    out = {}
    for tag, pops in POLICY_POPS.items():
        t = table(pm, pops, datas[tag])
        out[tag] = {k: {m: v[m] for m in pm} for k, v in t.items() if k in pops and v.get("n")}
    pc = {**pm, "parties_other_partitioned": lambda r: pm["parties_other"](r) and r.get("data") == "partitioned"}
    t = table(pc, {"all-2025": POPS["all-2025"]}, datas["full"])
    out["composition"] = {"all-2025": {m: t["all-2025"][m] for m in pc}}
    second = load_parties("data/coded/r2-parties-*dup.jsonl")
    ids = sorted(i for i in second if i in cell)
    x, y = [parties[i] for i in ids], [second[i] for i in ids]
    bx, by = [v == "ai-agents" for v in x], [v == "ai-agents" for v in y]
    out["parties_agreement"] = {"n": len(ids), "agree": sum(u == v for u, v in zip(x, y)), "kappa": kappa(x, y), "agree_ai": sum(u == v for u, v in zip(bx, by)), "kappa_ai": kappa(bx, by)}
    out["parties_agreement_policy2_dup"] = parties_agreement(PRIMARY_PARTIES, "data/coded/r2-parties-policy2-dup.jsonl")
    out["n_cell"] = len(cell)
    json.dump(out, open(POLICY2_PARTIES, "w"), indent=1)
    for tag in POLICY_POPS:
        for k, m in out[tag].items():
            print(tag, k, "  ".join(f"{c} {x['confirmed']} {100 * x['share']:.1f} [{100 * x['lo']:.1f}, {100 * x['hi']:.1f}]" for c, x in m.items()))


if __name__ == "__main__" and sys.argv[1:] == ["jobs-policy2"]:
    jobs_policy2()
elif __name__ == "__main__" and sys.argv[1:] == ["policy2-core"]:
    main_policy2_core()
elif __name__ == "__main__" and sys.argv[1:] == ["policy2"]:
    main_policy2()
elif __name__ == "__main__" and sys.argv[1:] == ["jobs"]:
    jobs()
elif __name__ == "__main__" and sys.argv[1:2] == ["jobs-ext"]:
    for tag in sys.argv[2:] or ["ext", "ext-ea"]:
        jobs_ext(tag)
elif __name__ == "__main__" and sys.argv[1:] == ["jobs-policy"]:
    jobs_policy()
elif __name__ == "__main__" and sys.argv[1:] == ["policy"]:
    main_policy()
elif __name__ == "__main__" and sys.argv[1:] == ["composition"]:
    main_composition()
elif __name__ == "__main__" and sys.argv[1:] == ["ext"]:
    main_ext()
elif __name__ == "__main__":
    pops = {k: v for k, v in POPS.items() if k != "ec-2025"}
    t = table(ALL)
    core = {m: ALL[m] for m in ("several", "interaction", "conflicting", "simulated")}
    reps = {meth: replicates(pops, core, meth) for meth in ("bootstrap", "jeffreys", "papers", "papers-jeffreys")}
    pm = parties_measures(load_parties())
    tp = table(pm)
    res = {"table": t, "contrasts": contrasts(t, reps), "cross_vendor": cross_vendor(), "sector": sector_comparison(),
           "parties": {k: {m: v[m] for m in pm} for k, v in tp.items() if k in POPS}, "parties_agreement": parties_agreement()}
    json.dump(res, open("data/estimates-round2.json", "w"), indent=1)
    r_ = lambda b: round(b, 2) if isinstance(b, float) else tuple(round(x, 2) for x in b)
    for k, v in res["contrasts"].items():
        print(k, {a: r_(b) for a, b in v.items()})
    print(res["cross_vendor"])
    for k, v in res["sector"].items():
        if not isinstance(v, dict):
            print(k, v)
            continue
        print(k, v["industry"]["n"], f"{100 * v['industry']['share']:.1f}", v["academic"]["n"], f"{100 * v['academic']['share']:.1f}", f"diff {v['diff']:.1f}", r_(v["bootstrap"]), r_(v["conservative"]))
    for p in pops:
        print(p, "  ".join(f"{m} {100 * t[p][m]['share']:.1f} [{100 * t[p][m]['lo']:.1f}, {100 * t[p][m]['hi']:.1f}]" for m in ALL))
