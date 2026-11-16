"""Each step writes its own part file; results.csv is always the concatenation of all parts."""
import pandas as pd
from core import ROOT

COLS = ["metric", "beta", "condition", "estimate", "ci_low", "ci_high", "n", "set"]
PARTS = ROOT / "outputs" / "parts"


def write_part(name, rows):
    PARTS.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows, columns=COLS)
    df.to_csv(PARTS / f"{name}.csv", index=False)
    combine()
    return df


def combine():
    order = ["heldout", "audit", "mitigation"]
    files = sorted(PARTS.glob("*.csv"), key=lambda p: (order.index(p.stem) if p.stem in order else 99, p.stem))
    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    df.to_csv(ROOT / "outputs" / "results.csv", index=False)
