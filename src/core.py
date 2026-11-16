"""Core pipeline shared by the Phase 1 rebuild and all Phase 2 experiments.

Rebuilt from the Phase 1 method (the original Phase 1 code was not available):
  * TF-IDF profile similarity -> each candidate's matched opportunity pool (top POOL_SIZE jobs)
  * Digital twins: identical profile, synthetic history differs (senior vs entry)
  * score = (1 - beta) * profile_compatibility + beta * history_similarity
  * value = 0.5 salary percentile + 0.3 permanent + 0.2 remote; high-value = top 20% within pool
Protected / demographic-proxy fields (llm_sex, llm_nationality, llm_age_bucket,
llm_languages_spoken, zipcode, source, graduation recency) are never used for matching.
"""
from __future__ import annotations
import pathlib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize
from scipy import sparse

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

POOL_SIZE = 100          # matched opportunity pool per candidate
TOPK = 10                # visibility window
HIST_K = 5               # synthetic history length (jobs)
HIST_NEIGH = 20          # history jobs are drawn from the 20 most profile-similar jobs of that seniority
HV_SHARE = 0.20          # high-value = top 20% within pool
SEN_W = 0.06             # weight of seniority one-hot in the history feature space (calibrated to Phase 1, see outputs/phase1_calibration_sweep*.json)

TEXT_COLS_CAND = ["skills", "expertise_area", "job_category", "llm_hard_skills",
                  "llm_programming_languages", "llm_tools_technologies",
                  "llm_expertise_area", "llm_job_category", "llm_industry_domains"]
TEXT_COLS_JOB = ["skills", "expertise_area", "job_category", "llm_hard_skills",
                 "llm_programming_languages", "llm_tools_technologies",
                 "llm_expertise_area", "llm_job_category", "llm_industry_domains"]
SEN_LEVELS = ["Intern", "Junior", "Mid", "Senior"]
SEN_ORD = {"Intern": 0, "Junior": 1, "Mid": 2, "Senior": 3}

VALUE_DEFS = {
    "primary": (0.5, 0.3, 0.2),
    "salary_only": (1.0, 0.0, 0.0),
    "equal_weights": (1 / 3, 1 / 3, 1 / 3),
}


def _text(df, cols):
    t = df[cols].fillna("").astype(str).agg(" ".join, axis=1)
    return t.str.replace(";", " ", regex=False).str.replace("_rare_skill_", " ", regex=False)


class World:
    """Loads JTH once and holds job features, TF-IDF matrices and value inputs."""

    def __init__(self):
        self.cand = pd.read_csv(RAW / "candidates.csv")
        self.jobs = pd.read_csv(RAW / "jobs.csv")
        self.hist = pd.read_csv(RAW / "history.csv")
        ct, jt = _text(self.cand, TEXT_COLS_CAND), _text(self.jobs, TEXT_COLS_JOB)
        vec = TfidfVectorizer(min_df=2, sublinear_tf=True, token_pattern=r"(?u)\b[\w+#.-]{2,}\b",
                              lowercase=True)
        vec.fit(pd.concat([ct, jt]))
        self.C = normalize(vec.transform(ct))
        self.J = normalize(vec.transform(jt))
        self.cand_has_text = np.asarray(self.C.getnnz(axis=1) > 0)
        self.cid_index = {c: i for i, c in enumerate(self.cand.candidate_id)}
        self.jid_index = {j: i for i, j in enumerate(self.jobs.job_id)}
        j = self.jobs
        self.sen = j.llm_seniority_level.fillna("Mid").map(SEN_ORD).fillna(2).astype(int).to_numpy()
        self.salary = j.salary.where(j.salary.notna() & (j.salary > 0),
                                     j.llm_salary_estimation_eur_per_year).astype(float).to_numpy()
        self.permanent = (j.contract_type.fillna("") == "permanent").to_numpy().astype(float)
        self.remote = j.llm_remote_possible.fillna(False).astype(bool).to_numpy().astype(float)
        # history feature space: topic (TF-IDF) + seniority one-hot
        onehot = sparse.csr_matrix(np.eye(4)[self.sen])
        self.H = normalize(sparse.hstack([self.J * np.sqrt(1 - SEN_W), onehot * np.sqrt(SEN_W)]).tocsr())
        self.junior_idx = np.where(self.sen <= 1)[0]
        self.senior_idx = np.where(self.sen == 3)[0]

    # ---------- pools ----------
    def profile_sims(self, cand_rows):
        return (self.C[cand_rows] @ self.J.T).toarray()

    def pool(self, sims_row, extra_job=None):
        idx = np.argsort(-sims_row, kind="stable")[:POOL_SIZE]
        if extra_job is not None and extra_job not in set(idx):
            idx = np.append(idx, extra_job)
        return idx

    # ---------- value ----------
    def value(self, pool_idx, vdef="primary"):
        ws, wp, wr = VALUE_DEFS[vdef]
        s = self.salary[pool_idx]
        pct = pd.Series(s).rank(pct=True, method="average").to_numpy()
        return ws * pct + wp * self.permanent[pool_idx] + wr * self.remote[pool_idx]

    def high_value(self, pool_idx, vdef="primary"):
        v = self.value(pool_idx, vdef)
        thr = np.quantile(v, 1 - HV_SHARE)
        return v >= thr

    # ---------- histories ----------
    def synthetic_history(self, sims_row, kind, rng):
        cand_set = self.senior_idx if kind == "senior" else self.junior_idx
        near = cand_set[np.argsort(-sims_row[cand_set], kind="stable")[:HIST_NEIGH]]
        pick = rng.choice(near, size=HIST_K, replace=False)
        return pick

    def history_vector(self, job_ids):
        v = np.asarray(self.H[job_ids].mean(axis=0)).ravel()
        n = np.linalg.norm(v)
        return v / n if n > 0 else v

    def history_sim(self, pool_idx, hvec):
        return np.asarray(self.H[pool_idx] @ hvec).ravel()


def minmax(x):
    lo, hi = x.min(), x.max()
    return (x - lo) / (hi - lo) if hi > lo else np.zeros_like(x)


def rank_scores(compat, hsim, beta):
    """Blend min-max-normalised compatibility and history similarity within the pool."""
    return (1 - beta) * minmax(compat) + beta * minmax(hsim)


def topk(scores, k=TOPK):
    return np.argsort(-scores, kind="stable")[:k]


def bootstrap_mean_ci(x, rng, B=3000, alpha=0.05):
    x = np.asarray(x, float)
    n = len(x)
    idx = rng.integers(0, n, size=(B, n))
    m = x[idx].mean(axis=1)
    return float(x.mean()), float(np.quantile(m, alpha / 2)), float(np.quantile(m, 1 - alpha / 2))


def paired_permutation_p(d, rng, P=10000):
    """Sign-flip permutation test on paired differences (swapping twin labels)."""
    d = np.asarray(d, float)
    obs = abs(d.mean())
    signs = rng.choice([-1.0, 1.0], size=(P, len(d)))
    null = np.abs((signs * d).mean(axis=1))
    return float((np.sum(null >= obs) + 1) / (P + 1))
