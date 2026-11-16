"""figures/heldout_curve.png from outputs/results.csv (test set only)."""
import pandas as pd
from core import ROOT
from figstyle import plt, finish, BLUE, NAVY, INK2, AMBER

d = pd.read_csv(ROOT / "outputs" / "results.csv")
d = d[(d.set == "test") & (d.condition == "real_history")]
fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
fig.subplots_adjust(top=0.82, bottom=0.2, wspace=0.25)
for ax, met, lab, scale, fmt in [(axes[0], "heldout_hit10", "Hit@10: hidden job in Top 10 (%)", 1, "{:.1f}%"),
                                 (axes[1], "heldout_mrr", "MRR: mean of 1 / rank of hidden job", 1, "{:.3f}")]:
    x = d[d.metric == met].sort_values("beta")
    ax.fill_between(x.beta, x.ci_low, x.ci_high, color=BLUE, alpha=0.15, lw=0, label="95% bootstrap CI")
    ax.plot(x.beta, x.estimate, color=BLUE, lw=2, marker="o", ms=8, mec="white", mew=2, label="Test set estimate")
    ax.axvline(0.45, color=AMBER, lw=1.5, ls="--", label="Phase 1 operating point (beta = 0.45)")
    for b in [0.0, 0.45, 0.60]:
        r = x[x.beta == b].iloc[0]
        ax.annotate(fmt.format(r.estimate), (b, r.estimate), textcoords="offset points", xytext=(-10 if b == 0.6 else 8, -4 if b == 0.6 else -18),
                    ha="right" if b == 0.6 else "left", fontsize=10, color=NAVY, fontweight="bold")
    ax.set_xlabel("History weight beta")
    ax.set_ylabel(lab)
    ax.set_xticks([0, 0.15, 0.30, 0.45, 0.60])
    ax.set_ylim(bottom=0)
axes[0].legend(loc="upper left")
axes[0].set_title("Hit@10 rises with history weight")
axes[1].set_title("MRR follows the same shape")
n = int(d[d.metric == "heldout_hit10"].n.iloc[0])
finish(fig, "Real history helps predict the next application, so personalization has real value",
       f"Source: JTH v1.1, held-out latest process for {n:,} test-set candidates; seed 20261115; 3,000 bootstrap resamples.",
       ROOT / "figures" / "heldout_curve.png")
print("saved")
