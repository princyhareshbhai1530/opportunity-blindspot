"""figures/gap_by_beta.png: test-set Twin Exposure Gap with 95% CI at each history weight (from results.csv).

Sized for a one-third-width cell on PDF page 3 (about 3 in), all text >= 10 pt at native size.
"""
import pandas as pd
from core import ROOT
from figstyle import plt, save_measured, BLUE, NAVY, INK2, AMBER, SLATE

d = pd.read_csv(ROOT / "outputs" / "results.csv")
d = d[(d.set == "test") & (d.metric == "TEG_pp")]
t = d[d.condition == "treatment"].sort_values("beta")
p = d[d.condition == "placebo_identical_history"].sort_values("beta")

fig, ax = plt.subplots(figsize=(3.0, 2.5))
ax.fill_between(t.beta, t.ci_low, t.ci_high, color=BLUE, alpha=0.18, lw=0)
ax.plot(t.beta, t.estimate, color=BLUE, lw=2, marker="o", ms=7, mec="white", mew=1.5, label="Twin gap (95% CI)")
ax.plot(p.beta, p.estimate, color=SLATE, lw=1.5, ls=":", marker="o", ms=4, label="Placebo (same history)")
ax.axvline(0.45, color=AMBER, lw=1.5, ls="--")
for _, r in t.iterrows():
    if r.beta in (0.15, 0.45, 0.60):
        ax.annotate(f"{r.estimate:.2f}", (r.beta, r.estimate), textcoords="offset points",
                    xytext=(-5, 6), ha="right", fontsize=10, color=NAVY, fontweight="bold")
ax.set_xticks([0, 0.15, 0.30, 0.45, 0.60])
ax.set_xticklabels(["0", ".15", ".30", ".45", ".60"])
ax.set_xlabel("History weight beta", fontsize=10)
ax.set_ylabel("Gap in high-value share (pp)", fontsize=10)
ax.tick_params(labelsize=10)
ax.set_ylim(-0.6, max(t.ci_high) * 1.3)
ax.legend(loc="upper left", fontsize=10, handlelength=1.6, borderaxespad=0.2)
ax.set_title("The gap grows as history weight grows", fontsize=10.5, loc="left", x=-0.27)
save_measured(fig, ROOT / "figures" / "gap_by_beta.png")
print("saved")
