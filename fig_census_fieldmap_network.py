"""Figure 2 (draft, 2026-11-09): a, the census (unchanged from fig_census.py); b, how often the literatures that hold the
pieces of interaction-time research cite each other, with algorithmic fairness before its first conference as an inset.
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

# a: census, same code and data as fig_census.py
raw = json.load(open("data/estimates-twostage.json"))
est = {k: {"n": v["n"], **{m: (v[m]["share"], v[m]["lo"], v[m]["hi"]) for m in ("several", "interaction", "simulated")}} for k, v in raw.items() if "n" in v}
rows = [("All papers, 2020", est["all-2020"]), ("All papers, 2025", est["all-2025"]), ("Agent papers, 2020", est["agent-2020"]),
        ("Agent papers, 2025", est["agent-2025"]), ("LLM-agent papers, 2025", est["llm-agent-2025"]),
        ("Other agent papers, 2025", est["other-agent-2025"]), ("EC 2025 (control)", est["ec-2025"])]
ax = fig.add_axes([0.27, 0.565, 0.70, 0.40])
for i, (lab, e) in enumerate(reversed(rows)):
    for m, dy, col, mk in (("several", 0.22, BLUE, "o"), ("interaction", 0.0, ORANGE, "D"), ("simulated", -0.22, GREY, "s")):
        v, lo, hi = e[m]
        ax.plot([100 * lo, 100 * hi], [i + dy, i + dy], color=col, lw=1.3, solid_capstyle="butt")
        ax.plot(100 * v, i + dy, mk, color=col, ms=5, zorder=3)
    v, lo, hi = e["several"]
    ax.text(100 * hi + 1.5, i + 0.22, f"{100 * v:.1f}%  (n = {e['n']})", va="center", fontsize=8, color=BLUE)
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
ax.text(38, 5.95, "several principals with several owners", color=BLUE, fontsize=8)
ax.text(38, 5.6, "...of which the contribution is about the interaction", color=ORANGE, fontsize=8)
ax.text(38, 5.25, "several principals simulated by one owner", color=GREY, fontsize=8)
fig.text(0.01, 0.975, "a", fontsize=11, fontweight="bold")

# b: field map
m1 = json.load(open(bib + "/results_m1.json"))["M1"]["1"]
fair = json.load(open(sys.argv[3] if len(sys.argv) > 3 else bib + "/results.json"))["fairness"]["2012-2016"]
st = lambda ref, a, b: max(ref[a][b] / ref[a][a], ref[b][a] / ref[b][b])
RED = "#9a3a2e"
NODES = {  # rules between agents (left column), learners inside the rules (right)
    "R1": ("Mechanism design", RED, (0.06, 0.92), "right"), "R2": ("Distributed computing", RED, (0.06, 0.64), "right"),
    "R3": ("Law", RED, (0.06, 0.36), "right"), "R4": ("Political science", RED, (0.06, 0.08), "right"),
    "C3": ("Learning in games", BLUE, (0.50, 0.92), "right"), "C2": ("Multi-agent RL", BLUE, (0.50, 0.64), "right"),
    "C4": ("Cooperative AI", BLUE, (0.50, 0.36), "right"), "C1": ("Performative prediction", BLUE, (0.50, 0.08), "right"),
    "C6": ("Economics of learning", PURPLE, (0.86, 0.92), "right"), "C5": ("ML-systems feedback loops", BLUE, (0.86, 0.50), "right"),
    "C7": ("System identification", GREEN, (0.86, 0.08), "right")}
FNODES = {"F1": ("Data mining", GREY, (0.12, 0.22), "below"), "F2": ("ML and theory", GREY, (0.88, 0.22), "below"), "F3": ("Law and policy", GREY, (0.50, 0.80), "above")}


def draw(ax, nodes, ref, sizes, fs, scale):
    for a, b in itertools.combinations(nodes, 2):
        (xa, ya), (xb, yb) = nodes[a][2], nodes[b][2]
        w = st(ref, a, b)
        if w < 0.01:
            continue  # below 1%: no line; isolation shows as a node without lines
        else:
            ax.plot([xa, xb], [ya, yb], lw=0.5 + 6 * min(w, 1.5) * scale, color=GREY, alpha=0.7, solid_capstyle="round", zorder=1)
            if w >= 0.10:
                ax.text((xa + xb) / 2, (ya + yb) / 2, f"{w:.0%}", fontsize=fs - 1, color=INK, ha="center", va="center",
                        bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none"), zorder=3)
    smax = max(sizes.values())
    for k, (name, col, (x, y), side) in nodes.items():
        r = (40 + 520 * (sizes[k] / smax) ** 0.5) * scale
        ax.scatter([x], [y], s=r, color=col, zorder=2, edgecolor="white", lw=1)
        d = 0.05 + (r ** 0.5) / 450
        tx, ty, ha, va = {"above": (x, y + d, "center", "bottom"), "below": (x, y - d, "center", "top"), "right": (x + d * 0.5 + 0.015, y + d * 0.9, "left", "bottom")}[side]
        ax.text(tx, ty, name, fontsize=fs, ha=ha, va=va, color=INK, zorder=4)
    ax.axis("off")


axb = fig.add_axes([0.01, 0.04, 0.66, 0.44])
draw(axb, NODES, m1["ref"], m1["sizes"], 8.5, 1.0)
axb.set_xlim(-0.04, 1.12); axb.set_ylim(-0.06, 1.10)
axb.text(0.06, -0.05, "rules between agents", fontsize=7.5, color=RED, ha="left", va="top", style="italic")
axb.text(0.50, -0.05, "learners inside the rules", fontsize=7.5, color=BLUE, ha="left", va="top", style="italic")
fig.text(0.01, 0.50, "b", fontsize=11, fontweight="bold")
axi = fig.add_axes([0.70, 0.12, 0.29, 0.26])
draw(axi, FNODES, fair["ref"], fair["sizes"], 7.5, 0.6)
axi.set_xlim(-0.15, 1.15); axi.set_ylim(-0.15, 1.1)
axi.set_title("For comparison: algorithmic\nfairness, 2012-2016", fontsize=8, color=INK)
for ext in ("pdf", "png"):
    fig.savefig(f"{out}.{ext}", dpi=220)
silent = [f"{a}-{b}" for a, b in itertools.combinations(NODES, 2) if st(m1["ref"], a, b) < 0.01]
print(len(silent), "of", len(list(itertools.combinations(NODES, 2))), "pairs below 1% (not drawn):", silent)
assert all(st(m1["ref"], "C7", k) < 0.01 for k in NODES if k != "C7"), "caption says system identification has no link of 1%"
