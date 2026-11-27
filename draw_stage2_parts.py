"""Stage-2 parts e, f, g and the EC remainder, added after parts a-d (data/xfam/stage2-confirm.json, xfam_full.py):

- e: every first-stage owners-several paper whose interests are not several-* (adversarial or one), so every owners-several paper is confirmed;
- f: 600 random non-agent papers the first stage does not code owners several (a further slice of d), and
  g: 150 random 2025 NeurIPS and ICML LLM-agent papers it codes owners one (a further slice of c), one Random(79) draw, f first;
- ec: every EC 2025 paper in no earlier part, so EC is confirmed in full.

  python3 draw_stage2_parts.py [outdir]   (default data/xfam) writes stage2-part-e.json, stage2-parts-fg.json, stage2-part-ec.json.
"""
import json
import random
import sys
from pathlib import Path

from xfam_full import SEVERAL

SEED = 79
ML_2025 = ("neurips-2025", "icml-2025")


def part_e(rows):
    return sorted(r["id"] for r in rows if r["owners_derived"] == "several" and r["interests"] not in SEVERAL)


def parts_fg(rows, items, confirmed, n_f=600, n_g=150, seed=SEED):
    """rows in id order (the first stage's results file); confirmed: the ids of parts a-d."""
    pool_f = [r["id"] for r in rows if r["agent"] == "no" and r["owners_derived"] != "several" and r["id"] not in confirmed]
    pool_g = [r["id"] for r in rows if r["agent"] == "yes" and r["llm_basis"] == "yes" and r["owners_derived"] == "one"
              and items[r["id"]]["venue"] in ML_2025 and r["id"] not in confirmed]
    rng = random.Random(seed)
    f = rng.sample(pool_f, n_f)
    return {"f": sorted(f), "g": sorted(rng.sample(pool_g, n_g))}


def part_ec(items, done):
    return sorted(i for i, x in items.items() if x["venue"] == "ec-2025" and i not in done)


def write(out="data/xfam"):
    out = Path(out)
    rows = sorted((json.loads(l) for l in open("data/xfam/full-v34/results-parsed.jsonl")), key=lambda r: r["id"])
    items = {x["xid"]: x for x in map(json.loads, open("data/xfam/items-full.jsonl"))}
    confirmed = {x["xid"] for x in json.load(open("data/xfam/stage2-confirm.json"))}
    e, fg = part_e(rows), parts_fg(rows, items, confirmed)
    ec = part_ec(items, confirmed | set(e) | set(fg["f"]) | set(fg["g"]))
    for name, obj in (("stage2-part-e.json", e), ("stage2-parts-fg.json", fg), ("stage2-part-ec.json", ec)):
        (out / name).write_text(json.dumps(obj))


if __name__ == "__main__":
    write(*sys.argv[1:2])
