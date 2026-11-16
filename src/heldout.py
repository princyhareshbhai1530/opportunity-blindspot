"""Step 3: held-out real-history test (criteria.md Section 2).

For each eligible candidate, hide the latest process, build history from earlier processes,
rank pool + hidden job, record Hit@10 and reciprocal rank for every method / grid value.
Per-candidate results are saved for both sets (tune is used only for mitigation tuning).
"""
import json
import numpy as np
import pandas as pd
from core import World, ROOT, TOPK, bootstrap_mean_ci
from methods import SEED2, BETAS2, all_methods, make_split, rank
from results_io import write_part

MIN_ELIGIBLE = 300


def eligible_table(w, split):
    h = w.hist.copy()
    dc = [c for c in h.columns if c.endswith("_date")]
    for c in dc:
        h[c] = pd.to_datetime(h[c], errors="coerce")
    h["t"] = h[dc].min(axis=1)
    h = h[h.job_id.isin(w.jid_index) & h.candidate_id.isin(w.cid_index)]
    h = h[h.candidate_id.map(lambda c: bool(w.cand_has_text[w.cid_index[c]]))]
    h = h.merge(split, on="candidate_id")
    rows = []
    for cid, g in h.groupby("candidate_id"):
        if len(g) < 2:
            continue
        g = g.sort_values(["t", "application_id"], kind="stable")
        if not g.t.iloc[-1] > g.t.iloc[-2]:
            continue
        hidden = g.job_id.iloc[-1]
        earlier = list(g.job_id.iloc[:-1])
        if hidden in earlier:
            continue
        rows.append((cid, g["set"].iloc[0], hidden, earlier))
    return pd.DataFrame(rows, columns=["candidate_id", "set", "hidden", "earlier"])


def evaluate(w, el):
    meths = all_methods()
    recs = []
    cand_rows = el.candidate_id.map(w.cid_index).to_numpy()
    for start in range(0, len(el), 500):
        sims = w.profile_sims(cand_rows[start:start + 500])
        for off in range(sims.shape[0]):
            r = el.iloc[start + off]
            s = sims[off]
            hid = w.jid_index[r.hidden]
            earlier = [w.jid_index[j] for j in r.earlier]
            pool = w.pool(s, extra_job=hid)
            pool = np.array([j for j in pool if j not in set(earlier)])
            pos = int(np.where(pool == hid)[0][0])
            compat = s[pool]
            hsim = w.history_sim(pool, w.history_vector(earlier))
            hv = w.high_value(pool)
            rec = {"candidate_id": r.candidate_id, "set": r.set, "n_earlier": len(earlier)}
            for label, m, p in meths:
                order = rank(m, p, compat, hsim, hv)
                rk = int(np.where(order == pos)[0][0]) + 1
                rec[f"hit|{label}"] = float(rk <= TOPK)
                rec[f"rr|{label}"] = 1.0 / rk
            recs.append(rec)
    return pd.DataFrame(recs)


def main():
    w = World()
    split = make_split(w)
    el = eligible_table(w, split)
    counts = el.set.value_counts().to_dict()
    n_test = int(counts.get("test", 0))
    print("eligible:", counts)
    rows = []
    if n_test < MIN_ELIGIBLE:
        rows.append(["heldout_skipped", "", f"only {n_test} eligible test candidates (<300)", np.nan, np.nan, np.nan, n_test, "test"])
        write_part("heldout", rows)
        return
    per = evaluate(w, el)
    per.to_csv(ROOT / "outputs" / "heldout_per_candidate.csv", index=False)
    rng = np.random.default_rng(SEED2 + 3)
    summary = {"eligible": counts}
    for st in ["test", "tune"]:
        d = per[per.set == st]
        for b in BETAS2:
            lab = f"beta={b:.2f}"
            for met, key in [("heldout_hit10", "hit"), ("heldout_mrr", "rr")]:
                x = d[f"{key}|{lab}"].to_numpy() * (100 if key == "hit" else 1)
                e, lo, hi = bootstrap_mean_ci(x, rng)
                rows.append([met, b, "real_history", e, lo, hi, len(x), st])
        diff = (d["hit|beta=0.45"] - d["hit|beta=0.00"]).to_numpy() * 100
        e, lo, hi = bootstrap_mean_ci(diff, rng)
        rows.append(["heldout_hit10_gain_vs_beta0", 0.45, "real_history", e, lo, hi, len(diff), st])
        if st == "test":
            h1 = (e >= 2.0) and (lo > 0 or hi < 0)
            summary["H1"] = {"gain_pp": e, "ci": [lo, hi], "n": len(diff), "pass": bool(h1)}
            rows.append(["H1_pass", 0.45, "criteria: gain>=2pp and CI excludes 0", float(h1), np.nan, np.nan, len(diff), st])
    write_part("heldout", rows)
    (ROOT / "outputs" / "heldout_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
