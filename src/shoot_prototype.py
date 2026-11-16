"""Test the prototype in a headless browser and capture figures/receipt.png and figures/scorecard.png."""
import sys
from playwright.sync_api import sync_playwright
from core import ROOT

URL = (ROOT / "prototype" / "index.html").resolve().as_uri()


def launch(p):
    for kw in ({"channel": "msedge"}, {"channel": "chrome"}, {}):
        try:
            return p.chromium.launch(**kw)
        except Exception:
            continue
    sys.exit("No Chromium-based browser available for Playwright")


with sync_playwright() as p:
    br = launch(p)
    pg = br.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=2)
    errors, requests = [], []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    pg.on("request", lambda r: requests.append(r.url) if not r.url.startswith(("file:", "data:")) else None)
    pg.goto(URL)
    # interaction tests
    assert "ranked lower" in pg.inner_text("#msg")
    pg.click("#showbtn"); assert pg.is_visible("#missed .job")
    pg.click("#bProf"); prof = pg.inner_text("#feed"); assert "Hidden by history" in prof
    pg.click("#bPers"); pers = pg.inner_text("#feed"); assert "Added by history" in pers
    for v, want in [("0", "All 4 audit checks pass"), ("3", "audit checks fail")]:
        pg.eval_on_selector("#beta", f"(e)=>{{e.value='{v}';e.dispatchEvent(new Event('input'))}}")
        assert want in pg.inner_text("#verdict"), pg.inner_text("#verdict")
    pg.fill("#t_TEG_pp", "6"); pg.wait_for_timeout(50)
    teg_badge = pg.inner_text("#exp .tile:first-child .badge"); pg.fill("#t_TEG_pp", "2.62")
    assert "PASS" in teg_badge
    # final state for screenshots: beta = 0.45, receipt expanded, profile-only toggle showing the hidden role
    pg.eval_on_selector("#beta", "(e)=>{e.value='3';e.dispatchEvent(new Event('input'))}")
    pg.click("#bProf")
    pg.locator("#receipt").screenshot(path=str(ROOT / "figures" / "receipt.png"))
    pg.locator("#scorecard").screenshot(path=str(ROOT / "figures" / "scorecard.png"))
    pg.screenshot(path=str(ROOT / "figures" / "prototype_full.png"), full_page=True)
    # PDF crops: receipt down to the row hidden by history; scorecard laid out wide
    pg.set_viewport_size({"width": 1400, "height": 1000})
    pg.evaluate("""()=>{document.querySelector('header.top').style.display='none';
                     document.querySelector('footer').style.display='none';
                     document.querySelector('main').style.gridTemplateColumns='minmax(0,1fr)';}""")
    pg.evaluate("()=>{document.getElementById('scorecard').style.display='none';document.getElementById('receipt').style.maxWidth='780px'}")
    pg.evaluate("()=>window.scrollTo(0,0)")
    box = pg.evaluate("()=>{const r=document.getElementById('receipt').getBoundingClientRect();return {x:r.left+scrollX,y:r.top+scrollY,w:r.width}}")
    hid = pg.evaluate("()=>{const r=document.querySelector('#feed li.hl').getBoundingClientRect();return r.bottom+scrollY}")
    pg.screenshot(path=str(ROOT / "figures" / "receipt_pdf.png"), full_page=True,
                  clip={"x": box["x"], "y": box["y"], "width": box["w"], "height": hid + 6 - box["y"]})
    pg.evaluate("""()=>{const sc=document.getElementById('scorecard');sc.style.display='';sc.style.maxWidth='1000px';
        document.getElementById('receipt').style.display='none';
        document.querySelector('.fxwrap').style.display='none';document.getElementById('thrcap').style.display='none';
        [...sc.querySelectorAll('h3')].pop().style.display='none';}""")
    pg.locator("#scorecard").screenshot(path=str(ROOT / "figures" / "scorecard_pdf.png"))
    pg.evaluate("""()=>{const r=document.getElementById('receipt');r.style.display='';r.style.maxWidth='';
        const sc=document.getElementById('scorecard');sc.style.maxWidth='';document.querySelector('.fxwrap').style.display='';document.getElementById('thrcap').style.display='';
        [...sc.querySelectorAll('h3')].pop().style.display='';}""")
    # phone width check: no horizontal scroll
    pg.set_viewport_size({"width": 390, "height": 900})
    sw = pg.evaluate("document.documentElement.scrollWidth")
    print("errors:", errors, "| external requests:", requests, "| scrollWidth@390:", sw)
    assert not errors and not requests and sw <= 390
    br.close()
print("prototype OK")
