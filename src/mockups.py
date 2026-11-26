"""Phase 5 design mockups, v2 (premium layout): static 1280x720 canvas, saved at 2x.

Uses the real numbers in data/processed/powerbi/ (and the boundary file in data/raw/geoboundaries/).
Outputs figures/mockups_v2/page0.png ... page4.png (2560x1440 px). The v1 mockups
(figures/mockups/page1-4.png) were drawn by the previous version of this file (see git history).

Design v2: left navy sidebar with logo and page buttons, Overview page, KPI tiles with accent bar,
icon and change pill, cards with radius 10 / soft shadow / 20px padding, two-line footer.

Run from repo root:  python src/mockups.py
"""

from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.collections import PolyCollection  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, Normalize  # noqa: E402
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from states import canonical_state  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PBI = ROOT / "data" / "processed" / "powerbi"
GJ = ROOT / "data" / "raw" / "geoboundaries" / "geoBoundaries-NGA-ADM1.geojson"
OUT = ROOT / "figures" / "mockups_v2"

# ---------------- design system ----------------
W, H = 1280, 720
BG, CARD, BORDER = "#F6F7F9", "#FFFFFF", "#E5E7EB"
NAVY, SUB, FOOT, LABEL = "#0F1B2D", "#4B5563", "#6B7280", "#64748B"
SOLAR, GEN, GRID, ALERT, GRIDLINE = "#F59E0B", "#475569", "#0D9488", "#DC2626", "#E5E7EB"
SB_W, SB_ACTIVE, SB_TEXT, SB_MUTED = 210, "#1E293B", "#CBD5E1", "#94A3B8"
PILL = {"red": ("#FEE2E2", ALERT), "teal": ("#CCFBF1", "#0F766E")}
ICON = "#94A3B8"
SEQ = LinearSegmentedColormap.from_list("amber_seq", ["#FEF3C7", "#B45309"])
M, GAP, R, P = 24, 16, 10, 20           # margin, gap between cards, card radius, card padding
X0 = SB_W + M                           # content left edge
CW = W - M - X0                         # content width (1022)
BOT = H - 44                            # content bottom (footer below)
NAV = [("overview", "Overview"), ("fuel", "Fuel Shock"), ("bars", "Gen vs Grid vs Solar"),
       ("clock", "Payback"), ("pin", "Where Next")]
SOURCES = ("Estimates with low–high ranges. Sources: NBS, NERC, CBN, Global Solar Atlas/Solargis (CC BY 4.0), "
           "geoBoundaries. Method and limits: docs/phase4_audit.md")
COPYRIGHT = ("© 2026 Malik Badmus · data CC BY 4.0 · "
             "github.com/malikbadmus79-max/nigeria-hidden-power-plant")

for f in ["segoeui.ttf", "seguisb.ttf"]:
    font_manager.fontManager.addfont(f"C:/Windows/Fonts/{f}")
REG, SEMI = "Segoe UI", "Segoe UI Semibold"
plt.rcParams.update({"font.family": REG, "font.size": 10, "axes.edgecolor": GRIDLINE, "text.color": NAVY,
                     "axes.labelcolor": NAVY, "xtick.color": SUB, "ytick.color": SUB, "svg.fonttype": "none"})
DPI = 96   # Power BI sizes are pt on a 96-dpi canvas; 1 data unit = 1 px


def naira(v: float, dec: int = 0) -> str:
    if v >= 1e6:
        return f"₦{v / 1e6:.{max(dec, 1)}f}m"
    return f"₦{v:,.{dec}f}"


def spaced(s: str) -> str:
    """Uppercase, letter-spaced label (hair spaces between letters)."""
    return "\u200a".join(s.upper())


# ---------------- data ----------------
gen = pd.read_csv(PBI / "fact_generator_cost.csv", dtype={"month": str})
sol = pd.read_csv(PBI / "fact_solar_cost.csv", dtype={"month": str})
tar = pd.read_csv(PBI / "fact_grid_tariff.csv", dtype={"month": str})
pay = pd.read_csv(PBI / "fact_payback.csv", dtype={"month": str})
pri = pd.read_csv(PBI / "fact_priority_index.csv")
LATEST = gen.month.max()
mlabel = lambda m: pd.Period(m, "M").strftime("%b %Y")  # noqa: E731
LATEST_LABEL = mlabel(LATEST)

NAT_GEN = gen.groupby(["user", "case", "month"]).running_ngn_per_month.median().unstack("case")
HH, BZ = NAT_GEN.loc["household"], NAT_GEN.loc["business"]
HH_NOW, BZ_NOW = HH.loc[LATEST, "central"], BZ.loc[LATEST, "central"]
HH_CHG = (HH_NOW / HH.loc["2023-01", "central"] - 1) * 100
BZ_CHG = (BZ_NOW / BZ.loc["2023-01", "central"] - 1) * 100
GL = gen[(gen.month == LATEST) & (gen.case == "central")]
SL = sol[(sol.month == LATEST) & (sol.case == "central")]
KWH_G = {u: GL[GL.user == u].set_index("state").running_ngn_per_kwh for u in ("household", "business")}
KWH_S = {u: SL[SL.user == u].set_index("state").lcoe_ngn_per_kwh for u in ("household", "business")}
GAP_HH = 1 - KWH_S["household"] / KWH_G["household"]
PC = pay[pay.case == "central"].groupby(["user", "month"]).payback_months.median().unstack("user")
PB_NOW, PB_START = PC["household"].loc[LATEST], PC["household"].loc["2023-06"]
PB24 = PC["household"].loc["2024-01":"2024-12"]
PB_PEAK_M, PB_PEAK = PB24.idxmax(), PB24.max()
PB_STATE = pay[(pay.month == LATEST) & (pay.user == "household")].pivot_table(index="state", columns="case",
                                                                             values="payback_months")
BASE = pri[(pri.weighting == "equal") & (pri.gap_user == "household") &
           (pri.reliance_measure == "primary_source")].sort_values("rank")
N_VAR = pri.groupby(["weighting", "gap_user", "reliance_measure"]).ngroups
FREQ = pri[pri["rank"] <= 10].groupby("state").size()
ALL12 = set(FREQ[FREQ == N_VAR].index)
TOP = BASE.iloc[0]


# ---------------- page scaffolding ----------------
class Page:
    def __init__(self, n: int, title: str | None, takeaway: str | None):
        self.fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI, facecolor=BG)
        self.base = self.fig.add_axes([0, 0, 1, 1])
        self.base.set_xlim(0, W)
        self.base.set_ylim(H, 0)
        self.base.axis("off")
        self.renderer = self.fig.canvas.get_renderer()
        self.sidebar(n)
        if title:
            self.text(X0, 22, title, 20, NAVY, SEMI)
        if takeaway:
            if n == 3:
                assert len(self.wrap(takeaway, 11.5, CW)) == 1, "page 3 takeaway must fit on one line"
            for k, line in enumerate(self.wrap(takeaway, 11.5, CW)):
                self.text(X0, 54 + k * 16, line, 11.5, SUB)
        self.text(X0, H - 26, SOURCES, 8.5, FOOT, va="bottom")
        self.text(X0, H - 11, COPYRIGHT, 8.5, FOOT, va="bottom")

    # --- primitives
    def text(self, x, y, s, size, color=NAVY, font=REG, ha="left", va="top", **kw):
        return self.base.text(x, y, s, fontsize=size, color=color, fontfamily=font, ha=ha, va=va, **kw)

    def width(self, t) -> float:
        return t.get_window_extent(renderer=self.renderer).width

    def text_width(self, s, size, font=REG) -> float:
        t = self.base.text(0, 0, s, fontsize=size, fontfamily=font)
        w = self.width(t)
        t.remove()
        return w

    def wrap(self, s, size, maxw, font=REG) -> list[str]:
        lines, cur = [], ""
        for word in s.split():
            trial = f"{cur} {word}".strip()
            if cur and self.text_width(trial, size, font) > maxw:
                lines.append(cur)
                cur = word
            else:
                cur = trial
        return lines + [cur]

    def fit(self, t, maxw, what):
        w = self.width(t)
        if w > maxw + 0.5:
            raise ValueError(f"text too wide ({w:.0f} > {maxw:.0f} px): {what!r}")

    def rrect(self, x, y, w, h, fc, ec="none", r=R, lw=1.0, z=1, alpha=1.0):
        p = FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}", fc=fc, ec=ec, lw=lw,
                           zorder=z, alpha=alpha)
        self.base.add_patch(p)
        return p

    def axes(self, x, y, w, h):
        return self.fig.add_axes([x / W, 1 - (y + h) / H, w / W, h / H])

    # --- components
    def card(self, x, y, w, h, title=None, label=None, accent=None):
        for dy, a in ((3, 0.035), (1.5, 0.05)):                   # soft shadow
            self.rrect(x, y + dy, w, h, NAVY, alpha=a, z=0.5)
        card = self.rrect(x, y, w, h, CARD, BORDER, z=1)
        if accent:
            bar = Rectangle((x, y), w, 4, fc=accent, ec="none", zorder=1.5)
            self.base.add_patch(bar)
            bar.set_clip_path(card)
        ty = y + P
        if label:
            self.text(x + P, ty - 2, spaced(label), 8, LABEL, SEMI)
            ty += 16
        if title:
            t = self.text(x + P, ty, title, 11.5, NAVY, SEMI)
            self.fit(t, w - 2 * P, title)
        return ty + 24

    def pill(self, x, y, s, kind, size=8.5):
        """Rounded pill with its left edge at x, vertically centred on y."""
        bg, fg = PILL[kind]
        t = self.text(x + 7, y, s, size, fg, SEMI, va="center", zorder=3)
        w = self.width(t)
        self.rrect(x, y - 9, w + 14, 18, bg, r=9, z=2.5)
        return w + 14

    def kpi(self, x, y, w, h, title, value, sub, accent, icon_kind, pill=None, value_color=NAVY):
        self.card(x, y, w, h, accent=accent)
        t = self.text(x + P, y + P - 2, title, 10, SUB, SEMI)
        self.fit(t, w - 2 * P - 26, title)
        icon(self, icon_kind, x + w - P - 9, y + P + 6, 16, ICON)
        t = self.text(x + P, y + 40, value, 30, value_color, SEMI)
        self.fit(t, w - 2 * P, value)
        sx = x + P
        if pill:
            sx += self.pill(sx, y + h - 20, *pill) + 8
        t = self.text(sx, y + h - 20, sub, 9, SUB, va="center")
        self.fit(t, x + w - P - sx, sub)

    def sidebar(self, n):
        self.base.add_patch(Rectangle((0, 0), SB_W, H, fc=NAVY, ec="none", zorder=0.2))
        sun(self.base, 32, 38, 8)
        self.text(52, 27, "Hidden Power Plant", 11, "#FFFFFF", SEMI)
        self.text(52, 46, "Generator vs solar · Nigeria", 8, SB_MUTED)
        y = 96
        for i, (kind, label) in enumerate(NAV):
            active = i == n
            if active:
                self.base.add_patch(Rectangle((0, y), SB_W, 38, fc=SB_ACTIVE, ec="none", zorder=0.3))
                self.base.add_patch(Rectangle((0, y), 4, 38, fc=SOLAR, ec="none", zorder=0.4))
            col = "#FFFFFF" if active else SB_TEXT
            icon(self, kind, 34, y + 19, 15, col)
            self.text(56, y + 19, label, 10, col, SEMI if active else REG, va="center")
            y += 44
        self.base.plot([20, SB_W - 20], [H - 70, H - 70], color="#1E293B", lw=1)
        self.text(20, H - 56, f"Data to {LATEST_LABEL}", 8.5, SB_MUTED)
        self.text(20, H - 38, "By Malik Badmus", 8.5, SB_MUTED)

    def save(self, name):
        OUT.mkdir(parents=True, exist_ok=True)
        self.fig.savefig(OUT / name, dpi=DPI * 2, facecolor=BG)
        plt.close(self.fig)


# ---------------- icons (simple line drawings) ----------------
def sun(ax, cx, cy, r):
    for k in range(8):
        a = np.pi * k / 4
        ax.plot([cx + np.cos(a) * (r + 3), cx + np.cos(a) * (r + 7)],
                [cy + np.sin(a) * (r + 3), cy + np.sin(a) * (r + 7)], color=SOLAR, lw=1.8,
                solid_capstyle="round", zorder=1)
    ax.add_patch(Circle((cx, cy), r, fc=SOLAR, ec="none", zorder=1))


def icon(p: Page, kind, cx, cy, s, col):
    """Line icon of size s centred on (cx, cy) in page coordinates (y down)."""
    ax, h, lw = p.base, s / 2, 1.4
    kw = dict(color=col, lw=lw, solid_capstyle="round", zorder=3)
    if kind == "overview":            # 2x2 tiles
        q = s * 0.42
        for dx in (-h, h - q):
            for dy in (-h, h - q):
                ax.add_patch(FancyBboxPatch((cx + dx, cy + dy), q, q, boxstyle="round,pad=0,rounding_size=1.5",
                                            fc="none", ec=col, lw=lw, zorder=3))
    elif kind == "fuel":              # jerrycan: body + spout
        ax.add_patch(FancyBboxPatch((cx - h * 0.8, cy - h * 0.55), s * 0.75, s * 0.95,
                                    boxstyle="round,pad=0,rounding_size=2", fc="none", ec=col, lw=lw, zorder=3))
        ax.plot([cx + h * 0.7, cx + h, cx + h], [cy - h * 0.35, cy - h * 0.7, cy - h], **kw)
        ax.plot([cx - h * 0.45, cx + h * 0.35], [cy - h * 0.55, cy + h * 0.25], **kw)
    elif kind == "bars":              # bar chart
        for i, frac in enumerate((0.45, 0.8, 1.0)):
            x = cx - h + i * s * 0.36 + 1
            ax.plot([x, x], [cy + h, cy + h - s * frac], color=col, lw=lw * 2.2, solid_capstyle="butt", zorder=3)
    elif kind == "clock":
        ax.add_patch(Circle((cx, cy), h, fc="none", ec=col, lw=lw, zorder=3))
        ax.plot([cx, cx, cx + h * 0.5], [cy - h * 0.6, cy, cy], **kw)
    elif kind == "pin":               # map pin
        ax.add_patch(Circle((cx, cy - h * 0.3), h * 0.62, fc="none", ec=col, lw=lw, zorder=3))
        ax.plot([cx - h * 0.5, cx, cx + h * 0.5], [cy + h * 0.05, cy + h, cy + h * 0.05], **kw)
        ax.add_patch(Circle((cx, cy - h * 0.3), h * 0.18, fc=col, ec="none", zorder=3))
    elif kind == "sun":
        sun_icon_r = h * 0.45
        ax.add_patch(Circle((cx, cy), sun_icon_r, fc="none", ec=col, lw=lw, zorder=3))
        for k in range(8):
            a = np.pi * k / 4
            ax.plot([cx + np.cos(a) * h * 0.7, cx + np.cos(a) * h], [cy + np.sin(a) * h * 0.7, cy + np.sin(a) * h],
                    **kw)
    elif kind == "trend":             # rising line with arrow
        ax.plot([cx - h, cx - h * 0.2, cx + h * 0.2, cx + h], [cy + h * 0.6, cy - h * 0.1, cy + h * 0.2, cy - h * 0.7],
                **kw)
        ax.plot([cx + h * 0.4, cx + h, cx + h], [cy - h * 0.7, cy - h * 0.7, cy - h * 0.1], **kw)
    elif kind == "factory":           # small business
        ax.plot([cx - h, cx - h, cx - h * 0.2, cx - h * 0.2, cx + h * 0.4, cx + h * 0.4, cx + h, cx + h, cx - h],
                [cy + h, cy - h * 0.2, cy + h * 0.2, cy - h * 0.2, cy + h * 0.2, cy - h, cy - h, cy + h, cy + h],
                **kw)


# ---------------- charts ----------------
def clean(ax, grid_axis="y"):
    for s in ["top", "right", "left"]:
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRIDLINE)
    ax.tick_params(length=0, labelsize=9.5)
    ax.grid(axis=grid_axis, color=GRIDLINE, lw=0.8)
    ax.set_axisbelow(True)


def month_axis(ax, months, every=6):
    ticks = list(range(0, len(months), every))
    ax.set_xticks(ticks)
    ax.set_xticklabels([pd.Period(months[i], "M").strftime("%b %y") for i in ticks])
    ax.set_xlim(-0.5, len(months) - 0.5)


def load_shapes():
    gj = json.loads(GJ.read_text(encoding="utf-8"))
    shapes = {}
    for f in gj["features"]:
        st = canonical_state(f["properties"]["shapeName"].replace("Federal Capital Territory", "FCT"))
        g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        k = np.cos(np.radians(9))
        shapes[st] = [np.column_stack([np.array(p_[0])[:, 0] * k, np.array(p_[0])[:, 1]]) for p_ in polys]
    return shapes


SHAPES = load_shapes()


def draw_map(ax, values: pd.Series, fmt, label_states=()):
    norm = Normalize(values.min(), values.max())
    polys, cols = [], []
    for st, rings in SHAPES.items():
        for r in rings:
            polys.append(r)
            cols.append(SEQ(norm(values[st])))
    ax.add_collection(PolyCollection(polys, facecolors=cols, edgecolors="#FFFFFF", linewidths=0.6))
    ax.autoscale_view()
    ax.set_aspect("equal")
    ax.axis("off")
    for st in label_states:
        r = max(SHAPES[st], key=len)
        ax.text(r[:, 0].mean(), r[:, 1].mean(), f"{st}\n{fmt(values[st])}", fontsize=8, ha="center", va="center",
                color=NAVY, fontfamily=SEMI,
                bbox=dict(boxstyle="round,pad=0.25", fc="#FFFFFF", ec="none", alpha=0.9))
    return norm


def legend_bar(p: Page, x, y, w, norm, fmt, label):
    ax = p.axes(x, y, w, 8)
    ax.imshow(np.linspace(0, 1, 256)[None, :], aspect="auto", cmap=SEQ)
    ax.axis("off")
    p.text(x, y + 12, fmt(norm.vmin), 9, SUB)
    p.text(x + w, y + 12, fmt(norm.vmax), 9, SUB, ha="right")
    p.text(x + w / 2, y + 12, label, 9, SUB, ha="center")


def map_card(p: Page, x, y, w, h, values, fmt, legend_fmt, unit, title, label="Map"):
    top = p.card(x, y, w, h, title, label)
    ax = p.axes(x + P, top + 4, w - 2 * P, h - (top - y) - 104)
    norm = draw_map(ax, values, fmt, [values.idxmax(), values.idxmin()])
    legend_bar(p, x + P + 24, y + h - 78, w - 2 * P - 48, norm, legend_fmt, unit)
    pct = (values.max() / values.min() - 1) * 100
    note = f"States differ by only about {pct:.0f}%; the colour scale is stretched to show the differences"
    lines = textwrap.wrap(note, int((w - 2 * P) / 5.2))
    for k, line in enumerate(lines):
        p.text(x + P, y + h - P - (len(lines) - 1 - k) * 13, line, 9, FOOT, va="bottom")


def payback_map(p: Page, x, y, w, h, label="Map"):
    map_card(p, x, y, w, h, PB_STATE["central"], lambda v: f"{v:.1f} mo", lambda v: f"{v:.1f}", "months (central)",
             "Household payback by state", f"{label} · {LATEST_LABEL}")


def kpi_row(p: Page, y, specs, h=116):
    k = len(specs)
    w = (CW - (k - 1) * GAP) / k
    for i, s in enumerate(specs):
        p.kpi(X0 + i * (w + GAP), y, w, h, **s)


# ================= PAGE 0: OVERVIEW =================
def page0():
    p = Page(0, None, None)
    p.text(X0, 22, spaced(f"Key insight · {LATEST_LABEL}"), 9, SOLAR, SEMI)
    head = (f"Solar + battery now costs about {GAP_HH.median() * 100:.0f}% less per kWh than a small petrol generator "
            f"— at least {int(GAP_HH.min() * 100)}% less in every state — and pays back in about {PB_NOW:.0f} "
            "months.")
    for k, line in enumerate(p.wrap(head, 19, CW, SEMI)):
        p.text(X0, 40 + k * 28, line, 19, NAVY, SEMI)
    top = 112
    g, s = KWH_G["household"], KWH_S["household"]
    kpi_row(p, top, [
        dict(title="Generator, ₦ per month", value=naira(HH_NOW), sub="since Jan 2023", accent=GEN,
             icon_kind="fuel", pill=(f"+{HH_CHG:.0f}%", "red")),
        dict(title="Solar + battery, ₦ per kWh", value=naira(s.median()),
             sub=f"vs generator {naira(g.median())}", accent=SOLAR, icon_kind="sun",
             pill=(f"−{GAP_HH.median() * 100:.0f}%", "teal")),
        dict(title="Payback now", value=f"{PB_NOW:.1f} mo", sub=f"vs {mlabel(PB_PEAK_M)} peak",
             accent=SOLAR, icon_kind="clock", pill=(f"−{PB_PEAK - PB_NOW:.1f} mo", "teal")),
        dict(title="Top priority state", value=TOP.state, sub=f"index {TOP['index']:.2f}", accent=GRID,
             icon_kind="pin", pill=(f"Top 10 in all {N_VAR}", "teal")),
    ])
    y2 = top + 116 + GAP
    h2 = BOT - y2
    mw = 400
    payback_map(p, X0, y2, mw, h2, label="Payback map")

    fx = X0 + mw + GAP
    fw = CW - mw - GAP
    ty = p.card(fx, y2, fw, h2, "What the numbers say", "Key findings")
    findings = [
        f"Running a small household generator cost a median {naira(HH_NOW)} a month in {LATEST_LABEL}, "
        f"{HH_CHG:.0f}% more than in January 2023, after the June 2023 petrol subsidy removal.",
        f"Solar + battery costs {naira(s.min())}–{naira(s.max())} per kWh against {naira(g.min())}–{naira(g.max())} "
        f"for a small petrol generator — cheaper in all 37 states.",
        f"Payback fell from {PB_PEAK:.0f} months at the {mlabel(PB_PEAK_M)} peak to about {PB_NOW:.0f} months. "
        f"{BASE.state.iloc[0]}, {BASE.state.iloc[1]} and {BASE.state.iloc[2]} rank highest for market priority.",
    ]
    y = ty + 18
    blocks = [p.wrap(f_, 12, fw - 2 * P - 56) for f_ in findings]
    heights = [len(b) * 21 for b in blocks]
    gap = min(64.0, (y2 + h2 - 70 - y - sum(heights)) / (len(blocks) - 1))
    for i, lines in enumerate(blocks, 1):
        p.base.add_patch(Circle((fx + P + 12, y + 11), 12, fc=SOLAR, ec="none", zorder=3))
        p.text(fx + P + 12, y + 11, str(i), 11, "#FFFFFF", SEMI, ha="center", va="center", zorder=4)
        for k, line in enumerate(lines):
            p.text(fx + P + 40, y + k * 21, line, 12, NAVY)
        y += heights[i - 1] + gap
    p.base.plot([fx + P, fx + fw - P], [y2 + h2 - 52, y2 + h2 - 52], color=BORDER, lw=1)
    method = ("Method: a monthly cost model for each state (fuel prices, tariffs, solar resource and system costs); "
              "central estimates with low–high ranges.")
    lines = p.wrap(method, 9, fw - 2 * P)
    for k, line in enumerate(lines):
        p.text(fx + P, y2 + h2 - P - (len(lines) - 1 - k) * 13, line, 9, FOOT, va="bottom")
    p.save("page0.png")


# ================= PAGE 1: THE FUEL SHOCK =================
def page1():
    p = Page(1, "The Fuel Shock", f"Running a small household generator cost a median {naira(HH_NOW)} a month in "
             f"{LATEST_LABEL}, {HH_CHG:.0f}% more than in January 2023 (central estimate).")
    top = 98
    kpi_row(p, top, [
        dict(title="Household generator, ₦ per month", value=naira(HH_NOW),
             sub=f"National median · range {naira(HH.loc[LATEST, 'low'])}–{naira(HH.loc[LATEST, 'high'])}",
             accent=GEN, icon_kind="fuel", pill=(f"+{HH_CHG:.0f}%", "red")),
        dict(title="Small-business generator, ₦ per month", value=naira(BZ_NOW),
             sub=f"National median · range {naira(BZ.loc[LATEST, 'low'])}–{naira(BZ.loc[LATEST, 'high'])}",
             accent=GEN, icon_kind="factory", pill=(f"+{BZ_CHG:.0f}%", "red")),
        dict(title="Change since January 2023", value=f"+{HH_CHG:.0f}%", value_color=ALERT,
             sub=f"Household (petrol) · business (diesel) +{BZ_CHG:.0f}%", accent=ALERT, icon_kind="trend"),
    ])
    y2 = top + 116 + GAP
    h2 = BOT - y2
    mw = 380
    st = GL[GL.user == "household"].set_index("state").running_ngn_per_month
    map_card(p, X0, y2, mw, h2, st, naira, naira, "₦ per month", "Household generator cost by state",
             f"Map · {LATEST_LABEL}, central")

    lx, lw = X0 + mw + GAP, CW - mw - GAP
    ty = p.card(lx, y2, lw, h2, "National median household generator cost, ₦/month", "Trend · central")
    p.text(lx + P, ty - 4, f"Central estimate; shaded band = low–high case, clipped at the top (high case reaches "
                           f"{naira(HH['high'].max())})", 9, FOOT)
    ax = p.axes(lx + P + 62, ty + 22, lw - 2 * P - 130, h2 - (ty - y2) - 56)
    hh = HH
    months = list(hh.index)
    xs = np.arange(len(months))
    ax.fill_between(xs, hh["low"], hh["high"], color="#F1F5F9", lw=0)
    ax.plot(xs, hh["central"], color=GEN, lw=2.2)
    clean(ax)
    month_axis(ax, months)
    ax.yaxis.set_major_formatter(lambda v, _: naira(v))
    ycap = hh["central"].max() * 1.9
    ax.set_ylim(0, ycap)
    j = months.index("2023-06")
    ax.axvline(j, color=ALERT, lw=1.2, ls="--")
    ax.text(j + 0.6, ycap * 0.97, "Jun 2023: petrol subsidy removed", color=ALERT, fontsize=10, fontfamily=SEMI,
            va="top")
    ax.text(xs[-1], hh["central"].iloc[-1], f"  {naira(HH_NOW)}", color=GEN, fontsize=10, fontfamily=SEMI,
            va="center", ha="left", clip_on=False)
    ax.text(xs[0], hh["central"].iloc[0] - ycap * 0.025, naira(hh["central"].iloc[0]), color=GEN, fontsize=10,
            va="top", ha="left")
    ax.set_yticks([t for t in ax.get_yticks() if 0 < t <= ycap])
    p.save("page1.png")


# ================= PAGE 2: GENERATOR VS GRID VS SOLAR =================
def page2():
    hg, hs = KWH_G["household"], KWH_S["household"]
    p = Page(2, "Generator vs Grid vs Solar",
             f"In {LATEST_LABEL} a small petrol generator cost {naira(hg.min())}–{naira(hg.max())} per kWh; "
             f"solar + battery {naira(hs.min())}–{naira(hs.max())}; grid Band A ₦209.50 where supply exists.")
    tl = tar[tar.month == LATEST]
    placeholder = set(tl[tl.tariff_status != "nerc_order"].state)
    band_a = tl[tl.band == "A"].tariff_ngn_per_kwh.median()
    band_b = tl[tl.band == "B"].tariff_ngn_per_kwh.median()
    top = 98
    cw = (CW - GAP) / 2
    ch = BOT - top
    for k, user in enumerate(["household", "business"]):
        x = X0 + k * (cw + GAP)
        g, s = KWH_G[user], KWH_S[user]
        order = g.sort_values(ascending=False)
        rows = (list(order.index[:5]) + [None] + list(order.index[-5:]))[::-1]
        lab = "Household · 2.5 kVA petrol" if user == "household" else "Small business · 20 kVA diesel"
        ty = p.card(x, top, cw, ch, f"{lab} — ₦ per kWh", f"Cost per kWh · {LATEST_LABEL}, central")
        p.text(x + P, ty - 4, "5 states with the costliest and 5 with the cheapest generator power", 9.5, SUB)
        # legend, two rows
        ly = ty + 20
        items = [[("rect", GEN, "Generator"), ("rect", SOLAR, "Solar + battery")],
                 [("line", GRID, "Grid tariff: price reference only"), ("diamond", GRID, "state-set tariff")]]
        for r_, row in enumerate(items):
            lx0 = x + P
            for kind, col, txt in row:
                yy = ly + r_ * 18
                if kind == "rect":
                    p.base.add_patch(Rectangle((lx0, yy - 5), 10, 10, color=col))
                elif kind == "line":
                    p.base.plot([lx0 + 5, lx0 + 5], [yy - 7, yy + 7], color=GRID, lw=1.6)
                else:
                    p.base.plot(lx0 + 5, yy, marker="D", ms=5, mfc="none", mec=GRID, mew=1.2)
                t = p.text(lx0 + 16, yy, txt, 9.5, SUB, va="center")
                lx0 += 16 + p.width(t) + 18
        ax = p.axes(x + P + 84, ty + 66, cw - 2 * P - 130, ch - (ty - top) - 136)
        for i, stt in enumerate(rows):
            if stt is None:
                ax.text(0, i, "   · · ·", va="center", fontsize=11, color=FOOT)
                continue
            ax.barh(i + 0.19, g[stt], height=0.36, color=GEN)
            ax.barh(i - 0.19, s[stt], height=0.36, color=SOLAR)
            ax.text(g[stt], i + 0.19, f"  {g[stt]:,.0f}", va="center", fontsize=8.5, color=GEN)
            ax.text(max(s[stt], band_a) + g.max() * 0.02, i - 0.19, f"{s[stt]:,.0f}", va="center", fontsize=8.5,
                    color=NAVY)
            if stt in placeholder:
                ax.plot(-0.02, i, marker="D", ms=5, mfc="none", mec=GRID, mew=1.2,
                        transform=ax.get_yaxis_transform(), clip_on=False)
        ax.set_yticks([i for i, r_ in enumerate(rows) if r_])
        ax.set_yticklabels([r_ for r_ in rows if r_], fontsize=9.5)
        ax.tick_params(axis="y", pad=18)
        clean(ax, "x")
        ax.set_xlim(0, g.max() * 1.18)
        ax.xaxis.set_major_formatter(lambda v, _: f"₦{v:,.0f}")
        ax.xaxis.set_major_locator(plt.MaxNLocator(4))
        ax.axvline(band_a, color=GRID, lw=1.3, ls="-")
        ax.axvline(band_b, color=GRID, lw=1.3, ls="--")
        ax.text(band_a, len(rows) - 0.3, f" Band A ₦{band_a:,.2f}", color=GRID, fontsize=8.5, va="bottom")
        ax.text(band_b, len(rows) - 0.3, f"Band B ₦{band_b:,.0f} ", color=GRID, fontsize=8.5, va="bottom",
                ha="right")
        ax.set_ylim(-0.6, len(rows) + 0.4)
        p.text(x + P, top + ch - P, f"All 37 states: generator {naira(g.min())}–{naira(g.max())}/kWh · solar "
                                    f"{naira(s.min())}–{naira(s.max())}/kWh (central)", 9.5, SUB, va="bottom")
    p.save("page2.png")


# ================= PAGE 3: PAYBACK =================
def page3():
    p = Page(3, "Payback", f"Solar + battery now pays back in about {PB_NOW:.0f} months for a typical household, "
             f"down from {PB_PEAK:.0f} at the {mlabel(PB_PEAK_M)} peak (median, central).")
    top = 98
    r_ = PB_STATE
    kpi_row(p, top, [
        dict(title="Household payback now", value=f"{PB_NOW:.1f} months",
             sub=f"States {r_['central'].min():.1f}–{r_['central'].max():.1f} · range "
                 f"{r_['low'].min():.1f}–{r_['high'].max():.1f}", accent=SOLAR, icon_kind="clock",
             pill=(f"−{PB_PEAK - PB_NOW:.1f} mo vs peak", "teal")),
        dict(title="At the start, June 2023", value=f"{PB_START:.1f} months",
             sub=f"Median of states · business {PC['business'].loc['2023-06']:.1f} months", accent=SOLAR,
             icon_kind="sun"),
        dict(title=f"2024 peak ({mlabel(PB_PEAK_M)})", value=f"{PB_PEAK:.1f} months", value_color=ALERT,
             sub="naira fall raised solar costs", accent=ALERT, icon_kind="trend",
             pill=(f"+{PB_PEAK - PB_START:.1f} mo", "red")),
    ])
    y2 = top + 116 + GAP
    h2 = BOT - y2
    mw, lw = 300, 360
    aw = CW - mw - lw - 2 * GAP
    payback_map(p, X0, y2, mw, h2)

    lx = X0 + mw + GAP
    ty = p.card(lx, y2, lw, h2, "Payback over time, months", "Trend · median of states, central")
    ax = p.axes(lx + P + 26, ty + 8, lw - 2 * P - 100, h2 - (ty - y2) - 44)
    months = list(PC.index)
    xs = np.arange(len(months))
    ax.plot(xs, PC["household"], color=SOLAR, lw=2.2)
    ax.plot(xs, PC["business"], color=GEN, lw=1.6)
    clean(ax)
    month_axis(ax, months, every=12)
    ax.set_ylim(0, max(PC.max()) * 1.25)
    ax.set_yticks([5, 10, 15, 20, 25, 30])
    ax.set_ylabel("months", fontsize=9.5, color=SUB)
    pi = months.index(PB_PEAK_M)
    ax.plot(pi, PB_PEAK, "o", color=ALERT, ms=6, zorder=5)
    ax.annotate(f"{mlabel(PB_PEAK_M)}: naira devaluation\npeak {PB_PEAK:.1f} months", (pi, PB_PEAK),
                xytext=(pi + 3, PB_PEAK + 4.2), color=ALERT, fontsize=9, fontfamily=SEMI, va="center",
                arrowprops=dict(arrowstyle="-", color=ALERT, lw=0.9))
    ax.text(xs[-1], PC["household"].iloc[-1], f" Household {PC['household'].iloc[-1]:.1f}", color="#B45309",
            fontsize=9, fontfamily=SEMI, va="bottom", ha="left", clip_on=False)
    ax.text(xs[-1], PC["business"].iloc[-1], f" Business {PC['business'].iloc[-1]:.1f}", color=GEN,
            fontsize=9, fontfamily=SEMI, va="top", ha="left", clip_on=False)

    ax_x = lx + lw + GAP
    ty = p.card(ax_x, y2, aw, h2, "Upfront cost ÷ monthly spending", "Affordability · households")
    a = pay[(pay.month == LATEST) & (pay.user == "household")].pivot_table(index="state", columns="case",
                                                                         values="upfront_months_of_consumption")
    a = a.sort_values("central", ascending=False).head(12)[::-1]
    axb = p.axes(ax_x + P + 60, ty, aw - 2 * P - 70, h2 - (ty - y2) - 64)
    yy = np.arange(len(a))
    axb.barh(yy, a["central"], color=SOLAR, height=0.62)
    axb.errorbar(a["central"], yy, xerr=[a["central"] - a["low"], a["high"] - a["central"]], fmt="none",
                 ecolor=GEN, elinewidth=0.9, capsize=2)
    axb.set_yticks(yy)
    axb.set_yticklabels(a.index, fontsize=9.5)
    for i, v in enumerate(a["central"]):
        axb.text(0.15, i, f"{v:.1f}", va="center", fontsize=8.5, color=NAVY, fontfamily=SEMI)
    clean(axb, "x")
    med = pay[(pay.month == LATEST) & (pay.user == "household") & (pay.case == "central")]
    med = med.upfront_months_of_consumption.median()
    p.text(ax_x + P, y2 + h2 - P, f"12 least affordable · whiskers = low–high · median {med:.1f}", 9, SUB,
           va="bottom")
    p.save("page3.png")


# ================= PAGE 4: WHERE TO GO NEXT =================
def page4():
    top3 = BASE.state.head(3).tolist()
    p = Page(4, "Where to Go Next", f"{top3[0]}, {top3[1]} and {top3[2]} rank highest; {', '.join(sorted(ALL12))} "
             f"stay in the top 10 under all {N_VAR} index variants.")
    top = 98
    ch = BOT - top
    lw = 460
    ty = p.card(X0, top, lw, ch, f"Market priority index — top 15 ({LATEST_LABEL}, equal weights)", "Ranking")
    t15 = BASE.head(15)[::-1]
    ax = p.axes(X0 + P + 92, ty + 4, lw - 2 * P - 160, ch - (ty - top) - 122)
    yy = np.arange(len(t15))
    ax.barh(yy, t15["index"], color=SOLAR, height=0.62)
    ax.set_yticks(yy)
    ax.set_yticklabels([f"{int(r)}  {s}" for r, s in zip(t15["rank"], t15.state)], fontsize=9.5)
    clean(ax, "x")
    ax.set_xlim(0, 1.15)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    for i, (s, v) in enumerate(zip(t15.state, t15["index"])):
        ax.text(v + 0.008, i, f"{v:.2f}", va="center", fontsize=8.5, color=NAVY)
        if s in ALL12:
            ax.text(v + 0.135, i, f"All {N_VAR}", va="center", fontsize=7.5, color=GRID, fontfamily=SEMI,
                    clip_on=False, bbox=dict(boxstyle="round,pad=0.25", fc="#FFFFFF", ec=GRID, lw=0.9))
    note = p.wrap("How the index is built: geometric mean of percentile ranks of generator reliance (NLSS 2018/19), "
                  "monthly ₦ saving from switching, and ability to pay (1 − MPI 2022). Shown as ranks, not precise "
                  f"scores. All {N_VAR} = top 10 under all 3 weightings × 2 users × 2 reliance measures.", 8.5,
                  lw - 2 * P - 16)
    for k_, line in enumerate(note):
        p.text(X0 + P, top + ch - P - (len(note) - 1 - k_) * 13, line, 8.5, SUB, va="bottom")

    tx = X0 + lw + GAP
    tw = CW - lw - GAP
    ty = p.card(tx, top, tw, ch, f"Top 10 at a glance — household, {LATEST_LABEL}",
                "Top 10 · central, payback low–high")
    pl = pay[(pay.month == LATEST) & (pay.user == "household")].pivot_table(
        index="state", columns="case", values=["saving_ngn_per_month", "payback_months",
                                               "upfront_months_of_consumption"])
    iw = tw - 2 * P
    cols = [("Rank", 0, "left"), ("State", 40, "left"), ("Saving ₦/month", 236, "right"),
            ("Payback, months", 372, "right"), ("Upfront ÷ spending", iw, "right")]
    y0 = ty + 12
    for name, dx, ha in cols:
        p.text(tx + P + dx, y0, name, 9.5, SUB, SEMI, ha=ha, va="center")
    p.base.plot([tx + P, tx + tw - P], [y0 + 14, y0 + 14], color=BORDER, lw=1)
    rh = (top + ch - P - 26 - (y0 + 14)) / 10
    for i, (_, r_) in enumerate(BASE.head(10).iterrows()):
        yy_ = y0 + 14 + rh * (i + 0.5)
        s = r_.state
        vals = [str(int(r_["rank"])), s, naira(pl.loc[s, ("saving_ngn_per_month", "central")]),
                f"{pl.loc[s, ('payback_months', 'central')]:.1f}  ({pl.loc[s, ('payback_months', 'low')]:.1f}–"
                f"{pl.loc[s, ('payback_months', 'high')]:.1f})",
                f"{pl.loc[s, ('upfront_months_of_consumption', 'central')]:.1f} months"]
        for (name, dx, ha), v in zip(cols, vals):
            t = p.text(tx + P + dx, yy_, v, 10, NAVY, SEMI if name == "State" else REG, ha=ha, va="center")
            if name == "State" and s in ALL12:
                p.text(tx + P + dx + p.width(t) + 6, yy_, "●", 7, GRID, va="center")
        p.base.plot([tx + P, tx + tw - P], [yy_ + rh / 2, yy_ + rh / 2], color=BORDER, lw=0.6)
    p.text(tx + P, top + ch - P, f"● top 10 under all {N_VAR} index variants", 9, GRID, va="bottom")
    p.save("page4.png")


if __name__ == "__main__":
    for fn in (page0, page1, page2, page3, page4):
        fn()
    print("written:", sorted(x.name for x in OUT.glob("page*.png")))
