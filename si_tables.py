"""Generate the Supplementary Information tables (LaTeX) from the coded data, so no number is typed by hand.

The census cells are those of the v2 policy pass (codebook-policy-v2.2.md): estimates-twostage.json keys policy2,
policy2-ext and policy2-ext-ea, estimates-round2-policy2-core.json, estimates-tipping-policy2.json and
estimates-reanalyses-policy2.json. The fragments that carry a parties number (tab-parties, parties-short, cell-composition, n-cell,
parties-agreement, setters-parties, tab-counts, aamas-short, tab-tipping, tip-margins; and the PARTIES rows of tab-coder-agreement)
are written only once estimates-round2-policy2.json exists, that is once every v2 cell paper has a parties code. The v3.4 and v1
keys and files stay on disk; the author's blind checks (focus-check, tip-author) are v3.4 codes."""
import glob
import json
import sys
from collections import Counter
from pathlib import Path

from analyze import agreement, category, final_codes, load_codes, wilson
from census import kappa
import si_ext

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "si")
OUT.mkdir(parents=True, exist_ok=True)
DOC = Path(sys.argv[2] if len(sys.argv) > 2 else "docs/fragments")  # fragments that only docs/census-methods.md (the deposit) cites
DOC.mkdir(parents=True, exist_ok=True)
COUNTS = sys.argv[3] if len(sys.argv) > 3 else "data/estimates-counts-policy2.json"  # the count estimates si_ext.write stores


def pct(k, n):
    lo, hi = wilson(k, n)
    return f"{k}/{n} & {100 * k / n:.1f} & {100 * lo:.1f}--{100 * hi:.1f}" if n else f"0/0 & -- & --"


items = json.load(open("data/stage2-items.json"))
codes = final_codes()
coder = load_codes()
second = load_codes("data/coded/overlap-*.jsonl")

VENUE = {"neurips-2020": "NeurIPS 2020", "icml-2020": "ICML 2020", "neurips-2025": "NeurIPS 2025", "icml-2025": "ICML 2025", "ec-2025": "EC 2025"}

# S1: sample composition
rows = []
for v in ["neurips-2020", "icml-2020", "neurips-2025", "icml-2025", "ec-2025"]:
    vs = [x for x in items if x["venue"] == v]
    cnt = {s: sum(s in x["strata"] for x in vs) for s in ("random", "agent", "llm_agent", "control")}
    rows.append(f"{VENUE[v]} & {len(vs)} & {cnt['random']} & {cnt['agent']} & {cnt['llm_agent']} & {cnt['control']} \\\\")
(DOC / "tab-sample.tex").write_text("\n".join(rows) + "\n")

labels = [("all-2020", "All papers 2020"), ("all-2025", "All papers 2025"), ("agent-2020", "Agent papers 2020"), ("agent-2025", "Agent papers 2025"),
          ("llm-agent-2025", "LLM-agent papers 2025"), ("other-agent-2025", "Other agent papers 2025"), ("ec-2025", "EC 2025")]

# S2b: the author's blind check of 50 papers against the coders
pv = {Path(f).stem: json.load(open(f)) for f in glob.glob("data/pi-validation/validation/*.json")}
# the blind code is the one shown in reconciliation as "mine"; a validation record re-saved after reconciliation (undo) is not blind
for f in glob.glob("data/pi-validation/adjudication/*.json"):
    d_ = json.load(open(f))
    for k, v in d_["fields"].items():
        pv[d_["id"]][k] = v["mine"]
vids = sorted(i for i in pv if i != "q1166")  # q1166 was added after the draw, for adjudication only
rows = []
for key in ("agent", "interests", "owners", "boundary"):
    a, b = [pv[i][key] for i in vids], [str(codes[i][key]).lower() for i in vids]
    rows.append(f"{key.upper()} & {sum(x == y for x, y in zip(a, b))}/{len(vids)} & {kappa(a, b):.2f} \\\\")
a, b = [category(pv[i]) for i in vids], [category(codes[i]) for i in vids]
rows.append(f"final category & {sum(x == y for x, y in zip(a, b))}/{len(vids)} & {kappa(a, b):.2f} \\\\")
(DOC / "tab-pi.tex").write_text("\n".join(rows) + "\n")
adj = [json.load(open(f)) for f in glob.glob("data/pi-validation/adjudication/*.json")]
verd = Counter(v["verdict"] for d_ in adj if d_["id"] in vids for v in d_["fields"].values())
nd = sum(verd.values())
(OUT / "pi-recon.tex").write_text(f"in all {nd} field disagreements I adopted the coders' reading" if verd["coders"] == nd else f"of {nd} field disagreements, I adopted the coders' reading in {verd['coders']}, kept my own in {verd['mine']} and marked the codebook unclear in {verd['unclear']}")
(OUT / "pi-kappa.tex").write_text(f"{kappa(a, b):.2f}")
(OUT / "n-pi.tex").write_text(f"{len(vids)}")

# S3: agreement on the double-coded items
ids = sorted(i for i in second if i in codes)
length = {x["id"]: len(x["abstract"]) for x in items}
rows = []
for key in ("agent", "interests", "owners", "control", "boundary"):
    n, k, kap = agreement(coder, second, key, ids)
    ln = [i for i in ids if length[i] > 900]
    sh = [i for i in ids if length[i] <= 900]
    _, _, kl = agreement(coder, second, key, ln)
    _, _, ks = agreement(coder, second, key, sh)
    rows.append(f"{key.upper()} & {k}/{n} & {kap:.2f} & {kl:.2f} & {ks:.2f} \\\\")
cp = [category(coder[i]) for i in ids]
cs2 = [category(second[i]) for i in ids]
rows.append(f"final category & {sum(a == b for a, b in zip(cp, cs2))}/{len(ids)} & {kappa(cp, cs2):.2f} & -- & -- \\\\")
(DOC / "tab-agreement.tex").write_text("\n".join(rows) + "\n")
(OUT / "n-overlap.tex").write_text(f"{len(ids)}")

# S3b: re-reading check (batches first coded from partially displayed abstracts, re-coded from full abstracts)
old = load_codes("data/coded-superseded/partial-read/primary-*.jsonl")
rid = sorted(old)
a, b = [category(old[i]) for i in rid], [category(coder[i]) for i in rid]
(OUT / "reread.tex").write_text(f"on the {len(rid)} re-coded papers the final category agreed with the first coding on {sum(x == y for x, y in zip(a, b))} ($\\kappa = {kappa(a, b):.2f}$), and the number with several principals with several owners changed from {a.count('multi-principal')} to {b.count('multi-principal')}")
(OUT / "n-coded.tex").write_text(f"{len(items):,}")

# S5: deployment reach
items_d = {x["id"]: x for x in json.load(open("data/deploy-items.json"))}
P = {}
for f in sorted(glob.glob("data/coded/deploy-0[0-9].jsonl")):
    for line in open(f):
        if line.strip():
            r = json.loads(line)
            P[r["id"]] = r
O = {}
for f in sorted(glob.glob("data/coded/deploy-overlap-*.jsonl")) + sorted(glob.glob("data/coded/deploy-second-*.jsonl")):  # second codes: random overlap, then every remaining agent page (from snapshots)
    for line in open(f):
        if line.strip():
            r = json.loads(line)
            O[r["id"]] = r


def dlab(r):
    s = str(r.get("status")).lower()
    if s != "ok":
        return s
    if str(r.get("agent")).lower() != "yes":
        return "not-agent"
    return str(r.get("reach")).lower()


labs = Counter(dlab(r) for r in P.values())
known = [k for k in ("internal", "customer", "cross-owner")]
n = sum(labs[k] for k in known)
src = Counter(items_d[i]["source"] for i in P)
rows = [f"{ {'customer': 'counterparty'}.get(k, k)} & {pct(labs[k], n)} \\\\" for k in known]
(OUT / "tab-deploy.tex").write_text("\n".join(rows) + "\n")
na = sum(v for k, v in labs.items() if k not in ("blocked", "not-deployment", "not-agent", "internal", "customer", "cross-owner"))
assert labs["blocked"] + labs["not-deployment"] + labs["not-agent"] + n + na == len(P)
stat = f"{len(P)} pages, {labs['blocked']} could not be read, {labs['not-deployment']} were not about a deployment, {labs['not-agent']} described no live agent, {na} described a live agent without saying what it acts on, and {n} described a live agent and what it acts on"
(OUT / "deploy-status.tex").write_text(stat)
(OUT / "n-deploy-pages.tex").write_text(f"{len(P)}")
(OUT / "deploy-sources.tex").write_text("; ".join(f"{k.removeprefix('Other vendor (').removesuffix(')')} {v}" for k, v in src.most_common()))
(OUT / "deploy-showcase-max.tex").write_text(si_ext.showcase_max(json.load(open("data/deploy-items.json"))))
dids = sorted(i for i in O if i in P and dlab(P[i]) != "blocked" and dlab(O[i]) != "blocked")
a, b = [dlab(P[i]) for i in dids], [dlab(O[i]) for i in dids]
(OUT / "deploy-agreement.tex").write_text(f"{sum(x == y for x, y in zip(a, b))}/{len(dids)} readable double-coded pages, Cohen's $\\kappa = {kappa(a, b):.2f}$")
co = [i for i, r in P.items() if dlab(r) == "cross-owner"]
both = sum(1 for i in co if i in O and dlab(O[i]) == "cross-owner")
(OUT / "deploy-cross-confirm.tex").write_text(f"{both} of the {len(co)}")
rows = [f"{items_d[i]['org']} & {P[i].get('confidence')} & {str(P[i].get('quote')).replace('&', 'and').replace('%', ' percent')} \\\\" for i in sorted(co)]
(DOC / "tab-crossowner.tex").write_text("\n".join(rows) + "\n")
hi = sum(1 for i in co if str(P[i].get("confidence")).lower() != "low")
(OUT / "deploy-sensitivity.tex").write_text(f"{hi}/{n} ({100 * hi / n:.1f}\\%)")
ok = [r for r in P.values() if str(r.get("status")).lower() == "ok"]
pl = sum(str(r.get("live")).lower() == "planned" for r in ok)
(OUT / "deploy-planned.tex").write_text(f"{pl} of {len(ok)} readable pages ({100 * pl / len(ok):.1f}\\%)")
# Two-stage census (twostage.py): shares, screen precision and misses, screen-confirmer agreement
tw_all = json.load(open("data/estimates-twostage.json"))
tw = {**tw_all["policy2"], "ext": tw_all["policy2-ext"], "ext-ea": tw_all["policy2-ext-ea"]}  # the v2 pass, shaped as the v3.4 keys
r2p = json.load(open("data/estimates-round2-policy2-core.json"))
from round2 import POLICY2_PARTIES
r2parties = json.load(open(POLICY2_PARTIES)) if Path(POLICY2_PARTIES).exists() else None  # the v2 parties split, once coded
b3 = lambda m: f"{100 * m['share']:.1f} ({100 * m['lo']:.1f}--{100 * m['hi']:.1f})"
from si_ext import ext_rows
rows = [f"{lab} & {tw[k]['n']:,} & {tw[k]['screened']} & {tw[k]['several']['confirmed']} & {b3(tw[k]['several'])} & {b3(tw[k]['interaction'])} & {b3(tw[k]['simulated'])} \\\\" for k, lab in labels]
rows += [f"{lab} & {e['n']:,} & {e['screened']} & {e['several']['confirmed']} & {b3(e['several'])} & {b3(e['interaction'])} & {b3(e['simulated'])} \\\\" for lab, e in ext_rows(tw)]  # AAMAS, once estimated
(OUT / "tab-twostage.tex").write_text("\n".join(rows) + "\n")
pr = r2p["screen_precision"]
(OUT / "screen-precision.tex").write_text(f"{pr['agent']['confirmed_several']} of {pr['agent']['screened']} agent papers and {pr['other']['confirmed_several']} of {pr['other']['screened']} other papers")
mr = tw["miss_rates"]["several"]
def strat(d):
    return "; ".join(f"{k.strip('()').replace(chr(39), '').replace(', True', ', LLM').replace(', False', '')}: {v[0]}/{v[1]}" for k, v in sorted(d.items()))
(OUT / "screen-misses.tex").write_text(f"agent papers ({strat(mr['agent'])}); other papers ({strat(mr['other'])})")
full = {}
for line in open("data/xfam/full-v34/results-parsed.jsonl"):
    r = json.loads(line)
    full[r["id"]] = r
xs = {json.loads(l)["sample_id"]: json.loads(l)["xid"] for l in open("data/xfam/items-full.jsonl") if json.loads(l).get("sample_id")}
conf = {}
for f in sorted(glob.glob("data/coded/confirm-*.jsonl")):
    for line in open(f):
        if line.strip():
            r = json.loads(line)
            conf[r["id"]] = r
cid = sorted(conf)
rows = []
for key, g_key, c_get in (("agent", "agent", lambda r: r["agent"]), ("interests", "interests", lambda r: r["interests"]), ("owners", "owners_derived", lambda r: "several" if r.get("faces_other_parties") == "yes" else ("one" if r.get("has_decision_maker") == "yes" else "na")), ("focus", "focus_derived", lambda r: r["focus"] if r.get("has_decision_maker") == "yes" else "na"), ("llm_basis", "llm_basis", lambda r: r["llm_basis"])):
    a_, b_ = [str(full[i][g_key]) for i in cid], [str(c_get(conf[i])) for i in cid]
    rows.append(f"{key.upper().replace('_', chr(92) + '_')} & {sum(x == y for x, y in zip(a_, b_))}/{len(cid)} & {kappa(a_, b_):.2f} \\\\")
# LLM_BASIS among the papers both stages code as agent papers (the populations' second split)
ag = [i for i in cid if full[i]["agent"] == "yes" and conf[i]["agent"] == "yes"]
a_, b_ = [str(full[i]["llm_basis"]) for i in ag], [str(conf[i]["llm_basis"]) for i in ag]
rows.append(f"LLM\\_BASIS, both AGENT yes & {sum(x == y for x, y in zip(a_, b_))}/{len(ag)} & {kappa(a_, b_):.2f} \\\\")
TEX = lambda k: k.upper().replace("_", chr(92) + "_")
rows += [f"{TEX(k)} & {v['agree']}/{v['n']} & {v['kappa']:.2f} \\\\" for k, v in r2p["screen_agreement"].items()]  # the v2 pass
(OUT / "tab-screen-agreement.tex").write_text("\n".join(rows) + "\n")
# Table S6, second part: the second confirming coder on the v2 pass (policy2-dup against policy2-add) and, once coded, the parties coders
CELL = {"cell": "cell, seven categories (several within the rules, several rule-breaking, several other, simulated, single learner, outside attacker, rest)",
        "several": "cell, several principals with several owners", "simulated": "cell, several principals simulated by interacting agents of one owner"}
rows = [f"{CELL.get(k, TEX(k))} & {v['agree']}/{v['n']} & {v['kappa']:.2f} \\\\" for k, v in r2p["coder_agreement"].items()]
for k, lab in (("parties_agreement_policy2_dup", "PARTIES, new cell papers"), ("parties_agreement", "PARTIES, every second-coded cell paper")):
    if r2parties:
        v = r2parties[k]
        rows.append(f"{lab} & {v['agree']}/{v['n']} & {v['kappa']:.2f} \\\\")
(OUT / "tab-coder-agreement.tex").write_text("\n".join(rows) + "\n")
(OUT / "screen-agree-pop.tex").write_text(f"on AGENT with $\\kappa = {kappa([str(full[i]['agent']) for i in cid], [str(conf[i]['agent']) for i in cid]):.2f}$ and on LLM\\_BASIS with $\\kappa = {kappa(a_, b_):.2f}$ among the {len(ag)} papers both code as agent papers")
(OUT / "n-confirm.tex").write_text(f"{r2p['n_confirm']:,}")
# the second confirming coder's seeded draws from the two venues confirmed in full (xfam_full.stage2_policy2)
venue_of = {x["xid"]: x["venue"] for t_ in ("full", "ext", "ext-ea") for x in map(json.loads, open(f"data/xfam/items-{t_}.jsonl"))}
dup_v = Counter(venue_of[i] for i in json.load(open("data/xfam/stage2-policy2.json"))["dup"])
(OUT / "dup-aamas.tex").write_text(f"{dup_v['aamas-2025']}")
(OUT / "dup-ec.tex").write_text(f"{dup_v['ec-2025']}")
(OUT / "n-census.tex").write_text(f"{len(full):,}")

# Supplementary Note 1: the author's blind FOCUS and OWNERS codes against the first stage (validation-ui/build_focus_page.py)
fl = json.load(open("data/focus-check-labels.json"))
fids = [x["id"] for x in json.load(open("data/xfam/focus-check-20.json"))]
cells = []
for key, g_key in (("focus", "focus_derived"), ("owners", "owners_derived")):
    # blind code: the adjudication record's "mine" where one exists (a validation record can be re-saved later), else the validation record
    a_ = [fl["adjudication"].get(i, {}).get("fields", {}).get(key, {}).get("mine", fl["validation"][i][key]) for i in fids]
    b_ = [str(full[xs[i]][g_key]) for i in fids]
    took = sum(fl["adjudication"].get(i, {}).get("fields", {}).get(key, {}).get("verdict") == "coders" for i in fids)
    cells.append(f"{key.upper()} {sum(x == y for x, y in zip(a_, b_))} of {len(fids)} ($\\kappa = {kappa(a_, b_):.2f}$; the screen's code accepted in {took} of the {sum(x != y for x, y in zip(a_, b_))} disagreements)")
assert len(fids) == 20 and set(fids) == set(fl["validation"]), "focus check set and labels differ"
(OUT / "focus-check.tex").write_text("; ".join(cells))
# the same blind codes against the confirming coder, whose codes enter the estimates, on the papers it coded
from twostage import claude_owners
cov = [i for i in fids if xs[i] in conf]
cells = []
for key in ("focus", "owners"):
    a_ = [fl["adjudication"].get(i, {}).get("fields", {}).get(key, {}).get("mine", fl["validation"][i][key]) for i in cov]
    b_ = [claude_owners(conf[xs[i]]) if key == "owners" else (conf[xs[i]]["focus"] if conf[xs[i]].get("has_decision_maker") == "yes" else "na") for i in cov]
    cells.append(f"{key.upper()} {sum(x == y for x, y in zip(a_, b_))} ($\\kappa = {kappa(a_, b_):.2f}$)")
(OUT / "focus-check-stage2.tex").write_text(" and ".join(cells) + f" of the {len(cov)} papers of the 20 that the confirming coder also coded")

# Round 2 (round2.py): the cell by interests, intervals for differences and ratios, CROSS_VENDOR, sector
r2 = r2p  # the v2 cells (round2.py policy2-core)
t2 = r2["table"]
num = lambda x, d=1: (lambda y: f"${y}$" if y.startswith("-") else y)(f"{(x if round(x, d) != 0 else 0.0):.{d}f}")
iv = lambda v, d=1: f"{num(v[0], d)} to {num(v[1], d)}"
rows = [f"{lab} & {b3(t2[k]['several'])} & {b3(t2[k]['aligned'])} & {b3(t2[k]['conflicting'])} & {b3(t2[k]['adversarial'])} & {b3(t2[k]['adversarial_incl'])} \\\\" for k, lab in labels if k != "ec-2025"]
(DOC / "tab-decomp.tex").write_text("\n".join(rows) + "\n")
P_ = lambda k, f: f"{100 * t2[k][f]['share']:.1f}"
(OUT / "decomp-short.tex").write_text("; ".join(f"{lab}, {P_(k, 'conflicting')} of {P_(k, 'several')}\\%" for k, lab in (("all-2020", "all papers 2020"), ("all-2025", "all papers 2025"), ("agent-2020", "agent papers 2020"), ("agent-2025", "agent papers 2025"), ("llm-agent-2025", "LLM-agent papers 2025"))) + f". Adding several-owner settings with an outside attacker raises the 2025 share to {P_('all-2025', 'adversarial_incl')}\\% for all papers and {P_('llm-agent-2025', 'adversarial_incl')}\\% for LLM-agent papers")
c2 = r2["contrasts"]
CL = [("all-several-2025-2020", "All papers, several principals, 2025 $-$ 2020 (points)", 1), ("all-interaction-2025-2020", "All papers, interaction, 2025 $-$ 2020 (points)", 1),
      ("all-conflicting-2025-2020", "All papers, conflicting interests, 2025 $-$ 2020 (points)", 1), ("agent-several-2025-2020", "Agent papers, several principals, 2025 $-$ 2020 (points)", 1),
      ("agent-simulated-2025-2020", "Agent papers, simulated, 2025 $-$ 2020 (points)", 1), ("ratio-agent-2025", "Agent papers 2025, simulated / several principals", 2),
      ("ratio-llm-agent-2025", "LLM-agent papers 2025, simulated / several principals", 2), ("ratio-other-agent-2025", "Other agent papers 2025, simulated / several principals", 2),
      ("ratio-llm-minus-other", "Difference of the two ratios above (LLM $-$ other)", 2)]
cell = lambda v, k, d: iv(v[k], d) if k in v else "--"
rows = [f"{lab} & {num(c2[k]['point'], d)} & {cell(c2[k], 'conservative', d)} & {cell(c2[k], 'bootstrap', d)} & {cell(c2[k], 'papers', d)} & {cell(c2[k], 'jeffreys', d)} & {cell(c2[k], 'papers-jeffreys', d)} \\\\" for k, lab, d in CL]
(DOC / "tab-contrasts.tex").write_text("\n".join(rows) + "\n")
main_iv = lambda k, d=1: f"difference {num(c2[k]['point'], d)} points, interval {iv(c2[k]['papers-jeffreys'], d)}"
(OUT / "trend-several.tex").write_text(main_iv("all-several-2025-2020"))
(OUT / "trend-interaction.tex").write_text(main_iv("all-interaction-2025-2020"))
(OUT / "trend-simulated-agent.tex").write_text(f"from {100 * t2['agent-2020']['simulated']['share']:.1f}\\% to {100 * t2['agent-2025']['simulated']['share']:.1f}\\% ({main_iv('agent-simulated-2025-2020')})")
# ratios print the conservative bounds: the resampling intervals cannot move a stratum whose slice holds no cell paper
rt = lambda k: f"{num(c2[k]['point'], 2)} (conservative bounds {iv(c2[k]['conservative'], 2)})"
(OUT / "ratio-agent.tex").write_text(rt("ratio-agent-2025"))
(OUT / "ratio-llm-other.tex").write_text(f"{c2['ratio-llm-agent-2025']['point']:.2f} for LLM-agent papers against {c2['ratio-other-agent-2025']['point']:.2f} for other agent papers (difference {num(c2['ratio-llm-minus-other']['point'], 2)}, conservative bounds {iv(c2['ratio-llm-minus-other']['conservative'], 2)})")
cv = r2["cross_vendor"]
xv = t2["llm-agent-2025"]["simulated_xvendor"]
assert xv["share"] == 0, "crossvendor.tex says none is cross-vendor; reword it"  # ponytail: template assumes zero cross-vendor simulated papers
(OUT / "crossvendor.tex").write_text(f"{cv['yes']} of the {cv['n']} LLM-agent papers of 2025 let models from different developers interact (the confirming coder's code for the {cv['n_stage2']} papers it coded, which hold all {cv['yes_stage2']}; the first stage's code for the rest). Of the papers placed among several principals simulated by interacting agents of one owner ({cv['simulated_stage2']} by the confirming coder, {cv['simulated_stage1_only']} more by the first stage alone), none is cross-vendor, so the estimated share of cross-vendor simulated papers is {100 * xv['share']:.1f}\\% (upper bound {100 * xv['hi']:.1f}\\%); cross-vendor papers are {cv['several_stage2_yes']} of the {cv['several_stage2']} confirmed several-owner LLM-agent papers")
sc = r2["sector"]
SL = [("primary", "Primary (dual affiliations as industry; unclassified dropped)"), ("dual-academic", "Dual affiliations as academic"), ("dual-excluded", "Dual affiliations dropped"),
      ("unknown-academic", "Unclassified last authors as academic"), ("unknown-industry", "Unclassified last authors as industry")]
rows = []
for k, lab in SL:
    for pop, plab in (("all", "all papers"), ("agent", "agent papers")):
        v = sc[f"{k}-{pop}"]
        rows.append(f"{lab}, {plab} & {v['industry']['n']:,} & {b3(v['industry'])} & {v['academic']['n']:,} & {b3(v['academic'])} & {num(v['diff'])} ({iv(v['bootstrap'])}) \\\\")
(DOC / "tab-sector.tex").write_text("\n".join(rows) + "\n")
v = sc["primary-all"]
(DOC / "sector-short.tex").write_text(f"{100 * v['industry']['share']:.1f}\\% against {100 * v['academic']['share']:.1f}\\% (difference {num(v['diff'])} points, interval {iv(v['bootstrap'])})")
(DOC / "sector-unclassified.tex").write_text(f"{sc['unclassified']:,} of the {sc['eligible']:,} eligible main-track papers ({100 * sc['unclassified'] / sc['eligible']:.1f}\\%)")

# who the other parties are in the cell (codebook-parties.md; round2.py policy2), once every v2 cell paper has a parties code
import os
import si_ext
PL = [("ai-agents", "AI agents of different owners"), ("humans", "Humans"), ("formal-model", "Formal-model parties"), ("other", "Other")]
if r2parties:
    pt = r2parties["full"]
    rows = [f"{lab} & {b3(tw[k]['several'])} & " + " & ".join(b3(pt[k][f'parties_{c}']) for c, _ in PL) + " \\\\" for k, lab in labels]
    r2ext = {tag: {"parties": r2parties[tag]} for tag in ("ext", "ext-ea")}
    ptx = r2ext["ext"]["parties"]
    rows += [f"{lab} & {b3(tw['ext'][k]['several'])} & " + " & ".join(b3(ptx[k][f'parties_{c}']) for c, _ in PL) + " \\\\" for k, lab in si_ext.PERSPECTIVE_EXT.items() if k in ptx]
    (OUT / "tab-parties.tex").write_text("\n".join(rows) + "\n")
    ai = lambda k: f"{100 * pt[k]['parties_ai-agents']['share']:.1f}\\%"
    (OUT / "parties-short.tex").write_text(f"{ai('all-2025')} of 2025 papers (agent papers {ai('agent-2025')}, LLM-agent papers {ai('llm-agent-2025')}, EC {ai('ec-2025')})")
    (OUT / "n-cell.tex").write_text(f"{r2parties['n_cell']:,}")
    pa = r2parties["parties_agreement"]
    (OUT / "parties-agreement.tex").write_text(f"{pa['agree']}/{pa['n']}, $\\kappa = {pa['kappa']:.2f}$; AI agents against the rest {pa['agree_ai']}/{pa['n']}, $\\kappa = {pa['kappa_ai']:.2f}$")
si_ext.write(OUT, tw, {"parties": r2parties["full"] if r2parties else {}}, {tag: {"parties": r2parties[tag]} for tag in ("ext", "ext-ea")} if r2parties else {},
             COUNTS, parties=bool(r2parties))
import statistics
abl = lambda keep: [len(x["abstract"]) for x in map(json.loads, open("data/xfam/items-full.jsonl")) if keep(x)]
ecl = abl(lambda x: x["venue"] == "ec-2025")
mll = abl(lambda x: x["venue"] in ("neurips-2025", "icml-2025") and x["main_track"])
(OUT / "ec-short-abstracts.tex").write_text(f"median {statistics.median(ecl):,.0f} characters; {sum(n < 500 for n in ecl)} of {len(ecl)} under 500; NeurIPS and ICML 2025 main tracks, median {statistics.median(mll):,.0f} characters")
# Section 4 of the main text: short forms, so that no census number in main.tex is typed by hand
(OUT / "headline-short.tex").write_text(f"{100 * tw['all-2025']['several']['share']:.1f}\\% (conservative bounds {100 * tw['all-2025']['several']['lo']:.1f} to {100 * tw['all-2025']['several']['hi']:.1f}\\%)")
(OUT / "ec-share.tex").write_text(f"{100 * tw['ec-2025']['several']['share']:.1f}\\%")
(OUT / "sim-agent-short.tex").write_text(f"{100 * tw['agent-2025']['simulated']['share']:.1f}\\%")
ic = tw["ext"]["all-iclr-2025"]["several"]
(OUT / "n-iclr.tex").write_text(f"{tw['ext']['all-iclr-2025']['n']:,}")
(OUT / "iclr-short.tex").write_text(f"{100 * ic['share']:.1f}\\% (conservative bounds {100 * ic['lo']:.1f} to {100 * ic['hi']:.1f}\\%)")
# Section 4 states approximate proportions (si_ext.rough_*); exact shares and bounds stay in Fig. 2a and the SI
(OUT / "sec4-ml-several.tex").write_text(si_ext.rough_pct([tw["all-2025"]["several"]["share"], ic["share"]]))
(OUT / "sec4-ec-several.tex").write_text(si_ext.rough_fraction(tw["ec-2025"]["several"]["share"]))
(OUT / "sec4-aamas-several.tex").write_text(si_ext.rough_fraction(tw["ext"]["all-aamas-2025"]["several"]["share"]))
if r2parties:
    _ai = lambda d, k: r2parties[d][k]["parties_ai-agents"]
    (OUT / "sec4-ai-all.tex").write_text(si_ext.rough_rate(_ai("full", "all-2025")["share"]))
    fm = lambda k: r2parties["full"][k]["parties_formal-model"]["share"] / tw[k]["several"]["share"]  # formal-model parties' part of the cell
    (OUT / "sec4-ml-formal.tex").write_text(f"{si_ext.rough_part(fm('all-2025'))} of them as parties in formal models")
    (OUT / "sec4-ec-formal.tex").write_text("mostly in formal models" if si_ext.rough_part(fm("ec-2025")) == "most" else f"{si_ext.rough_part(fm('ec-2025'))} of them in formal models")
    (OUT / "sec4-ai-under.tex").write_text(si_ext.rough_under([(m["share"], m["hi"]) for m in [_ai("full", k) for k in ("agent-2025", "llm-agent-2025", "ec-2025")] + [_ai("ext", "all-aamas-2025")]]))
# the majority cells (twostage.POLICY_SHARES) in the headline's form, and the cell's composition (round2.py policy2)
bnd = lambda m: f"{100 * m['share']:.1f}\\% (conservative bounds {100 * m['lo']:.1f} to {100 * m['hi']:.1f}\\%)"
(OUT / "setters-one-agent.tex").write_text(bnd(tw["agent-2025"]["setters_one"]))
(OUT / "setters-one-all.tex").write_text(bnd(tw["all-2025"]["setters_one"]))
(OUT / "principals-one-agent.tex").write_text(bnd(tw["agent-2025"]["principals_one"]))
# the v2 cells of 2025 NeurIPS + ICML main tracks (twostage.POLICY2_MEASURES; codebook v2.2)
a25 = tw["all-2025"]
(OUT / "several-rational-short.tex").write_text(bnd(a25["several_rational_within"]))  # Box 2's population: self-interested, within the rules
(OUT / "rule-breaking-short.tex").write_text(bnd(a25["several_rule_breaking"]))
(OUT / "single-learner-short.tex").write_text(bnd(a25["single_learner_several_principals"]))  # counted apart from the cells
rp_ = a25["rational_prescribed"]
(OUT / "rational-prescribed-n.tex").write_text(f"{rp_['confirmed']} confirmed papers of 2025, an estimated {100 * rp_['share']:.1f}\\% of all 2025 papers (conservative bounds {100 * rp_['lo']:.1f} to {100 * rp_['hi']:.1f}\\%)")
v34_ = a25["several_v34_exclusion"]
(OUT / "v34-exclusion-sensitivity.tex").write_text(f"{bnd(v34_)} with the settings that codebook version 3.4 codes adversarial left out, against {bnd(a25['several'])} with outside attackers left out ({v34_['confirmed']} confirmed papers against {a25['several']['confirmed']})")
pts = lambda m: f"{100 * m['share']:.1f}"
if r2parties:
    cp_, cc_ = r2parties["full"]["all-2025"], r2parties["composition"]["all-2025"]
    (OUT / "cell-composition.tex").write_text(f"of the {pts(tw['all-2025']['several'])}\\%, {pts(cp_['parties_formal-model'])} points are parties in formal models, {pts(cp_['parties_humans'])} people acting for themselves, {pts(cp_['parties_ai-agents'])} AI agents of different owners and {pts(cp_['parties_other'])} other parties, of which {pts(cc_['parties_other_partitioned'])} points are clients that hold data they do not pool (federated or cross-silo; each part rounded on its own)")

# POLICY_SETTERS by PARTIES and the partner literatures by coded fields (reanalyses.py; replaces the v3.4 owners-split.tex)
rx = json.load(open("data/estimates-reanalyses-policy2.json"))
sh = lambda m: f"{100 * m['share']:.1f}\\%"
SPL = (("formal-model", "formal-model parties"), ("humans", "humans acting for themselves"), ("ai-agents", "AI agents of different owners"), ("other", "other parties"))
if "setters_by_parties" in rx:
    sbp = rx["setters_by_parties"]
    (OUT / "setters-parties.tex").write_text("; ".join(f"{lab}, {sbp[k]['one']} of the {sbp[k]['n']} code one policy setter and {sbp[k]['cell']} are in the cell" for k, lab in SPL))
pg, ptab = rx["partners"]["groups"], rx["partners"]["table"]
f_, u_ = pg["partitioned-data"], pg["partners-from-others"]
wo = lambda k, g: f"{sh(ptab[k]['several'])} to {sh(ptab[k]['without-' + g])}"
(OUT / "partners.tex").write_text(f"The first stage codes {f_['screen_2025']} main-track papers of 2025 with data partitioned across parties (DATA partitioned, for example federated or cross-silo learning); the confirming coder coded {f_['confirmer_coded']} such papers, placed {f_['cell']} in the cell with several principals and several owners and {f_['simulated']} among the settings simulated by interacting agents of one owner, and leaving them out of the cell moves the 2025 share from {wo('all-2025', 'partitioned-data')} (agent papers {wo('agent-2025', 'partitioned-data')}). The first stage codes {u_['screen_2025']} as built to act with or against agents that other parties train or run and that it has not seen in training (PARTNERS\\_FROM\\_OTHERS yes); the confirming coder coded {u_['confirmer_coded']} such papers, placed {u_['cell']} in the cell and {u_['simulated']} among the simulated settings, and leaving them out moves the 2025 share from {wo('all-2025', 'partners-from-others')} (agent papers {wo('agent-2025', 'partners-from-others')})")

(OUT / "partners-agent-share.tex").write_text(bnd(ptab["agent-2025"]["partners-from-others"]))  # Argument 4's test: 2025 agent papers built for partners others train or run

# Supplementary Note 2, role-independent REACH (codebook-deploy-roleindep.md v3) on the same pages
from deploy import crosstab
V3 = {r["id"]: r for f in sorted(glob.glob("data/coded/r2-deploy-0*.jsonl")) for r in map(json.loads, filter(str.strip, open(f)))}
assert set(V3) == {i for i, r in P.items() if dlab(r) in known}, "v3 re-code must cover the pages with a stated reach"
ct = crosstab(P, V3)
v3n = Counter({"counterparty": "customer"}.get(r["reach"], r["reach"]) for r in V3.values())
rows = [f"{ {'customer': 'counterparty'}.get(k, k)} & {pct(labs[k], n)} & {pct(v3n[k], len(V3))} \\\\" for k in known]
(OUT / "tab-deploy.tex").write_text("\n".join(rows) + "\n")
moved = sum(c for (a, b), c in ct.items() if a != b)
(OUT / "deploy-v3-moves.tex").write_text(f"{moved} of {len(V3)} pages change category: " + "; ".join(f"{c} from {a} to {b}".replace("customer", "counterparty") for (a, b), c in sorted(ct.items()) if a != b))
(OUT / "deploy-v3-short.tex").write_text(f"{v3n['cross-owner']} of {len(V3)} ({100 * v3n['cross-owner'] / len(V3):.1f}\\%) when cross-owner is decided by the system the agent acts on, against {labs['cross-owner']} ({100 * labs['cross-owner'] / n:.1f}\\%) under the original rule")
(OUT / "n-v3.tex").write_text(f"{len(V3)}")
vl = Counter(r["vendor_layer"] for r in V3.values())
(OUT / "deploy-vendor-layer.tex").write_text(f"{vl['yes']} of {len(V3)}")
# Supplementary Note 2, reach by ownership layer (codebook-deploy-layers.md v4; deploy_layers.py estimate), once coded
if Path("data/estimates-deploy-layers.json").exists():
    from deploy_layers import fragments
    for name, text in fragments(json.load(open("data/estimates-deploy-layers.json"))).items():
        (OUT / name).write_text(text)
    from deploy_layers import load_coder, derive
    lc1, lc2 = load_coder("c1"), load_coder("c2")
    org = {x["id"]: x["org"] for x in json.load(open("data/deploy-items.json"))}
    (OUT / "deploy-orgs.tex").write_text(str(len({org[i].casefold() for i in lc1 if derive(lc1[i]) and derive(lc2[i])})))
    v4 = {i for i in lc1 if derive(lc1[i]) and derive(lc2[i])}  # the pages both code as live under codebook version 4
    v2 = {i for i, r in P.items() if dlab(r) in known}  # the first coding's pages with a live agent and what it acts on
    (OUT / "deploy-v2v4-overlap.tex").write_text(f"{len(v4 & v2)} of the {len(v4)} pages both code as live are among the {len(v2)} pages of the first coding that describe a live agent and what it acts on")

# Supplementary Note 1, delineation of the frame (the fields of the raw lists it reads: fetch_frames.py --delineation)
delin = json.load(open("data/frames-delineation.json"))
from census import dedupe, norm
from estimate import main_track
NAMES = {"neurips-2020": "NeurIPS 2020", "icml-2020": "ICML 2020", "neurips-2025": "NeurIPS 2025", "icml-2025": "ICML 2025", "ec-2025": "EC 2025"}
xitems = [json.loads(l) for l in open("data/xfam/items-full.jsonl")]
rows, nonmain = [], 0
for v in NAMES:
    recs = delin[v]
    dd = dedupe(recs)
    coded = [x for x in xitems if x["venue"] == v]
    mt = sum(x["main_track"] for x in coded)
    if v == "ec-2025":
        rule = f"OpenAlex source S4363608973 (ACM EC), filter publication\\_year 2025; all records kept, including {sum(r.get('type') == 'paratext' for r in recs)} research paper that OpenAlex types as paratext"
    elif v.endswith("2020"):
        rule = "all records (the 2020 lists hold main-track papers only; no OpenReview group field)"
    else:
        grp = lambda r: (r.get("sourceurl") or "").split("group?id=")[-1] if "group?id=" in (r.get("sourceurl") or "") else "journal track"
        ms = {norm(r["name"]) for r in recs if main_track(r)}
        sat = sum(1 for r in dd if not main_track(r) and norm(r["name"]) in ms)
        other = Counter(grp(r) for r in dd if norm(r["name"]) not in ms)
        nonmain += sum(other.values())
        conf_grp = v.split("-")[0].replace("neurips", "NeurIPS").replace("icml", "ICML") + ".cc/2025/Conference"
        rule = f"OpenReview group {conf_grp}" + (f", including {sat} orals listed first under a satellite session's group" if sat else "") + "; other tracks: " + ", ".join(f"{g.replace('_', chr(92) + '_')} {n}" for g, n in other.most_common())
    rows.append(f"{NAMES[v]} & {len(recs):,} & {len(recs) - len(dd):,} & {len(coded):,} & {mt:,} & {rule} \\\\")
(OUT / "tab-delineation.tex").write_text("\n".join(rows) + "\n")
(OUT / "n-nonmain.tex").write_text(f"{nonmain:,}")

# Supplementary Note 3: attention to interacting AI agents in neighbouring fields (bibliometric.py)
bib = json.load(open("data/bibliometric.json"))
show = ["2019", "2021", "2023", "2024", "2025"]
rows = [f"{name} & " + " & ".join(f"{d['per10k'][y]:.1f}" for y in show) + f" & {d['hits']['2025']:,} \\\\" for name, d in bib["fields"].items()]
(OUT / "tab-bibliometric.tex").write_text("\n".join(rows) + "\n")
(OUT / "bibliometric-date.tex").write_text(bib["retrieved"])
print("wrote", sorted(p.name for p in OUT.iterdir()))

# Supplementary Note 3, citation links (fields/run4-broad; run 3 is the narrower earlier sample): the numbers of the Fig. 2b paragraph
LITS = ("C1", "C2", "C3", "C4", "C5", "C6", "C7", "R1", "R2", "R3", "R4")
seeds = [x for x in json.load(open("data/fields/seeds-broad.json")) if x["cluster"] in LITS]
per = [sum(x["cluster"] == c for x in seeds) for c in LITS]
(OUT / "n3-seeds.tex").write_text(f"{len(LITS)} literatures, seeded with {min(per)} to {max(per)} papers each ({len(seeds)} in all)")
(OUT / "n3-seeds-cited.tex").write_text(str(len(json.load(open("data/fields/seeds-main-cites.json")))))  # seed -> main-text citation key, checked against the manuscript by test
nc = json.load(open("data/fields/neurips-coverage.json"))  # bibliometric.py coverage
sh = [nc["with_refs"][y] / nc["n"][y] for y in nc["n"]]
(OUT / "n3-neurips-coverage.tex").write_text(f"{100 * min(sh):.0f}\\% to {100 * max(sh):.0f}\\% of NeurIPS records from {min(nc['n'])} to {max(nc['n'])}")
m1 = json.load(open("data/fields/results_m1-eleven-broad.json"))["M1"]
lay = json.load(open("data/fields/results_layers-broad.json"))
bri, lr = m1["bridges"], [x["layers_ratio"] for x in lay["loo"]]
(OUT / "n3-scatter.tex").write_text(f"{m1['2']['summary']['ratio']:.4f} of the median within them ({m1['loo']['min']:.4f} to {m1['loo']['max']:.4f} when one seed is left out at a time; {m1['1']['summary']['ratio']:.3f} on the one-seed samples)")
(OUT / "n3-bridges.tex").write_text(f"{bri['C1C2_citing_C6C7_seed']} of the {bri['C1C2_works']:,} works building on performative prediction or multi-agent learning cite a seed in the economics of learning or control, while {bri['C6C7_citing_C1C2_seed']} of the {bri['C6C7_works']:,} works building on the economics of learning or control cite a seed in performative prediction or multi-agent learning")
(OUT / "n3-layers.tex").write_text(f"ratio {lay['2']['layers']['ratio']:.2f}; {min(lr):.2f} to {max(lr):.2f} when one rules seed is left out at a time")
fr = json.load(open("data/fields/results.json"))["fairness"]
(OUT / "n3-fairness.tex").write_text(f"{fr['2012-2016']['summary']['ratio']:.2f} in 2012--2016 and {fr['2019-2023']['summary']['ratio']:.2f} in 2019--2023")
(OUT / "n3-fairness-change.tex").write_text(si_ext.rough_change(fr['2012-2016']['summary']['ratio'], fr['2019-2023']['summary']['ratio']))


def questions(folder):
    """Per objectives-check variant (file stem), the sub-objectives that need two literatures linked below the variant's threshold."""
    return {Path(f).stem: {l.split(" | ")[0] for l in open(f) if " | needs " in l and "silent pairs: none" not in l} for f in sorted(glob.glob(f"{folder}/*.txt"))}


sys.path.append(str(Path(__file__).resolve().parent / "fields" / "run4-broad"))
import crossmap  # the Box 2 sub-questions and their coded need sets (codebook-needs.md)

if crossmap.coded():  # need sets from the two blind coders; variants that find every pair linked are set aside by rule
    sq_, need_, ag_, res_, _ = crossmap.analyse()
    for name, text in crossmap.fragments(res_, sq_, need_, ag_, json.load(open("data/fields/results_m1-eleven-dcbroad.json"))["M1"]["2"]["summary"]["ratio"]).items():
        (OUT / name).write_text(text)
else:  # until the coding exists: the earlier author-key outputs, unchanged
    qn = questions("fields/run4-broad/crossmap/new")
    rest = {k: v for k, v in qn.items() if k != "work_1_0.005"}  # the one-seed share-of-works measure at 0.5% finds every pair linked
    (OUT / "n3-questions.tex").write_text(f"between {min(map(len, qn.values()))} and {max(map(len, qn.values()))} need two literatures linked at below 0.5\\% to 5\\% (sixteen variants: two link measures, both samples and four thresholds; {min(map(len, rest.values()))} to {max(map(len, rest.values()))} without the one-seed share-of-works measure at 0.5\\%")
    (OUT / "n3-robust.tex").write_text(f"{len(set.intersection(*rest.values()))}")
    qo = questions("fields/run4-broad/crossmap/old")
    (OUT / "n3-earlier.tex").write_text(f"the median link was {json.load(open('data/fields/results_m1-eleven-dcbroad.json'))['M1']['2']['summary']['ratio']:.4f} and {len(set.intersection(*qo.values()))} questions needed such a pair in every variant")
cov = lay["coverage"]
(OUT / "n3-coverage.tex").write_text(f"only {100 * cov['R3']['subfield_share_with_refs']:.0f}\\% of works in law and {100 * cov['R4']['subfield_share_with_refs']:.0f}\\% in public administration carry references")
from bibliometric import DC_TOPICS  # constants only; the fetch runs under __main__
(OUT / "n3-dc-topics.tex").write_text(f"{len(DC_TOPICS.split('|'))}")
from bibliometric import robotics_share
(OUT / "n3-control-robotics.tex").write_text(robotics_share(json.load(open("data/bibliometric-topichits-2025-2026-11-09.json"))["Control"]))
(OUT / "n3-control-ref.tex").write_text(f"{bib['area_unions']['Control']['per10k']['2025']:.1f}")

# Supplementary Note 1, pilot of the policy codebook (pilot_agreement.py; ids and adjudication in data/pilot/)
import pilot_agreement
if Path(pilot_agreement.IDS3).exists():
    for name, text in pilot_agreement.fragments(*pilot_agreement.round3()).items():
        (OUT / name).write_text(text)

# Supplementary Note 1: tipping points, the smallest systematic coder error that overturns each claim (tipping.py)
tp = json.load(open("data/estimates-tipping-policy2.json"))
P1 = lambda x: f"{100 * x:.1f}\\%"
seen = lambda o: f"{P1(o[0])} (upper {P1(o[2])})"
from tipping import ec_band, null_seen, verdict
lv, ec_, it_, tr_, se_, ra_ = (tp[k] for k in ("level", "ec", "interaction", "trend", "sector", "ratio"))
pa_ = tp.get("parties")  # the parties claim, once every v2 cell paper has a parties code
neg = lambda d, s: (1 - s) * d["n"]
rows, MG = [], []


def add(claim, over, seen_txt, need, hi, short):
    """One row of the tipping table; the margin is the overturning error over the upper bound of the observed error."""
    rows.append(f"{claim} & {over} & {seen_txt} & {need / hi:.1f} & {verdict(need, hi)} \\\\")
    MG.append((need / hi, short, verdict(need, hi)))


for g in ("0.1", "0.2"):
    add(f"2025 main track below {g[2:]}0\\% ({P1(lv['share'])})", f"misses {P1(lv['need'][g])} of negatives ({lv['need'][g] * neg(lv, lv['share']):,.0f} papers)", seen(lv["observed"]), lv["need"][g], lv["observed"][2], f"2025 main track below {g[2:]}0\\%")
k_ec = round(ec_["share"] * ec_["n"])
add(f"EC above 20\\% ({P1(ec_['share'])})", f"false positives {P1(ec_['need'])} of cell papers ({ec_['need'] * k_ec:.0f} of {k_ec})", seen(ec_["observed"]), ec_["need"], ec_["observed"][2], "EC above 20\\%")
for g in ("0.01", "0.02") if pa_ else ():
    add(f"AI agents of different owners below {g[-1]}\\% ({P1(pa_['share'])}), parties miscoded in the cell", (f"{P1(pa_['need_within'][g])} of other cell papers ({pa_['papers'][g]:.0f} of {pa_['within_n']:.0f})" if pa_['papers'][g] <= pa_['within_n'] else f"more than all {pa_['within_n']:.0f} other cell papers ({pa_['papers'][g]:.0f} needed)"), seen(pa_["observed_within"]), pa_["need_within"][g], pa_["observed_within"][2], f"AI agents of different owners below {g[-1]}\\%, parties miscoded in the cell")
    add("\\quad the same, settings hidden outside the cell", f"{100 * pa_['need_outside'][g]:.2f}\\% of other papers ({pa_['papers'][g]:.0f} of {pa_['outside_n']:,.0f})", f"{100 * pa_['observed_outside'][0]:.2f}\\% (upper {100 * pa_['observed_outside'][2]:.2f}\\%)", pa_["need_outside"][g], pa_["observed_outside"][2], f"AI agents of different owners below {g[-1]}\\%, settings hidden outside the cell")
add(f"Interaction focus below 5\\% ({P1(it_['share'])})", f"misses {P1(it_['need'])} of negatives ({it_['need'] * (1 - it_['share']) * it_['n']:,.0f} papers)", seen(it_["observed"]), it_["need"], it_["observed"][2], "interaction focus below 5\\%")
pt_ = lambda d: (lambda p, b: f"{num(100 * p)} points (bound {100 * b:.1f})")(*null_seen(d))
for g in ("0.01", "0.02"):
    add(f"No change 2020 to 2025 excludes a {g[-1]}-point rise", f"differential misses {100 * tr_['need']['hide-rise'][g]:.2f} points", pt_(tr_), tr_["need"]["hide-rise"][g], tr_["observed"], f"no change excludes a {g[-1]}-point rise")
RL = [("agent-2025", "agent papers"), ("llm-agent-2025", "LLM-agent papers"), ("other-agent-2025", "other agent papers")]
for k, lab in RL:
    r = ra_[k]
    if r["claim"] == "simulated":
        add(f"Simulate more than assume, {lab} 2025 (ratio {r['ratio']:.1f})", f"{r['flip_papers']:.0f} of {r['S']:.0f} simulated papers ({P1(r['flip_share'])}) flip to several owners", seen(r["observed"]), r["flip_share"], r["observed"][2], f"simulate more than assume, {lab}")
    else:
        add(f"Assume more than simulate, {lab} 2025 (ratio {r['ratio']:.1f})", f"{r['flip_papers']:.0f} of {r['V']:.0f} several-owner papers ({P1(r['flip_share'])}) flip to one owner", seen(r["observed"]), r["flip_share"], r["observed"][2], f"assume more than simulate, {lab}")
if pa_:  # without the parties rows the table and its margins would leave a claim out
    (OUT / "tab-tipping.tex").write_text("\n".join(rows) + "\n")
    rob = sorted(m for m in MG if m[2] == "robust")
    (OUT / "tip-margins.tex").write_text(f"{rob[0][0]:.1f} ({rob[0][1]}) to {rob[-1][0]:.1f} ({rob[-1][1]})")
assert all((m > 1) == (v == "robust") for m, _, v in MG), "margin and verdict disagree"
# the sector null and the ratio-difference tipping point are documented in docs/census-methods.md, not in the SI
(DOC / "tip-sector.tex").write_text(f"a 1-point sector gap needs a differential miss rate of {100 * se_['need']['0.01']:.2f} points against an observed {pt_(se_)} ({verdict(se_['need']['0.01'], se_['observed'])})")
a_, l_, o_, d_ = ra_["agent-2025"], ra_["llm-agent-2025"], ra_["other-agent-2025"], ra_["llm-minus-other"]
side = lambda r: (f"{r['flip_papers']:.0f} of the {r['S']:.0f} simulated papers", "several-owner settings miscoded as one owner") if r["claim"] == "simulated" else (f"{r['flip_papers']:.0f} of the {r['V']:.0f} several-owner papers", "one-owner settings miscoded as several owners")
(DOC / "tip-ratio.tex").write_text(f"bringing the ratio among 2025 agent papers from {a_['ratio']:.1f} to 1 would take {side(a_)[0]} ({P1(a_['flip_share'])}) to be {side(a_)[1]} ({P1(l_['flip_share'])} for LLM-agent and {P1(o_['flip_share'])} for other agent papers); the larger observed disagreement across that boundary, of the two directions, is {P1(a_['observed'][0])} (upper {P1(a_['observed'][2])}). The difference between the LLM-agent and other agent ratios vanishes if {d_['flip_papers']:.0f} LLM-agent papers ({P1(d_['flip_share'])}) flip")
lo_, hi_ = ec_band(ec_)
(OUT / "ec-band.tex").write_text(f"{P1(lo_)} to {P1(hi_)}")
au = tp["author"]
ac = lambda k: f"$\\kappa = {au[k]['kappa']:.2f}$ (95\\% bootstrap interval {num(au[k]['ci'][0], 2)} to {num(au[k]['ci'][1], 2)})"
bnd = lambda k: sum(v for p, v in au[k]["pairs"].items() if set(p.split(">")) == {"one", "several"})
dis_ = lambda k: au[k]["n"] - au[k]["agree"]
(OUT / "tip-author.tex").write_text(f"against the first stage on all {au['screen-owners']['n']} papers, FOCUS {ac('screen-focus')} and OWNERS {ac('screen-owners')}; against the confirming coder on the {au['confirmer-owners']['n']} it also coded, FOCUS {ac('confirmer-focus')} and OWNERS {ac('confirmer-owners')}. Of the OWNERS disagreements, {bnd('screen-owners')} of {dis_('screen-owners')} and {bnd('confirmer-owners')} of {dis_('confirmer-owners')} lie on the boundary between one and several owners (the rest separate ``not fixed'' from several); against the confirming coder, {au['confirmer-owners']['pairs'].get('one>several', 0)} of these are papers I coded one owner where it coded several")
ap_ = json.load(open("data/estimates-tipping-author-policy2.json"))
(OUT / "tip-author-policy.tex").write_text(f"{ap_['raise']} of {ap_['m']} would raise the agent-paper ratio of simulated to several-owner settings, {ap_['lower']} would lower it and {ap_['leave']} would leave it unchanged")
(OUT / "n-author-check.tex").write_text(f"{au['screen-owners']['n']}")
(OUT / "author-draw.tex").write_text(si_ext.author_draw(json.load(open("data/xfam/focus-check-20-draw.json"))))  # the 20-paper check set as drawn
(OUT / "author-kappa-short.tex").write_text(f"$\\kappa = {au['screen-owners']['kappa']:.2f}$ with the screening model and $\\kappa = {au['confirmer-owners']['kappa']:.2f}$ with the confirming model (on the {au['confirmer-owners']['n']} papers it coded)")
print("wrote tipping fragments")
