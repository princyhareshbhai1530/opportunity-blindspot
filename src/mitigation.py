"""Step 5: tune mitigations on the tune set, evaluate the chosen setting once on the test set.

Tuning rule and fix-success thresholds are exactly those in criteria.md Section 4.
"""
import json
import numpy as np
import pandas as pd
from core import ROOT
from methods import SEED2, GRIDS
from results_io import write_part
from audit import boot

THR_TEG, THR_COMP, THR_HIT = 50.0, 2.0, 75.0


def stats(t, h, lab, rng, with_ci=True):
    """TEG reduction %, compat cost %, Hit@10 retained %, plus TEG/blindspot/compat/hit levels."""
    g = lambda k: t[k].to_numpy()
    dm = g(f"hv|A|{lab}") - g(f"hv|B|{lab}")
    d45 = g("hv|A|beta=0.45") - g("hv|B|beta=0.45")
    comp = (g(f"comp|A|{lab}") + g(f"comp|B|{lab}")) / 2
    comp0 = (g("comp|A|beta=0.00") + g("comp|B|beta=0.00")) / 2
    missB = g(f"miss|B|{lab}")
    hm, h0, h45 = h[f"hit|{lab}"].to_numpy(), h["hit|beta=0.00"].to_numpy(), h["hit|beta=0.45"].to_numpy()
    fns_t = {
        "TEG_pp": lambda i: dm[i].mean() * 100,
        "TEG_reduction_pct": lambda i: (1 - dm[i].mean() / d45[i].mean()) * 100,
        "compat_cost_pct": lambda i: (1 - comp[i].mean() / comp0[i].mean()) * 100,
        "blindspot_rate_pct": lambda i: (missB[i] >= 1).mean() * 100,
    }
    fns_h = {
        "heldout_hit10": lambda i: hm[i].mean() * 100,
        "hit10_retained_pct": lambda i: (hm[i].mean() - h0[i].mean()) / (h45[i].mean() - h0[i].mean()) * 100,
    }
    out = {}
    for fns, n in [(fns_t, len(t)), (fns_h, len(h))]:
        for k, fn in fns.items():
            out[k] = boot(fn, n, rng) if with_ci else (float(fn(np.arange(n))), np.nan, np.nan)
    return out


def passes(s, h1):
    ok_teg = s["TEG_reduction_pct"][0] >= THR_TEG
    ok_comp = s["compat_cost_pct"][0] <= THR_COMP
    ok_hit = (s["hit10_retained_pct"][0] >= THR_HIT) if h1 else True
    return ok_teg, ok_comp, ok_hit


def choose(cands, h1):
    """cands: list of (param, stats). Pre-registered tuning rule."""
    full = [(p, s) for p, s in cands if all(passes(s, h1))]
    if full:
        return max(full, key=lambda x: (x[1]["hit10_retained_pct"][0], x[1]["TEG_reduction_pct"][0]))[0], "met all thresholds on tune"
    ok_c = [(p, s) for p, s in cands if s["compat_cost_pct"][0] <= THR_COMP]
    if ok_c:
        return max(ok_c, key=lambda x: x[1]["TEG_reduction_pct"][0])[0], "no setting met all; largest TEG reduction with compat cost <= 2%"
    return max(cands, key=lambda x: x[1]["TEG_reduction_pct"][0])[0], "no setting met all; largest TEG reduction"


def main():
    h1 = bool(json.loads((ROOT / "outputs" / "heldout_summary.json").read_text())["H1"]["pass"])
    hd = pd.read_csv(ROOT / "outputs" / "heldout_per_candidate.csv")
    tt, ht = pd.read_csv(ROOT / "outputs" / "twins_tune.csv"), hd[hd.set == "tune"]
    te, he = pd.read_csv(ROOT / "outputs" / "twins_test.csv"), hd[hd.set == "test"]
    rng = np.random.default_rng(SEED2 + 21)
    rows, tuning, chosen = [], {}, {}
    for m, grid in GRIDS.items():
        cands = []
        for p in grid:
            s = stats(tt, ht, f"{m}={p}", rng, with_ci=False)
            cands.append((p, s))
            for k, v in s.items():
                rows.append([k, 0.45, f"{m}={p}", v[0], np.nan, np.nan, len(tt) if k not in ("heldout_hit10", "hit10_retained_pct") else len(ht), "tune"])
        p, why = choose(cands, h1)
        chosen[m] = p
        tuning[m] = {"chosen": p, "reason": why,
                     "grid": {str(q): {k: round(v[0], 3) for k, v in s.items()} for q, s in cands}}
    table = []
    labels = [("Profile only (beta = 0)", "beta=0.00"), ("Personalized (beta = 0.45)", "beta=0.45")] + \
             [(m, f"{m}={p}") for m, p in chosen.items()]
    for name, lab in labels:
        s = stats(te, he, lab, rng)
        for k, v in s.items():
            rows.append([k, 0.45, lab, *v, len(te) if k not in ("heldout_hit10", "hit10_retained_pct") else len(he), "test"])
        if lab.startswith("beta"):
            table.append({"method": name, "label": lab, **{k: v[0] for k, v in s.items()}, "role": "baseline"})
            continue
        a, b, c = passes(s, h1)
        ok = a and b and c
        rows.append(["fix_success_pass", 0.45, lab, float(ok), np.nan, np.nan, len(te), "test"])
        table.append({"method": name, "label": lab, **{k: v[0] for k, v in s.items()},
                      **{f"{k}_ci": [v[1], v[2]] for k, v in s.items()},
                      "pass_teg": a, "pass_comp": b, "pass_hit": c if h1 else "n/a", "pass": ok, "role": "mitigation"})
    write_part("mitigation", rows)
    passing = [r for r in table if r.get("pass") is True]
    if h1:
        rec = (max(passing, key=lambda r: r["hit10_retained_pct"])["label"] if passing
               else "Audit + 'rank by my profile only' control (no mitigation passed)")
    else:
        rec = "Audit + 'rank by my profile only' control (H1 failed; mitigations secondary)"
    out = {"H1": h1, "tuning": tuning, "test_table": table, "recommendation": rec}
    (ROOT / "outputs" / "mitigation_summary.json").write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps({m: {"chosen": v["chosen"], "reason": v["reason"]} for m, v in tuning.items()}, indent=1))
    print(pd.DataFrame(table)[["label", "TEG_pp", "TEG_reduction_pct", "compat_cost_pct", "blindspot_rate_pct",
                               "heldout_hit10", "hit10_retained_pct"] + [c for c in ["pass_teg", "pass_comp", "pass_hit", "pass"]]].round(2).to_string())
    print("recommendation:", rec)


if __name__ == "__main__":
    main()
