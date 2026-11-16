"""Browser test for prototype_site/index.html (run: python tests/test_demo_browser.py).

Opens the file from disk with every network request blocked, then checks:
  zero requests, zero console errors or warnings, keyboard pitch flow, the profile-only re-sort (#21 -> #7),
  every history weight against outputs/results.csv, a threshold edit flipping a badge, reduced motion,
  and saves screenshots to figures/demo/ at 1920x1080, 1440x900 and 390x844.
"""
import json, sys
from pathlib import Path
import pandas as pd
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "prototype_site" / "index.html"
OUT = ROOT / "figures" / "demo"
OUT.mkdir(parents=True, exist_ok=True)
fails, notes = [], []


def check(ok, msg):
    (notes if ok else fails).append(("ok   " if ok else "FAIL ") + msg)


# expected values straight from results.csv (independent of the demo's own JSON)
r = pd.read_csv(ROOT / "outputs" / "results.csv"); te = r[r.set == "test"]
def est(met, b, cond="treatment"):
    return float(te[(te.metric == met) & ((te.beta - b).abs() < 1e-9) & (te.condition == cond)].iloc[0].estimate)
BETAS = [0.0, 0.15, 0.30, 0.45, 0.60]
EXP = {}
mob0 = est("mobility_exposure_pct", 0.0)
for b in BETAS:
    EXP[b] = {"TEG_pp": f"{est('TEG_pp', b):.2f} pp", "blindspot_rate_pct": f"{est('blindspot_rate_pct', b):.1f}%",
              "mobility_drop_pp": f"{est('mobility_exposure_pct', b):.1f}%", "compat_cost_pct": f"{est('compat_cost_pct', b):.2f}%",
              "drop": mob0 - est("mobility_exposure_pct", b)}
D = json.loads((ROOT / "outputs" / "demo_data.json").read_text())
THR = D["defaults"]
M = D["twins"]["missed"]


def expected_badge(b, key):
    v = {"TEG_pp": est("TEG_pp", b), "blindspot_rate_pct": est("blindspot_rate_pct", b),
         "mobility_drop_pp": max(0, EXP[b]["drop"]), "compat_cost_pct": est("compat_cost_pct", b)}[key]
    return "Pass" if v <= THR[key] + 1e-9 else "Fail"


def open_page(br, w, h, reduced=False):
    ctx = br.new_context(viewport={"width": w, "height": h}, reduced_motion="reduce" if reduced else "no-preference",
                         offline=True)
    reqs, msgs = [], []
    ctx.route("**/*", lambda route: route.continue_() if route.request.url.startswith("file:") else (reqs.append(route.request.url), route.abort()))
    pg = ctx.new_page()
    pg.on("console", lambda m: msgs.append(f"{m.type}: {m.text}") if m.type in ("error", "warning") else None)
    pg.on("pageerror", lambda e: msgs.append(f"pageerror: {e}"))
    pg.on("request", lambda q: None if q.url.startswith(("file:", "data:")) else reqs.append(q.url))
    pg.goto(SITE.as_uri()); pg.wait_for_load_state("load")
    return ctx, pg, reqs, msgs


def missed_rank(pg, list_id):
    return pg.eval_on_selector(f'#{list_id} .row[data-id="{M["id"]}"]',
                               "e => [e.querySelector('.rk').textContent, getComputedStyle(e).getPropertyValue('--slot').trim(), e.classList.contains('out')]")


def shoot(pg, name):
    pg.screenshot(path=str(OUT / name))


def no_hscroll(pg, label):
    sw = pg.evaluate("document.documentElement.scrollWidth"); cw = pg.evaluate("document.documentElement.clientWidth")
    check(sw <= cw, f"{label}: no horizontal scroll ({sw} <= {cw})")


def run_view(br, w, h, tag, full):
    ctx, pg, reqs, msgs = open_page(br, w, h)
    pg.wait_for_timeout(5600)  # let the first-load key hint fade
    hint = pg.eval_on_selector("#hint", "e => getComputedStyle(e).opacity")
    check(float(hint) < 0.05, f"{tag}: key hint faded")
    shoot(pg, f"pitch_step_1{'' if full else '_' + tag}.png"); no_hscroll(pg, f"{tag} step 1")
    check("Same person, two feeds." in pg.inner_text("#headline"), f"{tag}: step 1 headline")
    a_rank = missed_rank(pg, "listA"); b_rank = missed_rank(pg, "listB1")
    check(a_rank[0] == f"#{M['rank_A']}" and not a_rank[2], f"{tag}: missed role visible in Twin A at #{M['rank_A']}")
    check(b_rank[2], f"{tag}: missed role absent from Twin B's Top 10")
    pg.keyboard.press("ArrowRight"); pg.wait_for_timeout(1900)
    check("The invisible rejection." in pg.inner_text("#headline"), f"{tag}: step 2 headline")
    rk = missed_rank(pg, "listB2")
    check(rk[0] == f"#{M['rank_B']}" and pg.inner_text("#rkB") == f"#{M['rank_B']}" and pg.inner_text("#rk0") == f"#{M['rank_profile']}",
          f"{tag}: step 2 slides #{M['rank_profile']} to #{M['rank_B']}")
    shoot(pg, f"pitch_step_2{'' if full else '_' + tag}.png"); no_hscroll(pg, f"{tag} step 2")
    pg.keyboard.press("ArrowRight"); pg.wait_for_timeout(700)
    check("The receipt." in pg.inner_text("#headline"), f"{tag}: step 3 headline")
    check("1 role that matches your profile was ranked lower because of your browsing history. Show it?" in pg.inner_text(".receipt .alert"),
          f"{tag}: receipt wording")
    pg.click("#showIt"); pg.wait_for_timeout(200)
    check(pg.is_visible("#rJob"), f"{tag}: Show it reveals the role")
    shoot(pg, f"pitch_step_3{'' if full else '_' + tag}.png"); no_hscroll(pg, f"{tag} step 3")
    check(missed_rank(pg, "listB3")[0] == f"#{M['rank_B']}", f"{tag}: before toggle the role is #{M['rank_B']}")
    pg.click("#profileOnly"); pg.wait_for_timeout(800)
    rk = missed_rank(pg, "listB3")
    check(rk[0] == f"#{M['rank_profile']}" and rk[1] == str(M["rank_profile"] - 1), f"{tag}: profile-only re-sort moves the role back to #{M['rank_profile']}")
    shoot(pg, f"pitch_step_3_profile_only{'' if full else '_' + tag}.png")
    pg.click("#profileOnly"); pg.wait_for_timeout(700)
    pg.focus("body"); pg.keyboard.press("ArrowRight"); pg.wait_for_timeout(900)
    check("The audit." in pg.inner_text("#headline"), f"{tag}: step 4 headline")
    shoot(pg, f"pitch_step_4{'' if full else '_' + tag}.png"); no_hscroll(pg, f"{tag} step 4")
    if full:
        # every beta via the keyboard on the slider
        pg.focus("#betaP"); pg.keyboard.press("Home"); pg.wait_for_timeout(600)
        for i, b in enumerate(BETAS):
            if i: pg.keyboard.press("ArrowRight"); pg.wait_for_timeout(600)
            for key in ["TEG_pp", "blindspot_rate_pct", "mobility_drop_pp", "compat_cost_pct"]:
                sel = f'#checksP [data-check="{key}"]'
                val = pg.inner_text(f"{sel} [data-val]"); bd = pg.inner_text(f"{sel} [data-badge]").strip()
                check(val == EXP[b][key], f"beta {b:.2f} {key}: shows {val}, outputs give {EXP[b][key]}")
                check(bd == expected_badge(b, key), f"beta {b:.2f} {key}: badge {bd}")
            check(pg.inner_text("#keyP [data-key]") == EXP[b]["TEG_pp"], f"beta {b:.2f}: key number {pg.inner_text('#keyP [data-key]')}")
        shoot(pg, "pitch_step_4_beta0.60.png")
        pg.keyboard.press("Home"); pg.wait_for_timeout(600); shoot(pg, "pitch_step_4_beta0.00.png")
        # R resets to step 1 (focus out of the slider first)
        pg.focus("#next"); pg.evaluate("document.activeElement.blur()")
        pg.keyboard.press("r"); pg.wait_for_timeout(400)
        check("Same person, two feeds." in pg.inner_text("#headline"), "R resets to step 1")
        check(pg.input_value("#betaP") == "3", "R resets beta to 0.45")
        for _ in range(3): pg.keyboard.press("ArrowRight"); pg.wait_for_timeout(250)
        check("The audit." in pg.inner_text("#headline"), "right arrow x3 reaches step 4")
        pg.keyboard.press("ArrowLeft"); pg.wait_for_timeout(200)
        check("The receipt." in pg.inner_text("#headline"), "left arrow goes back")
    # explore
    pg.keyboard.press("p"); pg.wait_for_timeout(500)
    check(pg.is_visible("#explore") and not pg.is_visible("#pitch"), f"{tag}: P switches to Explore")
    if full:
        sel = '#checksE [data-check="TEG_pp"]'
        check(pg.inner_text(f"{sel} [data-badge]").strip() == "Fail", "explore: TEG fails at default pass line")
        pg.fill(f'{sel} input[data-thr]', "6"); pg.wait_for_timeout(200)
        check(pg.inner_text(f"{sel} [data-badge]").strip() == "Pass", "explore: raising the TEG pass line to 6 flips the badge to Pass")
        pg.fill(f'{sel} input[data-thr]', "2.62"); pg.wait_for_timeout(200)
        check(pg.inner_text(f"{sel} [data-badge]").strip() == "Fail", "explore: back to 2.62 flips it to Fail")
        rows = pg.eval_on_selector_all("#fxTable tbody tr", "rs => rs.map(r => r.innerText.replace(/\\s+/g, ' '))")
        for row, want in zip(rows, [["History cap", "75.4%", "1.82%", "71.3%"], ["Profile floor", "34.3%", "1.21%", "78.7%"],
                                     ["Exploration slots", "66.8%", "1.92%", "45.7%"]]):
            check(all(x in row for x in want) and row.strip().endswith("Fail"), f"explore fix row: {want[0]} {want[1:]} Fail")
    pg.screenshot(path=str(OUT / f"explore_{tag}.png"), full_page=True); no_hscroll(pg, f"{tag} explore")
    pg.evaluate("document.activeElement && document.activeElement.blur()")
    pg.keyboard.press("p"); pg.wait_for_timeout(300)
    check(pg.is_visible("#pitch"), f"{tag}: P switches back to Pitch")
    check(not reqs, f"{tag}: zero network requests {reqs}")
    check(not msgs, f"{tag}: zero console errors or warnings {msgs}")
    ctx.close()


def run_reduced(br):
    ctx, pg, reqs, msgs = open_page(br, 1920, 1080, reduced=True)
    pg.keyboard.press("ArrowRight"); pg.wait_for_timeout(150)
    check(missed_rank(pg, "listB2")[0] == f"#{M['rank_B']}", "reduced motion: step 2 shows the end state at once")
    pg.keyboard.press("ArrowRight"); pg.click("#profileOnly"); pg.wait_for_timeout(100)
    check(missed_rank(pg, "listB3")[0] == f"#{M['rank_profile']}", "reduced motion: re-sort works")
    pg.focus("body"); pg.keyboard.press("ArrowRight"); pg.wait_for_timeout(100)
    check(pg.inner_text("#keyP [data-key]") == EXP[0.45]["TEG_pp"], "reduced motion: key number shows final value at once")
    dur = pg.eval_on_selector('#listB3 .row', "e => getComputedStyle(e).transitionDuration")
    check(all(float(x.rstrip('s')) < 0.01 for x in dur.split(",")), f"reduced motion: transitions off ({dur})")
    check(not reqs and not msgs, "reduced motion: no requests, no console errors")
    ctx.close()


with sync_playwright() as p:
    br = p.chromium.launch(channel="msedge")
    run_view(br, 1920, 1080, "1920", True)
    run_view(br, 1440, 900, "1440", False)
    run_view(br, 1280, 720, "1280", False)
    run_view(br, 390, 844, "phone", False)
    run_reduced(br)
    br.close()

size = SITE.stat().st_size
check(size < 2 * 1024 * 1024, f"file size {size / 1024:.1f} KB < 2 MB")
print("\n".join(notes + fails))
print(f"\n{len(notes)} passed, {len(fails)} failed")
sys.exit(1 if fails else 0)
