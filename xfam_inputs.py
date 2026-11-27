"""Inputs for the open-weight full-frame coding (Roihu, roihu/xfam.sbatch).

data/xfam/items-full.jsonl: every deduplicated non-paratext paper of the four ML venue-years plus all EC 2025 records,
with an opaque shuffled xid, venue, main_track, title, abstract and the stage-2 sample id (or null).
data/xfam/calls.jsonl: the coder view, one chat request per paper (codebook v3 as system prompt, title and abstract as user
message, a per-call JSON schema). Coders see no venue, year, track or sample id.

`python3 xfam_inputs.py ext` builds the extension to ICLR 2025 and AAMAS 2025 (main-conference papers only) into
data/xfam/items-ext.jsonl and calls-ext.jsonl, with the same codebook and call format, xids y00001.. (never x), and their
sha256 in data/xfam/ext-sha256.txt (sha256sum -c format). The full-run files are not touched.
"""
import json
import random
import sys
from pathlib import Path

from census import dedupe, norm
from estimate import ML, main_track

KEYS = ["id", "agent", "data", "objective", "control", "interests", "has_decision_maker", "faces_other_parties", "faces_quote", "one_party_runs_all", "owners", "eval_run", "cross_vendor", "focus", "boundary", "llm_basis", "confidence", "quote"]
# na everywhere a field can be unfixed by the abstract (codebook v3, paragraph 3)
ENUMS = {
    "agent": ["yes", "no", "na"],
    "data": ["pooled", "partitioned", "na"],
    "objective": ["single", "multiple", "na"],
    "control": ["central", "decentralized", "na"],
    "interests": ["one", "several-aligned", "several-conflicting", "adversarial", "na"],
    "has_decision_maker": ["yes", "no"],
    "faces_other_parties": ["yes", "no"],
    "one_party_runs_all": ["yes", "no"],
    "owners": ["one", "several", "na"],
    "eval_run": ["one", "several", "na"],
    "cross_vendor": ["yes", "no", "na"],
    "focus": ["agent", "interaction", "na"],
    "boundary": ["yes", "no", "na"],
    "llm_basis": ["yes", "no", "na"],
    "confidence": ["high", "medium", "low"],
}
INSTRUCTION = "Return one JSON object with exactly the keys listed in the Output line"
SEED = 20261106
EXT = ("iclr-2025", "aamas-2025")
EA = "aamas-2025-ea"  # AAMAS extended abstracts + Blue Sky: a sensitivity population, xids z00001..
EXT_SEED = 20261108
CODEBOOK_SHA = "d2f1aea9fdb66ca53315582d58505895497ea79068703a97a47f3e5885389067"  # v3.4, as in the full run


def schema(xid):
    props = {"id": {"type": "string", "const": xid}, **{k: {"type": "string", "enum": v} for k, v in ENUMS.items()}, "faces_quote": {"type": "string"}, "quote": {"type": "string"}}
    return {"type": "object", "properties": {k: props[k] for k in KEYS}, "required": KEYS, "additionalProperties": False}


def call(it, codebook, schema=schema):
    return {"call_id": it["xid"], "schema": schema(it["xid"]),
            "messages": [{"role": "system", "content": codebook.rstrip("\n") + "\n\n" + INSTRUCTION},
                         {"role": "user", "content": f"Title: {it['title']}\n\nAbstract: {it['abstract']}"}]}


# Policy pass (codebook-policy.md): its own system prompt and schema; the v3.4 calls, codebook and outputs are not touched.
POLICY_KEYS = ["id", "policy_setters", "policy_quote", "principals", "principals_quote", "partners_from_others"]
POLICY_ENUMS = {"policy_setters": ["one", "several", "na"], "principals": ["one", "several", "na"], "partners_from_others": ["yes", "no", "na"]}
POLICY_SHA = "f89a80bfed6c81fe5c178e46efc8170c6a095444d68d1b4d525c593850d01953"  # codebook-policy.md v1
POLICY_FILES = ("items-full.jsonl", "items-ext.jsonl", "items-ext-ea.jsonl")  # main frame, extension, EA sensitivity: one calls file


def schema_policy(xid):
    props = {"id": {"type": "string", "const": xid}, **{k: {"type": "string", "enum": v} for k, v in POLICY_ENUMS.items()},
             "policy_quote": {"type": "string"}, "principals_quote": {"type": "string"}}
    return {"type": "object", "properties": {k: props[k] for k in POLICY_KEYS}, "required": POLICY_KEYS, "additionalProperties": False}


def call_policy(it, codebook):
    return call(it, codebook, schema_policy)


def quotes_verbatim(rec, it, keys=("policy_quote", "principals_quote")):
    """Every quote in keys (v1: both; v2: QUOTES_V2) occurs in title + abstract (case and whitespace folded); an empty quote passes."""
    fold = lambda s: " ".join(s.lower().split())
    text = fold(it["title"] + " " + it["abstract"])
    return all(fold(rec[k]) in text for k in keys)


def policy_items():
    return [json.loads(l) for f in POLICY_FILES for l in open(f"data/xfam/{f}")]


def main_policy():
    """data/xfam/calls-policy.jsonl (every item of the three frames, in items order), calls-policy-smoke100.jsonl and
    calls-policy-smoke2.jsonl (the xids of calls-smoke100.jsonl and calls-smoke2.jsonl), sha256 in data/xfam/policy-sha256.txt. Items files are read, never rebuilt."""
    import hashlib
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    assert sha("codebook-v3.md") == CODEBOOK_SHA and sha("codebook-policy.md") == POLICY_SHA
    codebook = open("codebook-policy.md").read()
    items = policy_items()
    out = Path("data/xfam")
    smoke = [json.loads(l)["call_id"] for l in open(out / "calls-smoke100.jsonl")]
    smoke2 = [json.loads(l)["call_id"] for l in open(out / "calls-smoke2.jsonl")]  # 50 one-owner several-interest papers, 50 others
    by = {it["xid"]: it for it in items}
    with open(out / "calls-policy.jsonl", "w") as g:
        for it in items:
            g.write(json.dumps(call_policy(it, codebook), ensure_ascii=False) + "\n")
    (out / "calls-policy-smoke100.jsonl").write_text("".join(json.dumps(call_policy(by[i], codebook), ensure_ascii=False) + "\n" for i in smoke))
    (out / "calls-policy-smoke2.jsonl").write_text("".join(json.dumps(call_policy(by[i], codebook), ensure_ascii=False) + "\n" for i in smoke2))
    names = ["calls-policy.jsonl", "calls-policy-smoke100.jsonl", "calls-policy-smoke2.jsonl", *POLICY_FILES]
    (out / "policy-sha256.txt").write_text("".join(f"{sha(out / n)}  {n}\n" for n in names))
    print(len(items), "policy calls;", len(smoke), "smoke calls")


# Policy pass v2: the codebook is a parameter; swap in a revision by changing POLICY2_CODEBOOK and
# POLICY2_SHA together. The v1 constants, calls and outputs above are not touched.
V2_KEYS = ["id", "policy_setters", "policy_quote", "principals", "principals_quote", "behaviour", "behaviour_quote",
           "rule_breaking", "interacting", "outside_attacker", "partners_from_others"]  # rule_breaking: v2.2 (rule R5)
V2_ENUMS = {"policy_setters": ["one", "several", "na"], "principals": ["one", "several", "na"],
            "behaviour": ["obedient", "rational", "byzantine", "mixed", "not-stated", "na"], "rule_breaking": ["yes", "no", "na"],
            "interacting": ["yes", "no", "na"], "outside_attacker": ["yes", "no"], "partners_from_others": ["yes", "no", "na"]}
QUOTES_V2 = ("policy_quote", "principals_quote", "behaviour_quote")
POLICY2_CODEBOOK = "codebook-policy-v2.2.md"  # v2 (83502ded) and v2.1 (e3d71d3f) stay on disk for their pilot rounds
POLICY2_SHA = "720acb5b47bb4c0c26e7e9127636a00212ca0b94f380036fd939b26a0411b33a"


def schema_policy2(xid):
    props = {"id": {"type": "string", "const": xid}, **{k: {"type": "string", "enum": v} for k, v in V2_ENUMS.items()},
             **{k: {"type": "string"} for k in QUOTES_V2}}
    return {"type": "object", "properties": {k: props[k] for k in V2_KEYS}, "required": V2_KEYS, "additionalProperties": False}


def call_policy2(it, codebook):
    return call(it, codebook, schema_policy2)


def main_policy2(codebook=POLICY2_CODEBOOK, sha=POLICY2_SHA, n_pilot=100):
    """data/xfam/calls-policy2.jsonl (every item of the three frames, in the v1 calls-policy.jsonl order),
    calls-policy2-smoke100.jsonl (the xids of calls-policy-smoke100.jsonl) and calls-policy2-pilot100.jsonl (the first
    n_pilot pilot ids of data/pilot/pilot-ids.json in sorted order), with their and the codebook's sha256 in
    data/xfam/policy2-sha256.txt. The codebook must hash to the pinned sha."""
    import hashlib
    h = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    assert h(codebook) == sha, f"{codebook} sha256 {h(codebook)} is not the pinned {sha}: update POLICY2_CODEBOOK and POLICY2_SHA together"
    text = open(codebook).read()
    items = policy_items()
    by = {it["xid"]: it for it in items}
    out = Path("data/xfam")
    smoke = [json.loads(l)["call_id"] for l in open(out / "calls-policy-smoke100.jsonl")]
    p = json.load(open("data/pilot/pilot-ids.json"))
    pilot = sorted([x["id"] for x in p["disputed"]] + p["random"])[:n_pilot]  # disputed: {id, clusters, part}; random: ids
    rows = lambda ids: "".join(json.dumps(call_policy2(by[i], text), ensure_ascii=False) + "\n" for i in ids)
    files = {"calls-policy2.jsonl": [it["xid"] for it in items], "calls-policy2-smoke100.jsonl": smoke, "calls-policy2-pilot100.jsonl": pilot}
    for name, ids in files.items():
        (out / name).write_text(rows(ids))
    (out / "policy2-sha256.txt").write_text("".join(f"{h(out / n)}  {n}\n" for n in files) + f"{sha}  {Path(codebook).name}\n")
    print(len(items), "policy2 calls;", len(smoke), "smoke;", len(pilot), "pilot; codebook", Path(codebook).name, sha[:8])


def build(raw, sample, seed=SEED, prefix="x"):
    """raw: {venue: [records]}; sample: stage-2 items. EC keeps its paratext-typed research paper."""
    sid = {(x["venue"], norm(x["title"])): x["id"] for x in sample}
    rows = []
    for venue, recs in raw.items():
        # a paper is main track if any of its listings is (an oral can be listed first under a satellite session's group)
        main = {norm(r["name"]) for r in recs if main_track(r)}
        for r in dedupe(recs):
            if venue != "ec-2025" and r.get("type") == "paratext":
                continue
            rows.append({"venue": venue, "main_track": norm(r["name"]) in main, "title": r["name"], "abstract": r.get("abstract") or "",
                         "sample_id": sid.get((venue, norm(r["name"])))})
    random.Random(seed).shuffle(rows)
    return [{"xid": f"{prefix}{i:05d}", **r} for i, r in enumerate(rows, 1)]


def ext_items(raw, seed=EXT_SEED, prefix="y"):
    """Main-conference papers of the extension venues, xids y00001.. (a separate id space from the full run's x ids; z for EA)."""
    return build({v: [r for r in recs if main_track(r)] for v, recs in raw.items()}, [], seed, prefix=prefix)


def smoke2(items, primary, seed=SEED, n=50):
    """(simulated, rest): n sampled papers whose Claude code is owners one with several-party interests, and n others
    from the coded sample that were not in smoke 1 (the first 100 sampled papers in xid order)."""
    sampled = [x for x in items if x["sample_id"] in primary]
    first = {x["xid"] for x in sampled[:100]}
    sim = lambda x: str(primary[x["sample_id"]]["owners"]).lower() == "one" and str(primary[x["sample_id"]]["interests"]).lower() in ("several-aligned", "several-conflicting")
    rng = random.Random(seed)
    a = rng.sample([x for x in sampled if sim(x)], n)
    b = rng.sample([x for x in sampled if not sim(x) and x["xid"] not in first], n)
    return sorted(a, key=lambda x: x["xid"]), sorted(b, key=lambda x: x["xid"])


def main():
    raw = {}
    for v in ML + ("ec-2025",):
        d = json.load(open(f"data/raw/{v}.json"))
        raw[v] = d["results"] if isinstance(d, dict) else d
    sample = json.load(open("data/stage2-items.json"))
    items = build(raw, sample)
    assert sum(i["sample_id"] is not None for i in items) == len(sample), "every stage-2 item must map to one paper"
    codebook = open("codebook-v3.md").read()
    out = Path("data/xfam")
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "items-full.jsonl", "w") as f, open(out / "calls.jsonl", "w") as g:
        for it in items:
            c = call(it, codebook)
            assert c["messages"][1]["content"].endswith(it["abstract"])  # full abstract, no truncation
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
            g.write(json.dumps(c, ensure_ascii=False) + "\n")
    smoke = [json.dumps(call(it, codebook), ensure_ascii=False) + "\n" for it in items if it["sample_id"]][:100]
    (out / "calls-smoke100.jsonl").write_text("".join(smoke))  # first 100 calls with a coded-sample counterpart
    from analyze import load_codes
    a, b = smoke2(items, load_codes())
    (out / "calls-smoke2.jsonl").write_text("".join(json.dumps(call(it, codebook), ensure_ascii=False) + "\n" for it in a + b))
    (out / "smoke2-halves.json").write_text(json.dumps({"simulated": [x["xid"] for x in a], "rest": [x["xid"] for x in b]}))
    longest = max(len(json.dumps(call(it, codebook)["messages"], ensure_ascii=False)) for it in items)
    print(f"{len(items)} items ({sum(i['sample_id'] is not None for i in items)} in the coded sample); longest call {longest} chars")


def main_ext(venues=EXT, prefix="y", tag="ext"):
    """`ext`: ICLR + AAMAS main papers (xids y..). `ext-ea`: the AAMAS EA + Blue Sky sensitivity (xids z..), same codebook and calls."""
    import hashlib
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    assert sha("codebook-v3.md") == CODEBOOK_SHA, "codebook differs from the full run's v3.4"
    raw = {}
    for v in venues:
        d = json.load(open(f"data/raw/{v}.json"))
        raw[v] = d["results"] if isinstance(d, dict) else d
    items = ext_items(raw, prefix=prefix)
    out = Path("data/xfam")
    taken = {json.loads(l)["xid"] for f in ("items-full.jsonl", "items-ext.jsonl") if (out / f).exists() and f != f"items-{tag}.jsonl" for l in open(out / f)}
    assert not taken & {i["xid"] for i in items}
    codebook = open("codebook-v3.md").read()
    with open(out / f"items-{tag}.jsonl", "w") as f, open(out / f"calls-{tag}.jsonl", "w") as g:
        for it in items:
            c = call(it, codebook)
            assert c["messages"][1]["content"].endswith(it["abstract"]) and it["abstract"]
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
            g.write(json.dumps(c, ensure_ascii=False) + "\n")
    names = [n for n in ("calls-ext.jsonl", "items-ext.jsonl", "calls-ext-ea.jsonl", "items-ext-ea.jsonl") if (out / n).exists()]
    (out / "ext-sha256.txt").write_text("".join(f"{sha(out / n)}  {n}\n" for n in names))
    from collections import Counter
    print(len(items), "items", dict(Counter(i["venue"] for i in items)))


if __name__ == "__main__":
    if sys.argv[1:] == ["ext"]:
        main_ext()
    elif sys.argv[1:] == ["policy"]:
        main_policy()
    elif sys.argv[1:2] == ["policy2"]:  # policy2 --codebook <path> (must hash to POLICY2_SHA)
        import argparse
        ap = argparse.ArgumentParser(prog="xfam_inputs.py policy2")
        ap.add_argument("--codebook", required=True)
        main_policy2(ap.parse_args(sys.argv[2:]).codebook)
    elif sys.argv[1:] == ["ext-ea"]:
        main_ext((EA,), "z", "ext-ea")
    else:
        main()
