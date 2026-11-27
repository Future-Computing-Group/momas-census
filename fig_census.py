"""Figure 1: share of papers whose setting has several principals, from the full two-stage census, with conservative 95% bounds."""
import json
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

raw = json.load(open("data/estimates-twostage.json"))  # written by twostage.py (full census, two-stage confirmation)
est = {k: {"n": v["n"], **{m: (v[m]["share"], v[m]["lo"], v[m]["hi"]) for m in ("several", "interaction", "simulated")}} for k, v in raw.items() if "n" in v}
rows = [
    ("All papers, 2020", est["all-2020"]),
    ("All papers, 2025", est["all-2025"]),
    ("Agent papers, 2020", est["agent-2020"]),
    ("Agent papers, 2025", est["agent-2025"]),
    ("LLM-agent papers, 2025", est["llm-agent-2025"]),
    ("Other agent papers, 2025", est["other-agent-2025"]),
    ("EC 2025 (comparison)", est["ec-2025"]),
]
from si_ext import ext_rows  # AAMAS 2025 as a second comparison venue once the extension is estimated; ICLR is held out
rows += [(f"{lab} (comparison)", {"n": e["n"], **{m: (e[m]["share"], e[m]["lo"], e[m]["hi"]) for m in ("several", "interaction", "simulated")}}) for lab, e in ext_rows(raw)]
fig, ax = plt.subplots(figsize=(6.8, 3.5))
for i, (lab, e) in enumerate(reversed(rows)):
    for m, dy, col, mk in (("several", 0.22, "#1f4e79", "o"), ("interaction", 0.0, "#c26a1b", "D"), ("simulated", -0.22, "#8a8a8a", "s")):
        v, lo, hi = e[m]
        ax.plot([100 * lo, 100 * hi], [i + dy, i + dy], color=col, lw=1.3, solid_capstyle="butt")
        ax.plot(100 * v, i + dy, mk, color=col, ms=5, zorder=3)
    v, lo, hi = e["several"]
    ax.text(100 * hi + 1.5, i + 0.22, f"{100 * v:.1f}%  (n = {e['n']})", va="center", fontsize=8, color="#1f4e79")
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
ax.text(45, len(rows) - 1 - 0.05, "several principals with several owners", color="#1f4e79", fontsize=8)
ax.text(45, len(rows) - 1 - 0.4, "...of which the contribution is about the interaction", color="#c26a1b", fontsize=8)
ax.text(45, len(rows) - 1 - 0.75, "several principals simulated by one owner", color="#8a8a8a", fontsize=8)
fig.tight_layout()
out = sys.argv[1] if len(sys.argv) > 1 else "fig-census"
fig.savefig(out + ".pdf")
fig.savefig(out + ".png", dpi=220)
for lab, e in rows:
    print(lab, e)
