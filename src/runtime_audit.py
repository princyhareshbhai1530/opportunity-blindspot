"""A3: time one full Opportunity Blindspot audit from a clean start (fresh Python process).

The timed run: load JTH + build TF-IDF, build 1,200 test-set twin pairs, rank both twins (plus placebo) at every
beta in {0, 0.15, 0.30, 0.45, 0.60}, compute the three exposure metrics plus the compatibility guard, and run
3,000 bootstrap resamples per metric per beta plus the 10,000-flip permutation test.
Writes outputs/runtime.json (wall-clock seconds, CPU model, RAM). Results are not written; audit.py is the source.
"""
import json, platform, re, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = 3

CHILD = r"""
import numpy as np
from core import World, TOPK
from methods import SEED2, BETAS2, load_split, rank
from twins import sample_pairs, pair_detail
from audit import boot
from core import paired_permutation_p
w = World()
rows = sample_pairs(w, load_split(), "test")
rec = {b: {k: [] for k in ("hvA", "hvB", "missB", "mobB", "comp")} for b in BETAS2}
for i, row in enumerate(rows):
    d = pair_detail(w, row, i, "test")
    pool, compat, hv = d["pool"], d["compat"], d["hv"]["primary"]
    top0B = set(rank("beta", 0.0, compat, d["simB"], hv)[:TOPK])
    for b in BETAS2:
        tA = rank("beta", b, compat, d["simA"], hv)[:TOPK]
        tB = rank("beta", b, compat, d["simB"], hv)[:TOPK]
        rank("beta", b, compat, d["simA"], hv)  # placebo ranking (B with A's history)
        r = rec[b]; sB = set(tB)
        r["hvA"].append(hv[tA].mean()); r["hvB"].append(hv[tB].mean())
        r["missB"].append(sum(1 for j in top0B if hv[j] and j not in sB))
        r["mobB"].append((w.sen[pool[tB]] == 2).mean())
        r["comp"].append((compat[tA].mean() + compat[tB].mean()) / 2)
rng = np.random.default_rng(SEED2 + 11)
c0 = np.array(rec[0.0]["comp"])
for b in BETAS2:
    r = {k: np.array(v) for k, v in rec[b].items()}
    n = len(r["hvA"])
    boot(lambda i: (r["hvA"][i] - r["hvB"][i]).mean() * 100, n, rng)
    boot(lambda i: (r["missB"][i] >= 1).mean() * 100, n, rng)
    boot(lambda i: r["mobB"][i].mean() * 100, n, rng)
    boot(lambda i: (1 - r["comp"][i].mean() / c0[i].mean()) * 100, n, rng)
r = rec[0.45]
paired_permutation_p(np.array(r["hvA"]) - np.array(r["hvB"]), np.random.default_rng(SEED2 + 13))
print("audit done", len(rows), "pairs")
"""


def machine():
    cpu = platform.processor()
    try:
        cpu = subprocess.run(["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Processor).Name"],
                             capture_output=True, text=True, timeout=60).stdout.strip() or cpu
    except Exception:
        pass
    try:
        import psutil
        ram = round(psutil.virtual_memory().total / 2**30, 1)
    except Exception:
        ram = None
    return cpu, ram


def main():
    runs = []
    for _ in range(RUNS):  # each run is a new Python process; report the slowest so the PDF never overstates speed
        t0 = time.perf_counter()
        out = subprocess.run([sys.executable, "-c", CHILD], cwd=HERE, capture_output=True, text=True)
        runs.append(round(time.perf_counter() - t0, 1))
        if out.returncode != 0:
            sys.exit(out.stderr)
    secs = max(runs)
    cpu, ram = machine()
    res = {"wall_clock_seconds": round(secs, 1), "runs_seconds": runs, "reported": f"slowest of {RUNS} fresh runs", "wall_clock_minutes": round(secs / 60, 1),
           "cpu": cpu, "cpu_short": re.sub(r"\s+", " ", re.sub(r"\((R|TM)\)", "", cpu)).strip(), "ram_gb": ram, "os": platform.platform(), "python": platform.python_version(),
           "scope": "fresh process: load JTH + TF-IDF, 1,200 test twin pairs, ranking at 5 betas (+placebo), "
                    "3 exposure metrics + compatibility guard, 3,000 bootstraps each, 10,000-flip permutation test",
           "child_stdout": out.stdout.strip()}
    (HERE.parent / "outputs" / "runtime.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
