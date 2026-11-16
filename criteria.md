# Phase 2 Pre-registration: The Opportunity Blindspot Audit

Written on 2026-11-14 **before any Phase 2 experiment was run**. The only results that existed when this
was written are the Phase 1 rebuild (seed 20261016) in `outputs/phase1_reproduction.json`.
This file is locked by a git commit and a SHA-256 in `criteria.lock`. It will not be edited after results
are seen. If a criterion fails, the failure is reported.

## 1. Data, split and seeds

- Data: JTH v1.1 (Zenodo 21390581), files `candidates.csv`, `jobs.csv`, `history.csv`.
- Pipeline: `src/core.py`, frozen as used for the Phase 1 rebuild (pool = top 100 jobs by TF-IDF
  profile similarity, history feature = TF-IDF plus seniority one-hot with weight 0.06,
  min-max normalised blend `score = (1 - beta) * compat + beta * history_sim`).
- Phase 2 seed: **20261115** for all sampling.
- Split: all 37,554 candidate IDs are sorted, then shuffled with seed 20261115. The first half is the
  **tune** set, the second half is the **test** set. Saved to `outputs/split.csv`.
- Every threshold and parameter is chosen on the tune set. Every headline number is reported on the test set.
- Uncertainty: 95% percentile bootstrap CIs with 3,000 resamples of the unit of analysis
  (candidate or twin pair). Paired sign-flip permutation test with 10,000 permutations on the headline TEG.
- Demographic or demographic-proxy fields (`llm_sex`, `llm_nationality`, `llm_age_bucket`,
  `llm_languages_spoken`, `zipcode`, `source`, `llm_graduation_recency`) are not used and not analysed.

## 2. Held-out history test (Step 3)

- Eligible: test-set candidates with non-empty profile text and at least 2 history processes whose jobs
  exist in `jobs.csv`, where the latest process is uniquely latest. A process's time is the earliest
  dated stage in that row. Candidates whose hidden job also appears among their earlier processes are dropped.
- Run only if at least 300 test candidates are eligible. Otherwise skipped, with the reason recorded in `results.csv`.
- For each eligible candidate: hide the latest process; build the real history vector as the mean history
  feature of the jobs in the earlier processes; rank the candidate's pool (top 100 by profile similarity) plus the
  hidden job if it is not already there; jobs from the earlier processes are removed from the ranked list.
- Betas: 0, 0.15, 0.30, 0.45, 0.60.
- Metrics: Hit@10 (hidden job in Top 10) and MRR (1 / rank of the hidden job in the full ranked list).
- The same procedure on tune-set candidates is used only for tuning mitigations.

**H1 (does history help?).** History has predictive value if, on the test set, Hit@10 at beta = 0.45 minus
Hit@10 at beta = 0 is **at least 2 percentage points** and the 95% paired-bootstrap CI of that difference
**excludes 0**. Otherwise H1 fails.

## 3. Audit metrics (Step 4)

- 1,200 twin pairs drawn without replacement from test-set candidates with non-empty profile text, seed 20261115.
  Twin A = senior-oriented synthetic history (5 Senior jobs), Twin B = entry-level synthetic history
  (5 Junior or Intern jobs), each drawn from the 20 most profile-similar jobs of that level. Profiles and pools are identical.
- Betas: 0, 0.15, 0.30, 0.45, 0.60.
- **Twin Exposure Gap (TEG)**: mean over pairs of (high-value share of Twin A's Top 10 minus Twin B's), in pp.
  High-value = top 20% of the pool on the value score (primary: 0.5 salary percentile + 0.3 permanent + 0.2 remote).
- **Missed opportunity**: a high-value job in a twin's own beta = 0 (profile-only) Top 10 that is absent from that
  twin's Top 10 at the given beta.
- **Blindspot Rate**: % of entry-history twins (Twin B) with at least 1 missed opportunity. Mean and median count per Twin B also reported.
- **Mobility Exposure**: share of Twin B's Top 10 that is one seniority level above its history level.
  Twin B's history is Junior or Intern level, so "one level up" = `Mid` (JTH `llm_seniority_level`, an LLM-inferred proxy).
  Senior twins have no level above Senior, so the metric is reported for Twin B only.
- **Compatibility cost**: 1 minus (mean Top-10 raw cosine profile compatibility at the given beta / mean at beta = 0),
  averaged over both twins of all pairs, in %.
- **Placebo**: both twins get Twin A's history; TEG should be about 0.
- **Robustness**: TEG at beta = 0.45 under primary, salary-only and equal-weights value definitions.
- **R1 (replication)**: Phase 1 replicates if test-set TEG at beta = 0.45 (primary) is > 0 with a CI excluding 0.
- **R2 (placebo)**: placebo |TEG| < 0.5 pp at beta = 0.45.
- **R3 (robustness)**: TEG at beta = 0.45 is > 0 with a CI excluding 0 under all three value definitions.

## 4. Mitigations (Step 5)

Baselines: beta = 0 (profile only) and beta = 0.45 (personalised). All mitigations start from beta = 0.45.

1. **History cap**: jobs flagged high-value are scored with beta_cap instead of 0.45. Grid beta_cap in {0, 0.05, 0.10, 0.15, 0.20, 0.30}.
2. **Profile floor**: every job in the twin's beta = 0 Top 10 whose min-max-normalised pool compatibility is at least tau
   keeps its Top-10 slot. The remaining slots are filled in beta = 0.45 order. Grid tau in {0.95, 0.90, 0.85, 0.80, 0.70}.
3. **Exploration slots**: the first 10 - k slots follow the beta = 0.45 ranking. The last k slots go to the
   highest-compatibility jobs not yet shown whose history similarity is at or below the pool median
   ("outside the history pattern"); if too few exist, the highest-compatibility remaining jobs fill them. Grid k in {1, 2, 3}.

**Tuning rule (tune set only).** For each method, compute on tune-set twins (1,200 pairs, seed 20261115) and tune-set
held-out candidates: TEG reduction, compatibility cost, Hit@10 retained. Keep the parameters that meet the fix-success
thresholds below on the tune set. Among those, pick the one with the highest Hit@10 retained (ties: larger TEG reduction).
If none meet all thresholds, pick the parameter with the largest TEG reduction among those with compatibility cost <= 2%;
if none of those exist, pick the largest TEG reduction. The chosen parameter is then evaluated once on the test set.

**Fix success (test set).** A mitigation succeeds if all of these hold:

- TEG reduction >= 50%: (TEG at 0.45 - TEG of method) / TEG at 0.45 >= 0.50.
- Compatibility cost <= 2% relative to beta = 0 (definition in Section 3).
- If H1 holds: Hit@10 retained >= 75%, where retained = (Hit@10 method - Hit@10 at 0) / (Hit@10 at 0.45 - Hit@10 at 0)
  on the held-out test candidates. If H1 fails, this condition is not applied and is reported as not applicable.

Decisions use point estimates on the test set; CIs are reported alongside.

## 5. Decision rule

- If **H1 holds**: the recommendation is the Audit plus the best mitigation that passes fix success
  (highest Hit@10 retained). If none pass, the recommendation is the Audit plus a "rank by my profile only" control,
  and every mitigation is reported as failing.
- If **H1 fails**: the recommendation becomes the Audit plus a "rank by my profile only" control, and
  mitigations are reported only as secondary results.
