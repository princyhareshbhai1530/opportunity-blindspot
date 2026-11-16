| Method | TEG reduction (>=50%) | Compat cost (<=2%) | Hit@10 retained (>=75%) | Blindspot Rate | Verdict |
|---|---|---|---|---|---|
| Profile only (beta = 0) (beta=0.00) | 100.0% | 0.0% | 0.0% | 0.0% | baseline |
| Personalized (beta = 0.45) (beta=0.45) | 0.0% | 2.0% | 100.0% | 45.8% | baseline |
| history_cap (history_cap=0.3) | 75.4 [67.2, 84.6]% PASS | 1.8 [1.7, 1.9]% PASS | 71.3 [59.1, 83.8]% FAIL | 34.1 [31.5, 36.8]% | FAIL |
| profile_floor (profile_floor=0.7) | 34.3 [27.0, 41.3]% FAIL | 1.2 [1.1, 1.3]% PASS | 78.7 [66.7, 93.1]% PASS | 31.2 [28.4, 33.8]% | FAIL |
| exploration (exploration=3) | 66.8 [56.5, 77.9]% PASS | 1.9 [1.8, 2.0]% PASS | 45.7 [27.4, 62.1]% FAIL | 37.3 [34.6, 40.0]% | FAIL |

Recommendation (criteria.md Section 5): Audit + 'rank by my profile only' control (no mitigation passed)
