"""Field map: how actively the literatures behind the interaction-time items cite each other, against algorithmic fairness
before and after FAccT. Link strength = how often one literature cites the other, relative to how often it cites itself (reference share into
the other literature divided by reference share into its own; the larger of the two directions). 100% means "cites the
other as much as itself". One-seed corpora for every panel, so the fairness baseline is like for like.
Usage: python3 -I fieldmap.py results.json results_m1.json out_prefix"""
import itertools, json, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

INK, GREY, SILENT = "#1d2230", "#8a8f9c", "#c9ccd3"
COL = {"ai": "#2c3f86", "econ": "#a26f0c", "ctrl": "#1f7a6d", "fair": "#6b4fa0"}
NODES = {  # name, group, position, label side
    "C1": ("Performative\nprediction", "ai", (0.30, 0.86), "above"), "C2": ("Multi-agent RL", "ai", (0.02, 0.55), "below"),
    "C3": ("Learning in games\nand collusion", "ai", (0.16, 0.14), "below"), "C4": ("Cooperative AI and\nmulti-agent safety", "ai", (0.46, 0.14), "below"),
    "C5": ("ML-systems\nfeedback loops", "ai", (0.50, 0.62), "right"), "C6": ("Economics of\nlearning and policy", "econ", (0.92, 0.86), "above"),
    "C7": ("System\nidentification", "ctrl", (0.92, 0.14), "below"),
}
FNODES = {"F1": ("Data mining", (0.10, 0.18), "below"), "F2": ("ML and theory", (0.90, 0.18), "below"), "F3": ("Law and policy", (0.50, 0.80), "above")}


def strength(ref, a, b):
    return max(ref[a][b] / ref[a][a], ref[b][a] / ref[b][b])


def draw(ax, nodes, work, sizes, colour_of, title):
    for a, b in itertools.combinations(nodes, 2):
        (xa, ya), (xb, yb) = nodes[a][-2], nodes[b][-2]
        w = strength(work, a, b)
        if w < 0.01:
            ax.plot([xa, xb], [ya, yb], ls=(0, (1, 2.5)), lw=0.8, color=SILENT, zorder=1)
        else:
            ax.plot([xa, xb], [ya, yb], lw=0.6 + 6 * min(w, 1.5), color=GREY, alpha=0.75, solid_capstyle="round", zorder=1)
            if w >= 0.10:
                ax.text((xa + xb) / 2, (ya + yb) / 2, f"{w:.0%}", fontsize=7.5, color=INK, ha="center", va="center",
                        bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none"), zorder=3)
    smax = max(sizes.values())
    for k, v in nodes.items():
        x, y = v[-2]
        r = 60 + 700 * (sizes[k] / smax) ** 0.5
        ax.scatter([x], [y], s=r, color=colour_of(k), zorder=2, edgecolor="white", lw=1)
        d = 0.05 + (r ** 0.5) / 500
        pos = {"above": (x, y + d + 0.03, "center", "bottom"), "below": (x, y - d - 0.03, "center", "top"),
               "right": (x + d + 0.04, y, "left", "center")}[v[-1]]
        ax.text(pos[0], pos[1], v[0], fontsize=7.5, ha=pos[2], va=pos[3], color=INK, zorder=4)
    ax.set_title(title, fontsize=9, color=INK, loc="left")
    ax.set_xlim(-0.14, 1.12); ax.set_ylim(-0.12, 1.12); ax.axis("off")


def main(res, res_m1, out):
    m1 = json.load(open(res_m1))["M1"]["1"]
    fair = json.load(open(res))["fairness"]
    fig = plt.figure(figsize=(7.2, 4.0))
    ax = fig.add_axes([0.01, 0.10, 0.60, 0.82])
    draw(ax, NODES, m1["ref"], m1["sizes"], lambda k: COL[NODES[k][1]], "a  Interaction-time literatures, 2015-2026")
    for i, (period, lab) in enumerate([("2012-2016", "b  Algorithmic fairness, 2012-2016"),
                                       ("2019-2023", "c  Algorithmic fairness, 2019-2023")]):
        axf = fig.add_axes([0.64, 0.53 - 0.43 * i, 0.35, 0.38])
        draw(axf, FNODES, fair[period]["ref"], fair[period]["sizes"], lambda k: COL["fair"], lab)
    fig.text(0.01, 0.045, "Line width: how often one literature cites the other, relative to how often it cites itself (larger direction; "
             "100% = as often). Dotted: below 1%.", fontsize=6.5, color=GREY)
    fig.text(0.01, 0.015, "Dot area: number of papers. FAccT began in 2018 (as FAT*). Source: OpenAlex citation sample.",
             fontsize=6.5, color=GREY)
    for ext in ("pdf", "png"):
        fig.savefig(f"{out}.{ext}", dpi=220)
    silent = sum(strength(m1["ref"], a, b) < 0.01 for a, b in itertools.combinations(NODES, 2))
    print(f"interaction-time pairs below 1%: {silent} of 21")
    assert silent >= 1


if __name__ == "__main__":
    main(*sys.argv[1:4])
