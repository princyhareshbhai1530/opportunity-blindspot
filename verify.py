"""Step 8: verify the submission. Exit code 1 if any hard check fails.

1. Every number in pdf/source.html is either a spec value (re-read from outputs/*.csv|json and compared)
   or a structural token (page / step / citation numbers, policy dates) explicitly marked in the template.
2. Every numeric token in the rendered PDF text is accounted for by (1).
3. PDF: <= 5 pages, US Letter landscape, English, no TODO, no em/en dashes, layout overflow check.
4. Prototype embeds exactly outputs/prototype_data.json and makes no external requests (checked by shoot_prototype.py).
5. criteria.md unchanged since lock; rule wording checks.
"""
import hashlib, json, re, sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
import numbers_spec as N  # noqa: E402

fails, notes = [], []
NUM = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?")


class Walk(HTMLParser):
    """Collect text, separating spec values (span.v), structural spans (span.s) and free text."""
    def __init__(self):
        super().__init__(); self.stack = []; self.vals = []; self.free = []; self.skip = 0; self.nv = 0
    def handle_starttag(self, tag, attrs):
        a = dict(attrs); kind = None
        if tag in ("style", "script", "title"): kind = "skip"
        elif tag == "span" and a.get("class") == "v":
            self.nv += 1; kind = ("v", a.get("data-k"), self.nv); self.vals.append([a.get("data-k"), ""])
        elif tag == "span" and a.get("class") == "s": kind = "s"
        self.stack.append((tag, kind))
        if kind == "v": pass
    def handle_endtag(self, tag):
        while self.stack:
            t, _ = self.stack.pop()
            if t == tag: break
    def handle_data(self, d):
        kinds = [k for _, k in self.stack if k]
        if "skip" in kinds: return
        v = next((k for k in reversed(kinds) if isinstance(k, tuple)), None)
        if v: self.vals[v[2] - 1][1] += d; return
        if "s" in kinds: return
        self.free.append(d)


# Literal labels that contain digits but are not data (each with its reason).
LITERALS = {
    "v1.1": "dataset version (JTH v1.1)", "BY-NC 4.0": "licence name", "95% CI": "confidence level (criteria.md)",
    "50/50": "tune/test split (criteria.md)", "Hit@10": "metric name", "Top-10": "metric name",
    "Phase 1": "challenge phase name", "Phase 2": "challenge phase name", "H1": "hypothesis name",
    "?p=45382": "source URL", "/394101": "source URL", "January 1, 2026": "source article title",
}


def strip_literals(t):
    for lit in LITERALS:
        t = t.replace(lit, " ")
    return t


# ---------- 1. HTML source numbers ----------
src = (ROOT / "pdf" / "source.html").read_text(encoding="utf-8")
w = Walk(); w.feed(src)
for k, shown in w.vals:
    try:
        expect = N.value(k)
    except Exception as e:
        fails.append(f"spec key {k} cannot be resolved: {e}"); continue
    if shown != expect:
        fails.append(f"MISMATCH {k}: PDF shows '{shown}', outputs give '{expect}'")
free = strip_literals(re.sub(r"\[\[[^\]]*\]\]", "", " ".join(w.free)))
stray = [m for m in NUM.findall(free)]
if stray:
    fails.append(f"numbers in the PDF text not traced to outputs or marked structural: {sorted(set(stray))}")
consts = sorted({k for k, _ in w.vals if N.SPEC[k][0] == "const"})
data_keys = sorted({k for k, _ in w.vals if N.SPEC[k][0] != "const"})
notes.append("literal labels excluded from the number scan: " + "; ".join(f"'{k}' ({v})" for k, v in LITERALS.items()))
notes.append(f"{len(w.vals)} number instances checked: {len(data_keys)} data keys from outputs, {len(consts)} design constants ({', '.join(consts)})")

# ---------- 2. rendered PDF ----------
import fitz  # noqa: E402
pdf = ROOT / "pdf" / "Opportunity_Blindspot_Phase2.pdf"
doc = fitz.open(pdf)
if doc.page_count > 5: fails.append(f"PDF has {doc.page_count} pages (> 5)")
for i, p in enumerate(doc):
    if (round(p.rect.width), round(p.rect.height)) != (792, 612):
        fails.append(f"page {i+1} size {p.rect.width}x{p.rect.height}, expected 792x612 (Letter landscape)")
text = "\n".join(p.get_text() for p in doc)
allowed = {t for _, s in w.vals for t in NUM.findall(s)}
struct_txt = re.findall(r'<span class="s">([^<]*)</span>', src)
allowed |= {t for s in struct_txt for t in NUM.findall(s)}
pdf_nums = {t.rstrip(",.") for t in NUM.findall(strip_literals(" ".join(text.split())))}
unknown = sorted(n for n in pdf_nums if n not in allowed)
if unknown: fails.append(f"numbers in rendered PDF text not accounted for: {unknown}")
for bad, why in [("[[TODO", "leftover TODO"), ("—", "em dash"), ("–", "en dash")]:
    if bad in text or bad in src: fails.append(f"{why} found")
placeholders = sorted(set(re.findall(r"\[\[[^\]]+\]\]", text)))
words = re.findall(r"[A-Za-z]+", text.lower())
eng = sum(wd in {"the", "and", "of", "to", "a", "in", "is", "on", "for", "with"} for wd in words) / max(len(words), 1)
if eng < 0.05: fails.append(f"text does not look English (stopword ratio {eng:.3f})")
notes.append(f"PDF: {doc.page_count} pages, Letter landscape, English stopword ratio {eng:.2f}, {len(pdf_nums)} distinct numbers all traced")

# ---------- 3. layout ----------
from build_pdf import LAYOUT_JS, SRC_HTML  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402
with sync_playwright() as p:
    br = p.chromium.launch(channel="msedge"); pg = br.new_page(viewport={"width": 1056, "height": 816})
    pg.goto(SRC_HTML.resolve().as_uri()); pg.wait_for_load_state("networkidle")
    probs = pg.evaluate(LAYOUT_JS)
    imgs = pg.evaluate("() => [...document.querySelectorAll('img')].map(i => [i.getAttribute('src'), i.clientWidth, i.naturalWidth])")
    br.close()
if probs: fails += [f"layout: {x}" for x in probs]
else: notes.append("layout: no element overflows its page or footer, no clipped text, all images loaded")
# chart text size at print: page is 1056 CSS px = 11 in, so displayed inches = clientWidth / 96
fonts = json.loads((ROOT / "figures" / "chart_fonts.json").read_text())
for src_, cw, nw in imgs:
    name = src_.rsplit("/", 1)[-1]
    if name not in fonts:
        continue  # prototype screenshots, not charts
    pt = fonts[name]["min_font_pt"] * (cw / 96) / (nw / fonts[name]["dpi"])
    if pt < 9: fails.append(f"chart {name}: smallest text prints at {pt:.1f} pt (< 9 pt)")
    else: notes.append(f"chart {name}: smallest text prints at {pt:.1f} pt")
for s, _, _ in imgs:
    n = s.rsplit("/", 1)[-1]
    if n not in fonts and n not in ("receipt_pdf.png", "scorecard_pdf.png"):
        fails.append(f"image {n} has no measured font record (is it a chart?)")

# ---------- 4. prototype ----------
html = (ROOT / "prototype" / "index.html").read_text(encoding="utf-8")
m = re.search(r"const DATA = (\{.*?\});\n", html, re.S)
proto = json.loads(m.group(1)) if m else None
if proto != json.loads((ROOT / "outputs" / "prototype_data.json").read_text()):
    fails.append("prototype embedded data differs from outputs/prototype_data.json")
if re.search(r"(src|href)=[\"']https?://|fetch\(|XMLHttpRequest|@import", html):
    fails.append("prototype references an external resource")
notes.append("prototype: embedded JSON equals outputs/prototype_data.json; no external resources")

# ---------- 5. pre-registration + wording rules ----------
lock = (ROOT / "criteria.lock").read_text()
h = hashlib.sha256((ROOT / "criteria.md").read_bytes()).hexdigest()
if h not in lock: fails.append("criteria.md changed after lock")
else: notes.append(f"criteria.md sha256 {h[:16]}... matches criteria.lock")
low = text.lower()
for pat, why in [(r"discriminat", "demographic-bias wording"), (r"mentor", "mentor claim"),
                 (r"(?<!test the )newcomer", "newcomer finding (allowed only as future work: 'test the newcomer scenario')"), (r"co-designed with (job seekers|users) (showed|found|told)", "co-design claim"),
                 (r"pilot (showed|found|results)", "pilot claim")]:
    if re.search(pat, low): fails.append(f"rule wording: {why} ({pat})")
if "motivating scenario, not a finding" not in low: fails.append("Canadian-experience scenario not labelled as a scenario")
if "not an audit of a real platform" not in low: fails.append("simulation disclaimer missing")

print("\n".join("OK   " + n for n in notes))
print("PLACEHOLDERS to fill:", placeholders)
if fails:
    print("\n".join("FAIL " + f for f in fails)); sys.exit(1)
print("ALL CHECKS PASSED")
