"""Step 4/5 engine: build 1,200 twin pairs per set and compute per-pair metrics for every method.

Output: outputs/twins_<set>.csv, one row per pair, columns '<stat>|<twin>|<method label>'.
stats: hv (high-value share of Top 10), miss (missed opportunities vs own beta=0 Top 10),
       comp (mean raw compatibility of Top 10), mob (share of Top 10 at Mid level),
       hv_<vdef> (robustness), plc_hv (placebo: Twin B gets Twin A's history).
"""
import sys
import numpy as np
import pandas as pd
from core import World, ROOT, TOPK, VALUE_DEFS
from methods import SEED2, BETAS2, all_methods, load_split, rank

N_PAIRS = 1200


def sample_pairs(w, split, which):
    ids = set(split.candidate_id[split.set == which])
    rows = np.array([i for i, c in enumerate(w.cand.candidate_id) if c in ids and w.cand_has_text[i]])
    rng = np.random.default_rng(SEED2)  # criteria.md: seed 20261115 for both sets
    return rng.choice(rows, size=N_PAIRS, replace=False)


def pair_detail(w, row, pair_i, which):
    """Everything needed to rank one twin pair. Deterministic per (set, pair index)."""
    s = w.profile_sims(np.array([row]))[0]
    rng = np.random.default_rng([SEED2, pair_i, 0 if which == "test" else 1])
    pool = w.pool(s)
    hA_jobs = w.synthetic_history(s, "senior", rng)
    hB_jobs = w.synthetic_history(s, "entry", rng)
    hA, hB = w.history_vector(hA_jobs), w.history_vector(hB_jobs)
    return dict(pool=pool, compat=s[pool], simA=w.history_sim(pool, hA), simB=w.history_sim(pool, hB),
                hv={v: w.high_value(pool, v) for v in VALUE_DEFS}, hA_jobs=hA_jobs, hB_jobs=hB_jobs)


def run(which):
    w = World()
    split = load_split()
    rows = sample_pairs(w, split, which)
    meths = all_methods()
    recs = []
    for i, row in enumerate(rows):
        d = pair_detail(w, row, i, which)
        pool, compat, hv = d["pool"], d["compat"], d["hv"]["primary"]
        rec = {"pair": i, "candidate_id": w.cand.candidate_id.iloc[row]}
        top0 = {}
        for tw, hs in [("A", d["simA"]), ("B", d["simB"])]:
            top0[tw] = set(rank("beta", 0.0, compat, hs, hv)[:TOPK])
        for label, m, p in meths:
            for tw, hs in [("A", d["simA"]), ("B", d["simB"])]:
                top = rank(m, p, compat, hs, hv)[:TOPK]
                ts = set(top)
                rec[f"hv|{tw}|{label}"] = hv[top].mean()
                rec[f"miss|{tw}|{label}"] = sum(1 for j in top0[tw] if hv[j] and j not in ts)
                rec[f"comp|{tw}|{label}"] = compat[top].mean()
                rec[f"mob|{tw}|{label}"] = (w.sen[pool[top]] == 2).mean()
                if m == "beta":
                    for v in VALUE_DEFS:
                        rec[f"hv_{v}|{tw}|{label}"] = d["hv"][v][top].mean()
            if m == "beta":
                topP = rank("beta", p, compat, d["simA"], hv)[:TOPK]   # placebo: B gets A's history
                rec[f"plc_hv|B|{label}"] = hv[topP].mean()
        recs.append(rec)
        if i % 200 == 0:
            print(which, i, flush=True)
    df = pd.DataFrame(recs)
    df.to_csv(ROOT / "outputs" / f"twins_{which}.csv", index=False)
    return df


if __name__ == "__main__":
    for which in sys.argv[1:] or ["tune", "test"]:
        run(which)
