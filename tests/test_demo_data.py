"""Data test for prototype_site/index.html (run: python tests/test_demo_data.py).

Loads the JSON embedded in the final HTML and asserts every headline number the pitch must show,
formatted exactly as the demo formats it, plus a cross-check against outputs/results.csv and the
other output files, so the embedded data cannot drift from the pipeline.
"""
import json, re, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
html = (ROOT / "prototype_site" / "index.html").read_text(encoding="utf-8")
m = re.search(r"const D = (\{.*?\});\n", html, re.S)
assert m, "embedded data not found"
D = json.loads(m.group(1))
fails, oks = [], []


def eq(label, got, want):
    (oks if got == want else fails).append(f"{'ok  ' if got == want else 'FAIL'} {label}: {got!r} (want {want!r})")


f1 = lambda x: f"{x:.1f}"; f2 = lambda x: f"{x:.2f}"
p, p0 = D["per_beta"]["0.45"], D["per_beta"]["0.00"]
# Section 0.4 of the brief
eq("Twin Exposure Gap", f2(p["TEG_pp"][0]), "5.25")
eq("TEG CI", (f2(p["TEG_pp"][1]), f2(p["TEG_pp"][2])), ("4.51", "5.95"))
eq("Twin A high-value share", f1(p["hv_A_pct"][0]), "21.8")
eq("Twin B high-value share", f1(p["hv_B_pct"][0]), "16.5")
eq("Blindspot Rate", f1(p["blindspot_rate_pct"][0]), "45.8")
eq("Blindspot CI", (f1(p["blindspot_rate_pct"][1]), f1(p["blindspot_rate_pct"][2])), ("42.8", "48.6"))
eq("Placebo", f2(p["placebo_pp"][0]), "0.00")
eq("Hit@10 profile only", f1(p0["hit10_pct"][0]), "5.4")
eq("Hit@10 personalized", f1(p["hit10_pct"][0]), "7.9")
eq("Hit@10 gain", f2(D["h1_gain_pp"][0]), "2.49")
eq("Compatibility cost", f2(p["compat_cost_pct"][0]), "2.02")
eq("Mobility Exposure", f1(p["mobility_exposure_pct"][0]), "42.6")
eq("Mobility profile only", f1(p0["mobility_exposure_pct"][0]), "46.9")
eq("Mobility drop", f1(p0["mobility_exposure_pct"][0] - p["mobility_exposure_pct"][0]), "4.3")
d = D["defaults"]
eq("Default thresholds", (f2(d["TEG_pp"]), f1(d["blindspot_rate_pct"]), f2(d["mobility_drop_pp"]), str(+d["compat_cost_pct"]).rstrip("0").rstrip(".")),
   ("2.62", "22.9", "2.14", "2"))
want_fix = {"History cap": ("75.4", "1.82", "71.3", False), "Profile floor": ("34.3", "1.21", "78.7", False),
            "Exploration slots": ("66.8", "1.92", "45.7", False)}
for x in D["fixes"]:
    eq(f"Fix {x['name']}", (f1(x["gap_cut_pct"]), f2(x["compat_cost_pct"]), f1(x["hit10_kept_pct"]), x["pass"]), want_fix[x["name"]])
eq("Fix names", sorted(x["name"] for x in D["fixes"]), sorted(want_fix))
M = D["twins"]["missed"]
eq("Example twin role", (M["title"], M["salary_band"], M["rank_profile"], M["rank_B"]),
   ("Senior full stack developer", "EUR 65k to 70k", 7, 21))
eq("Missed role in Twin A's Top 10", any(c["id"] == M["id"] for c in D["twins"]["feed_A"]), True)
eq("Missed role absent from Twin B's Top 10", any(c["id"] == M["id"] for c in D["twins"]["feed_B"]), False)
eq("Missed role at #7 in profile-only Top 10", [c["id"] for c in D["twins"]["feed_profile"]].index(M["id"]) + 1, 7)
eq("Receipt counts", (D["twins"]["n_with_blindspot"], D["twins"]["n_twins"], D["twins"]["n_missed"]), (549, 1200, 1))

# Cross-check embedded data against the pipeline outputs
r = pd.read_csv(ROOT / "outputs" / "results.csv"); te = r[r.set == "test"]
for b, e in D["per_beta"].items():
    for key, (met, cond) in {"TEG_pp": ("TEG_pp", "treatment"), "blindspot_rate_pct": ("blindspot_rate_pct", "treatment"),
                             "mobility_exposure_pct": ("mobility_exposure_pct", "treatment"), "compat_cost_pct": ("compat_cost_pct", "treatment"),
                             "hit10_pct": ("heldout_hit10", "real_history"), "placebo_pp": ("TEG_pp", "placebo_identical_history"),
                             "hv_A_pct": ("hv_share_A_pct", "treatment"), "hv_B_pct": ("hv_share_B_pct", "treatment")}.items():
        row = te[(te.metric == met) & ((te.beta - float(b)).abs() < 1e-9) & (te.condition == cond)].iloc[0]
        eq(f"beta {b} {key} equals results.csv", [round(v, 9) for v in e[key]],
           [round(float(row.estimate), 9), round(float(row.ci_low), 9), round(float(row.ci_high), 9)])
eq("embedded data equals outputs/demo_data.json", D, json.loads((ROOT / "outputs" / "demo_data.json").read_text()))
proto = json.loads((ROOT / "outputs" / "prototype_data.json").read_text())
eq("defaults equal the PDF prototype", D["defaults"], proto["scorecard"]["defaults"])
ext = re.findall(r"""(?:src|href)\s*=\s*["'](https?:)?//""", html) + re.findall(r"@import|fetch\(|XMLHttpRequest|<link[^>]+stylesheet", html)
eq("no external references in the HTML", ext, [])
eq("no em or en dashes in the HTML", [c for c in ("—", "–") if c in html], [])
eq("footer licence note", "Data: JTH v1.1, CC BY-NC 4.0. Non-commercial research prototype. Precomputed test-set results; does not rank live jobs." in html, True)

print("\n".join(oks + fails))
print(f"\n{len(oks)} passed, {len(fails)} failed")
sys.exit(1 if fails else 0)
