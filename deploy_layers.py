"""Deployment reach by ownership layer (codebook-deploy-layers.md, deployment codebook v4).

`python3 deploy_layers.py jobs` writes the blind batches data/batches/layers-NN.json (id and page text only, from the stored
snapshots; gitignored) and their briefs data/batches/layers-briefs.jsonl, two independent coders per batch.
`python3 deploy_layers.py estimate` reads data/coded/layers-NN-c1.jsonl and -c2.jsonl and writes data/estimates-deploy-layers.json.
si_tables.py turns that file into si/deploy-layers-short.tex and si/tab-deploy-layers.tex."""
import json
import math
import random
import sys
from pathlib import Path

from analyze import load_codes, wilson
from census import kappa

PARTY = {"model-vendor", "platform-vendor", "tool-operator", "counterparty-org", "other-org-agent", "none"}
ACTION = {"runs-on", "calls-tool", "writes", "transacts", "messages-agent", "none"}
THIRD = {"tool-operator", "counterparty-org", "other-org-agent"}
DERIVED = ("acts_on_other_owner", "model_vendor_reach", "platform_vendor_reach", "third_party_reach", "tool_operator_reach", "counterparty_reach", "agent_to_agent", "counterparty")
LABEL = {"acts_on_other_owner": "any layer another party operates", "model_vendor_reach": "model vendor", "platform_vendor_reach": "platform vendor",
         "third_party_reach": "further party (tool operator, counterparty organization or another organization's agent)",
         "tool_operator_reach": "tool operator", "counterparty_reach": "counterparty organization",
         "agent_to_agent": "another organization's agent", "counterparty": "messages outside persons (counterparty)"}
SNAP = Path("data/raw/deploy-pages")  # local snapshots (not released; hashes and URLs in MANIFEST)
MANIFEST = "data/deploy-pages-manifest.json"
OUTPUT = "data/estimates-deploy-layers.json"


def live(r):
    return str(r.get("status")).lower() == "ok" and str(r.get("live_agent")).lower() == "yes"


def validate(r):
    """Problems with one coded page (empty list when it follows the codebook)."""
    bad = []
    lay = r.get("other_owner_layers")
    if not isinstance(lay, list):
        return [f"{r.get('id')}: other_owner_layers is not a list"]
    if not live(r):
        return [f"{r.get('id')}: layers coded for a page without a live agent"] if lay else []
    if not lay:
        bad.append(f"{r.get('id')}: live agent with no entry (use the single none entry)")
    for e in lay:
        if e.get("party_kind") not in PARTY or e.get("action") not in ACTION:
            bad.append(f"{r.get('id')}: bad entry {e}")
        elif e["party_kind"] != "none" and not str(e.get("quote", "")).strip():
            bad.append(f"{r.get('id')}: entry without quote {e}")
    kinds = [e.get("party_kind") for e in lay]
    if "none" in kinds and len(kinds) > 1:
        bad.append(f"{r.get('id')}: none together with other entries")
    if str(r.get("outside_persons")).lower() not in ("yes", "no"):
        bad.append(f"{r.get('id')}: outside_persons must be yes or no for a live agent")
    return bad


def derive(r):
    """The derived reach fields of one coded page; None when the coder found no live agent on it."""
    if not live(r):
        return None
    k = {e["party_kind"] for e in r["other_owner_layers"]}
    return {"acts_on_other_owner": bool(k - {"none"}), "model_vendor_reach": "model-vendor" in k, "platform_vendor_reach": "platform-vendor" in k,
            "third_party_reach": bool(k & THIRD), "tool_operator_reach": "tool-operator" in k, "counterparty_reach": "counterparty-org" in k, "agent_to_agent": "other-org-agent" in k, "counterparty": str(r.get("outside_persons")).lower() == "yes"}


def frame():
    """The pages to code: the 83 live agent pages with a stated reach (v2) and the one without, the six readable Google Cloud
    pages coded blocked, and the pages on which the two v2 coders disagreed on AGENT (93 pages)."""
    P = load_codes("data/coded/deploy-0[0-9].jsonl")
    O = {**load_codes("data/coded/deploy-overlap-*.jsonl"), **load_codes("data/coded/deploy-second-*.jsonl")}
    src = {x["id"]: x["source"] for x in json.load(open("data/deploy-items.json"))}
    ok = lambda r: str(r.get("status")).lower() == "ok"
    agent = {i for i, r in P.items() if ok(r) and str(r.get("agent")).lower() == "yes"}
    fetched = {i for i, r in json.load(open(MANIFEST)).items() if "sha256" in r}  # pages whose snapshot was taken (fetch_deploy_pages.py)
    google = {i for i, r in P.items() if not ok(r) and src[i] == "Google Cloud" and i in fetched}
    dis = {i for i in O if i in P and ok(P[i]) and ok(O[i]) and str(P[i].get("agent")).lower() != str(O[i].get("agent")).lower()}
    return sorted(agent | google | dis)


BRIEF = ('You are a careful research coder. Do the work yourself: spawn no agents, run nothing in the background, fetch no web pages, use no scripts or keyword rules to assign codes (a helper script only to serialize your hand-assigned codes is fine, kept in your private directory {priv}).\n\n'
         'BASE = "BASE"\nRead BASE/codebook-deploy-layers.md and the pages in BASE/data/batches/layers-{b}.json (each has id and text, a text snapshot of a vendor case page). Open no other file under BASE: in particular nothing in BASE/data/coded/, no other batch and no other codebook. '
         'Code every page by hand from its text, read in full (a long page may be cut in your file view: re-read that part until you have the whole text). '
         'Write BASE/data/coded/layers-{b}-{c}.jsonl with exactly one JSON object per line per page, in input order, in the output format the codebook specifies, ids copied exactly. Write no other file under BASE. '
         'Return only: the number of pages coded, the number with live_agent yes, and the number of entries per party_kind.')


def jobs(out=Path("data/batches"), k=5, seed=20261110):
    """Blind batches of the frame (id and snapshot text only) and one brief per batch and coder; returns {batch: ids}."""
    out = Path(out)
    ids = frame()
    random.Random(seed).shuffle(ids)
    step = math.ceil(len(ids) / k)
    batches = {f"{n + 1:02d}": ids[n * step:(n + 1) * step] for n in range(k)}
    with open(out / "layers-briefs.jsonl", "w") as f:
        for b, bi in batches.items():
            json.dump([{"id": i, "text": (SNAP / f"{i}.txt").read_text()} for i in bi], open(out / f"layers-{b}.json", "w"), indent=0, ensure_ascii=False)
            for c in ("c1", "c2"):
                priv = f"/private/tmp/layers-{b}-{c}/"
                f.write(json.dumps({"batch": b, "coder": c, "n": len(bi), "private": priv, "writes": [f"layers-{b}-{c}.jsonl"], "brief": BRIEF.format(b=b, c=c, priv=priv)}) + "\n")
    return batches


def share(k, n):
    lo, hi = wilson(k, n)
    return {"k": k, "n": n, "share": k / n if n else float("nan"), "lo": lo, "hi": hi}


def estimate(c1, c2):
    """Shares per coder, on both coders' reading (both code a live agent and the field) and on either coder's reading
    (some coder codes a live agent with the field, among pages some coder codes as a live agent), and kappa per field
    over the pages both code as live agents."""
    assert set(c1) == set(c2), "both coders must code the same pages"
    bad = [p for r in (*c1.values(), *c2.values()) for p in validate(r)]
    assert not bad, "\n".join(bad)
    ids = sorted(c1)
    d1, d2 = {i: derive(c1[i]) for i in ids}, {i: derive(c2[i]) for i in ids}
    both = [i for i in ids if d1[i] and d2[i]]
    either = [i for i in ids if d1[i] or d2[i]]
    out = {"pages": len(ids), "fields": list(DERIVED)}
    out["c1"] = {f: share(sum(d1[i][f] for i in ids if d1[i]), sum(1 for i in ids if d1[i])) for f in DERIVED}
    out["c2"] = {f: share(sum(d2[i][f] for i in ids if d2[i]), sum(1 for i in ids if d2[i])) for f in DERIVED}
    out["both"] = {f: share(sum(d1[i][f] and d2[i][f] for i in both), len(both)) for f in DERIVED}
    out["either"] = {f: share(sum(bool((d1[i] or {}).get(f) or (d2[i] or {}).get(f)) for i in either), len(either)) for f in DERIVED}
    ka = lambda a, b: {"n": len(a), "agree": sum(x == y for x, y in zip(a, b)), "kappa": kappa(a, b) if a else float("nan")}
    out["kappa"] = {f: ka([d1[i][f] for i in both], [d2[i][f] for i in both]) for f in DERIVED}
    g1, g2 = [live(c1[i]) for i in ids], [live(c2[i]) for i in ids]
    out["gate"] = {"c1": sum(g1), "c2": sum(g2), "both": len(both), "either": len(either), "kappa": ka(g1, g2)}
    return out


def fragments(est):
    """{file name: LaTeX fragment} for the SI and the main text."""
    p = lambda m: f"{m['k']} of {m['n']} ({100 * m['share']:.1f}\\%)"
    c = lambda m: f"{m['k']}/{m['n']} ({100 * m['share']:.1f}; {100 * m['lo']:.1f}--{100 * m['hi']:.1f})"
    t = "third_party_reach"
    short = f"{p(est['both'][t])} live agent deployments on both coders' reading and {p(est['either'][t])} on either coder's"
    kf = lambda x: "--" if x is None else f"{x:.2f}"  # None: undefined, both coders give one value
    rows = [f"{LABEL[f]} & {c(est['c1'][f])} & {c(est['c2'][f])} & {c(est['both'][f])} & {c(est['either'][f])} & {kf(est['kappa'][f]['kappa'])} \\\\" for f in DERIVED]
    b, k = est["both"], lambda m: f"{m['k']} of {m['n']}"
    main = {"deploy-any-layer.tex": k(b["acts_on_other_owner"]), "deploy-platform.tex": k(b["platform_vendor_reach"]), "deploy-a2a.tex": k(b["agent_to_agent"]),
            "deploy-model.tex": k(b["model_vendor_reach"])}  # main-text short forms, both coders' reading
    iv = lambda m: f"{k(m)} ({100 * m['share']:.1f}\\%, {100 * m['lo']:.1f} to {100 * m['hi']:.1f}\\%)"
    main |= {"deploy-third.tex": iv(b[t]), "deploy-tool.tex": iv(b["tool_operator_reach"]), "deploy-counterparty.tex": iv(b["counterparty_reach"])}
    g = est["gate"]["kappa"]  # the live-agent gate that sets the pages both code as live
    main["deploy-gate-agreement.tex"] = f"{g['agree']} of {g['n']} pages ($\\kappa = {kf(g['kappa'])}$)"
    return {"deploy-layers-short.tex": short, "tab-deploy-layers.tex": "\n".join(rows) + "\n", **main}


def load_coder(c):
    return load_codes(f"data/coded/layers-[0-9][0-9]-{c}.jsonl")


def main():
    c1, c2 = load_coder("c1"), load_coder("c2")
    assert set(c1) == set(frame()), f"coder c1 covers {len(c1)} of {len(frame())} pages"
    est = estimate(c1, c2)
    json.dump(est, open(OUTPUT, "w"), indent=1)
    for v in ("c1", "c2", "both", "either"):
        print(v, {f: f"{m['k']}/{m['n']}" for f, m in est[v].items()})
    print("kappa", {f: m["kappa"] and round(m["kappa"], 2) for f, m in est["kappa"].items()}, "gate", est["gate"])


if __name__ == "__main__":
    if sys.argv[1:] == ["jobs"]:
        print({b: len(v) for b, v in jobs().items()})
    elif sys.argv[1:] == ["estimate"]:
        main()
    else:
        sys.exit(__doc__)
