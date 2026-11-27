"""P4 test: is the single-principal share higher in industry-authored papers?

Author institutions come from the virtual-site JSON; sector is assigned by rules (industry rule first), and the unknown rate is reported.
"""
import json
import re
import sys
from collections import Counter

from analyze import category, fmt, load_codes
from census import norm

# ponytail: name lists, not an entity resolver; the unknown rate printed by main() bounds what they miss
INDUSTRY = re.compile(
    r"\b(google|deepmind|microsoft|meta|facebook|openai|anthropic|amazon|aws|apple|nvidia|ibm|intel|qualcomm|samsung|sony|adobe|"
    r"salesforce|alibaba|tencent|baidu|huawei|bytedance|tiktok|kuaishou|meituan|jd\.com|jd explore|xiaomi|oppo|vivo|lenovo|ant group|"
    r"netease|sensetime|megvii|iflytek|zhipu|moonshot|deepseek|minimax|mistral|cohere|hugging ?face|databricks|snowflake|uber|lyft|"
    r"netflix|spotify|twitter|linkedin|pinterest|snap|yandex|naver|kakao|lg ai|sap|siemens|bosch|toyota|honda|bloomberg|jpmorgan|"
    r"goldman|two sigma|citadel|criteo|booking|zalando|valeo|ericsson|nokia|bell labs|preferred networks|sakana|cerebras|"
    r"together ai|scale ai|character\.ai|x\.ai|xai|international business machines)\b|\b(inc|ltd|llc|corp|corporation|gmbh|co\.,|company|technologies)\b",
    re.I,
)
ACADEMIC = re.compile(
    r"universit|institut|college|school|academy|acad[ée]mie|[ée]cole|hochschule|polytechni|\b(eth|epfl|mit|kaist|cmu|ucla|ucsd|"
    r"usc|nyu|ust|hkust|kaust|mbzuai|inria|cnrs|riken|csiro|a\*star|mila|vector|max planck|mpi|fraunhofer|helmholtz|"
    r"national lab|laboratory|hospital|center for|centre for|ai lab|berkeley|stanford|technion|uiuc|ut austin|caltech|"
    r"ku leuven|virginia tech|georgia tech|postech|tsinghua|politecnico|oxford|cambridge|harvard|princeton|yale|cornell|"
    r"columbia|toronto|mcgill|waterloo|weizmann|imperial|ucl|kth|tum|lmu|cuhk|hku|nus|ntu|snu|unist|gist|iisc|iit)\b",
    re.I,
)


def fisher(k1, n1, k2, n2):
    """Two-sided Fisher exact p for k1/n1 vs k2/n2 (sum of tables no more likely than the observed one)."""
    from math import comb

    k, n = k1 + k2, n1 + n2
    pr = lambda a: comb(n1, a) * comb(n2, k - a) / comb(n, k)
    obs = pr(k1)
    return min(1.0, sum(pr(a) for a in range(max(0, k - n2), min(k, n1) + 1) if pr(a) <= obs * (1 + 1e-9)))


def sector(inst, dual="industry"):
    """Industry rule first; dual: the sector given to a string that names both a company and an academic institution."""
    s = (inst or "").strip()
    if not s:
        return "unknown"
    if INDUSTRY.search(s):
        return dual if ACADEMIC.search(s) else "industry"
    if ACADEMIC.search(s):
        return "academic"
    return "unknown"


def alphabetical(names):
    """True if the author list is ordered by surname (last token); undefined (False) for one author."""
    s = [n.split()[-1].lower() for n in names if n and n.split()]
    return len(s) >= 2 and s == sorted(s) and len(set(s)) > 1


def position_sectors(authors):
    secs = [sector(a.get("institution")) for a in authors]
    known = [s for s in secs if s != "unknown"]
    frac = sum(s == "industry" for s in known) / len(known) if known else None
    share = "unknown" if frac is None else "none" if frac == 0 else "majority" if frac > 0.5 else "some"
    return {"first": secs[0] if secs else "unknown", "last": secs[-1] if secs else "unknown", "share": share, "n": len(secs)}


def paper_group(sectors):
    s = set(sectors) - {"unknown"}
    if not s:
        return "unknown"
    return "mixed" if s == {"industry", "academic"} else s.pop()


def main():
    items = json.load(open("data/stage2-items.json"))
    codes = load_codes()
    authors = {}
    for venue in ("neurips-2020", "icml-2020", "neurips-2025", "icml-2025"):
        for r in json.load(open(f"data/raw/{venue}.json"))["results"]:
            authors[(venue, norm(r["name"]))] = [a.get("institution") for a in (r.get("authors") or [])]
    inst = [i for v in authors.values() for i in v]
    unk = Counter(i for i in inst if sector(i) == "unknown")
    print(f"author strings: {len(inst)}; unknown sector {sum(unk.values())} ({100 * sum(unk.values()) / len(inst):.1f}%)")
    print("top unknown:", unk.most_common(15))
    rows = []
    for x in items:
        k = (x["venue"], norm(x["title"]))
        if k in authors and x["id"] in codes:
            rows.append((x, codes[x["id"]], paper_group([sector(i) for i in authors[k]])))
    print(f"matched coded items: {len(rows)}")
    for label, keep in (("random strata", lambda x: "random" in x["strata"]), ("agent-flagged", lambda x: "agent" in x["strata"] or "llm_agent" in x["strata"]), ("LLM-agent 2025", lambda x: "llm_agent" in x["strata"])):
        print(f"\n## {label}")
        for g in ("industry", "mixed", "academic", "unknown"):
            sub = [c for x, c, pg in rows if keep(x) and pg == g and category(c) != "na"]
            if sub:
                print(f"{g:9s} multi-principal {fmt(sum(category(c) == 'multi-principal' for c in sub), len(sub))}")
        ind = [c for x, c, pg in rows if keep(x) and pg in ("industry", "mixed") and category(c) != "na"]
        aca = [c for x, c, pg in rows if keep(x) and pg == "academic" and category(c) != "na"]
        ki, ka = sum(category(c) == "multi-principal" for c in ind), sum(category(c) == "multi-principal" for c in aca)
        print(f"any-industry {fmt(ki, len(ind))} vs academic-only {fmt(ka, len(aca))}; Fisher two-sided p = {fisher(ki, len(ind), ka, len(aca)):.3f}")


def positions():
    """Position analysis, specified before it was run: primary = last author, >=2 authors, non-alphabetical, agent-flagged."""
    items = json.load(open("data/stage2-items.json"))
    codes = load_codes()
    raw = {}
    for venue in ("neurips-2020", "icml-2020", "neurips-2025", "icml-2025"):
        for r in json.load(open(f"data/raw/{venue}.json"))["results"]:
            raw[(venue, norm(r["name"]))] = r.get("authors") or []
    rows = []
    for x in items:
        a = raw.get((x["venue"], norm(x["title"])))
        if a is not None and x["id"] in codes and category(codes[x["id"]]) != "na":
            rows.append((x, codes[x["id"]], position_sectors(a), alphabetical([y.get("fullname", "") for y in a])))
    ns = sorted(p["n"] for _, _, p, _ in rows)
    print(f"papers {len(rows)}; authors per paper median {ns[len(ns) // 2]}, single-author {sum(n == 1 for n in ns)}")
    print(f"alphabetical author order (>=2 authors): {fmt(sum(al for *_, al in rows), sum(p['n'] >= 2 for _, _, p, _ in rows))}")
    print("first-author sector:", dict(Counter(p["first"] for _, _, p, _ in rows)), " last-author sector:", dict(Counter(p["last"] for _, _, p, _ in rows)))
    print("industry share of authors:", dict(Counter(p["share"] for _, _, p, _ in rows)))
    mp = lambda cs: sum(category(c) == "multi-principal" for c in cs)
    alpha_mp = [c for x, c, p, al in rows if al]
    print(f"multi-principal among alphabetical-order papers {fmt(mp(alpha_mp), len(alpha_mp))} vs others {fmt(mp([c for x, c, p, al in rows if not al]), sum(not al for *_, al in rows))}")
    pops = (("agent-flagged (PRIMARY population)", lambda x: "agent" in x["strata"] or "llm_agent" in x["strata"]), ("random strata", lambda x: "random" in x["strata"]))
    for label, keep in pops:
        print(f"\n## {label}")
        base = [(c, p) for x, c, p, al in rows if keep(x) and p["n"] >= 2 and not al]
        for pos in ("last", "first"):
            ind = [c for c, p in base if p[pos] == "industry"]
            aca = [c for c, p in base if p[pos] == "academic"]
            tag = "PRIMARY " if pos == "last" and label.startswith("agent") else ""
            print(f"{tag}{pos}-author industry {fmt(mp(ind), len(ind))} vs academic {fmt(mp(aca), len(aca))}; Fisher p = {fisher(mp(ind), len(ind), mp(aca), len(aca)):.3f}")
        allp = [(c, p) for x, c, p, al in rows if keep(x)]
        for sh in ("none", "some", "majority"):
            cs = [c for c, p in allp if p["share"] == sh]
            print(f"industry share {sh:8s} {fmt(mp(cs), len(cs))}")


if __name__ == "__main__":
    positions() if sys.argv[1:] == ["positions"] else main(*sys.argv[1:])
