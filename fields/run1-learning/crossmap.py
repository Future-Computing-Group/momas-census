"""Which AI-side sub-objectives need results from literatures that do not cite each other?
A sub-objective needs a literature when one of its items cites one of that literature's seed papers (author match).
Cross-talk between two needed literatures is the larger of the two directions of "share of works citing at least one work
of the other" (results_m1.json, two-seed corpora). Usage: python3 -I crossmap.py <Cross-field ledger.md> <results_m1.json> [corpus 2|1] [threshold]"""
import itertools, json, re, sys

SEEDS = {  # author strings as the ledger writes them; matched against each X section
    "C1": ["Perdomo", "Hardt et al. 2016", "Mendler-Dünner, Ding", "Miller, Perdomo", "Jagadeesan", "Brown, Hod", "Zrnic"],
    "C2": ["Hernandez-Leal", "LOLA", "Meta-MAPG", "M-FOS", "MADDPG", "Lowe", "Papoudakis", "Panait"],
    "C3": ["Deng, Schneider", "Braverman", "Banchio", "Arora, Dekel", "Hart and Mas-Colell", "Arunachaleswaran", "Zhang, Farina", "Shoham"],
    "C4": ["Hammond", "Leibo", "Carroll", "Mirsky", "Stone et al", "Stone, Kaminka", "AI Economist", "Zheng", "Sourbut"],
    "C5": ["Shumailov", "Gerstgrasser", "Bertrand", "Taori", "Ensign", "Chaney", "Jiang", "Brennan"],
    "C6": ["Lucas", "Marcet", "Honkapohja", "Cho, Williams", "Esponda", "Bolton", "Keller, Rady", "Fudenberg"],
    "C7": ["Forssell", "Gevers", "Bombois", "Rojas", "Weerts", "Hendrickx", "Cheng, Shi", "van Waarde"],
}


def item_clusters(md):
    out = {}
    for sec in re.split(r"^## ", md, flags=re.M)[1:]:
        m = re.match(r"(X-\d+) ", sec)
        if m:
            body = sec.split("\nFUSILLI:")[0]
            out[m[1]] = {c for c, keys in SEEDS.items() if any(k in body for k in keys)}
    return out


def subobjectives(md):
    sec = md[md.find("## AI-side objectives"):md.find("## X-01 ")]
    for m in re.finditer(r"^#### (A\d\.\d) (.*?)\n(.*?)(?=^#### |^### |\Z)", sec, flags=re.M | re.S):
        yield m[1], m[2].strip(), re.findall(r"X-\d+", re.search(r"^Items: (.*)$", m[3], flags=re.M)[1])


def main(ledger, res, corpus="2", thr="0.02"):
    thr = float(thr)
    md = open(ledger, encoding="utf-8").read()
    work = json.load(open(res))["M1"][corpus]["work"]
    talk = lambda a, b: max(work[a][b], work[b][a])
    ic = item_clusters(md)
    n = n_silent = 0
    silent_pairs = {}
    for sid, name, items in subobjectives(md):
        need = sorted(set().union(*(ic.get(x, set()) for x in items)))
        pairs = [(a, b, talk(a, b)) for a, b in itertools.combinations(need, 2)]
        silent = [(a, b, t) for a, b, t in pairs if t < thr]
        n += 1; n_silent += bool(silent)
        for a, b, _ in silent:
            silent_pairs[(a, b)] = silent_pairs.get((a, b), 0) + 1
        print(f"{sid} | {name} | {','.join(items)} | needs {' '.join(need) or 'none measured'} | silent pairs: "
              + (", ".join(f"{a}-{b} ({t:.3f})" for a, b, t in silent) or "none"))
    print(f"\n{n_silent} of {n} sub-objectives need two or more literatures that do not cite each other (both directions below {thr:.1%} of works; {corpus}-seed corpora).")
    print("Silent pairs by number of sub-objectives needing them:", sorted(silent_pairs.items(), key=lambda kv: -kv[1]))
    assert n >= 20


if __name__ == "__main__":
    main(*sys.argv[1:5])
