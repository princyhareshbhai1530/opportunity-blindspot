"""Rebuild every Phase 2 output from raw data: python run_all.py"""
import subprocess, sys
from pathlib import Path

SRC = Path(__file__).resolve().parent / "src"
STEPS = [
    ("Download and check JTH data", "get_data.py"),
    ("Step 1: schema", "inspect_schema.py"),
    ("Step 1: Phase 1 rebuild (seed 20261016)", "phase1_reproduce.py"),
    ("Steps 2-3: split + held-out history test", "heldout.py"),
    ("Step 4: twin pairs (tune + test)", "twins.py"),
    ("Step 4: audit metrics", "audit.py"),
    ("Step 5: mitigation tuning + test evaluation", "mitigation.py"),
    ("A1: imputed-salary robustness", "robust_salary.py"),
    ("Figure: held-out curve", "fig_heldout.py"),
    ("Figure: trade-off", "fig_tradeoff.py"),
    ("Figure: gap by beta", "fig_gap_beta.py"),
    ("Figures: compact page 3 charts", "fig_pdf_charts.py"),
    ("A3: audit runtime (fresh process)", "runtime_audit.py"),
    ("Step 6: prototype", "build_prototype.py"),
    ("Step 6: prototype tests + screenshots", "shoot_prototype.py"),
    ("Live demo: build prototype_site/index.html", "build_demo.py"),
    ("Step 7: PDF", "build_pdf.py"),
]
for name, script in STEPS:
    print(f"\n=== {name} ===", flush=True)
    subprocess.run([sys.executable, script], cwd=SRC, check=True)
for t in ["test_demo_data.py", "test_demo_browser.py"]:
    print(f"\n=== Live demo test: {t} ===", flush=True)
    subprocess.run([sys.executable, str(SRC.parent / "tests" / t)], cwd=SRC.parent, check=True)
print("\n=== Step 8: verify ===", flush=True)
sys.exit(subprocess.run([sys.executable, "verify.py"], cwd=SRC.parent).returncode)
