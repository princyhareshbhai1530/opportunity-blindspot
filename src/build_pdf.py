"""Step 7: fill the PDF template from numbers_spec, render US Letter landscape PDF, check layout, export page PNGs."""
import html as H
import json
import re
import sys
import fitz  # PyMuPDF
from playwright.sync_api import sync_playwright
from core import ROOT, World
import numbers_spec as N

PDF_DIR = ROOT / "pdf"
SRC_HTML = PDF_DIR / "source.html"
PDF = PDF_DIR / "Opportunity_Blindspot_Phase2.pdf"


def data_counts():
    w = World()
    (ROOT / "outputs" / "data_counts.json").write_text(json.dumps(
        {"candidates": len(w.cand), "jobs": len(w.jobs), "history": len(w.hist)}))


def derived():
    m = json.loads((ROOT / "outputs" / "mitigation_summary.json").read_text())
    fx = [r for r in m["test_table"] if r["role"] == "mitigation"]
    p1 = json.loads((ROOT / "outputs" / "phase1_published.json").read_text())
    rb = json.loads((ROOT / "outputs" / "phase1_reproduction.json").read_text())["beta_0.45"]["gap_pp"]
    inside = p1["gap_ci_low"] <= rb <= p1["gap_ci_high"]
    # The PDF says the rebuild lands inside the Phase 1 95% CI: stop the build if that stops being true.
    assert inside, f"Phase 1 rebuild {rb} is outside the published CI; reword pages 1 and 3"
    rs = json.loads((ROOT / "outputs" / "robust_salary.json").read_text())
    # The PDF says the gap holds without imputed salaries: both CIs must exclude zero.
    holds = all(rs[c]["ci_low"] > 0 for c in ("posted_salary_only", "exclude_imputed_from_hv"))
    assert holds, "imputed-salary robustness no longer holds; reword the page 3 robustness line"
    (ROOT / "outputs" / "derived.json").write_text(json.dumps(
        {"n_fix": len(fx), "n_fix_pass": sum(1 for r in fx if r["pass"] is True),
         "p1_rebuild_inside_p1_ci": inside, "gap_holds_without_imputed_salaries": holds}))


def fill():
    tpl = (ROOT / "src" / "pdf_template.html").read_text(encoding="utf-8")
    keys = set(re.findall(r"\{\{(\w+)\}\}", tpl))
    missing = keys - set(N.SPEC)
    if missing:
        sys.exit(f"template keys not in spec: {missing}")
    html = re.sub(r"\{\{(\w+)\}\}", lambda m: f'<span class="v" data-k="{m.group(1)}">{H.escape(N.value(m.group(1)))}</span>', tpl)
    SRC_HTML.write_text(html, encoding="utf-8")
    return keys


LAYOUT_JS = """() => {
  const out = [];
  document.querySelectorAll('.page').forEach((pg, i) => {
    const pr = pg.getBoundingClientRect();
    const foot = pg.querySelector('.foot').getBoundingClientRect();
    pg.querySelectorAll('*').forEach(el => {
      if (el.closest('.foot')) return;
      const r = el.getBoundingClientRect();
      if (r.width === 0 && r.height === 0) return;
      if (r.right > pr.right - 40 + 0.5 || r.bottom > foot.top - 4 + 0.5)
        out.push(`page ${i+1}: <${el.tagName.toLowerCase()} class="${el.className}"> bottom ${Math.round(r.bottom-pr.top)} right ${Math.round(r.right-pr.left)} (foot top ${Math.round(foot.top-pr.top)})`);
      if (el.scrollHeight > el.clientHeight + 1 && getComputedStyle(el).overflow === 'hidden' && !el.classList.contains('page') && !el.classList.contains('shot'))
        out.push(`page ${i+1}: clipped content in <${el.tagName.toLowerCase()} class="${el.className}">`);
    });
    pg.querySelectorAll('img').forEach(im => { if (!im.complete || im.naturalWidth === 0) out.push(`page ${i+1}: image not loaded ${im.src}`); });
  });
  return out;
}"""


def render():
    with sync_playwright() as p:
        br = p.chromium.launch(channel="msedge")
        pg = br.new_page(viewport={"width": 1056, "height": 816})
        pg.goto(SRC_HTML.resolve().as_uri())
        pg.wait_for_load_state("networkidle")
        problems = pg.evaluate(LAYOUT_JS)
        pg.pdf(path=str(PDF), width="11in", height="8.5in", print_background=True,
               margin={"top": "0", "right": "0", "bottom": "0", "left": "0"}, prefer_css_page_size=True)
        br.close()
    return problems


def pngs():
    doc = fitz.open(PDF)
    out = []
    for i, page in enumerate(doc):
        path = PDF_DIR / f"page_{i + 1}.png"
        page.get_pixmap(dpi=110).save(path)
        out.append(path)
    return len(doc), out


if __name__ == "__main__":
    data_counts()
    derived()
    keys = fill()
    probs = render()
    n, files = pngs()
    print(f"keys used: {len(keys)} | pages: {n} | layout problems: {len(probs)}")
    for x in probs[:40]:
        print("  ", x)
