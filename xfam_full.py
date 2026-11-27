"""Full-frame screen (Gemma-4-31B, codebook v3.4): distributions by venue-year and track, and the stage-2 confirmation set.

  python3 xfam_full.py data/xfam/full-v34/results-parsed.jsonl
-> prints the distributions; writes data/xfam/stage2-confirm.json (venue and main_track are for analysis only, never shown to coders).

  python3 xfam_full.py ext data/xfam/ext-v34/results-parsed.jsonl
-> the same for the ICLR 2025 / AAMAS 2025 extension (items-ext.jsonl): writes data/xfam/stage2-ext.json and the blind
confirmation batches data/batches/ext-confirm-NN.json with their briefs (data/batches/ext-confirm-briefs.jsonl).

  python3 xfam_full.py ext-ea data/xfam/ext-ea-v34/results-parsed.jsonl
-> the AAMAS EA + Blue Sky sensitivity (items-ext-ea.jsonl): stage2-ext-ea.json and batches ext-ea-confirm-NN.
"""
import json
import random
import sys
from collections import Counter

FIELDS = ("interests", "owners_derived", "faces_other_parties", "faces_quote", "one_party_runs_all", "eval_run", "focus_derived", "agent", "llm_basis")
SEVERAL = ("several-aligned", "several-conflicting")
SEED = 20261107
EXT_SEED, BATCH_SEED, BATCH = 20261109, 80, 70
# screen-negatives drawn per stratum (venue x agent x LLM basis), whole strata when smaller
QUOTA = {"agent-llm": 150, "agent": 150, "other": 300}
FULL_VENUE = 500  # a venue this small is confirmed in full (a direct count, as EC was), so its thin strata never pool with another venue's
# The brief used for confirm-e* and confirm-fg* (coding/briefs.jsonl, recovered from the session record); BASE is replaced by the repo path at dispatch.
BRIEF = 'You are a careful research coder. Do the work yourself: spawn no agents, run nothing in the background, write no scripts that call other models, and use no keyword rules or scripts to assign codes. If you use a helper script only to serialize your hand-assigned codes, keep it in a private directory /private/tmp/conf-{t}/ (other coders work in parallel).\n\nBASE = "BASE"\nRead BASE/codebook-v3.md (v3.4) in full and the papers in BASE/data/batches/{b}.json. Open no other file under BASE.\n\nRead every abstract to its very end yourself; if a line looks cut in your file view, re-read that part until you have the whole abstract. Code every paper exactly as the codebook says, answering its decision questions (has_decision_maker, faces_other_parties, one_party_runs_all) before OWNERS. Write JSON Lines, one object per paper for ALL papers, in input order, to BASE/data/coded/{b}.jsonl, with exactly the keys listed in the codebook\'s Output line ("faces_quote" and "quote" verbatim from the abstract, or empty). Write no other files under BASE.\n\nFinal text: lines written vs papers in input, counts of owners and interests values, and papers you coded with low confidence (id and reason).'


# Policy pass (codebook-policy.md). The addendum brief follows the recorded confirm brief (BRIEF) with the policy codebook in
# place of v3.4; a paper the v3.4 confirmer never coded gets its v3.4 code from BRIEF itself in a separate batch, so every
# policy code comes from the same instrument with no v3.4 text in view.
ADD_BRIEF = 'You are a careful research coder. Do the work yourself: spawn no agents, run nothing in the background, write no scripts that call other models, and use no keyword rules or scripts to assign codes. If you use a helper script only to serialize your hand-assigned codes, keep it in a private directory /private/tmp/{b}/ (other coders work in parallel).\n\nBASE = "BASE"\nRead BASE/codebook-policy.md (v1) in full and the papers in BASE/data/batches/{b}.json. Open no other file under BASE.\n\nRead every abstract to its very end yourself; if a line looks cut in your file view, re-read that part until you have the whole abstract. Code every paper exactly as the codebook says, answering POLICY_SETTERS before PRINCIPALS. Write JSON Lines, one object per paper for ALL papers, in input order, to BASE/data/coded/{b}.jsonl, with exactly the keys listed in the codebook\'s Output line ("policy_quote" and "principals_quote" verbatim from the title or abstract, or empty). Write no other files under BASE.\n\nFinal text: lines written vs papers in input, counts of policy_setters and principals values, and papers you coded with low confidence (id and reason).'
POLICY_SEED, POLICY_BATCH_SEEDS = 20261110, {"policy-add": 90, "policy-v34": 91, "policy-dup": 92, "policy2-add": 93, "policy2-v34": 94, "policy2-dup": 95}
# Policy pass v2 (codebook-policy-v2.2.md). The addendum and second-coder brief is the
# pilot3 brief (data/batches/pilot3-briefs.jsonl, test-checked) with the batch name as the parameter; v34 batches use BRIEF.
ADD2_BRIEF = 'You are a careful research coder. Do the work yourself: spawn no agents, run nothing in the background, write no scripts that call other models, and use no keyword rules or scripts to assign codes. If you use a helper script only to serialize your hand-assigned codes, keep it in a private directory /private/tmp/{b}/ (other coders work in parallel).\n\nBASE = "BASE"\nRead BASE/codebook-policy-v2.2.md in full and the papers in BASE/data/batches/{b}.json. Open no other file under BASE.\n\nRead every abstract to its very end yourself; if a line looks cut in your file view, re-read that part until you have the whole abstract. Code every paper exactly as the codebook says. Write JSON Lines, one object per paper for ALL papers, in input order, to BASE/data/coded/{b}.jsonl, with exactly the keys listed in the codebook\'s Output line (each quote verbatim from the title or abstract, or empty). Write no other files under BASE.\n\nFinal text: lines written vs papers in input, counts per field value, and papers you coded with low confidence (id and reason).'
POLICY2_SEED = 20261111
NON_MAIN_2025 = lambda x: x["venue"] in ("neurips-2025", "icml-2025") and not x["main_track"]


def stage2_policy(items, coded, s34, sp, dup_share=0.1, dup_venue_n=70, seed=POLICY_SEED):
    """add: the policy addendum on every paper the v3.4 confirmer coded plus every uncoded paper the policy screen codes
    POLICY_SETTERS or PRINCIPALS several or failed to code, and every uncoded v3.4 owners-na paper (both kinds also in v34: the recorded v3.4
    brief, never coded twice); 2025 papers outside the main track enter no estimate and are not drawn. dup: a second coder
    on the addendum, dup_venue_n each from EC and AAMAS (direct counts) and a seeded dup_share of the rest."""
    new = sorted(i for i, x in items.items() if i not in coded and not NON_MAIN_2025(x)
                 and (i not in sp or "several" in (sp[i]["policy_setters"], sp[i]["principals"]) or s34[i]["owners_derived"] == "na"))
    add = sorted(coded) + new
    rng = random.Random(seed)
    venue = lambda v: [i for i in add if items[i]["venue"] == v]
    rest = [i for i in add if items[i]["venue"] not in ("ec-2025", "aamas-2025")]
    dup = sorted(rng.sample(venue("ec-2025"), min(dup_venue_n, len(venue("ec-2025")))) + rng.sample(venue("aamas-2025"), min(dup_venue_n, len(venue("aamas-2025"))))
                 + rng.sample(rest, round(dup_share * len(rest))))
    return {"add": add, "v34": new, "dup": dup}


def policy_batches(prefix, ids, items, seed=None, size=BATCH):
    """Blind batches (id, title, abstract), shuffled, named prefix-NN."""
    ids = list(ids)
    random.Random(POLICY_BATCH_SEEDS[prefix] if seed is None else seed).shuffle(ids)
    return [(f"{prefix}-{n:02d}", [{"id": i, "title": items[i]["title"], "abstract": items[i]["abstract"]} for i in ids[b:b + size]])
            for n, b in enumerate(range(0, len(ids), size))]


def policy_brief(batch):
    if batch.startswith(("policy-v34-", "policy2-v34-")):
        return BRIEF.format(b=batch, t=batch)
    return (ADD2_BRIEF if batch.startswith("policy2-") else ADD_BRIEF).format(b=batch)


def stage2_policy2(items, coded, s34, sp, slices, disputed, dup_share=0.1, dup_venue_n=70, seed=POLICY2_SEED):
    """The v2 stage-2 draw. coded: every paper a confirmer has coded so far (the v1 addendum, data/coded/policy-add-*, which
    holds every v3.4-coded paper, slices included); sp: the v2 screen's parsed records (a paper missing from it failed to parse).
    add: coded, plus every other paper that is v2 screen-positive or failed to parse or is v3.4 owners-na. The positive rule
    (twostage.policy2_positive): POLICY_SETTERS several, or PRINCIPALS several, or RULE_BREAKING yes, or INTERACTING yes.
    2025 papers outside the main track enter no population and are never added.
    v34: the added papers outside coded, for their v3.4 code under the recorded confirm brief.
    dup: a second coder on add: a seeded dup_venue_n from EC and from AAMAS and a seeded dup_share of the rest (as v1), plus
    every slice paper (old parts c, d, f, g) and every pilot-disputed paper in add, both within the populations; the slice
    papers of a venue whose every paper is coded (EC, AAMAS, AAMAS EA: direct counts) weigh one, like any confirmed paper, and
    are left to the seeded draw."""
    from twostage import policy2_positive
    new = sorted(i for i, x in items.items() if i not in coded and not NON_MAIN_2025(x)
                 and (policy2_positive(sp.get(i)) or s34[i]["owners_derived"] == "na"))
    add = sorted(coded) + new
    rng = random.Random(seed)
    venue = lambda v: [i for i in add if items[i]["venue"] == v]
    rest = [i for i in add if items[i]["venue"] not in ("ec-2025", "aamas-2025")]
    drawn = rng.sample(venue("ec-2025"), min(dup_venue_n, len(venue("ec-2025")))) + rng.sample(venue("aamas-2025"), min(dup_venue_n, len(venue("aamas-2025")))) \
        + rng.sample(rest, round(dup_share * len(rest)))
    census = {x["venue"] for x in items.values()} - {x["venue"] for i, x in items.items() if i not in coded}
    inpop = set(add) - {i for i in add if NON_MAIN_2025(items[i])}
    forced = {i for i in slices if items[i]["venue"] not in census} | set(disputed)
    return {"add": add, "v34": new, "dup": sorted(set(drawn) | forced & inpop)}


def main_policy2(path="data/xfam/policy-v2/results-parsed.jsonl"):
    """Writes data/xfam/stage2-policy2.json, data/batches/policy2-{add,v34,dup}-NN.json and data/batches/policy2-briefs.jsonl;
    refuses a v2 screen that does not account for every item of the three frames (parsed or failed)."""
    import twostage
    items, s34, slices, claude = {}, {}, set(), set()
    for tag in ("full", "ext", "ext-ea"):
        it, sc, part, cl = twostage.load() if tag == "full" else twostage.load_ext(tag)
        items.update(it), s34.update(sc), claude.update(cl)
        slices |= {i for i, p in part.items() if p in "cd"}
    sp = {r["id"]: r for r in map(json.loads, open(path))}
    fails = [json.loads(l)["call_id"] for l in open(path.replace("results-parsed", "failures"))]
    assert sorted([*sp, *fails]) == sorted(items), "the v2 screen must account for every item of the three frames"
    coded = set(twostage.load_codes("data/coded/policy-add-*.jsonl"))
    assert coded and coded <= claude | set(twostage.load_codes("data/coded/policy-v34-*.jsonl")), "every coded paper has a v3.4 code"
    disputed = [x["id"] for x in json.load(open("data/pilot/pilot-ids.json"))["disputed"]]
    d = stage2_policy2(items, coded, s34, sp, slices, disputed)
    json.dump(d, open("data/xfam/stage2-policy2.json", "w"), indent=0)
    n = {}
    with open("data/batches/policy2-briefs.jsonl", "w") as f:
        for prefix, key in (("policy2-add", "add"), ("policy2-v34", "v34"), ("policy2-dup", "dup")):
            bs = policy_batches(prefix, d[key], items)
            n[prefix] = (len(bs), len(bs[-1][1]) if bs else 0)
            for name, b in bs:
                json.dump(b, open(f"data/batches/{name}.json", "w"), indent=0)
                f.write(json.dumps({"batch": name, "n": len(b), "brief": policy_brief(name)}) + "\n")
    dup = set(d["dup"])
    print({k: len(v) for k, v in d.items()}, "batches (count, last size)", n)
    print("v34 by venue", dict(Counter(items[i]["venue"] for i in d["v34"])), "fails", len(fails))
    print("dup: slices", len(dup & slices), "disputed", len(dup & set(disputed)), "by venue", dict(Counter(items[i]["venue"] for i in dup)))
    v1 = {r["id"]: r for r in map(json.loads, open(twostage.POLICY_RUN))}
    for tag in ("full", "ext", "ext-ea"):
        it, sc, part, _ = twostage.load() if tag == "full" else twostage.load_ext(tag)
        print("estimator parts", tag, dict(sorted(Counter(twostage.policy2_parts(part, it, sc, v1, sp).values()).items())))


def validate_policy2_outputs(briefs="data/batches/policy2-briefs.jsonl"):
    """Every batch in briefs whose output data/coded/<batch>.jsonl exists: one record per paper in input order, exactly V2_KEYS
    (add, dup) or the v3.4 KEYS (v34) in order, every value in V2_ENUMS or ENUMS (AssertionError naming the batch otherwise).
    Returns the count of valid outputs, the batches with no output yet, and the (batch, id) of v2 records whose three quotes
    (QUOTES_V2) are not all verbatim in title plus abstract."""
    import os
    from xfam_inputs import ENUMS, KEYS, QUOTES_V2, V2_ENUMS, V2_KEYS, policy_items, quotes_verbatim
    items = {x["xid"]: x for x in policy_items()}
    out = {"valid": 0, "missing": [], "nonverbatim": []}
    for l in open(briefs):
        b = json.loads(l)["batch"]
        if not os.path.exists(f"data/coded/{b}.jsonl"):
            out["missing"].append(b)
            continue
        want = [x["id"] for x in json.load(open(f"data/batches/{b}.json"))]
        rows = [json.loads(x) for x in open(f"data/coded/{b}.jsonl") if x.strip()]
        v34 = b.startswith("policy2-v34-")
        keys, enums = (KEYS, ENUMS) if v34 else (V2_KEYS, V2_ENUMS)
        assert [r["id"] for r in rows] == want, f"{b}: ids or order differ from the batch"
        for r in rows:
            assert list(r) == keys and all(r[k] in v for k, v in enums.items()), f"{b} {r.get('id')}: keys or values"
        out["nonverbatim"] += [] if v34 else [(b, r["id"]) for r in rows if not quotes_verbatim(r, items[r["id"]], QUOTES_V2)]
        out["valid"] += 1
    return out


def main_policy(path="data/xfam/policy-v1/results-parsed.jsonl"):
    """Writes data/xfam/stage2-policy.json, data/batches/policy-{add,v34,dup}-NN.json and data/batches/policy-briefs.jsonl."""
    import twostage
    items, s34, coded = {}, {}, set()
    for tag in ("full", "ext", "ext-ea"):
        it, sc, part, claude = twostage.load() if tag == "full" else twostage.load_ext(tag)
        assert all(i in claude for i in part)
        items.update(it), s34.update(sc), coded.update(part)
    sp = {r["id"]: r for r in map(json.loads, open(path))}
    fails = [json.loads(l)["call_id"] for l in open(path.replace("results-parsed", "failures"))]
    assert sorted([*sp, *fails]) == sorted(items), "stage 1 must have run every item of the three frames"
    d = stage2_policy(items, coded, s34, sp)
    json.dump(d, open("data/xfam/stage2-policy.json", "w"), indent=0)
    with open("data/batches/policy-briefs.jsonl", "w") as f:
        for prefix, key in (("policy-add", "add"), ("policy-v34", "v34"), ("policy-dup", "dup")):
            for name, b in policy_batches(prefix, d[key], items):
                json.dump(b, open(f"data/batches/{name}.json", "w"), indent=0)
                f.write(json.dumps({"batch": name, "n": len(b), "brief": policy_brief(name)}) + "\n")
    print({k: len(v) for k, v in d.items()}, "new by venue", dict(Counter(items[i]["venue"] for i in d["v34"])))


def stage2(rows, items, seed=SEED, n_agent_one=300, n_other_one=200):
    """(a) every agent=yes, owners several, interests several-*; (b) every other owners several, interests several-*;
    (c) SRS of agent=yes, owners one; (d) SRS of agent=no, owners one."""
    multi = lambda r: r["owners_derived"] == "several" and r["interests"] in SEVERAL
    rng = random.Random(seed)
    parts = {"a": [r for r in rows if multi(r) and r["agent"] == "yes"], "b": [r for r in rows if multi(r) and r["agent"] != "yes"],
             "c": rng.sample([r for r in rows if r["agent"] == "yes" and r["owners_derived"] == "one"], n_agent_one),
             "d": rng.sample([r for r in rows if r["agent"] == "no" and r["owners_derived"] == "one"], n_other_one)}
    return [record(p, r, items) for p, rs in parts.items() for r in rs]


def record(part, r, items):
    return {"part": part, **{k: items[r["id"]][k] for k in ("xid", "sample_id", "venue", "main_track", "title", "abstract")}, **{k: r[k] for k in FIELDS}}


def stage2_ext(rows, items, seed=EXT_SEED, quota=QUOTA):
    """Every owners-several paper ((a) agent with interests several-*, (b) other with interests several-*, (e) the rest), and per
    venue simple random slices of the screen-negatives: (c) agent papers by LLM basis, (d) other papers (owners one or na)."""
    rows = sorted(rows, key=lambda r: r["id"])
    multi = lambda r: r["interests"] in SEVERAL
    out = [record("a" if multi(r) and r["agent"] == "yes" else "b" if multi(r) else "e", r, items) for r in rows if r["owners_derived"] == "several"]
    strata = {}
    for r in rows:
        if r["owners_derived"] != "several":
            q = "other" if r["agent"] != "yes" else "agent-llm" if r["llm_basis"] == "yes" else "agent"
            strata.setdefault((items[r["id"]]["venue"], q), []).append(r)
    size = Counter(x["venue"] for x in items.values())
    rng = random.Random(seed)
    for (v, q), rs in sorted(strata.items()):
        k = len(rs) if size[v] <= FULL_VENUE else min(quota[q], len(rs))
        out += [record("d" if q == "other" else "c", r, items) for r in rng.sample(rs, k)]
    return out


def confirm_batches(stage2, seed=BATCH_SEED, size=BATCH):
    """Blind batches of the stage-2 papers: id (the xid), title and abstract only, shuffled across parts and venues."""
    ids = [x["xid"] for x in stage2]
    random.Random(seed).shuffle(ids)
    by = {x["xid"]: x for x in stage2}
    return [[{"id": i, "title": by[i]["title"], "abstract": by[i]["abstract"]} for i in ids[b:b + size]] for b in range(0, len(ids), size)]


def confirm_brief(batch):
    """t names the coder's private directory: confirm-e00 -> e00 (as dispatched), ext-confirm-00 -> ext-00, ext-ea-confirm-00 -> ext-ea-00."""
    return BRIEF.format(b=batch, t=batch.replace("confirm-", ""))


def agreement_batch(stage2, venue, n=70, seed=81):
    """Second-coder batch for a venue confirmed in full (a direct count has no sampling interval, only coder error): a seeded
    random n of its papers, blind as the confirm batches, named outside the confirm-* glob so it never replaces a primary code."""
    ids = sorted(x["xid"] for x in stage2 if x["venue"] == venue)
    by = {x["xid"]: x for x in stage2}
    pick = random.Random(seed).sample(ids, n)
    return f"ext-dup-{venue.split('-')[0]}", [{"id": i, "title": by[i]["title"], "abstract": by[i]["abstract"]} for i in pick]


def main_ext(path, tag="ext"):
    """tag "ext": ICLR + AAMAS main papers; "ext-ea": the AAMAS EA + Blue Sky sensitivity, drawn and batched on its own so the
    headline draw and batches do not depend on it."""
    rows = [json.loads(l) for l in open(path)]
    items = {x["xid"]: x for x in map(json.loads, open(f"data/xfam/items-{tag}.jsonl"))}
    assert sorted(r["id"] for r in rows) == sorted(items), "stage 1 must have parsed every extension item"
    out = stage2_ext(rows, items)
    json.dump(out, open(f"data/xfam/stage2-{tag}.json", "w"), indent=0, ensure_ascii=False)
    with open(f"data/batches/{tag}-confirm-briefs.jsonl", "w") as f:
        for n, b in enumerate(confirm_batches(out)):
            name = f"{tag}-confirm-{n:02d}"
            json.dump(b, open(f"data/batches/{name}.json", "w"), indent=0)
            f.write(json.dumps({"batch": name, "n": len(b), "brief": confirm_brief(name)}) + "\n")
    if tag == "ext" and sum(x["venue"] == "aamas-2025" for x in out) >= 70:  # the AAMAS second coder, briefs kept apart from the confirm briefs
        name, b = agreement_batch(out, "aamas-2025")
        json.dump(b, open(f"data/batches/{name}.json", "w"), indent=0)
        open(f"data/batches/{name}-brief.jsonl", "w").write(json.dumps({"batch": name, "n": len(b), "brief": confirm_brief(name)}) + "\n")
    print("stage-2 parts:", dict(Counter((x["venue"], x["part"]) for x in out)), "total", len(out), "batches", n + 1)


def main(path):
    rows = [json.loads(l) for l in open(path)]
    items = {x["xid"]: x for x in map(json.loads, open("data/xfam/items-full.jsonl"))}
    for f in ("agent", "llm_basis", "owners_derived", "focus_derived", "eval_run"):
        print(f"\n## {f}")
        groups = Counter((items[r["id"]]["venue"], items[r["id"]]["main_track"]) for r in rows)
        for g in sorted(groups):
            c = Counter(r[f] for r in rows if (items[r["id"]]["venue"], items[r["id"]]["main_track"]) == g)
            print(f"{g[0]} {'main' if g[1] else 'other'} n={groups[g]}: " + ", ".join(f"{k} {v} ({100 * v / groups[g]:.1f}%)" for k, v in sorted(c.items())))
    out = stage2(rows, items)
    json.dump(out, open("data/xfam/stage2-confirm.json", "w"), indent=0, ensure_ascii=False)
    print("\nstage-2 parts:", dict(Counter(x["part"] for x in out)), "total", len(out))


if __name__ == "__main__":
    if sys.argv[1] == "policy":
        main_policy(*sys.argv[2:])
    elif sys.argv[1] == "policy2":  # policy2 [results-parsed.jsonl of the v2 screen]
        main_policy2(*sys.argv[2:])
    elif sys.argv[1] == "validate-policy2":
        v = validate_policy2_outputs()
        print(v["valid"], "outputs valid;", len(v["missing"]), "missing", v["missing"], "; non-verbatim v2 quotes:", len(v["nonverbatim"]), v["nonverbatim"])
    else:
        main_ext(sys.argv[2], sys.argv[1]) if sys.argv[1] in ("ext", "ext-ea") else main(*sys.argv[1:])
