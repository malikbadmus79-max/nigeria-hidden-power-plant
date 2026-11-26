"""Phase 5 step 1: static design mockups (1280x720 canvas, 2x PNG) for the Power BI dashboard.

Uses the real numbers in data/processed/powerbi/ (and the boundary file in data/raw/geoboundaries/).
Outputs figures/mockups/page1.png ... page4.png (2560x1440 px).

Run from repo root:  python src/mockups.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.collections import PolyCollection  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, Normalize  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from states import canonical_state  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PBI = ROOT / "data" / "processed" / "powerbi"
GJ = ROOT / "data" / "raw" / "geoboundaries" / "geoBoundaries-NGA-ADM1.geojson"
OUT = ROOT / "figures" / "mockups"

# ---------------- design system ----------------
W, H = 1280, 720
BG, CARD, BORDER = "#F6F7F9", "#FFFFFF", "#E5E7EB"
NAVY, SUB, FOOT = "#0F1B2D", "#4B5563", "#6B7280"
SOLAR, GEN, GRID, ALERT, GRIDLINE = "#F59E0B", "#475569", "#0D9488", "#DC2626", "#E5E7EB"
SEQ = LinearSegmentedColormap.from_list("amber_seq", ["#FEF3C7", "#B45309"])
M, GAP, R = 24, 16, 8
TABS = ["1  The Fuel Shock", "2  Generator vs Grid vs Solar", "3  Payback", "4  Where to Go Next"]
FOOTNOTE = ("Estimates with low–high ranges. Sources: NBS, NERC, CBN, Global Solar Atlas/Solargis (CC BY 4.0), "
            "geoBoundaries. Method and limits: docs/phase4_audit.md")

for f in ["segoeui.ttf", "seguisb.ttf"]:
    font_manager.fontManager.addfont(f"C:/Windows/Fonts/{f}")
REG, SEMI = "Segoe UI", "Segoe UI Semibold"
plt.rcParams.update({"font.family": REG, "font.size": 10, "axes.edgecolor": GRIDLINE, "text.color": NAVY,
                     "axes.labelcolor": NAVY, "xtick.color": SUB, "ytick.color": SUB, "svg.fonttype": "none"})

# Power BI sizes are in pt on a 96-dpi canvas; draw at 96 dpi so pt match, save at 2x.
DPI = 96


def naira(v: float, dec: int = 0) -> str:
    if v >= 1e6:
        return f"₦{v / 1e6:.{max(dec, 1)}f}m"
    return f"₦{v:,.{dec}f}"


# ---------------- page scaffolding ----------------
class Page:
    def __init__(self, n: int, title: str, takeaway: str):
        self.fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI, facecolor=BG)
        self.base = self.fig.add_axes([0, 0, 1, 1])
        self.base.set_xlim(0, W)
        self.base.set_ylim(H, 0)
        self.base.axis("off")
        self.n = n
        # header
        self.base.text(M, M + 2, title, fontsize=22, fontfamily=SEMI, color=NAVY, va="top")
        self.base.text(M, M + 40, takeaway, fontsize=13, color=SUB, va="top")
        # tabs (right-aligned)
        x = W - M
        widths = [len(t) * 6.3 + 24 for t in TABS]
        for i in reversed(range(4)):
            w = widths[i]
            x -= w
            active = i == n - 1
            self.base.add_patch(FancyBboxPatch((x, M), w, 26, boxstyle=f"round,pad=0,rounding_size={R}",
                                               fc=NAVY if active else CARD, ec=NAVY if active else BORDER, lw=1))
            self.base.text(x + w / 2, M + 13, TABS[i], fontsize=9, fontfamily=SEMI if active else REG,
                           color="#FFFFFF" if active else SUB, ha="center", va="center")
            x -= 8
        # footnote
        self.base.text(M, H - M + 4, FOOTNOTE, fontsize=9, color=FOOT, va="bottom")

    def card(self, x, y, w, h, title=None):
        self.base.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={R}",
                                           fc=CARD, ec=BORDER, lw=1))
        if title:
            self.base.text(x + GAP, y + GAP, title, fontsize=12, fontfamily=SEMI, color=NAVY, va="top")

    def axes(self, x, y, w, h):
        return self.fig.add_axes([x / W, 1 - (y + h) / H, w / W, h / H])

    def kpi(self, x, y, w, h, title, value, sub, value_color=NAVY):
        self.card(x, y, w, h, title)
        self.base.text(x + GAP, y + GAP + 24, value, fontsize=28, fontfamily=SEMI, color=value_color, va="top")
        self.base.text(x + GAP, y + h - GAP, sub, fontsize=10, color=SUB, va="bottom")

    def save(self, name):
        OUT.mkdir(parents=True, exist_ok=True)
        self.fig.savefig(OUT / name, dpi=DPI * 2, facecolor=BG)
        plt.close(self.fig)


def clean(ax, grid_axis="y"):
    for s in ["top", "right", "left"]:
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRIDLINE)
    ax.tick_params(length=0, labelsize=10)
    ax.grid(axis=grid_axis, color=GRIDLINE, lw=0.8)
    ax.set_axisbelow(True)


# ---------------- map ----------------
def load_shapes():
    gj = json.loads(GJ.read_text(encoding="utf-8"))
    shapes = {}
    for f in gj["features"]:
        st = canonical_state(f["properties"]["shapeName"].replace("Federal Capital Territory", "FCT"))
        g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        k = np.cos(np.radians(9))
        shapes[st] = [np.column_stack([np.array(p[0])[:, 0] * k, np.array(p[0])[:, 1]]) for p in polys]
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
        cx, cy = r[:, 0].mean(), r[:, 1].mean()
        ax.text(cx, cy, f"{st}\n{fmt(values[st])}", fontsize=8, ha="center", va="center", color=NAVY,
                fontfamily=SEMI, bbox=dict(boxstyle="round,pad=0.2", fc="#FFFFFF", ec="none", alpha=0.85))
    return norm


def spread_note(p: Page, x, y, values: pd.Series):
    pct = (values.max() / values.min() - 1) * 100
    p.base.text(x, y, f"States differ by only about {pct:.0f}%; the colour scale is stretched to show the differences",
                fontsize=9, color=FOOT, va="bottom")


def legend_bar(p: Page, x, y, w, norm, fmt, label):
    ax = p.axes(x, y, w, 8)
    ax.imshow(np.linspace(0, 1, 256)[None, :], aspect="auto", cmap=SEQ)
    ax.axis("off")
    p.base.text(x, y + 12, fmt(norm.vmin), fontsize=9, color=SUB, va="top")
    p.base.text(x + w, y + 12, fmt(norm.vmax), fontsize=9, color=SUB, va="top", ha="right")
    p.base.text(x + w / 2, y + 12, label, fontsize=9, color=SUB, va="top", ha="center")


# ---------------- data ----------------
gen = pd.read_csv(PBI / "fact_generator_cost.csv", dtype={"month": str})
sol = pd.read_csv(PBI / "fact_solar_cost.csv", dtype={"month": str})
tar = pd.read_csv(PBI / "fact_grid_tariff.csv", dtype={"month": str})
pay = pd.read_csv(PBI / "fact_payback.csv", dtype={"month": str})
pri = pd.read_csv(PBI / "fact_priority_index.csv")
LATEST = gen.month.max()
LATEST_LABEL = pd.Period(LATEST, "M").strftime("%b %Y")
mlabel = lambda m: pd.Period(m, "M").strftime("%b %Y")  # noqa: E731


def month_axis(ax, months, every=6):
    ticks = list(range(0, len(months), every))
    ax.set_xticks(ticks)
    ax.set_xticklabels([pd.Period(months[i], "M").strftime("%b %y") for i in ticks])
    ax.set_xlim(-0.5, len(months) - 0.5)


# ================= PAGE 1 =================
def page1():
    g = gen[gen.case.isin(["low", "central", "high"])]
    nat = g.groupby(["user", "case", "month"]).running_ngn_per_month.median().unstack("case")
    hh, bz = nat.loc["household"], nat.loc["business"]
    first = "2023-01"
    hh_now, bz_now = hh.loc[LATEST, "central"], bz.loc[LATEST, "central"]
    hh_chg = (hh_now / hh.loc[first, "central"] - 1) * 100
    bz_chg = (bz_now / bz.loc[first, "central"] - 1) * 100
    takeaway = (f"Running a small household generator cost a median {naira(hh_now)} a month in {LATEST_LABEL}, "
                f"{hh_chg:.0f}% more than in January 2023 (central estimate).")
    p = Page(1, "The Fuel Shock", takeaway)
    top = 104
    kw = (W - 2 * M - 2 * GAP) / 3
    p.kpi(M, top, kw, 110, f"Household generator, ₦/month ({LATEST_LABEL})", naira(hh_now),
          f"National median, central · range {naira(hh.loc[LATEST, 'low'])}–{naira(hh.loc[LATEST, 'high'])}")
    p.kpi(M + kw + GAP, top, kw, 110, f"Small-business generator, ₦/month ({LATEST_LABEL})", naira(bz_now),
          f"National median, central · range {naira(bz.loc[LATEST, 'low'])}–{naira(bz.loc[LATEST, 'high'])}")
    p.kpi(M + 2 * (kw + GAP), top, kw, 110, "Change since January 2023", f"+{hh_chg:.0f}%",
          f"Household (petrol) · business (diesel) +{bz_chg:.0f}%", value_color=ALERT)

    y2 = top + 110 + GAP
    h2 = H - M - 22 - y2
    mw = 470
    p.card(M, y2, mw, h2, f"Household generator cost by state ({LATEST_LABEL}, central)")
    st = g[(g.user == "household") & (g.case == "central") & (g.month == LATEST)].set_index("state").running_ngn_per_month
    ax = p.axes(M + GAP, y2 + 40, mw - 2 * GAP, h2 - 112)
    norm = draw_map(ax, st, naira, label_states=[st.idxmax(), st.idxmin()])
    legend_bar(p, M + GAP + 60, y2 + h2 - 62, mw - 2 * GAP - 120, norm, naira, "₦ per month")
    spread_note(p, M + GAP, y2 + h2 - 10, st)

    lx = M + mw + GAP
    lw = W - M - lx
    p.card(lx, y2, lw, h2, "National median household generator cost, ₦/month (central and low–high band)")
    ax = p.axes(lx + GAP + 62, y2 + 66, lw - 2 * GAP - 140, h2 - 100)
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
    ax.text(j + 0.6, ycap * 0.97, "Jun 2023: petrol subsidy removed", color=ALERT, fontsize=10,
            fontfamily=SEMI, va="top")
    ax.text(xs[-1], hh["central"].iloc[-1], f"  {naira(hh_now)}", color=GEN, fontsize=10, fontfamily=SEMI,
            va="center", ha="left", clip_on=False)
    ax.text(xs[0] + 0.3, hh["central"].iloc[0] + ycap * 0.04, naira(hh["central"].iloc[0]), color=GEN, fontsize=10,
            va="bottom", ha="left")
    ax.set_yticks([t for t in ax.get_yticks() if 0 < t <= ycap])
    ax.tick_params(axis="x", pad=6)
    p.base.text(lx + GAP, y2 + 38, f"Shaded band = low–high case, clipped at the top (high case reaches "
                f"{naira(hh['high'].max())})", color=FOOT, fontsize=9, ha="left", va="top")
    p.save("page1.png")


# ================= PAGE 2 =================
def page2():
    gl = gen[(gen.month == LATEST) & (gen.case == "central")]
    sl = sol[(sol.month == LATEST) & (sol.case == "central")]
    tl = tar[tar.month == LATEST]
    placeholder = set(tl[tl.tariff_status != "nerc_order"].state)
    hh_g = gl[gl.user == "household"].set_index("state").running_ngn_per_kwh
    hh_s = sl[sl.user == "household"].set_index("state").lcoe_ngn_per_kwh
    takeaway = (f"In {LATEST_LABEL} a small petrol generator cost {naira(hh_g.min())}–{naira(hh_g.max())} per kWh; "
                f"solar + battery {naira(hh_s.min())}–{naira(hh_s.max())}; grid Band A ₦209.50 where supply exists.")
    p = Page(2, "Generator vs Grid vs Solar", takeaway)
    top = 104
    cw = (W - 2 * M - GAP) / 2
    ch = H - M - 22 - top
    band_a = tl[tl.band == "A"].tariff_ngn_per_kwh.median()
    band_b = tl[tl.band == "B"].tariff_ngn_per_kwh.median()
    for k, user in enumerate(["household", "business"]):
        x = M + k * (cw + GAP)
        g = gl[gl.user == user].set_index("state").running_ngn_per_kwh
        s = sl[sl.user == user].set_index("state").lcoe_ngn_per_kwh
        order = g.sort_values(ascending=False)
        rows = list(order.index[:5]) + [None] + list(order.index[-5:])
        rows = rows[::-1]
        lab = "Household · 2.5 kVA petrol" if user == "household" else "Small business · 20 kVA diesel"
        p.card(x, top, cw, ch, f"{lab} — ₦ per kWh ({LATEST_LABEL}, central)")
        p.base.text(x + GAP, top + 38, "5 states with the costliest and 5 with the cheapest generator power",
                    fontsize=10, color=SUB, va="top")
        ax = p.axes(x + GAP + 92, top + 112, cw - 2 * GAP - 150, ch - 168)
        for i, stt in enumerate(rows):
            if stt is None:
                ax.text(0, i, "   · · ·", va="center", fontsize=11, color=FOOT)
                continue
            ax.barh(i + 0.19, g[stt], height=0.36, color=GEN)
            ax.barh(i - 0.19, s[stt], height=0.36, color=SOLAR)
            ax.text(g[stt], i + 0.19, f"  {g[stt]:,.0f}", va="center", fontsize=9, color=GEN)
            ax.text(max(s[stt], band_a), i - 0.19, f"  {s[stt]:,.0f}", va="center", fontsize=9, color=NAVY)
            if stt in placeholder:
                ax.plot(-0.02, i, marker="D", ms=5, mfc="none", mec=GRID, mew=1.2,
                        transform=ax.get_yaxis_transform(), clip_on=False)
        ax.set_yticks([i for i, r_ in enumerate(rows) if r_])
        ax.set_yticklabels([r_ for r_ in rows if r_], fontsize=10)
        ax.tick_params(axis="y", pad=20)
        clean(ax, "x")
        ax.set_xlim(0, g.max() * 1.18)
        ax.xaxis.set_major_formatter(lambda v, _: f"₦{v:,.0f}")
        ax.axvline(band_a, color=GRID, lw=1.3, ls="-")
        ax.axvline(band_b, color=GRID, lw=1.3, ls="--")
        ax.text(band_a, len(rows) - 0.3, f" Band A ₦{band_a:,.2f}", color=GRID, fontsize=9, va="bottom")
        ax.text(band_b, len(rows) - 0.3, f"Band B ₦{band_b:,.0f} ", color=GRID, fontsize=9, va="bottom", ha="right")
        ax.set_ylim(-0.6, len(rows) + 0.4)
        ly = top + 74
        lx0 = x + GAP
        items = [("rect", GEN, "Generator", 96), ("rect", SOLAR, "Solar + battery", 130),
                 ("line", GRID, "Grid tariff: price reference only", 220), ("diamond", GRID, "state-set tariff", 0)]
        for kind, col, txt, wdt in items:
            if kind == "rect":
                p.base.add_patch(plt.Rectangle((lx0, ly - 5), 10, 10, color=col))
            elif kind == "line":
                p.base.plot([lx0 + 5, lx0 + 5], [ly - 7, ly + 7], color=GRID, lw=1.6)
            else:
                p.base.plot(lx0 + 5, ly, marker="D", ms=5, mfc="none", mec=GRID, mew=1.2)
            p.base.text(lx0 + 16, ly, txt, fontsize=10, color=SUB, va="center")
            lx0 += wdt
        p.base.text(x + GAP, top + ch - GAP,
                    f"All 37 states: generator {naira(g.min())}–{naira(g.max())}/kWh · solar "
                    f"{naira(s.min())}–{naira(s.max())}/kWh (central)", fontsize=10, color=SUB, va="bottom")
    p.save("page2.png")


# ================= PAGE 3 =================
def page3():
    pc = pay[pay.case == "central"]
    nat = pc.groupby(["user", "month"]).payback_months.median().unstack("user")
    hh = nat["household"]
    mid24 = hh.loc["2024-01":"2024-12"]
    peak_m, peak_v = mid24.idxmax(), mid24.max()
    now, start = hh.loc[LATEST], hh.loc["2023-06"]
    ranges = pay[(pay.month == LATEST) & (pay.user == "household")].pivot_table(index="state", columns="case",
                                                                               values="payback_months")
    takeaway = (f"Solar + battery now pays back in about {now:.0f} months for a typical household (median, "
                f"{LATEST_LABEL}), down from {peak_v:.0f} months at the {mlabel(peak_m)} peak (central estimates).")
    p = Page(3, "Payback", takeaway)
    top = 104
    kw = (W - 2 * M - 2 * GAP) / 3
    p.kpi(M, top, kw, 110, f"Household payback now ({LATEST_LABEL})", f"{now:.1f} months",
          f"Median of states, central · states {ranges['central'].min():.1f}–{ranges['central'].max():.1f}; "
          f"range {ranges['low'].min():.1f}–{ranges['high'].max():.1f}")
    p.kpi(M + kw + GAP, top, kw, 110, "At the start, June 2023", f"{start:.1f} months",
          f"Median of states, central · business {nat['business'].loc['2023-06']:.1f} months")
    p.kpi(M + 2 * (kw + GAP), top, kw, 110, f"2024 peak ({mlabel(peak_m)})", f"{peak_v:.1f} months",
          "Naira fall raised solar costs before petrol prices caught up", value_color=ALERT)

    y2 = top + 110 + GAP
    h2 = H - M - 22 - y2
    mw, lw = 360, 420
    aw = W - 2 * M - mw - lw - 2 * GAP
    p.card(M, y2, mw, h2, f"Household payback by state ({LATEST_LABEL})")
    ax = p.axes(M + GAP, y2 + 40, mw - 2 * GAP, h2 - 128)
    norm = draw_map(ax, ranges["central"], lambda v: f"{v:.1f} mo",
                    label_states=[ranges["central"].idxmax(), ranges["central"].idxmin()])
    legend_bar(p, M + GAP + 30, y2 + h2 - 76, mw - 2 * GAP - 60, norm, lambda v: f"{v:.1f}", "months (central)")
    pct = (ranges["central"].max() / ranges["central"].min() - 1) * 100
    p.base.text(M + GAP, y2 + h2 - 24, f"States differ by only about {pct:.0f}%; the colour scale is",
                fontsize=9, color=FOOT, va="bottom")
    p.base.text(M + GAP, y2 + h2 - 10, "stretched to show the differences", fontsize=9, color=FOOT, va="bottom")

    lx = M + mw + GAP
    p.card(lx, y2, lw, h2, "Payback over time, months (median of states, central)")
    ax = p.axes(lx + GAP + 28, y2 + 44, lw - 2 * GAP - 112, h2 - 80)
    months = list(nat.index)
    xs = np.arange(len(months))
    ax.plot(xs, nat["household"], color=SOLAR, lw=2.2)
    ax.plot(xs, nat["business"], color=GEN, lw=1.6)
    clean(ax)
    month_axis(ax, months, every=6)
    ax.set_ylim(0, max(nat.max()) * 1.18)
    ax.set_yticks([5, 10, 15, 20, 25, 30])
    ax.set_ylabel("months", fontsize=10, color=SUB)
    ax.tick_params(axis="x", pad=6)
    pi = months.index(peak_m)
    ax.plot(pi, peak_v, "o", color=ALERT, ms=6)
    ax.text(pi, peak_v + 1.2, f"Peak {peak_v:.1f} mo", color=ALERT, fontsize=10, fontfamily=SEMI, ha="center")
    ax.text(xs[-1], nat["household"].iloc[-1], f" Household {nat['household'].iloc[-1]:.1f}", color="#B45309",
            fontsize=9, fontfamily=SEMI, va="bottom", ha="left", clip_on=False)
    ax.text(xs[-1], nat["business"].iloc[-1], f" Business {nat['business'].iloc[-1]:.1f}", color=GEN,
            fontsize=9, fontfamily=SEMI, va="top", ha="left", clip_on=False)

    ax_x = lx + lw + GAP
    p.card(ax_x, y2, aw, h2, "Upfront cost in months of household spending")
    a = pay[(pay.month == LATEST) & (pay.user == "household")].pivot_table(index="state", columns="case",
                                                                         values="upfront_months_of_consumption")
    a = a.sort_values("central", ascending=False).head(12)[::-1]
    ax = p.axes(ax_x + GAP + 62, y2 + 40, aw - 2 * GAP - 80, h2 - 104)
    yy = np.arange(len(a))
    ax.barh(yy, a["central"], color=SOLAR, height=0.62)
    ax.errorbar(a["central"], yy, xerr=[a["central"] - a["low"], a["high"] - a["central"]], fmt="none",
                ecolor=GEN, elinewidth=0.9, capsize=2)
    ax.set_yticks(yy)
    ax.set_yticklabels(a.index, fontsize=10)
    for i, v in enumerate(a["central"]):
        ax.text(0.15, i, f"{v:.1f}", va="center", fontsize=9, color=NAVY, fontfamily=SEMI)
    clean(ax, "x")
    med = pay[(pay.month == LATEST) & (pay.user == "household") & (pay.case == "central")].upfront_months_of_consumption.median()
    p.base.text(ax_x + GAP, y2 + h2 - GAP, f"12 least affordable · whiskers = low–high · "
                f"all-state median {med:.1f}", fontsize=9, color=SUB, va="bottom")
    p.save("page3.png")


# ================= PAGE 4 =================
def page4():
    base = pri[(pri.weighting == "equal") & (pri.gap_user == "household") & (pri.reliance_measure == "primary_source")]
    base = base.sort_values("rank")
    freq = pri[pri["rank"] <= 10].groupby("state").size()
    allv = set(freq[freq == pri.groupby(["weighting", "gap_user", "reliance_measure"]).ngroups].index)
    top3 = base.state.head(3).tolist()
    takeaway = (f"{top3[0]}, {top3[1]} and {top3[2]} rank highest; {', '.join(sorted(allv))} stay in the top 10 "
                f"under all 12 index variants.")
    p = Page(4, "Where to Go Next", takeaway)
    top = 104
    ch = H - M - 22 - top
    lw = 560
    p.card(M, top, lw, ch, f"Market priority index — top 15 states ({LATEST_LABEL}, equal weights)")
    t15 = base.head(15)[::-1]
    ax = p.axes(M + GAP + 96, top + 46, lw - 2 * GAP - 112, ch - 132)
    yy = np.arange(len(t15))
    ax.barh(yy, t15["index"], color=SOLAR, height=0.62)
    ax.set_yticks(yy)
    ax.set_yticklabels([f"{int(r)}  {s}" for r, s in zip(t15["rank"], t15.state)], fontsize=10)
    clean(ax, "x")
    ax.set_xlim(0, 1.15)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    for i, (s, v) in enumerate(zip(t15.state, t15["index"])):
        ax.text(v + 0.008, i, f"{v:.2f}", va="center", fontsize=9, color=NAVY)
        if s in allv:
            ax.text(v + 0.085, i, "All 12", va="center", fontsize=8, color=GRID, fontfamily=SEMI,
                    bbox=dict(boxstyle="round,pad=0.25", fc="#FFFFFF", ec=GRID, lw=0.9))
    note = ["How the index is built: geometric mean of percentile ranks of generator reliance (NLSS 2018/19),",
            "monthly ₦ saving from switching, and ability to pay (1 − MPI 2022). Shown as ranks, not precise scores.",
            "All 12 = in the top 10 under all 3 weightings × 2 users × 2 reliance measures."]
    for k_, line in enumerate(note):
        p.base.text(M + GAP, top + ch - GAP - (len(note) - 1 - k_) * 13, line, fontsize=9, color=SUB, va="bottom")

    tx = M + lw + GAP
    tw = W - M - tx
    p.card(tx, top, tw, ch, f"Top 10 at a glance — household, {LATEST_LABEL} (central; payback range low–high)")
    pl = pay[(pay.month == LATEST) & (pay.user == "household")].pivot_table(
        index="state", columns="case", values=["saving_ngn_per_month", "payback_months", "upfront_months_of_consumption"])
    cols = [("Rank", 0, "left"), ("State", 44, "left"), ("Saving ₦/month", 250, "right"),
            ("Payback, months", 420, "right"), ("Upfront ÷ monthly spending", tw - 2 * GAP, "right")]
    y0 = top + 52
    for name, dx, ha in cols:
        p.base.text(tx + GAP + dx, y0, name, fontsize=10, fontfamily=SEMI, color=SUB, ha=ha, va="center")
    p.base.plot([tx + GAP, tx + tw - GAP], [y0 + 14, y0 + 14], color=BORDER, lw=1)
    for i, (_, r) in enumerate(base.head(10).iterrows()):
        yy_ = y0 + 40 + i * 42
        s = r.state
        vals = [str(int(r["rank"])), s, naira(pl.loc[s, ("saving_ngn_per_month", "central")]),
                f"{pl.loc[s, ('payback_months', 'central')]:.1f}  ({pl.loc[s, ('payback_months', 'low')]:.1f}–"
                f"{pl.loc[s, ('payback_months', 'high')]:.1f})",
                f"{pl.loc[s, ('upfront_months_of_consumption', 'central')]:.1f} months"]
        for (name, dx, ha), v in zip(cols, vals):
            p.base.text(tx + GAP + dx, yy_, v, fontsize=10, ha=ha, va="center",
                        fontfamily=SEMI if name == "State" else REG, color=NAVY)
        if s in allv:
            p.base.text(tx + GAP + 44 + len(s) * 7.2 + 8, yy_, "●", color=GRID, fontsize=8, va="center")
        p.base.plot([tx + GAP, tx + tw - GAP], [yy_ + 21, yy_ + 21], color=BORDER, lw=0.6)
    p.base.text(tx + GAP, top + ch - GAP, "● top 10 under all 12 index variants", fontsize=9, color=GRID, va="bottom")
    p.save("page4.png")


if __name__ == "__main__":
    page1()
    page2()
    page3()
    page4()
    print("written:", sorted(str(x) for x in OUT.glob("page*.png")))
