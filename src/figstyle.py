"""Shared chart style matching the Phase 1 deck."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.text

NAVY = "#10283F"; INK2 = "#5B6B7C"; GRID = "#E6EDF4"
BLUE = "#1A6FE0"; CORAL = "#F25C6A"; TEAL = "#2EC4D0"; GREEN = "#1A9E6E"; AMBER = "#FFB000"; SLATE = "#5E7185"

plt.rcParams.update({
    "font.family": ["Arial", "DejaVu Sans"], "font.size": 11,
    "axes.edgecolor": "#C9D5E1", "axes.labelcolor": INK2, "axes.titlecolor": NAVY,
    "axes.titleweight": "bold", "axes.titlesize": 12, "axes.titlelocation": "left",
    "xtick.color": INK2, "ytick.color": INK2, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.8, "axes.spines.top": False, "axes.spines.right": False,
    "axes.axisbelow": True, "figure.dpi": 100, "savefig.dpi": 220,
    "legend.frameon": False, "legend.fontsize": 10,
})


def finish(fig, title, source, path):
    fig.suptitle(title, x=0.012, y=0.97, ha="left", fontsize=14, fontweight="bold", color=NAVY)
    fig.text(0.012, 0.005, source, ha="left", va="bottom", fontsize=8.5, color=INK2)
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def save_measured(fig, path):
    """Save a chart and record the smallest font size actually drawn (pt at native size).

    verify.py combines this with the image's displayed width in the PDF to check printed text >= 9 pt.
    """
    import json
    from pathlib import Path
    fig.canvas.draw()
    sizes = [t.get_fontsize() for t in fig.findobj(matplotlib.text.Text)
             if t.get_visible() and t.get_text().strip() and t.get_window_extent().width > 0]
    path = Path(path)
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    rec = path.parent / "chart_fonts.json"
    d = json.loads(rec.read_text()) if rec.exists() else {}
    d[path.name] = {"min_font_pt": min(sizes), "dpi": plt.rcParams["savefig.dpi"]}
    rec.write_text(json.dumps(d, indent=2))
