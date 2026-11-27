"""Which sub-questions of Box 2 need results from literatures that do not cite each other?
The units are the sub-questions in data/fields/subquestions.json. A sub-question needs a literature when blind coders, judging
from the literature's seed titles and abstracts (codebook-needs.md), found a result the sub-question uses: both coders yes
(primary rule "both") or either coder yes (variant "either"). Two needed literatures form a silent pair when their link is below
the threshold. Link: work = the larger direction of "share of works citing at least one work of the other"; rel = the larger
direction of reference share into the other over reference share into its own sample (Fig. 2b). Sixteen link variants
(measure x corpus x threshold) per need rule, on the run-4 links and, as the earlier-sample check, on the run-3 links with each
yes restricted to the seeds the run-3 sample had (group "base"). A variant whose links leave no pair of the eleven literatures
below its threshold ("finds every pair linked") is set aside. Usage, from anywhere: python3 -s -E fields/run4-broad/crossmap.py
(writes crossmap/{both,either,earlier-both,earlier-either}/{measure}_{corpus}_{threshold}.txt; does nothing until the coding exists)."""
import itertools
import json
import sys
from pathlib import Path

D = Path(__file__).resolve().parent
ROOT = D.parents[1]
sys.path.append(str(ROOT))
from census import kappa  # noqa: E402

LITS = ("C1", "C2", "C3", "C4", "C5", "C6", "C7", "R1", "R2", "R3", "R4")
CODERS = ("c1", "c2")
RULES = ("both", "either")
BASIS = {"abstract", "title", "knowledge"}
VARIANTS = [(m, c, t) for m in ("work", "rel") for c in ("2", "1") for t in (0.005, 0.01, 0.02, 0.05)]
SUBQ = ROOT / "data/fields/subquestions.json"
KEYS = ROOT / "data/fields/needs-keys.json"
SEEDS = ROOT / "data/fields/seeds-broad.json"
BATCH = {c: ROOT / f"data/batches/needs-{c}.json" for c in CODERS}
CODED = {c: ROOT / f"data/coded/needs-{c}.jsonl" for c in CODERS}
LINKS = {"broad": ROOT / "data/fields/results_m1-eleven-broad.json", "earlier": ROOT / "data/fields/results_m1-eleven-dcbroad.json"}
OUT = D / "crossmap"


def stem(measure, corpus, thr):
    return f"{measure}_{corpus}_{thr:g}"


def coded():
    return all(p.exists() for p in CODED.values())


def load_coded(path, batch):
    """A coder's file as {(q, code): row}, rejected unless every (q, literature) cell of the batch appears once and each row obeys
    the codebook: need yes or no; a yes cites one to three distinct seeds of that literature, a result and a basis; a no no seeds."""
    cells = {(q["id"], l["code"]) for q in batch["subquestions"] for l in batch["literatures"]}
    seeds = {l["code"]: {s["id"] for s in l["seeds"]} for l in batch["literatures"]}
    out = {}
    for n, line in enumerate(open(path, encoding="utf-8"), 1):
        if not line.strip():
            continue
        r = json.loads(line)
        k = (r.get("q"), r.get("lit"))
        why = None
        if k not in cells:
            why = "cell not in the batch"
        elif k in out:
            why = "duplicate cell"
        elif r.get("need") == "yes":
            s = r.get("seeds")
            if not (isinstance(s, list) and 1 <= len(s) <= 3 and len(set(s)) == len(s) and set(s) <= seeds[k[1]]):
                why = "a yes must cite one to three distinct seeds of its literature"
            elif not str(r.get("result") or "").strip():
                why = "a yes needs a result"
            elif r.get("basis") not in BASIS:
                why = f"basis must be one of {sorted(BASIS)}"
        elif r.get("need") == "no":
            if r.get("seeds") != []:
                why = "a no carries an empty seed list"
        else:
            why = "need must be yes or no"
        if why:
            raise ValueError(f"{path}:{n}: {why}")
        out[k] = r
    if len(out) != len(cells):
        raise ValueError(f"{path}: {len(cells) - len(out)} cells missing, e.g. {sorted(cells - set(out))[:3]}")
    return out


def needs(coded_, keys, qids, rule, base=None):
    """{q: set of literatures needed} under rule both (every coder yes) or either (some coder yes); with `base`, a yes counts only
    if one of its recorded seeds is in `base`."""
    yes = [{(q, keys[c][l]) for (q, l), r in rows.items() if r["need"] == "yes" and (base is None or set(r["seeds"]) & base)}
           for c, rows in coded_.items()]
    comb = set.intersection(*yes) if rule == "both" else set.union(*yes)
    return {q: {l for qq, l in comb if qq == q} for q in qids}


def agreement(coded_, keys, subq):
    """Cohen's kappa over all cells and per Box 2 question, and each coder's number of yes cells."""
    lab = {c: {(q, keys[c][l]): r["need"] for (q, l), r in rows.items()} for c, rows in coded_.items()}
    c1, c2 = (lab[c] for c in CODERS)
    assert set(c1) == set(c2)
    cells = sorted(c1)
    tag = {q["id"]: q["tag"] for q in subq}
    kap = lambda ks: kappa([c1[k] for k in ks], [c2[k] for k in ks])
    return {"n": len(cells), "kappa": kap(cells), "yes": {c: list(lab[c].values()).count("yes") for c in CODERS},
            "by_tag": {t: kap([k for k in cells if tag[k[0]] == t]) for t in dict.fromkeys(tag.values())}}


def run(subq, need, m1, corpus, thr, measure):
    """One link variant: per sub-question its needed literatures and silent pairs, in the line format of the earlier outputs."""
    m = m1[corpus]
    if measure == "work":
        w = m["work"]
        talk = lambda a, b: max(w[a][b], w[b][a])
    else:
        ref = m["ref"]
        talk = lambda a, b: max(ref[a][b] / ref[a][a], ref[b][a] / ref[b][b])
    below = [(a, b) for a, b in itertools.combinations(list(m["work"]), 2) if talk(a, b) < thr]
    lines, silent, pairs = [], {}, {}
    for q in subq:
        nd = sorted(need.get(q["id"], ()))
        s = [(a, b, talk(a, b)) for a, b in itertools.combinations(nd, 2) if talk(a, b) < thr]
        if s:
            silent[q["id"]] = s
        for a, b, _ in s:
            pairs[(a, b)] = pairs.get((a, b), 0) + 1
        lines.append(f"{q['id']} | {q['text']} | needs {' '.join(nd) or 'none measured'} | silent pairs: "
                     + (", ".join(f"{a}-{b} ({t:.3f})" for a, b, t in s) or "none"))
    n_lit = len(m["work"])
    lines += ["", f"{len(silent)} of {len(subq)} sub-questions need two or more literatures that do not cite each other (link below {thr:.1%}; {measure}; {corpus}-seed corpora).",
              f"Silent pairs by number of sub-questions needing them: {sorted(pairs.items(), key=lambda kv: -kv[1])}; literature pairs below the threshold: {len(below)} of {n_lit * (n_lit - 1) // 2}."]
    return {"lines": lines, "silent": silent, "n": len(subq), "all_linked": not below}


def analyse():
    """Sub-questions, need sets, coder agreement, per-variant results and the text outputs, from the coded files."""
    subq = json.load(open(SUBQ))
    qids = [q["id"] for q in subq]
    assert len(set(qids)) == len(qids)
    keys = json.load(open(KEYS))
    coded_ = {c: load_coded(CODED[c], json.load(open(BATCH[c]))) for c in CODERS}
    base = {s["openalex"] for s in json.load(open(SEEDS)) if s["group"] == "base"}
    need = {rule: needs(coded_, keys, qids, rule) for rule in RULES}
    res, texts = {}, {}
    for sample, restrict in (("broad", None), ("earlier", base)):
        m1 = json.load(open(LINKS[sample]))["M1"]
        for rule in RULES:
            nd = need[rule] if restrict is None else needs(coded_, keys, qids, rule, restrict)
            for v in VARIANTS:
                r = run(subq, nd, m1, v[1], v[2], v[0])
                assert r["n"] == len(subq)
                res.setdefault(sample, {}).setdefault(rule, {})[stem(*v)] = {"silent": r["silent"], "all_linked": r["all_linked"]}
                texts[f"{'' if sample == 'broad' else 'earlier-'}{rule}/{stem(*v)}.txt"] = "\n".join(r["lines"]) + "\n"
    return subq, need, agreement(coded_, keys, subq), res, texts


def _and(xs):
    xs = list(xs)
    return "" if not xs else xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


def _label(s):
    m, c, t = s.split("_")
    return f"the {'share-of-works' if m == 'work' else 'reference-share'} measure on the {'one' if c == '1' else 'two'}-seed samples at {100 * float(t):g}\\%"


US = {"behaviour": "behavior", "favour": "favor", "maximise": "maximize", "optimise": "optimize", "randomisation": "randomization"}  # the SI is in US spelling


def _us(s):
    for uk, us in US.items():
        s = s.replace(uk, us)
    return s


def _tex(s):
    for a in "&%$#_":
        s = s.replace(a, "\\" + a)
    return s


def fragments(summary, subq, need, ag, earlier_median):
    """The Supplementary Note 3 fragments and the rows of the sub-question table (si/tab-subquestions.tex)."""
    retained = lambda vs: {s: v for s, v in vs.items() if not v["all_linked"]}
    robust = lambda vs: set.intersection(*(set(v["silent"]) for v in retained(vs).values())) if retained(vs) else set()
    b, e = summary["broad"], summary["earlier"]
    ret = retained(b["both"])
    cnt = {rule: [len(v["silent"]) for v in retained(b[rule]).values()] for rule in RULES}
    thr = [t for *_, t in VARIANTS]
    rb = robust(b["both"])
    by_tag = ", ".join(f"{t} {k:.2f}" for t, k in ag["by_tag"].items())
    f = {"n3-nsub.tex": str(len(subq)), "n3-nretained.tex": str(len(ret)),
         "n3-excluded.tex": _and(_label(s) for s, v in b["both"].items() if v["all_linked"]) or "none",
         "n3-questions.tex": f"between {min(cnt['both'])} and {max(cnt['both'])} need two literatures linked at below {100 * min(thr):g}\\% to {100 * max(thr):g}\\% in the {len(ret)} retained variants (between {min(cnt['either'])} and {max(cnt['either'])} when either coder's yes suffices)",
         "n3-robust.tex": str(len(rb)), "n3-robust-either.tex": str(len(robust(b["either"]))),
         "n3-robust-ids.tex": _and(q["id"] for q in subq if q["id"] in rb) or "none",
         "n3-earlier.tex": f"the median link was {earlier_median:.4f} and {len(robust(e['both']))} sub-questions needed such a pair in every retained variant ({len(robust(e['either']))} when either coder's yes suffices)",
         "n3-kappa.tex": f"{ag['kappa']:.2f}",
         "n3-agreement.tex": f"$\\kappa = {ag['kappa']:.2f}$ over the {ag['n']} cells" + (f" ({by_tag})" if by_tag else "")
                             + f"; the coders said yes on {ag['yes']['c1']} and {ag['yes']['c2']} of them"}

    def every(q):
        s = [{(a, bb) for a, bb, _ in v["silent"].get(q, [])} for v in ret.values()]
        return set.intersection(*s) if s else set()

    rows = []
    for tag in dict.fromkeys(q["tag"] for q in subq):
        rows.append(f"\\multicolumn{{4}}{{l}}{{\\emph{{{tag}}}}} \\\\")
        for q in (q for q in subq if q["tag"] == tag):
            nb, add = sorted(need["both"][q["id"]]), sorted(need["either"][q["id"]] - need["both"][q["id"]])
            cell = (", ".join(nb) or "--") + (f" [{', '.join(add)}]" if add else "")
            rows.append(f"{q['id']} & {_tex(_us(q['text']))} & {cell} & {', '.join(f'{a}--{bb}' for a, bb in sorted(every(q['id']))) or '--'} \\\\")
    f["tab-subquestions.tex"] = "\n".join(rows) + "\n"
    return f


def main():
    if not coded():
        print("NEEDS coding not found (" + ", ".join(p.name for p in CODED.values()) + " in data/coded/); outputs left untouched")
        return None
    subq, need, ag, res, texts = analyse()
    for name, t in texts.items():
        p = OUT / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(t)
    print(f"kappa {ag['kappa']:.2f} over {ag['n']} cells; wrote {len(texts)} files under {OUT}")
    return res


if __name__ == "__main__":
    main()
