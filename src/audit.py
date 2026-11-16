"""Step 4: audit metrics on the test-set twins (criteria.md Section 3) -> results.csv part 'audit'."""
import json
import numpy as np
import pandas as pd
from core import ROOT, VALUE_DEFS, paired_permutation_p
from methods import SEED2, BETAS2
from results_io import write_part

B = 3000


def boot(fn, n, rng, B=B):
    est = fn(np.arange(n))
    reps = np.array([fn(rng.integers(0, n, n)) for _ in range(B)])
    return float(est), float(np.quantile(reps, 0.025)), float(np.quantile(reps, 0.975))


def metric_fns(t, lab):
    """Return {metric: fn(idx)} for one method label on twin table t."""
    g = lambda k: t[k].to_numpy()
    hvA, hvB = g(f"hv|A|{lab}"), g(f"hv|B|{lab}")
    missB = g(f"miss|B|{lab}"); missA = g(f"miss|A|{lab}")
    comp = (g(f"comp|A|{lab}") + g(f"comp|B|{lab}")) / 2
    comp0 = (g("comp|A|beta=0.00") + g("comp|B|beta=0.00")) / 2
    mob = g(f"mob|B|{lab}")
    return {
        "TEG_pp": lambda i: (hvA[i] - hvB[i]).mean() * 100,
        "blindspot_rate_pct": lambda i: (missB[i] >= 1).mean() * 100,
        "missed_mean": lambda i: missB[i].mean(),
        "blindspot_rate_twinA_pct": lambda i: (missA[i] >= 1).mean() * 100,
        "mobility_exposure_pct": lambda i: mob[i].mean() * 100,
        "compat_cost_pct": lambda i: (1 - comp[i].mean() / comp0[i].mean()) * 100,
        "hv_share_A_pct": lambda i: hvA[i].mean() * 100,
        "hv_share_B_pct": lambda i: hvB[i].mean() * 100,
    }


def main():
    t = pd.read_csv(ROOT / "outputs" / "twins_test.csv")
    n = len(t)
    rng = np.random.default_rng(SEED2 + 11)
    rows = []
    for b in BETAS2:
        lab = f"beta={b:.2f}"
        for met, fn in metric_fns(t, lab).items():
            rows.append([met, b, "treatment", *boot(fn, n, rng), n, "test"])
        mB = t[f"miss|B|{lab}"]
        rows.append(["missed_median", b, "treatment", float(mB.median()), np.nan, np.nan, n, "test"])
        plc = (t[f"hv|A|{lab}"] - t[f"plc_hv|B|{lab}"]).to_numpy() * 100
        rows.append(["TEG_pp", b, "placebo_identical_history", *boot(lambda i: plc[i].mean(), n, rng), n, "test"])
        for v in VALUE_DEFS:
            d = (t[f"hv_{v}|A|{lab}"] - t[f"hv_{v}|B|{lab}"]).to_numpy() * 100
            rows.append(["TEG_pp", b, f"value_{v}", *boot(lambda i: d[i].mean(), n, rng), n, "test"])
    d45 = (t["hv|A|beta=0.45"] - t["hv|B|beta=0.45"]).to_numpy()
    p = paired_permutation_p(d45, np.random.default_rng(SEED2 + 13))
    rows.append(["TEG_permutation_p", 0.45, "treatment", p, np.nan, np.nan, n, "test"])
    df = pd.DataFrame(rows, columns=["metric", "beta", "condition", "estimate", "ci_low", "ci_high", "n", "set"])
    get = lambda m, c="treatment", b=0.45: df[(df.metric == m) & (df.condition == c) & (df.beta == b)].iloc[0]
    teg = get("TEG_pp"); plc = get("TEG_pp", "placebo_identical_history")
    r1 = bool(teg.estimate > 0 and teg.ci_low > 0)
    r2 = bool(abs(plc.estimate) < 0.5)
    r3 = all(get("TEG_pp", f"value_{v}").estimate > 0 and get("TEG_pp", f"value_{v}").ci_low > 0 for v in VALUE_DEFS)
    for name, ok, note in [("R1_replication_pass", r1, "TEG>0 and CI excludes 0"),
                           ("R2_placebo_pass", r2, "|placebo TEG| < 0.5 pp"),
                           ("R3_robustness_pass", r3, "TEG>0, CI excl 0, all 3 value defs")]:
        rows.append([name, 0.45, note, float(ok), np.nan, np.nan, n, "test"])
    write_part("audit", rows)
    show = df[df.beta.isin([0.0, 0.45])]
    print(show.round(3).to_string())
    print("perm p", p, "R1", r1, "R2", r2, "R3", r3)


if __name__ == "__main__":
    main()
