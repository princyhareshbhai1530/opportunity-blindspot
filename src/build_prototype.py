"""Step 6: export prototype data (from outputs only) and inline it into prototype/index.html.

Receipt twin selection rule (fixed in code, no manual choice):
  among test-set entry-history twins with >= 1 missed opportunity at beta = 0.45,
  take the median missed count m, then the twin with the lowest pair index whose count == m.
"""
import json
import numpy as np
import pandas as pd
from core import World, ROOT, TOPK
from methods import BETAS2, load_split, rank
from twins import sample_pairs, pair_detail



def label(w, j):
    r = w.jobs.iloc[j]
    cat = str(r.llm_job_category).split(";")[0] if isinstance(r.llm_job_category, str) else "role"
    return f"{r.llm_seniority_level or 'Mid'} {cat}".strip()


def job_card(w, pool, compat, j_local, prof_rank, hv):
    j = int(pool[j_local]); r = w.jobs.iloc[j]
    entered = pd.notna(r.salary) and r.salary > 0
    s = float(w.salary[j]); lo = int(s // 5000 * 5)
    t = label(w, j)
    return {"title": t[0].upper() + t[1:],
            "salary_band": f"EUR {lo}k to {lo + 5}k", "salary_source": "posted" if entered else "LLM estimate",
            "contract": str(r.contract_type).capitalize(), "remote": bool(w.remote[j]),
            "seniority": str(r.llm_seniority_level), "match": round(float(compat[j_local]), 3),
            "profile_rank": int(prof_rank[j_local]), "high_value": bool(hv[j_local])}


def receipt(w):
    t = pd.read_csv(ROOT / "outputs" / "twins_test.csv")
    m = t["miss|B|beta=0.45"]
    med = int(m[m >= 1].median())
    pair = int(t[m == med].pair.min())
    rows = sample_pairs(w, load_split(), "test")
    d = pair_detail(w, rows[pair], pair, "test")
    pool, compat, hv = d["pool"], d["compat"], d["hv"]["primary"]
    prof_order = rank("beta", 0.0, compat, d["simB"], hv)
    prof_rank = np.empty(len(pool), int); prof_rank[prof_order] = np.arange(1, len(pool) + 1)
    pers_order = rank("beta", 0.45, compat, d["simB"], hv)
    top0, top45 = list(prof_order[:TOPK]), list(pers_order[:TOPK])
    missed = [j for j in top0 if hv[j] and j not in top45]
    assert len(missed) == med == int(m.iloc[pair]), "recomputed receipt does not match twins_test.csv"
    pers_rank = np.empty(len(pool), int); pers_rank[pers_order] = np.arange(1, len(pool) + 1)
    feed = lambda order: [dict(job_card(w, pool, compat, j, prof_rank, hv), missed=bool(j in missed),
                               new_in_personalized=bool(j not in top0)) for j in order]
    miss_cards = [dict(job_card(w, pool, compat, j, prof_rank, hv), personalized_rank=int(pers_rank[j])) for j in missed]
    hist = [label(w, int(j)) for j in d["hB_jobs"]]
    return {"pair_index": pair, "n_missed": len(missed), "median_rule_value": med,
            "n_with_blindspot": int((m >= 1).sum()), "n_twins": int(len(m)),
            "history_labels": hist, "missed": miss_cards,
            "feed_profile": feed(top0), "feed_personalized": feed(top45)}


def scorecard():
    r = pd.read_csv(ROOT / "outputs" / "results.csv")
    te = r[r.set == "test"]
    g = lambda met, b, cond="treatment": te[(te.metric == met) & (te.beta == b) & (te.condition == cond)].iloc[0]
    per_beta = {}
    for b in BETAS2:
        e = {}
        for k in ["TEG_pp", "blindspot_rate_pct", "mobility_exposure_pct", "compat_cost_pct"]:
            x = g(k, b); e[k] = [round(x.estimate, 2), round(x.ci_low, 2), round(x.ci_high, 2)]
        x = te[(te.metric == "heldout_hit10") & (te.beta == b)].iloc[0]
        e["heldout_hit10"] = [round(x.estimate, 2), round(x.ci_low, 2), round(x.ci_high, 2)]
        per_beta[f"{b:.2f}"] = e
    p = per_beta["0.45"]; mob0 = per_beta["0.00"]["mobility_exposure_pct"][0]
    # Default thresholds: the pre-registered 50% rule applied to each harm metric; compat guard = 2% (criteria.md)
    defaults = {"TEG_pp": round(p["TEG_pp"][0] / 2, 2),
                "blindspot_rate_pct": round(p["blindspot_rate_pct"][0] / 2, 1),
                "mobility_drop_pp": round((mob0 - p["mobility_exposure_pct"][0]) / 2, 2),
                "compat_cost_pct": 2.0}
    mit = json.loads((ROOT / "outputs" / "mitigation_summary.json").read_text())
    fixes = [{"label": x["label"], "method": x["method"], "TEG_reduction_pct": round(x["TEG_reduction_pct"], 1),
              "compat_cost_pct": round(x["compat_cost_pct"], 2), "hit10_retained_pct": round(x["hit10_retained_pct"], 1),
              "pass": x["pass"]} for x in mit["test_table"] if x["role"] == "mitigation"]
    return {"per_beta": per_beta, "mobility_beta0": mob0, "defaults": defaults, "fixes": fixes,
            "n_pairs": int(g("TEG_pp", 0.45).n), "n_heldout": int(te[te.metric == "heldout_hit10"].n.iloc[0])}


def main():
    w = World()
    data = {"receipt": receipt(w), "scorecard": scorecard()}
    (ROOT / "outputs" / "prototype_data.json").write_text(json.dumps(data, indent=2))
    html = (ROOT / "src" / "prototype_template.html").read_text(encoding="utf-8")
    html = html.replace("/*__DATA__*/null", json.dumps(data))
    (ROOT / "prototype" / "index.html").write_text(html, encoding="utf-8")
    rc = data["receipt"]
    print("receipt pair", rc["pair_index"], "missed", rc["n_missed"], rc["missed"])
    print("defaults", data["scorecard"]["defaults"])
    # prototype_site/index.html is the live pitch demo, built by build_demo.py from the same outputs

if __name__ == "__main__":
    main()
