"""Step 1: print JTH schema, row counts, key columns, ordered-history counts."""
import pandas as pd, numpy as np, json, pathlib
R = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
c = pd.read_csv(R/"candidates.csv"); j = pd.read_csv(R/"jobs.csv"); h = pd.read_csv(R/"history.csv")
for n, d in [("candidates", c), ("jobs", j), ("history", h)]:
    print(f"\n=== {n}: {d.shape[0]:,} rows x {d.shape[1]} cols")
    print(", ".join(d.columns))
print("\n--- key columns ---")
print("jobs.llm_seniority_level:", j.llm_seniority_level.value_counts(dropna=False).to_dict())
print("cand.llm_seniority_level:", c.llm_seniority_level.value_counts(dropna=False).to_dict())
print("jobs.salary non-null:", j.salary.notna().sum(), " llm_salary_estimation non-null:", j.llm_salary_estimation_eur_per_year.notna().sum())
print("jobs.contract_type top:", j.contract_type.value_counts(dropna=False).head(8).to_dict())
print("jobs.llm_remote_possible:", j.llm_remote_possible.value_counts(dropna=False).to_dict())
print("jobs.years_experience:", j.years_experience.value_counts(dropna=False).to_dict())
date_cols = [x for x in h.columns if x.endswith("_date")]
print("history date cols:", date_cols)
print("last_stage_reached:", h.last_stage_reached.value_counts().to_dict())
# ordering: first non-null date of each process
H = h.copy()
for col in date_cols: H[col] = pd.to_datetime(H[col], errors="coerce")
H["start"] = H[date_cols].min(axis=1)
print("processes with any timestamp:", H.start.notna().sum(), "/", len(H))
g = H.dropna(subset=["start"]).groupby("candidate_id")
n_proc = g.size()
n_dates = g.start.nunique()
# orderable: >=2 processes and the latest process start strictly after the earlier ones' max (no tie for last)
def last_unique(s):
    s = s.sort_values(); return len(s) >= 2 and s.iloc[-1] > s.iloc[-2]
orderable = g.start.apply(last_unique)
print("candidates in history:", h.candidate_id.nunique())
print("candidates with >=2 processes:", int((n_proc>=2).sum()))
print("candidates with >=2 processes and a uniquely-latest process (orderable):", int(orderable.sum()))
print("distribution of process counts:", n_proc.value_counts().sort_index().head(10).to_dict())
