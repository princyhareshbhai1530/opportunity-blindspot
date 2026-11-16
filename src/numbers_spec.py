"""Single declaration of every number used in the PDF, with its source.

Kinds:
  csv   -> outputs/results.csv row (metric, beta, condition, set) and column
  json  -> outputs/<file>.json path
  const -> fixed design constant, with provenance (criteria.md, data docs, policy source)
"""
import json
import pandas as pd
from core import ROOT

OUT = ROOT / "outputs"


def fmt(v, f):
    if f == "f0": return f"{float(v):.0f}"
    if f == "f1": return f"{float(v):.1f}"
    if f == "f2": return f"{float(v):.2f}"
    if f == "f3": return f"{float(v):.3f}"
    if f == "int": return f"{int(round(float(v))):,}"
    if f == "p": return "< 0.001" if float(v) < 0.001 else f"{float(v):.3f}"
    if f == "str": return str(v)
    raise ValueError(f)


def C(metric, beta, cond, st="test", col="estimate", f="f2"):
    return ("csv", (metric, beta, cond, st, col), f)


def J(file, path, f):
    return ("json", (file, path), f)


def K(value, f, why):
    return ("const", (value, why), f)


SPEC = {
    # --- Phase 1 published + rebuild
    "p1_gap": J("phase1_published", "gap_pp", "f2"),
    "p1_lo": J("phase1_published", "gap_ci_low", "f2"),
    "p1_hi": J("phase1_published", "gap_ci_high", "f2"),
    "p1_rebuild": J("phase1_reproduction", "beta_0.45/gap_pp", "f2"),
    # --- audit, test set
    "teg": C("TEG_pp", 0.45, "treatment"), "teg_lo": C("TEG_pp", 0.45, "treatment", col="ci_low"),
    "teg_hi": C("TEG_pp", 0.45, "treatment", col="ci_high"),
    "teg15": C("TEG_pp", 0.15, "treatment"), "teg30": C("TEG_pp", 0.30, "treatment"),
    "teg60": C("TEG_pp", 0.60, "treatment"),
    "plc": C("TEG_pp", 0.45, "placebo_identical_history"),
    "perm_p": C("TEG_permutation_p", 0.45, "treatment", f="p"),
    "hvA": C("hv_share_A_pct", 0.45, "treatment", f="f1"), "hvB": C("hv_share_B_pct", 0.45, "treatment", f="f1"),
    "bl": C("blindspot_rate_pct", 0.45, "treatment", f="f1"),
    "bl_lo": C("blindspot_rate_pct", 0.45, "treatment", col="ci_low", f="f1"),
    "bl_hi": C("blindspot_rate_pct", 0.45, "treatment", col="ci_high", f="f1"),
    "blA": C("blindspot_rate_twinA_pct", 0.45, "treatment", f="f1"),
    "miss_mean": C("missed_mean", 0.45, "treatment"),
    "mob45": C("mobility_exposure_pct", 0.45, "treatment", f="f1"),
    "mob0": C("mobility_exposure_pct", 0.0, "treatment", f="f1"),
    "cc45": C("compat_cost_pct", 0.45, "treatment"),
    "rob_sal": C("TEG_pp", 0.45, "value_salary_only"), "rob_eq": C("TEG_pp", 0.45, "value_equal_weights"),
    "n_pairs": C("TEG_pp", 0.45, "treatment", col="n", f="int"),
    # --- A1 imputed-salary robustness (exploratory, robust_salary.py)
    "rob_posted": C("TEG_pp", 0.45, "posted_salary_only"),
    "rob_posted_lo": C("TEG_pp", 0.45, "posted_salary_only", col="ci_low"),
    "rob_posted_hi": C("TEG_pp", 0.45, "posted_salary_only", col="ci_high"),
    "rob_excl": C("TEG_pp", 0.45, "exclude_imputed_from_hv"),
    "rob_excl_lo": C("TEG_pp", 0.45, "exclude_imputed_from_hv", col="ci_low"),
    "rob_excl_hi": C("TEG_pp", 0.45, "exclude_imputed_from_hv", col="ci_high"),
    "imp_pool": C("imputed_salary_share_pool_pct", 0.45, "matched_pool_entries", f="f1"),
    # --- A3 runtime (runtime_audit.py)
    "rt_sec": J("runtime", "wall_clock_seconds", "f0"),
    "rt_cpu": J("runtime", "cpu_short", "str"),
    "rt_ram": J("runtime", "ram_gb", "f0"),
    "rt_runs": K(3, "f0", "runtime_audit.py RUNS"),
    # --- held-out, test set
    "hit0": C("heldout_hit10", 0.0, "real_history", f="f1"), "hit45": C("heldout_hit10", 0.45, "real_history", f="f1"),
    "hit60": C("heldout_hit10", 0.60, "real_history", f="f1"),
    "h1": C("heldout_hit10_gain_vs_beta0", 0.45, "real_history"),
    "h1_lo": C("heldout_hit10_gain_vs_beta0", 0.45, "real_history", col="ci_low"),
    "h1_hi": C("heldout_hit10_gain_vs_beta0", 0.45, "real_history", col="ci_high"),
    "n_heldout": C("heldout_hit10", 0.45, "real_history", col="n", f="int"),
    "n_heldout_tune": C("heldout_hit10", 0.45, "real_history", st="tune", col="n", f="int"),
    # --- mitigations, test set (chosen settings) + one tune value
    **{f"{k}_{m}": C(met, 0.45, lab, f=f) for k, m, lab in
       [("cap", "red", "history_cap=0.3"), ("floor", "red", "profile_floor=0.7"), ("expl", "red", "exploration=3")]
       for met, f in [("TEG_reduction_pct", "f1")]},
    **{f"{k}_{s}": C(met, 0.45, lab, f=f) for k, lab in
       [("cap", "history_cap=0.3"), ("floor", "profile_floor=0.7"), ("expl", "exploration=3")]
       for s, met, f in [("cc", "compat_cost_pct", "f2"), ("hit", "hit10_retained_pct", "f1"), ("bl", "blindspot_rate_pct", "f1")]},
    "cap_hit_tune": C("hit10_retained_pct", 0.45, "history_cap=0.3", st="tune", f="f1"),
    "cap_hit_lo": C("hit10_retained_pct", 0.45, "history_cap=0.3", col="ci_low", f="f1"),
    "cap_hit_hi": C("hit10_retained_pct", 0.45, "history_cap=0.3", col="ci_high", f="f1"),
    "cap_param": J("mitigation_summary", "tuning/history_cap/chosen", "f2"),
    "floor_param": J("mitigation_summary", "tuning/profile_floor/chosen", "f2"),
    "expl_param": J("mitigation_summary", "tuning/exploration/chosen", "int"),
    # --- receipt + scorecard
    "r_nblind": J("prototype_data", "receipt/n_with_blindspot", "int"),
    "r_ntwins": J("prototype_data", "receipt/n_twins", "int"),
    "r_med": J("prototype_data", "receipt/median_rule_value", "int"),
    "r_title": J("prototype_data", "receipt/missed/0/title", "str"),
    "r_band": J("prototype_data", "receipt/missed/0/salary_band", "str"),
    "r_prank": J("prototype_data", "receipt/missed/0/profile_rank", "int"),
    "r_frank": J("prototype_data", "receipt/missed/0/personalized_rank", "int"),
    "r_match": J("prototype_data", "receipt/missed/0/match", "f2"),
    "d_teg": J("prototype_data", "scorecard/defaults/TEG_pp", "f2"),
    "d_bl": J("prototype_data", "scorecard/defaults/blindspot_rate_pct", "f1"),
    "d_mob": J("prototype_data", "scorecard/defaults/mobility_drop_pp", "f2"),
    "n_fix_pass": J("derived", "n_fix_pass", "int"), "n_fix": J("derived", "n_fix", "int"),
    # --- data counts (generated by build_pdf from the raw tables)
    "n_cand": J("data_counts", "candidates", "int"), "n_jobs": J("data_counts", "jobs", "int"),
    "n_proc": J("data_counts", "history", "int"),
    # --- constants with provenance
    "seed2": K(20261115, "str", "criteria.md seed"), "seed1": K(20261016, "str", "Phase 1 seed"),
    "B": K(3000, "int", "criteria.md bootstrap resamples"), "P": K(10000, "int", "criteria.md permutations"),
    "thr_teg": K(50, "f0", "criteria.md fix success"), "thr_cc": K(2, "f0", "criteria.md fix success"),
    "thr_hit": K(75, "f0", "criteria.md fix success"), "thr_h1": K(2, "f0", "criteria.md H1"),
    "hv_share": K(20, "f0", "Phase 1 method: top 20% of pool"), "pool": K(100, "f0", "core.py POOL_SIZE"),
    "beta": K(0.45, "f2", "Phase 1 operating point"), "topk": K(10, "f0", "Top-10 visibility window"),
    "senw": K(0.06, "f2", "core.py SEN_W calibration"),
    "w_sal": K(50, "f0", "Phase 1 value weights"), "w_perm": K(30, "f0", "Phase 1 value weights"),
    "w_rem": K(20, "f0", "Phase 1 value weights"), "hist_k": K(5, "f0", "core.py HIST_K"), "n_metrics": K(3, "f0", "TEG, Blindspot Rate, Mobility Exposure"),
}


def _dig(obj, path):
    for p in path.split("/"):
        obj = obj[int(p)] if isinstance(obj, list) else obj[p]
    return obj


def raw(key, _cache={}):
    kind, arg, f = SPEC[key]
    if kind == "csv":
        if "csv" not in _cache:
            _cache["csv"] = pd.read_csv(OUT / "results.csv")
        r = _cache["csv"]
        met, beta, cond, st, col = arg
        row = r[(r.metric == met) & ((r.beta - beta).abs() < 1e-9) & (r.condition == cond) & (r.set == st)]
        if len(row) != 1:
            raise KeyError(f"{key}: {len(row)} rows match {arg}")
        return row.iloc[0][col]
    if kind == "json":
        file, path = arg
        return _dig(json.loads((OUT / f"{file}.json").read_text()), path)
    return arg[0]


def value(key):
    return fmt(raw(key), SPEC[key][2])
