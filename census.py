"""Stage-1 census: deduplicate accepted papers and flag agent / multi-party abstracts.

Input: data/raw/{conf}-{year}.json from {conf}.cc/static/virtual/data/{conf}-{year}-orals-posters.json
(orals appear twice, as oral and poster events, so rows are deduplicated by normalized title).
"""
import json
import random
import re
import sys
from pathlib import Path

# ponytail: keyword flags are a screening instrument only; stage-2 coding measures their recall
AGENT = re.compile(r"\b(agents?|agentic|multi-agent|multiagent)\b", re.I)
NOT_AGENT = re.compile(r"\b(reducing|oxidizing|chemical|contrast|therapeutic|binding|chelating|biological|infectious)\s+agents?\b", re.I)
LLM_AGENT = re.compile(
    r"\b(agentic|(llm|language|language-model|web|gui|coding|software|computer-use|tool-using)[- ]agents?|"
    r"agents? (built on|powered by|based on) (llms?|large language models?)|multi-agent (llm|language)|llm-based (multi-)?agents?)\b",
    re.I,
)
MULTIPARTY = re.compile(
    r"\b(multi-agent|multiagent|mechanism design|auctions?|markets?|incentives?|strategic|game-theoretic|games?|equilibri(um|a)|"
    r"federated|decentrali[sz]ed|principal-agent|stakeholders?|negotiat\w*|coalitions?|institutions?|collusion|social choice)\b",
    re.I,
)


def norm(title):
    return re.sub(r"\W+", " ", title.lower()).strip()


def dedupe(rows):
    seen, out = set(), []
    for r in rows:
        k = norm(r["name"])
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out


def flags(text):
    agent_hits = len(AGENT.findall(text)) - len(NOT_AGENT.findall(text))
    return {"agent": agent_hits > 0, "llm_agent": bool(LLM_AGENT.search(text)), "multiparty": bool(MULTIPARTY.search(text))}


def sample(rows, n, seed):
    return random.Random(seed).sample(rows, min(n, len(rows)))


def kappa(a, b):
    """Cohen's kappa for two coders' labels on the same items; None where it is undefined (chance agreement 1)."""
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in set(a) | set(b))
    return None if pe == 1 else (po - pe) / (1 - pe)  # undefined when both coders give one and the same value


ALLOWED = {
    "agent": {"yes", "no", "na"},  # na: abstract truncated in the source
    "data": {"pooled", "partitioned", "na"},
    "objective": {"single", "multiple", "na"},
    "control": {"central", "decentralized", "na"},
    "interests": {"one", "several-aligned", "several-conflicting", "adversarial", "na"},
    "owners": {"one", "several", "na"},
    "boundary": {"yes", "no", "na"},  # na: abstract too thin to fix the setting (one case in the full run)
    "confidence": {"high", "medium", "low"},
}


def validate(rows, expected_ids):
    """Return a list of problems with one coded batch (empty list = valid)."""
    errs = []
    got = [r.get("id") for r in rows]
    errs += [f"missing {i}" for i in expected_ids if i not in got]
    errs += [f"unexpected {i}" for i in got if i not in expected_ids]
    for r in rows:
        for k, ok in ALLOWED.items():
            if str(r.get(k)).lower() not in ok:
                errs.append(f"{r.get('id')}: {k}={r.get(k)!r}")
    return errs


def read_to_end(last_words, abstract):
    """True if a coder's reported last words are the abstract's final words (case and punctuation ignored)."""
    got, tail = norm(last_words).split(), norm(abstract).split()
    return bool(got) and tail[-len(got):] == got


def load(path):
    d = json.load(open(path))
    return dedupe(d["results"] if isinstance(d, dict) else d)


def main(raw_dir="data/raw"):
    print("venue-year\tpapers\tagent\tagent%\tmultiparty\tagent&multiparty")
    for p in sorted(Path(raw_dir).glob("*.json")):
        rows = load(p)
        f = [flags(r["name"] + " " + (r.get("abstract") or "")) for r in rows]
        a = sum(x["agent"] for x in f)
        m = sum(x["multiparty"] for x in f)
        am = sum(x["agent"] and x["multiparty"] for x in f)
        print(f"{p.stem}\t{len(rows)}\t{a}\t{100 * a / len(rows):.1f}\t{m}\t{am}")


if __name__ == "__main__":
    main(*sys.argv[1:])
