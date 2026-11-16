"""Compact charts for PDF page 3 (one-third-width cells, all text >= 10 pt at native size).

figures/heldout_hit10.png  Hit@10 only (from results.csv, test set)
figures/tradeoff_pdf.png   gap cut vs Hit@10 kept for the three tuned fixes (from mitigation_summary.json, test set)
The full two-panel versions (heldout_curve.png, tradeoff.png) are still produced by fig_heldout.py / fig_tradeoff.py.
"""
import json
import pandas as pd
from matplotlib.patches import Rectangle
from core import ROOT
from figstyle import plt, save_measured, BLUE, NAVY, INK2, AMBER, TEAL, GREEN, GRID

# ---- Hit@10
d = pd.read_csv(ROOT / "outputs" / "results.csv")
x = d[(d.set == "test") & (d.condition == "real_history") & (d.metric == "heldout_hit10")].sort_values("beta")
fig, ax = plt.subplots(figsize=(3.0, 2.5))
ax.fill_between(x.beta, x.ci_low, x.ci_high, color=BLUE, alpha=0.18, lw=0)
ax.plot(x.beta, x.estimate, color=BLUE, lw=2, marker="o", ms=7, mec="white", mew=1.5, label="Hit@10 (95% CI)")
ax.axvline(0.45, color=AMBER, lw=1.5, ls="--")
for b, off, ha in [(0.0, (6, -14), "left"), (0.45, (-6, 6), "right")]:
    r = x[x.beta == b].iloc[0]
    ax.annotate(f"{r.estimate:.1f}%", (b, r.estimate), textcoords="offset points", xytext=off, ha=ha,
                fontsize=10, color=NAVY, fontweight="bold")
ax.set_xticks([0, 0.15, 0.30, 0.45, 0.60]); ax.set_xticklabels(["0", ".15", ".30", ".45", ".60"])
ax.set_xlabel("History weight beta", fontsize=10)
ax.set_ylabel("Hidden next job in Top 10 (%)", fontsize=10)
ax.tick_params(labelsize=10)
ax.set_ylim(0, max(x.ci_high) * 1.25)
ax.legend(loc="upper left", fontsize=10, handlelength=1.6, borderaxespad=0.2)
ax.set_title("History helps predict the next job", fontsize=10.5, loc="left", x=-0.25)
save_measured(fig, ROOT / "figures" / "heldout_hit10.png")

# ---- trade-off (one panel)
m = json.loads((ROOT / "outputs" / "mitigation_summary.json").read_text())
NAME = {"history_cap": "Cap", "profile_floor": "Floor", "exploration": "Explore"}
COL = {"history_cap": TEAL, "profile_floor": GREEN, "exploration": AMBER}
LAB = {"history_cap": (97, 62), "profile_floor": (17, 66), "exploration": (45, 38)}  # label positions in data units, clear of CIs
fig, ax = plt.subplots(figsize=(3.0, 2.5))
ax.add_patch(Rectangle((50, 75), 60, 45, color=GRID, alpha=0.9, lw=0))
ax.text(108, 117, "Pass zone", ha="right", va="top", fontsize=10, color=INK2)
ax.axvline(50, color=INK2, lw=1, ls=":"); ax.axhline(75, color=INK2, lw=1, ls=":")
for r in m["test_table"]:
    xv, yv = r["TEG_reduction_pct"], r["hit10_retained_pct"]
    if r["role"] == "baseline":
        ax.plot(xv, yv, marker="s", ms=8, mfc="white", mec=NAVY, mew=1.8, ls="none")
        lab = "Profile only" if r["label"] == "beta=0.00" else "Personalized"
        if xv > 50:
            ax.text(xv - 6, yv + 1, lab, ha="right", va="center", fontsize=10, color=NAVY)
        else:
            ax.text(xv - 4, yv + 11, lab, ha="left", va="center", fontsize=10, color=NAVY)
        continue
    k = r["label"].split("=")[0]
    xe = [[xv - r["TEG_reduction_pct_ci"][0]], [r["TEG_reduction_pct_ci"][1] - xv]]
    ye = [[yv - r["hit10_retained_pct_ci"][0]], [r["hit10_retained_pct_ci"][1] - yv]]
    ax.errorbar(xv, yv, xerr=xe, yerr=ye, fmt="o", ms=7, color=COL[k], mec="white", mew=1.5,
                ecolor=COL[k], elinewidth=1.3, capsize=2.5)
    verdict = "PASS" if r["pass"] else "FAIL"
    ax.text(*LAB[k], NAME[k] + "\n" + verdict, ha="center", va="center", fontsize=10,
            color={"history_cap": "#14838C", "profile_floor": GREEN, "exploration": "#B57D00"}[k],
            fontweight="bold", linespacing=1.1)
ax.set_xlim(-8, 110); ax.set_ylim(-10, 120)
ax.set_xlabel("Gap cut vs personalized (%)", fontsize=10)
ax.set_ylabel("Hit@10 gain kept (%)", fontsize=10)
ax.tick_params(labelsize=10)
ax.set_title("No fix lands in the pass zone", fontsize=10.5, loc="left", x=-0.25)
save_measured(fig, ROOT / "figures" / "tradeoff_pdf.png")
print("saved")
