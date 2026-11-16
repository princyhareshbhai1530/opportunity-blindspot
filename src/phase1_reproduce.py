"""Rebuild the Phase 1 headline with seed 20261016 (1,200 twin pairs, all candidates)."""
import json, sys
import numpy as np
from core import (World, ROOT, rank_scores, topk, bootstrap_mean_ci, paired_permutation_p,
                  VALUE_DEFS)

SEED = 20261016
N_PAIRS = 1200
BETAS = [0.0, 0.15, 0.30, 0.45]


def run(world, cand_rows, seed, betas=BETAS, placebo=False):
    rng = np.random.default_rng(seed + 1)
    sims = world.profile_sims(cand_rows)
    out = {b: {v: [] for v in VALUE_DEFS} | {"compA": [], "compB": [], "salA": [], "salB": [],
                                             "remA": [], "remB": [], "permA": [], "permB": []}
           for b in betas}
    for r in range(len(cand_rows)):
        s = sims[r]
        pool = world.pool(s)
        compat = s[pool]
        hA = world.history_vector(world.synthetic_history(s, "senior", rng))
        hB = world.history_vector(world.synthetic_history(s, "entry", rng))
        if placebo:
            hB = hA
        simA, simB = world.history_sim(pool, hA), world.history_sim(pool, hB)
        hv = {v: world.high_value(pool, v) for v in VALUE_DEFS}
        for b in betas:
            tA, tB = topk(rank_scores(compat, simA, b)), topk(rank_scores(compat, simB, b))
            for v in VALUE_DEFS:
                out[b][v].append((hv[v][tA].mean(), hv[v][tB].mean()))
            out[b]["compA"].append(compat[tA].mean()); out[b]["compB"].append(compat[tB].mean())
            out[b]["salA"].append(np.median(world.salary[pool[tA]]))
            out[b]["salB"].append(np.median(world.salary[pool[tB]]))
            out[b]["remA"].append(world.remote[pool[tA]].mean()); out[b]["remB"].append(world.remote[pool[tB]].mean())
            out[b]["permA"].append(world.permanent[pool[tA]].mean()); out[b]["permB"].append(world.permanent[pool[tB]].mean())
    return out


def main():
    w = World()
    rng = np.random.default_rng(SEED)
    eligible = np.where(w.cand_has_text)[0]
    rows = rng.choice(eligible, size=N_PAIRS, replace=False)
    res = run(w, rows, SEED)
    plc = run(w, rows, SEED, betas=[0.45], placebo=True)
    brng = np.random.default_rng(SEED + 7)
    summary = {"seed": SEED, "n_pairs": N_PAIRS, "eligible_candidates": int(len(eligible))}
    for b in BETAS:
        a = np.array(res[b]["primary"])
        d = (a[:, 0] - a[:, 1]) * 100
        est, lo, hi = bootstrap_mean_ci(d, brng)
        summary[f"beta_{b}"] = {"A_pct": a[:, 0].mean() * 100, "B_pct": a[:, 1].mean() * 100,
                                "gap_pp": est, "ci": [lo, hi]}
    b = 0.45
    for v in VALUE_DEFS:
        a = np.array(res[b][v]); d = (a[:, 0] - a[:, 1]) * 100
        summary[f"robust_{v}"] = bootstrap_mean_ci(d, brng)
    a = np.array(plc[0.45]["primary"]); summary["placebo_pp"] = float(((a[:, 0] - a[:, 1]) * 100).mean())
    a = np.array(res[b]["primary"]); d = a[:, 0] - a[:, 1]
    summary["perm_p"] = paired_permutation_p(d, np.random.default_rng(SEED + 9))
    r = res[b]
    summary["econ"] = {
        "salary_median_diff_eur": float(np.mean(np.array(r["salA"]) - np.array(r["salB"]))),
        "remote_pp": float(np.mean(np.array(r["remA"]) - np.array(r["remB"])) * 100),
        "permanent_pp": float(np.mean(np.array(r["permA"]) - np.array(r["permB"])) * 100),
        "compat_rel_pct": float((np.mean(r["compA"]) / np.mean(r["compB"]) - 1) * 100),
    }
    (ROOT / "outputs").mkdir(exist_ok=True)
    (ROOT / "outputs" / "phase1_reproduction.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
