"""Live pitch demo: export demo data (from outputs + the existing pipeline) and inline it into prototype_site/index.html.

Everything shown in the demo comes from here:
  * the receipt twin pair (same fixed selection rule as build_prototype.py, recomputed and cross-checked),
    with Twin A's and Twin B's real personalized Top 10 and the shared profile-only Top 10
  * per-beta test-set metrics with 95% CIs from outputs/results.csv
  * the three tuned fixes from outputs/mitigation_summary.json
  * pre-registered thresholds from numbers_spec.py (criteria.md constants)
Output: outputs/demo_data.json, prototype_site/index.html (single self-contained file).
"""
import json
import numpy as np
import pandas as pd
from core import World, ROOT, TOPK, POOL_SIZE, HIST_K
from methods import BETAS2, SEED2, load_split, rank
from twins import sample_pairs, pair_detail
from build_prototype import label, job_card
import numbers_spec as N


def twin_feeds(w):
    proto = json.loads((ROOT / "outputs" / "prototype_data.json").read_text())["receipt"]
    pair = proto["pair_index"]
    rows = sample_pairs(w, load_split(), "test")
    d = pair_detail(w, rows[pair], pair, "test")
    pool, compat, hv = d["pool"], d["compat"], d["hv"]["primary"]

    def ranks(order):
        r = np.empty(len(pool), int); r[order] = np.arange(1, len(pool) + 1); return r

    o0 = rank("beta", 0.0, compat, d["simB"], hv)          # profile only: identical for both twins
    oA = rank("beta", 0.45, compat, d["simA"], hv)
    oB = rank("beta", 0.45, compat, d["simB"], hv)
    r0, rA, rB = ranks(o0), ranks(oA), ranks(oB)
    top0, topB = list(o0[:TOPK]), list(oB[:TOPK])
    missed = [j for j in top0 if hv[j] and j not in topB]
    assert len(missed) == proto["n_missed"], "recomputed receipt differs from prototype_data.json"

    def card(j):
        c = job_card(w, pool, compat, j, r0, hv)
        c.update(id=int(pool[j]), rank_profile=int(r0[j]), rank_A=int(rA[j]), rank_B=int(rB[j]),
                 missed_by_B=bool(j in missed))
        return c

    m = card(missed[0])
    assert m["title"] == proto["missed"][0]["title"] and m["rank_B"] == proto["missed"][0]["personalized_rank"]
    return {
        "pair_index": pair, "pool_size": int(len(pool)),
        "history_A": [label(w, int(j)) for j in d["hA_jobs"]],
        "history_B": [label(w, int(j)) for j in d["hB_jobs"]],
        "feed_profile": [card(j) for j in o0[:TOPK]],
        "feed_A": [card(j) for j in oA[:TOPK]],
        "feed_B": [card(j) for j in oB[:TOPK]],
        "missed": m, "n_missed": len(missed),
        "n_with_blindspot": proto["n_with_blindspot"], "n_twins": proto["n_twins"],
    }


def per_beta():
    r = pd.read_csv(ROOT / "outputs" / "results.csv")
    te = r[r.set == "test"]

    def g(met, b, cond="treatment"):
        x = te[(te.metric == met) & ((te.beta - b).abs() < 1e-9) & (te.condition == cond)]
        assert len(x) == 1, (met, b, cond)
        x = x.iloc[0]
        return [float(x.estimate), float(x.ci_low), float(x.ci_high)]

    out = {}
    for b in BETAS2:
        out[f"{b:.2f}"] = {
            "TEG_pp": g("TEG_pp", b), "placebo_pp": g("TEG_pp", b, "placebo_identical_history"),
            "hv_A_pct": g("hv_share_A_pct", b), "hv_B_pct": g("hv_share_B_pct", b),
            "blindspot_rate_pct": g("blindspot_rate_pct", b), "mobility_exposure_pct": g("mobility_exposure_pct", b),
            "compat_cost_pct": g("compat_cost_pct", b), "hit10_pct": g("heldout_hit10", b, "real_history"),
        }
    h1 = g("heldout_hit10_gain_vs_beta0", 0.45, "real_history")
    n_pairs = int(te[(te.metric == "TEG_pp") & (te.condition == "treatment")].n.iloc[0])
    n_held = int(te[(te.metric == "heldout_hit10")].n.iloc[0])
    return out, h1, n_pairs, n_held


def main():
    w = World()
    pb, h1, n_pairs, n_held = per_beta()
    proto = json.loads((ROOT / "outputs" / "prototype_data.json").read_text())["scorecard"]
    mit = json.loads((ROOT / "outputs" / "mitigation_summary.json").read_text())
    names = {"history_cap": "History cap", "profile_floor": "Profile floor", "exploration": "Exploration slots"}
    params = {"history_cap": "beta {} for high-value roles", "profile_floor": "keep profile matches scoring at least {}",
              "exploration": "{} of 10 slots for roles outside the history"}
    fixes = []
    for x in mit["test_table"]:
        if x["role"] != "mitigation":
            continue
        m, p = x["label"].split("=")
        fixes.append({"name": names[m], "setting": params[m].format(p), "gap_cut_pct": x["TEG_reduction_pct"],
                      "compat_cost_pct": x["compat_cost_pct"], "hit10_kept_pct": x["hit10_retained_pct"],
                      "pass_gap": x["pass_teg"], "pass_compat": x["pass_comp"], "pass_hit": x["pass_hit"],
                      "pass": x["pass"]})
    data = {
        "meta": {"dataset": "JTH v1.1", "seed": int(N.raw("seed2")), "n_pairs": n_pairs, "n_heldout": n_held,
                 "bootstrap": int(N.raw("B")), "pool_size": POOL_SIZE, "topk": TOPK, "hist_k": HIST_K,
                 "betas": [f"{b:.2f}" for b in BETAS2], "beta_default": "0.45"},
        "twins": twin_feeds(w),
        "per_beta": pb,
        "h1_gain_pp": h1,
        "defaults": proto["defaults"],
        "fix_criteria": {"gap_cut_min_pct": float(N.raw("thr_teg")), "compat_max_pct": float(N.raw("thr_cc")),
                         "hit10_kept_min_pct": float(N.raw("thr_hit"))},
        "fixes": fixes,
    }
    (ROOT / "outputs" / "demo_data.json").write_text(json.dumps(data, indent=2))
    html = (ROOT / "src" / "demo_template.html").read_text(encoding="utf-8")
    assert "/*__DATA__*/null" in html
    html = html.replace("/*__DATA__*/null", json.dumps(data, separators=(",", ":")))
    site = ROOT / "prototype_site"
    site.mkdir(exist_ok=True)
    for f in site.iterdir():
        if f.name != "index.html":
            raise SystemExit(f"prototype_site/ must contain only index.html, found {f.name}")
    (site / "index.html").write_text(html, encoding="utf-8")
    t = data["twins"]
    print("pair", t["pair_index"], "missed", t["missed"]["title"], t["missed"]["salary_band"],
          "ranks profile/A/B", t["missed"]["rank_profile"], t["missed"]["rank_A"], t["missed"]["rank_B"])
    print("A feed:", [(c["title"], c["rank_profile"]) for c in t["feed_A"]])
    print("size KB", round((site / "index.html").stat().st_size / 1024, 1))


if __name__ == "__main__":
    main()
