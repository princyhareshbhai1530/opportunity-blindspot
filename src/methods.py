"""Phase 2 ranking methods (baselines + mitigations), exactly as pre-registered in criteria.md."""
import numpy as np
import pandas as pd
from core import minmax, rank_scores, TOPK, ROOT

SEED2 = 20261115
BETAS2 = [0.0, 0.15, 0.30, 0.45, 0.60]
BASE_BETA = 0.45
GRIDS = {
    "history_cap": [0.0, 0.05, 0.10, 0.15, 0.20, 0.30],
    "profile_floor": [0.95, 0.90, 0.85, 0.80, 0.70],
    "exploration": [1, 2, 3],
}


def full_order(scores):
    return np.argsort(-scores, kind="stable")


def rank(method, param, compat, hsim, hv):
    """Return the full ranked order (indices into the pool). First TOPK entries = the feed."""
    if method == "beta":
        return full_order(rank_scores(compat, hsim, param))
    base = rank_scores(compat, hsim, BASE_BETA)
    if method == "history_cap":
        s = np.where(hv, rank_scores(compat, hsim, param), base)
        return full_order(s)
    base_order = full_order(base)
    if method == "profile_floor":
        p0 = full_order(rank_scores(compat, hsim, 0.0))[:TOPK]
        cn = minmax(compat)
        keep = [j for j in p0 if cn[j] >= param]
        top = list(keep)
        for j in base_order:
            if len(top) >= TOPK:
                break
            if j not in top:
                top.append(j)
        # present in personalised order for readability; membership is what matters
        top = sorted(top, key=lambda j: -base[j])
    elif method == "exploration":
        k = int(param)
        top = list(base_order[:TOPK - k])
        med = np.median(hsim)
        cand = [j for j in full_order(compat) if j not in top and hsim[j] <= med]
        extra = cand[:k]
        if len(extra) < k:
            extra += [j for j in full_order(compat) if j not in top and j not in extra][:k - len(extra)]
        top = top + extra
    else:
        raise ValueError(method)
    tset = set(top)
    rest = [j for j in base_order if j not in tset]
    return np.array(top + rest)


def all_methods(tuned=None):
    """List of (label, method, param). tuned: dict method->param for the chosen mitigation settings."""
    out = [(f"beta={b:.2f}", "beta", b) for b in BETAS2]
    for m, grid in GRIDS.items():
        params = [tuned[m]] if tuned and m in tuned else grid
        out += [(f"{m}={p}", m, p) for p in params]
    return out


def load_split():
    return pd.read_csv(ROOT / "outputs" / "split.csv")


def make_split(world):
    ids = np.array(sorted(world.cand.candidate_id))
    rng = np.random.default_rng(SEED2)
    perm = rng.permutation(len(ids))
    half = len(ids) // 2
    s = np.empty(len(ids), dtype=object)
    s[perm[:half]] = "tune"
    s[perm[half:]] = "test"
    df = pd.DataFrame({"candidate_id": ids, "set": s})
    df.to_csv(ROOT / "outputs" / "split.csv", index=False)
    return df
