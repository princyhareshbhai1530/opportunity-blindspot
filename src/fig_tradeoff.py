"""figures/tradeoff.png from outputs/mitigation_summary.json (test set)."""
import json
from core import ROOT
from figstyle import plt, finish, NAVY, INK2, TEAL, GREEN, AMBER, GRID

d = json.loads((ROOT / "outputs" / "mitigation_summary.json").read_text())
rows = d["test_table"]
NAMES = {"beta=0.00": "Profile only (beta = 0)", "beta=0.45": "Personalized (beta = 0.45)",
         "history_cap": "History cap", "profile_floor": "Profile floor", "exploration": "Exploration slots"}
COL = {"history_cap": TEAL, "profile_floor": GREEN, "exploration": AMBER}
PARAM = {"history_cap": "beta cap {}", "profile_floor": "tau {}", "exploration": "k = {}"}
OFF = {"history_cap": (10, -16), "exploration": (-10, 8), "profile_floor": (10, 8)}

fig, axes = plt.subplots(1, 2, figsize=(11, 5.0))
fig.subplots_adjust(top=0.82, bottom=0.30, wspace=0.28)
for ax, ykey, ylab, thr in [(axes[0], "hit10_retained_pct", "Hit@10 gain retained (%)", 75),
                            (axes[1], "compat_cost_pct", "Compatibility cost vs profile only (%)", 2)]:
    ax.axvspan(50, 110, color=GRID, alpha=0.6, lw=0)
    ax.axvline(50, color=INK2, lw=1, ls=":")
    ax.axhline(thr, color=INK2, lw=1, ls=":")
    for r in rows:
        x, y = r["TEG_reduction_pct"], r[ykey]
        if r["role"] == "baseline":
            ax.plot(x, y, marker="s", ms=10, mfc="white", mec=NAVY, mew=2, ls="none")
            dx = -10 if x > 80 else 10
            ax.annotate(NAMES[r["label"]], (x, y), textcoords="offset points", xytext=(dx, 10),
                        ha="right" if dx < 0 else "left", fontsize=8.5, color=NAVY, fontweight="bold")
            continue
        m, p = r["label"].split("=")
        xe = [[x - r["TEG_reduction_pct_ci"][0]], [r["TEG_reduction_pct_ci"][1] - x]]
        ye = [[y - r[ykey + "_ci"][0]], [r[ykey + "_ci"][1] - y]]
        tag = "PASS" if r["pass"] else "FAIL"
        ax.errorbar(x, y, xerr=xe, yerr=ye, fmt="o", ms=9, color=COL[m], mec="white", mew=2,
                    ecolor=COL[m], elinewidth=1.4, capsize=3, label=f"{NAMES[m]} ({PARAM[m].format(p)}): {tag}")
        o = OFF[m]
        ax.annotate(tag, (x, y), textcoords="offset points", xytext=o, ha="left" if o[0] > 0 else "right",
                    fontsize=8.5, color=NAVY, fontweight="bold")
    ax.set_xlim(-10, 110)
    ax.set_xlabel("Twin Exposure Gap reduction vs personalized (%)")
    ax.set_ylabel(ylab)
axes[0].set_ylim(-10, 115)
axes[1].set_ylim(-0.2, 2.6)
axes[0].set_title("No fix halves the gap and keeps 75% of the Hit@10 gain")
axes[1].set_title("All three fixes stay under the 2% compatibility guard")
axes[0].text(108, 112, "Pass zone", fontsize=8.5, color=INK2, va="top", ha="right")
axes[1].text(108, 2.55, "Pass zone", fontsize=8.5, color=INK2, va="top", ha="right")
h, l = axes[0].get_legend_handles_labels()
fig.legend(h, l, loc="lower center", ncol=3, bbox_to_anchor=(0.5, 0.07), fontsize=9)
finish(fig, "Mitigation trade-off on held-out test data: every fix fails at least one pre-registered test",
       "Source: JTH v1.1 test set; 1,200 twin pairs and 3,769 held-out candidates; settings tuned on the tune set; "
       "95% bootstrap CIs (3,000 resamples); seed 20261115.", ROOT / "figures" / "tradeoff.png")
print("saved")
