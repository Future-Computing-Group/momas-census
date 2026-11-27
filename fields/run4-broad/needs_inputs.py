"""Inputs of the blind NEEDS coding (codebook-needs.md): the seeds' abstracts from OpenAlex (three cached, keyless filter calls
of at most 50 IDs; no email or key, asserted in oa.py), then one batch per coder with the eleven literatures under codes L01 to
L11 assigned at random per coder and the seeds of each literature shuffled. The code-to-literature keys go to a separate file
that the coders are not given. Usage, from the repository root: python3 -s -E fields/run4-broad/needs_inputs.py"""
import hashlib
import json
import os
import random
import subprocess
import sys
import urllib.parse
from pathlib import Path

D = Path(__file__).resolve().parent
ROOT = D.parents[1]
LITS = ("C1", "C2", "C3", "C4", "C5", "C6", "C7", "R1", "R2", "R3", "R4")
CODERS = {"c1": 1, "c2": 2}  # coder -> seed of its random code assignment and seed order
NO_ABSTRACT = "no abstract in OpenAlex"
DATE = "2026-11-10"
ARCHIVE = f"data/raw/openalex-abstracts-{DATE}.tar.gz"
BRIEF = ("You are a careful research coder. Do the work yourself: spawn no agents, run nothing in the background, fetch no web pages, "
         "use no scripts or keyword rules to assign codes (a helper script only to serialize your hand-assigned codes is fine, kept in "
         "your private directory /private/tmp/needs-{c}/).\n\nBASE = \"BASE\"\nRead BASE/codebook-needs.md and the sub-questions and "
         "literatures in BASE/data/batches/needs-{c}.json (25 sub-questions; 11 literatures under codes L01 to L11, each a list of seed "
         "papers with id, title, year and abstract). Open no other file. Judge every pair of a sub-question and a literature by hand, "
         "as the codebook says, reading each abstract to its end. Write BASE/data/coded/needs-{c}.jsonl with exactly one JSON object "
         "per line per pair (275 lines), in the output format the codebook specifies, sub-question IDs, literature codes and seed IDs "
         "copied exactly. Return only: the number of lines written and the number of yes cells.")
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def abstract(inv):
    """Text of an OpenAlex abstract_inverted_index, or None when OpenAlex holds no abstract."""
    if not inv:
        return None
    pos = {i: w for w, idx in inv.items() for i in idx}
    return " ".join(pos[i] for i in sorted(pos))


def fetch():
    """The 131 seeds of the eleven literatures with their abstracts; also returns the raw cache files used."""
    sys.path.insert(0, str(D))
    import oa
    seeds = [s for s in json.load(open(ROOT / "data/fields/seeds-broad.json")) if s["cluster"] in LITS]
    ids = [s["openalex"] for s in seeds]
    got, urls = {}, []
    for i in range(0, len(ids), 50):
        params = {"filter": "openalex:" + "|".join(ids[i:i + 50]), "select": "id,abstract_inverted_index", "per-page": 50}
        got.update({oa.sid(w["id"]): w.get("abstract_inverted_index") for w in oa.get("works", **params)["results"]})
        urls.append(f"{oa.BASE}/works?" + urllib.parse.urlencode(params, safe=":|,"))  # the URL oa.get caches under
    missing = [x for x in ids if x not in got]
    assert not missing, f"OpenAlex returned no record for {missing}"
    out = [{"openalex": s["openalex"], "cluster": s["cluster"], "group": s["group"], "title": s["oa_title"], "year": s["oa_year"],
            "abstract": abstract(got[s["openalex"]])} for s in seeds]
    raw = [Path(oa.RAW) / (hashlib.sha1(u.encode()).hexdigest() + ".json") for u in urls]
    assert all(p.exists() for p in raw)
    return out, raw, dict(oa.CALLS)


def build(abstracts, subq):
    """One batch per coder and the code-to-literature keys; deterministic given CODERS."""
    batches, keys = {}, {}
    for c, seed in CODERS.items():
        rng = random.Random(seed)
        order = [l for l in LITS if any(a["cluster"] == l for a in abstracts)]
        rng.shuffle(order)
        keys[c] = {f"L{k + 1:02d}": lit for k, lit in enumerate(order)}
        lits = []
        for code, lit in keys[c].items():
            ss = [{"id": a["openalex"], "title": a["title"], "year": a["year"], "abstract": a["abstract"] or NO_ABSTRACT}
                  for a in abstracts if a["cluster"] == lit]
            rng.shuffle(ss)
            lits.append({"code": code, "seeds": ss})
        batches[c] = {"subquestions": [{"id": q["id"], "tag": q["tag"], "text": q["text"]} for q in subq], "literatures": lits}
    return batches, keys


def dump(obj, path):
    Path(path).write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    os.chdir(ROOT)
    out, raw, calls = fetch()
    dump(out, "data/fields/seeds-broad-abstracts.json")
    Path("data/raw").mkdir(exist_ok=True)
    if not Path(ARCHIVE).exists():
        subprocess.run(["tar", "-czf", ARCHIVE, "-C", str(raw[0].parent), *(p.name for p in raw)], check=True)
        Path(ARCHIVE + ".sha256").write_text(f"{sha(ARCHIVE)}  {Path(ARCHIVE).name}\n")
    subq = json.load(open("data/fields/subquestions.json"))
    batches, keys = build(out, subq)
    for c, b in batches.items():
        dump(b, f"data/batches/needs-{c}.json")
    dump({"rng_seeds": CODERS, **keys}, "data/fields/needs-keys.json")
    dump({"inputs_built": DATE, "model": "claude-sonnet-5-5", "coders": list(CODERS),
          "subquestions_sha256": sha("data/fields/subquestions.json"), "codebook_sha256": sha("codebook-needs.md"),
          "brief_template_sha256": hashlib.sha256(BRIEF.encode()).hexdigest(),
          "abstracts_sha256": sha("data/fields/seeds-broad-abstracts.json"),
          "abstracts": {"seeds": len(out), "without_abstract": sum(a["abstract"] is None for a in out), "openalex_calls": calls},
          "raw_archive": ARCHIVE, "raw_archive_sha256": sha(ARCHIVE),
          "raw_responses": {p.name: sha(p) for p in raw},
          "batches": {f"needs-{c}.json": sha(f"data/batches/needs-{c}.json") for c in CODERS},
          "keys_sha256": sha("data/fields/needs-keys.json")}, "data/fields/needs-manifest.json")
    for c in CODERS:  # the dispatched brief carries the repository path; it stays in internal/ (not tracked)
        Path("internal/plan-c").mkdir(parents=True, exist_ok=True)
        Path(f"internal/plan-c/brief-{c}.txt").write_text(BRIEF.replace("{c}", c).replace('BASE = "BASE"', f'BASE = "{ROOT}"') + "\n")
    print(f"{len(out)} seeds, {sum(a['abstract'] is None for a in out)} without abstract; OpenAlex calls {calls}")


if __name__ == "__main__":
    main()
