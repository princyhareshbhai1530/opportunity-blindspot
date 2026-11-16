# The Opportunity Blindspot Audit (Phase 2)

TECHNATION "Behind the Feed" Phase 2 submission. A controlled simulation on the public JTH v1.1 dataset.
It is not an audit of a real platform.

## Reproduce everything with one command

```bash
pip install pandas numpy scipy scikit-learn matplotlib pymupdf playwright pyarrow
python run_all.py
```

`run_all.py` downloads JTH v1.1 from Zenodo (record 21390581) and checks each file's SHA-256. It then runs every step and ends with `verify.py`. A full run takes about 2.5 minutes, and repeated runs give byte-identical `results.csv`.

Rendering uses Playwright with the installed Microsoft Edge (`channel="msedge"`). If you don't have Edge, run `python -m playwright install chromium` and remove the `channel` argument.

## Deliverables

| File | What |
|---|---|
| `pdf/Opportunity_Blindspot_Phase2.pdf` | The 5-page submission (US Letter landscape) |
| `prototype/index.html` | Single-file prototype: Opportunity Receipt and Operator Audit Scorecard. No external requests. |
| `prototype_site/index.html` | Live pitch demo (Pitch and Explore modes), one self-contained file for hosting. Built by `src/build_demo.py`, tested by `tests/test_demo_data.py` and `tests/test_demo_browser.py`; screenshots in `figures/demo/` |
| `criteria.md`, `criteria.lock` | Pre-registration, committed before any Phase 2 result (git commit `eaee1ee`) |
| `outputs/results.csv` | Every Phase 2 metric: `metric, beta, condition, estimate, ci_low, ci_high, n, set` |
| `outputs/passfail.md` | Mitigation pass/fail table against the pre-registered criteria |
| `outputs/sources.md` | Policy and data source verification log |
| `figures/` | `heldout_curve.png`, `tradeoff.png`, `receipt.png`, `scorecard.png` (plus print crops) |

## Pipeline (`src/`)

| Step | Script | Output |
|---|---|---|
| Data | `get_data.py` | `data/raw/*.csv` (not committed; CC BY-NC 4.0) |
| 1 | `inspect_schema.py`, `phase1_reproduce.py` | Schema printout; `outputs/phase1_reproduction.json` |
| 2-3 | `heldout.py` | `outputs/split.csv`, held-out Hit@10 and MRR, H1 verdict |
| 4 | `twins.py`, `audit.py` | `outputs/twins_{tune,test}.csv`, audit rows in `results.csv` |
| 5 | `mitigation.py` | Tuning on the tune set, one test evaluation per method, `mitigation_summary.json` |
| A1 | `robust_salary.py` (exploratory, added after pre-registration) | Gap without LLM-imputed salaries: `outputs/robust_salary.json`, `results.csv` conditions `posted_salary_only`, `exclude_imputed_from_hv` |
| Figures | `fig_heldout.py`, `fig_tradeoff.py`, `fig_gap_beta.py`, `fig_pdf_charts.py` | `figures/*.png`; `figures/chart_fonts.json` records the smallest drawn font so `verify.py` can check printed size |
| A3 | `runtime_audit.py` | Wall-clock time of one full audit in a fresh process: `outputs/runtime.json` |
| 6 | `build_prototype.py`, `shoot_prototype.py` | `prototype/index.html`, interaction tests, screenshots |
| 7 | `build_pdf.py` (template `pdf_template.html`, numbers from `numbers_spec.py`) | `pdf/source.html`, the PDF, `pdf/page_*.png` |
| 8 | `verify.py` | Traces every number in the PDF to `outputs/`, checks layout and wording rules |

Shared code: `core.py` (matching, twins, value proxy, bootstrap), `methods.py` (ranking methods and the split).

## Method notes

- **Phase 1 rebuild.** The Phase 1 code was not available, so the pipeline was rebuilt from the Phase 1 method. One unrecorded choice, the seniority weight in the history features (`SEN_W = 0.06`), was calibrated against the published Phase 1 figures. The trials are in `outputs/phase1_calibration_sweep*.json`. The rebuild gives 5.09 pp against 5.45 pp published. The value was frozen before Phase 2.
- **Seeds.** Seed 20261115 drives all Phase 2 sampling, with a 50/50 tune/test split by candidate ID. Every CI uses 3,000 bootstrap resamples, and the permutation test uses 10,000 sign flips.
- **Demographic fields.** The LLM-inferred demographic fields in JTH (`llm_sex`, `llm_nationality`, `llm_age_bucket`) are never used or analysed. The same applies to likely proxies such as languages spoken, zipcode and source.
