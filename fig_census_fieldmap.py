"""Figure 2 (draft, 2026-11-09): a, the census (unchanged from fig_census.py); b, how often the eleven literatures that hold
the pieces of interaction-time research cite each other, as a triangular matrix, with algorithmic fairness before (2012-2016) and
after (2019-2023) its first conference as two insets on the same scale (the node-link version is fig_census_fieldmap_network.py).
Link strength b: reference share into the other literature over reference share into the literature's own corpus, larger
direction (one-seed OpenAlex corpora). Usage: python3 -I fig_census_fieldmap.py <bibliometric dir> <out prefix>"""
import itertools
import json
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

BLUE, ORANGE, GREY, GREEN, SILENT, INK, PURPLE = "#1f4e79", "#c26a1b", "#8a8a8a", "#2e7d6b", "#c4c4c4", "#222222", "#7a5c99"
bib, out = sys.argv[1], sys.argv[2]

fig = plt.figure(figsize=(6.8, 7.0))

# a: census, the v2 policy pass (codebook-policy-v2.2.md; estimates-twostage.json keys policy2, policy2-ext): several = POLICY_SETTERS
# and PRINCIPALS several without an outside attacker; simulated = interacting agents under one owner serving several principals (codebook v2)
tw = json.load(open("data/estimates-twostage.json"))
raw = {**tw["policy2"], "ext": tw["policy2-ext"]}
est = {k: {"n": v["n"], **{m: (v[m]["share"], v[m]["lo"], v[m]["hi"]) for m in ("several", "interaction", "simulated")}} for k, v in raw.items() if "screened" in v}
# EC is counted in full; its several-owner bar is the band the observed disagreement between the two coders allows (tipping.ec_band)
from tipping import ec_band
est["ec-2025"]["several"] = (est["ec-2025"]["several"][0], *ec_band(json.load(open("data/estimates-tipping-policy2.json"))["ec"]))
rows = [("All papers, 2020", est["all-2020"]), ("All papers, 2025", est["all-2025"]), ("Agent papers, 2020", est["agent-2020"]),
        ("Agent papers, 2025", est["agent-2025"]), ("LLM-agent papers, 2025", est["llm-agent-2025"]),
        ("Other agent papers, 2025", est["other-agent-2025"]), ("EC 2025 (comparison)", est["ec-2025"])]
from si_ext import ext_rows  # AAMAS 2025 as a second comparison venue once the extension is estimated; ICLR is held out
rows += [(f"{lab} (comparison)", {"n": e["n"], **{m: (e[m]["share"], e[m]["lo"], e[m]["hi"]) for m in ("several", "interaction", "simulated")}}) for lab, e in ext_rows(raw)]
ax = fig.add_axes([0.27, 0.565, 0.70, 0.40])
for i, (lab, e) in enumerate(reversed(rows)):
    for m, dy, col, mk in (("several", 0.22, BLUE, "o"), ("interaction", 0.0, ORANGE, "D"), ("simulated", -0.22, GREY, "s")):
        v, lo, hi = e[m]
        ax.plot([100 * lo, 100 * hi], [i + dy, i + dy], color=col, lw=1.3, solid_capstyle="butt")
        ax.plot(100 * v, i + dy, mk, color=col, ms=5, zorder=3)
    v, lo, hi = e["several"]
    right = hi < 0.6  # a bar reaching far right takes its label on the left
    ax.text(100 * (hi if right else lo) + (1.5 if right else -1.5), i + 0.22, f"{100 * v:.1f}%  (n = {e['n']})", va="center", ha="left" if right else "right", fontsize=8, color=BLUE)
ax.set_yticks(range(len(rows)))
ax.set_yticklabels([r[0] for r in reversed(rows)], fontsize=9)
ax.set_xlim(0, 100)
ax.set_xlabel("Papers (%)", fontsize=9)
ax.tick_params(axis="x", labelsize=8.5)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.tick_params(axis="y", length=0)
ax.grid(axis="x", color="#e2e2e2", lw=0.6)
ax.set_axisbelow(True)
ax.text(38, len(rows) - 1 - 0.05, "several principals with several owners", color=BLUE, fontsize=8)
ax.text(38, len(rows) - 1 - 0.4, "...of which the contribution is about the interaction", color=ORANGE, fontsize=8)
ax.text(38, len(rows) - 1 - 0.75, "several principals, interacting agents of one owner", color=GREY, fontsize=8)
fig.text(0.01, 0.975, "a", fontsize=11, fontweight="bold")

# b: link matrix
import numpy as np
from matplotlib.colors import LogNorm

m1 = json.load(open(bib + "/results_m1-eleven-broad.json"))["M1"]["1"]
fairs = json.load(open(sys.argv[3] if len(sys.argv) > 3 else bib + "/results.json"))["fairness"]
st = lambda ref, a, b: max(ref[a][b] / ref[a][a], ref[b][a] / ref[b][b])
ORDER = [("R1", "Economics of the rules"), ("R2", "Distributed computing"), ("R3", "Law"), ("R4", "Political science"),
         ("C3", "Learning in games"), ("C2", "Multi-agent RL"), ("C4", "Cooperative AI"), ("C1", "Performative prediction"),
         ("C5", "ML-system loops"), ("C6", "Economics of learning"), ("C7", "Control")]
FORDER = [("F1", "Data mining"), ("F2", "ML and theory"), ("F3", "Law and policy")]
norm = LogNorm(vmin=0.01, vmax=1.0)
cmap = plt.get_cmap("Blues")


def tri(ax, order, ref, fs, show_vals=True, row_labels=True):
    """Lower triangle without the empty first row and last column: rows 2..n (labels left) against columns 1..n-1 (labels below)."""
    n = len(order)
    for i in range(1, n):
        for j in range(i):
            w = st(ref, order[i][0], order[j][0])
            col = "white" if w < 0.01 else cmap(norm(min(w, 1.0)))
            ax.add_patch(plt.Rectangle((j, n - 1 - i), 1, 1, facecolor=col, edgecolor="#d9d9d9", lw=0.5))
            if show_vals and w >= 0.05:
                ax.text(j + 0.5, n - 1 - i + 0.5, f"{w:.0%}" if w < 9.995 else ">999%", ha="center", va="center", fontsize=fs - 1.5,
                        color="white" if norm(min(w, 1.0)) > 0.6 else INK)
    for i, (_, lab) in enumerate(order[1:] if row_labels else [], start=1):
        ax.text(-0.15, n - 1 - i + 0.5, lab, ha="right", va="center", fontsize=fs, color=INK)
    for j, (_, lab) in enumerate(order[:-1]):
        ax.text(j + 0.6, -0.15, lab, ha="right", va="top", rotation=45, rotation_mode="anchor", fontsize=fs, color=INK)
    ax.set_xlim(-0.05, n - 1 + 0.05); ax.set_ylim(-0.05, n - 1 + 0.05); ax.set_aspect("equal"); ax.axis("off")


axb = fig.add_axes([0.25, 0.175, 0.40, 0.305])
tri(axb, ORDER, m1["ref"], 8.5)
n = len(ORDER)
axb.plot([4, 4], [0, n - 4], color=INK, lw=0.8)            # rules fields (first four) against learning fields
axb.plot([0, 4], [n - 4, n - 4], color=INK, lw=0.8)
axb.text(n - 1, n - 1, "Rules between agents:\nthe first four fields.\nLearners inside the\nrules: the rest.\nFramed: links\nbetween the two.", ha="right", va="top", fontsize=7.5, color=GREY)
fig.text(0.01, 0.50, "b", fontsize=11, fontweight="bold")
fig.text(0.845, 0.475, "For comparison: algorithmic fairness,\nbefore and after its first conference", ha="center", va="bottom", fontsize=8, color=INK)
for x, period, rl in ((0.745, "2012-2016", True), (0.865, "2019-2023", False)):
    axi = fig.add_axes([x, 0.30, 0.10, 0.10])
    tri(axi, FORDER, fairs[period]["ref"], 7, row_labels=rl)
    axi.set_title(period.replace("-", "\u2013"), fontsize=8, color=INK)
cax = fig.add_axes([0.71, 0.17, 0.26, 0.018])
cb = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), cax=cax, orientation="horizontal")
cb.set_ticks([0.01, 0.03, 0.1, 0.3, 1.0]); cb.set_ticklabels(["1%", "3%", "10%", "30%", "100%"]); cb.ax.tick_params(labelsize=7.5)
cb.set_label("link, relative to own citations\n(white: below 1%)", fontsize=7.5)
for ext in ("pdf", "png"):
    fig.savefig(f"{out}.{ext}", dpi=220, metadata={"CreationDate": None} if ext == "pdf" else None)  # no date stamp: byte-reproducible
below = [f"{a}-{b}" for a, b in itertools.combinations([o[0] for o in ORDER], 2) if st(m1["ref"], a, b) < 0.01]
print(len(below), "of 55 pairs below 1%")
print("control (C7) links of 1% or more:", {k: round(st(m1["ref"], "C7", k), 4) for k, _ in ORDER if k != "C7" and st(m1["ref"], "C7", k) >= 0.01})
