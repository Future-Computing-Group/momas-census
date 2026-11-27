"""Steps 2-5: corpora, M1 cross-talk, bridges, M2 periphery, fairness calibration. Network calls only via cached oa.get."""
import collections, json, os, statistics as st, sys
from oa import get, sid, CALLS

D = os.path.dirname(os.path.abspath(__file__))
W = json.load(open(os.path.join(D, "works.json")))
SEEDS = json.load(open(os.path.join(D, "seeds.json")))
VEN = {"NeurIPS": "S4363606243", "ICML": "S4306419644", "ICLR": "S4306419637", "EC": "S4363608973"}
MAIN = [f"C{i}" for i in range(1, 8)]
AI = MAIN[:5]
REC = {}  # everything printed also saved to results.json


def seedsets(prefixes):
    by = collections.defaultdict(set)
    for s in SEEDS:
        if s["cluster"] in prefixes:
            by[s["cluster"]].add(s["openalex"])
    return by


def corpora(pool, by, k, drop=None):
    """Corpus per cluster: pool works citing >= k of its seeds (drop = one seed left out), plus the seeds."""
    rec, corp = {}, {}
    for c, seeds in by.items():
        ss = seeds - {drop} if drop else seeds
        ws = {w["id"]: w for w in pool[c] if len(ss & set(w["refs"])) >= k}
        for s in ss:
            if s in W["seeds"]:
                ws[s] = W["seeds"][s]
        corp[c] = ws
        rec.update(ws)
    return corp, rec


def m1(corp, by, exclude_seed_targets=False):
    """ref[i][j]: share of refs of corpus i pointing into corpus j; work[i][j]: share of corpus-i works citing >=1 corpus-j work."""
    allseeds = set().union(*by.values())
    ref, work = {}, {}
    for i in corp:
        ref[i], work[i] = {}, {}
        tot = sum(len(w["refs"]) for w in corp[i].values())
        for j in corp:
            tgt = set(corp[j]) - (allseeds if exclude_seed_targets else set())
            hits = [len(tgt.intersection(w["refs"])) for w in corp[i].values()]
            ref[i][j] = sum(hits) / tot if tot else float("nan")
            work[i][j] = sum(h > 0 for h in hits) / len(hits) if hits else float("nan")
    return ref, work


def summary(ref):
    off = [ref[i][j] for i in ref for j in ref if i != j]
    diag = [ref[i][i] for i in ref]
    return {"median_off": st.median(off), "median_diag": st.median(diag), "ratio": st.median(off) / st.median(diag)}


def show(name, mat, fmt="{:6.3f}"):
    ks = list(mat)
    print(f"\n{name}\n      " + " ".join(f"{k:>6}" for k in ks))
    for i in ks:
        print(f"{i:>5} " + " ".join(fmt.format(mat[i][j]) for j in ks))


def main_m1():
    by = seedsets(MAIN)
    out = {}
    for k in (2, 1):
        corp, _ = corpora(W["citers"], by, k)
        sizes = {c: len(v) for c, v in corp.items()}
        ov = {i: {j: len(set(corp[i]) & set(corp[j])) for j in corp} for i in corp}
        ref, work = m1(corp, by)
        ref_ns, work_ns = m1(corp, by, exclude_seed_targets=True)
        out[k] = {"sizes": sizes, "overlap": ov, "ref": ref, "work": work, "ref_nonseed": ref_ns,
                  "work_nonseed": work_ns, "summary": summary(ref), "summary_nonseed": summary(ref_ns)}
        print(f"\n===== corpora: >= {k} seeds; sizes {sizes}")
        show("overlap (shared works)", ov, "{:6d}")
        show("M1 reference share i->j", ref)
        show("M1 share of i works citing >=1 j work", work)
        show("M1 reference share i->j, seed targets excluded", ref_ns)
        print("summary", out[k]["summary"], "nonseed", out[k]["summary_nonseed"])
    # leave-one-seed-out sensitivity on the k=2 ratio
    loo = []
    for s in SEEDS:
        if s["cluster"] in MAIN:
            corp, _ = corpora(W["citers"], by, 2, drop=s["openalex"])
            loo.append((s["label"], summary(m1(corp, by)[0])["ratio"]))
    rs = [r for _, r in loo]
    print("\nLOO ratio range", min(rs), max(rs), "argmax", max(loo, key=lambda x: x[1])[0])
    out["loo"] = {"min": min(rs), "max": max(rs), "all": loo}
    # bridges
    corp, _ = corpora(W["citers"], by, 2)
    s12, s67 = by["C1"] | by["C2"], by["C6"] | by["C7"]
    a = {wid: w for c in ("C1", "C2") for wid, w in corp[c].items()}
    b = {wid: w for c in ("C6", "C7") for wid, w in corp[c].items()}
    br = {"C1C2_works": len(a), "C1C2_citing_C6C7_seed": sum(bool(s67 & set(w["refs"])) for w in a.values()),
          "C6C7_works": len(b), "C6C7_citing_C1C2_seed": sum(bool(s12 & set(w["refs"])) for w in b.values())}
    for c in ("C1", "C2"):
        for t in ("C6", "C7"):
            br[f"{c}_citing_{t}_seed"] = sum(bool(by[t] & set(w["refs"])) for w in corp[c].values())
    for c in ("C6", "C7"):
        for t in ("C1", "C2"):
            br[f"{c}_citing_{t}_seed"] = sum(bool(by[t] & set(w["refs"])) for w in corp[c].values())
    # same counts on the full citer pools (>=1 seed) for scale
    a1 = [w for c in ("C1", "C2") for w in W["citers"][c]]
    b1 = [w for c in ("C6", "C7") for w in W["citers"][c]]
    br["pool1_C1C2"] = len({w["id"] for w in a1})
    br["pool1_C1C2_citing_C6C7_seed"] = len({w["id"] for w in a1 if s67 & set(w["refs"])})
    br["pool1_C6C7"] = len({w["id"] for w in b1})
    br["pool1_C6C7_citing_C1C2_seed"] = len({w["id"] for w in b1 if s12 & set(w["refs"])})
    br["bridging_titles"] = sorted({w["title"] for w in a1 if s67 & set(w["refs"])} | {w["title"] for w in b1 if s12 & set(w["refs"])})
    print("\nbridges", {k: v for k, v in br.items() if k != "bridging_titles"})
    out["bridges"] = br
    REC["M1"] = out
    return corp


def locations(ids):
    """Any-location source ids per work (batched openalex: filter, 50 ids per call)."""
    ids, out = sorted(ids), {}
    for i in range(0, len(ids), 50):
        for w in get("works", filter="openalex:" + "|".join(ids[i:i + 50]), select="id,locations", **{"per-page": 200})["results"]:
            out[sid(w["id"])] = {sid((l.get("source") or {}).get("id")) for l in w.get("locations") or []} - {None}
    return out


def venue_years(field):
    """Total works per year for each venue, by primary_location or any location."""
    out = {}
    for v, s in VEN.items():
        g = get("works", filter=f"{field}.source.id:{s}", group_by="publication_year")["group_by"]
        out[v] = {int(x["key"]): x["count"] for x in g}
    return out


def vy_stats(field, v, y, n):
    """Venue-year median and top-1% threshold of cited_by_count via sorted page-number lookup (per-page=1)."""
    f = f"{field}.source.id:{VEN[v]},publication_year:{y}"
    at = lambda r: get("works", filter=f, sort="cited_by_count:desc", select="cited_by_count", page=r, **{"per-page": 1})["results"][0]["cited_by_count"]
    lo, hi = (n + 1) // 2, n // 2 + 1  # ranks of the two middle values (equal when n odd)
    med = (at(lo) + at(hi)) / 2 if lo != hi else at(lo)
    return {"n": n, "median": med, "top1_threshold": at(max(1, n // 100))}


def m2(corp, loc, years=range(2015, 2027), label="main", clusters=AI, venues=("NeurIPS", "ICML", "ICLR")):
    out = {}
    for field in ("primary_location", "locations"):
        tot = venue_years(field)
        match = lambda w, v: (w["src"] == VEN[v]) if field == "primary_location" else (VEN[v] in loc.get(w["id"], set()))
        tab = {}
        groups = {c: corp[c] for c in clusters}
        groups["union"] = {k: w for c in clusters for k, w in corp[c].items()}
        for c, ws in groups.items():
            tab[c] = {}
            for y in years:
                den = sum(tot[v].get(y, 0) for v in venues)
                num = len({w["id"] for w in ws.values() if w["year"] == y and any(match(w, v) for v in venues)})
                tab[c][y] = (num, den, num / den if den else float("nan"))
        if "C3" in clusters:
            tab["C3_EC"] = {y: (len([w for w in corp["C3"].values() if w["year"] == y and match(w, "EC")]), tot["EC"].get(y, 0)) for y in years}
        out[field] = {"totals": tot, "share": tab}
        print(f"\n[{label}] M2(a) share of NeurIPS+ICML+ICLR output, matched by {field}; totals by venue for 2025:",
              {v: tot[v].get(2025) for v in VEN})
        print("cluster " + " ".join(f"{y:>9}" for y in years))
        for c, row in tab.items():
            print(f"{c:>7} " + " ".join(f"{row[y][0]:>3}/{row[y][1]:<5}" for y in years))
        # M2(b): attention of venue-matched works vs their venue-year distribution
        att = {}
        for c, ws in groups.items():
            vm = [(w, v) for w in ws.values() for v in (venues + (("EC",) if c == "C3" else ())) if match(w, v) and w["year"] in years]
            rows = []
            for w, v in vm:
                n = tot[v].get(w["year"], 0)
                if n:
                    s_ = vy_stats(field, v, w["year"], n)
                    rows.append((w["cites"], s_["median"], s_["top1_threshold"]))
            if rows:
                att[c] = {"n": len(rows), "corpus_median": st.median(r[0] for r in rows),
                          "venue_year_median_pooled": st.median(r[1] for r in rows),
                          "share_above_vy_median": sum(r[0] > r[1] for r in rows) / len(rows),
                          "share_in_vy_top1": sum(r[0] >= r[2] for r in rows) / len(rows),
                          "corpus_p90": sorted(r[0] for r in rows)[int(0.9 * (len(rows) - 1))]}
        out[field]["attention"] = att
        print(f"[{label}] M2(b) venue-matched attention ({field}):")
        for c, a in att.items():
            print("  ", c, {k: round(x, 3) if isinstance(x, float) else x for k, x in a.items()})
    return out


def cnp_table(corp, clusters):
    """Whole-corpus attention: raw citations and OpenAlex citation_normalized_percentile (field- and year-normalised)."""
    t = {}
    for c in clusters:
        ws = [w for w in corp[c].values() if 2015 <= w["year"] <= 2026]
        cn = [w["cnp"] for w in ws if w["cnp"] is not None]
        cs = sorted(w["cites"] for w in ws)
        t[c] = {"n": len(ws), "median_cites": st.median(cs), "p90_cites": cs[int(0.9 * (len(cs) - 1))],
                "n_cnp": len(cn), "median_norm_percentile": st.median(cn) if cn else None,
                "share_top1_field": sum(bool(w["top1"]) for w in ws) / len(ws),
                "share_2025_2026": sum(w["year"] >= 2025 for w in ws) / len(ws)}
        print("  ", c, {k: round(x, 3) if isinstance(x, float) else x for k, x in t[c].items()})
    return t


def fairness():
    by = seedsets({"F1", "F2", "F3"})
    out = {}
    for p in ("2012-2016", "2019-2023"):
        pool = {c: W["citers"][f"{c}:{p}"] for c in by}
        corp, _ = corpora(pool, by, 1)
        ref, work = m1(corp, by)
        ref_ns, _ = m1(corp, by, exclude_seed_targets=True)
        print(f"\n===== fairness {p}, subcorpora >= 1 of 2 seeds; sizes", {c: len(v) for c, v in corp.items()})
        show("F M1 reference share", ref)
        show("F M1 share of works citing >=1", work)
        print("summary", summary(ref), "nonseed", summary(ref_ns))
        # union fairness corpus: >= 2 of the 6 seeds
        allf = set().union(*by.values())
        uni = {w["id"]: w for c in by for w in pool[c] if len(allf & set(w["refs"])) >= 2}
        out[p] = {"sizes": {c: len(v) for c, v in corp.items()}, "ref": ref, "work": work, "summary": summary(ref),
                  "summary_nonseed": summary(ref_ns), "union_size": len(uni), "union": uni}
    return out


if __name__ == "__main__":
    corp = main_m1()
    json.dump(REC, open(os.path.join(D, "results_m1.json"), "w"), indent=1)
    if "m1" in sys.argv:
        sys.exit()
    aiw = {k for c in AI for k in corp[c]}
    fz = fairness()
    fz_ids = {k for p in fz for k in fz[p]["union"]}
    loc = locations(aiw | fz_ids)
    REC["M2"] = m2(corp, loc)
    print("\nwhole-corpus attention (all venues):")
    REC["attention_all"] = cnp_table(corp, MAIN)
    fc = {"FAIR": {}}
    for p in fz:
        fc["FAIR"].update(fz[p]["union"])
    REC["fair_M2"] = m2(fc, loc, years=list(range(2012, 2017)) + list(range(2019, 2024)), label="fairness", clusters=["FAIR"])
    for p in fz:
        fz[p].pop("union")
    REC["fairness"] = fz
    json.dump(REC, open(os.path.join(D, "results.json"), "w"), indent=1, default=str)
    print("calls", CALLS)
