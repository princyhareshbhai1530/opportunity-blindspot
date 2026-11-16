"""A1 (exploratory, added after Phase 2 lock): does the gap depend on LLM-imputed salaries?

JTH gives a posted salary for some jobs; for the rest our value proxy uses the LLM salary estimate.
Test set, beta = 0.45, same 1,200 twin pairs (seed 20261115), 3,000 bootstrap resamples.

  imputed_salary_share      share of matched-pool entries (and of primary high-value entries) with imputed salary
  condition = exclude_imputed_from_hv
      ranking unchanged on the full pool; the high-value set is the top 20% by value among the pool's
      posted-salary jobs only (salary percentile among posted jobs), so an imputed job can never be high-value.
  condition = posted_salary_only
      imputed-salary jobs removed from the pool entirely; ranking, Top 10, value and high-value all computed
      within the posted-salary pool. Pairs with fewer than MIN_POSTED posted jobs in the pool are dropped.
Output: results.csv part 'robust_salary', outputs/robust_salary.json.
"""
import json
import numpy as np
import pandas as pd
from core import World, ROOT, TOPK, HV_SHARE, paired_permutation_p
from methods import SEED2, load_split, rank
from twins import sample_pairs, pair_detail
from audit import boot
from results_io import write_part

BETA = 0.45
MIN_POSTED = 2 * TOPK


def hv_from(w, idx):
    """Primary value and top-20% high-value flag within the given job index set."""
    v = w.value(idx, "primary")
    return v >= np.quantile(v, 1 - HV_SHARE)


def main():
    w = World()
    j = w.jobs
    posted_all = (j.salary.notna() & (j.salary > 0)).to_numpy()
    rows_ = sample_pairs(w, load_split(), "test")
    pool_n = pool_imp = hv_n = hv_imp = 0
    a_rec, b_rec, dropped = [], [], 0
    for i, row in enumerate(rows_):
        d = pair_detail(w, row, i, "test")
        pool, compat, hv = d["pool"], d["compat"], d["hv"]["primary"]
        post = posted_all[pool]
        pool_n += len(pool); pool_imp += int((~post).sum())
        hv_n += int(hv.sum()); hv_imp += int((hv & ~post).sum())
        # (a) exclude imputed jobs from the high-value set
        hva = np.zeros(len(pool), bool)
        pidx = np.where(post)[0]
        if len(pidx) >= 1:
            hva[pidx] = hv_from(w, pool[pidx])
        tops = {tw: rank("beta", BETA, compat, hs, hv)[:TOPK] for tw, hs in [("A", d["simA"]), ("B", d["simB"])]}
        a_rec.append((hva[tops["A"]].mean(), hva[tops["B"]].mean()))
        # (b) posted-salary-only pool
        if len(pidx) < MIN_POSTED:
            dropped += 1; continue
        sub = pool[pidx]
        hvb = hv_from(w, sub)
        tA = rank("beta", BETA, compat[pidx], d["simA"][pidx], hvb)[:TOPK]
        tB = rank("beta", BETA, compat[pidx], d["simB"][pidx], hvb)[:TOPK]
        b_rec.append((hvb[tA].mean(), hvb[tB].mean()))
        if i % 300 == 0:
            print("pair", i, flush=True)
    rng = np.random.default_rng(SEED2 + 21)
    rows, out = [], {}
    share_pool = pool_imp / pool_n * 100
    share_hv = hv_imp / hv_n * 100
    rows.append(["imputed_salary_share_pool_pct", BETA, "matched_pool_entries", share_pool, np.nan, np.nan, pool_n, "test"])
    rows.append(["imputed_salary_share_hv_pct", BETA, "primary_high_value_entries", share_hv, np.nan, np.nan, hv_n, "test"])
    out["pool_entries"] = pool_n; out["pool_imputed"] = pool_imp; out["pool_imputed_pct"] = share_pool
    out["hv_entries"] = hv_n; out["hv_imputed"] = hv_imp; out["hv_imputed_pct"] = share_hv
    out["jobs_total"] = int(len(j)); out["jobs_imputed"] = int((~posted_all).sum())
    out["jobs_imputed_pct"] = float((~posted_all).mean() * 100)
    for cond, rec in [("exclude_imputed_from_hv", a_rec), ("posted_salary_only", b_rec)]:
        r = np.array(rec)
        dd = (r[:, 0] - r[:, 1]) * 100
        est, lo, hi = boot(lambda ix: dd[ix].mean(), len(dd), rng)
        p = paired_permutation_p(dd, np.random.default_rng(SEED2 + 23))
        rows.append(["TEG_pp", BETA, cond, est, lo, hi, len(dd), "test"])
        rows.append(["TEG_permutation_p", BETA, cond, p, np.nan, np.nan, len(dd), "test"])
        out[cond] = dict(TEG_pp=est, ci_low=lo, ci_high=hi, n=len(dd), perm_p=p)
    out["posted_salary_only"]["pairs_dropped_lt_min_posted"] = dropped
    out["min_posted"] = MIN_POSTED
    write_part("robust_salary", rows)
    (ROOT / "outputs" / "robust_salary.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
