"""Write the 5 report pages of the premium v2 dashboard (PBIR JSON), matching figures/mockups_v2/page0-4.png.

Layout constants and the static wording come from src/mockups.py (the approved v2 mockups); every number is a
DAX measure (model_spec.py). Working parts of the v1 build are reused from build_pages.py: maps, error bars
(band on page 1, whiskers on page 3), page-2 row tables, priority bars. Run with Power BI Desktop closed.
Usage: python powerbi/build_pages_v2.py
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))
import build_pages as bp  # noqa: E402
import mockups as mk  # noqa: E402  (design constants and the mockup numbers, for layout only)

from build_pages import (C, SEMI, FONT, color, column, container, image, label, lit, m_proj, mcard,  # noqa: E402
                         para, props, run, text_w, textbox)

W, H = 1280, 720
NAVY, SUB, FOOT, LABEL = mk.NAVY, mk.SUB, mk.FOOT, mk.LABEL
SOLAR, GEN, GRID, ALERT, BORDER, CARD, BG = mk.SOLAR, mk.GEN, mk.GRID, mk.ALERT, mk.BORDER, mk.CARD, mk.BG
SB_W, SB_ACTIVE, SB_TEXT, SB_MUTED = mk.SB_W, mk.SB_ACTIVE, mk.SB_TEXT, mk.SB_MUTED
PILL = mk.PILL
M, GAP, R, P = mk.M, mk.GAP, float(mk.R), mk.P
X0, CW, BOT = mk.X0, mk.CW, mk.BOT
KH = 116
RES = bp.RES
STAGING = HERE / "pbir_staging" / "definition"
PAGES_DIR = STAGING / "pages"

PAGES = [("p0_overview", "Overview", "overview"), ("p1_fuel_shock", "The Fuel Shock", "fuel"),
         ("p2_gen_grid_solar", "Generator vs Grid vs Solar", "bars"), ("p3_payback", "Payback", "clock"),
         ("p4_where_next", "Where to Go Next", "pin")]
NAV_LABELS = [label_ for _, label_ in mk.NAV]
ICON_COLOURS = {"white": "#FFFFFF", "nav": SB_TEXT, "kpi": "#94A3B8"}
SOURCES, COPYRIGHT = mk.SOURCES, mk.COPYRIGHT


def spaced(s):
    return mk.spaced(s)


# ---------------- SVG icons ----------------
def svg_icon(kind, col, sw=1.8):
    st = f'fill="none" stroke="{col}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"'
    body = {
        "overview": "".join(f'<rect x="{x}" y="{y}" width="7.5" height="7.5" rx="1.6" {st}/>'
                            for x in (3, 13.5) for y in (3, 13.5)),
        "fuel": f'<rect x="4.5" y="7" width="12" height="14" rx="2" {st}/><path d="M14.5 7 L19 2.5 L21 4.5" {st}/>'
                f'<path d="M8 10.5 L13.5 17" {st}/>',
        "bars": f'<path d="M6 20 V13 M12 20 V8 M18 20 V4" fill="none" stroke="{col}" stroke-width="3.6" '
                f'stroke-linecap="butt"/>',
        "clock": f'<circle cx="12" cy="12" r="9" {st}/><path d="M12 6.5 V12 H16" {st}/>',
        "pin": f'<path d="M12 21.5 C12 21.5 5 14.5 5 9.8 A7 7 0 0 1 19 9.8 C19 14.5 12 21.5 12 21.5 Z" {st}/>'
               f'<circle cx="12" cy="9.8" r="2.2" fill="{col}"/>',
        "sun": f'<circle cx="12" cy="12" r="4.2" {st}/>' + "".join(
            f'<path d="M{12 + 7 * c:.2f} {12 + 7 * s_:.2f} L{12 + 10 * c:.2f} {12 + 10 * s_:.2f}" {st}/>'
            for c, s_ in ((1, 0), (0.7071, 0.7071), (0, 1), (-0.7071, 0.7071), (-1, 0), (-0.7071, -0.7071),
                          (0, -1), (0.7071, -0.7071))),
        "trend": f'<path d="M3 17 L9 11 L13 14 L21 6" {st}/><path d="M15 6 H21 V12" {st}/>',
        "factory": f'<path d="M3 21 V11 L9 14 V11 L15 14 V4 H21 V21 Z" {st}/>',
        "logo": f'<circle cx="12" cy="12" r="5.2" fill="{col}"/>' + "".join(
            f'<path d="M{12 + 7.5 * c:.2f} {12 + 7.5 * s_:.2f} L{12 + 11 * c:.2f} {12 + 11 * s_:.2f}" '
            f'fill="none" stroke="{col}" stroke-width="2" stroke-linecap="round"/>'
            for c, s_ in ((1, 0), (0.7071, 0.7071), (0, 1), (-0.7071, 0.7071), (-1, 0), (-0.7071, -0.7071),
                          (0, -1), (0.7071, -0.7071))),
    }[kind]
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24">{body}</svg>'


def icon_name(kind, tone):
    return f"icon_{kind}_{tone}.svg"


def write_icons():
    names = []
    for kind in ("overview", "fuel", "bars", "clock", "pin"):
        for tone in ("white", "nav"):
            names.append(icon_name(kind, tone))
            (RES / names[-1]).write_text(svg_icon(kind, ICON_COLOURS[tone]), encoding="utf-8")
    for kind in ("fuel", "sun", "clock", "pin", "trend", "factory"):
        names.append(icon_name(kind, "kpi"))
        (RES / names[-1]).write_text(svg_icon(kind, ICON_COLOURS["kpi"]), encoding="utf-8")
    names.append("logo_sun.svg")
    (RES / names[-1]).write_text(svg_icon("logo", SOLAR), encoding="utf-8")
    return names


def register(names):
    rj = bp.REPORT / "definition" / "report.json"
    rep = json.loads(rj.read_text(encoding="utf-8"))
    pkg = next(p_ for p_ in rep["resourcePackages"] if p_["name"] == "RegisteredResources")
    have = {i["name"] for i in pkg["items"]}
    pkg["items"] += [{"name": n, "path": n, "type": "Image"} for n in names if n not in have]
    rj.write_text(json.dumps(rep, indent=2) + "\n", encoding="utf-8")


def icon(name, x, y, s, z, item):
    visual = {"visualType": "image",
              "objects": {"general": [{"properties": {"imageUrl": bp.resource(item)}}],
                          "imageScaling": [{"properties": props(imageScalingType="Fit")}]},
              "visualContainerObjects": bp.chrome()}
    return container(name, x, y, s, s, z, visual)


# ---------------- boxes, cards, text ----------------
def box(name, x, y, w, h, z, bg, radius=0.0, border=None, shadow=False):
    vco = bp.chrome(panel=True, bg=bg, border=border is not None, border_color=border or bg, radius=radius)
    if shadow:
        vco["dropShadow"] = [{"properties": props(show=True, color=C(NAVY), transparency=92.0, position="Outer",
                                                   preset="Custom", shadowSpread=0.0, shadowBlur=6.0, angle=90.0,
                                                   shadowDistance=2.0)}]
    visual = {"visualType": "textbox", "objects": {"general": [{"properties": {"paragraphs": [para(run(" ", 1.0))]}}]},
              "visualContainerObjects": vco}
    return container(name, x, y, w, h, z, visual)


def txt(name, x, y, w, z, s, size, col=NAVY, font=FONT, lines=1, align="left"):
    """Static text whose top-left matches a mockup text at (x, y) (va=top)."""
    return label(name, x - 4, y - 6, w + 8, z, s, size, col, font, align=align, lines=lines)


def mtxt(name, x, y, w, z, m, size, col=NAVY, font=FONT, on=CARD, h=None):
    """Measure text whose top-left matches a mockup text at (x, y)."""
    return mcard(name, x - 4, y - 6, w + 8, z, m, size, col, font, on=on, h=h)


def card(prefix, x, y, w, h, z, title=None, label_=None, label_m=None, title_m=None, accent=None):
    v = []
    if accent:
        v.append(box(f"{prefix}Accent", x, y, w, 24, z, accent, R))
        v.append(box(f"{prefix}Card", x, y + 4, w, h - 4, z + 1, CARD, R, BORDER, shadow=True))
    else:
        v.append(box(f"{prefix}Card", x, y, w, h, z, CARD, R, BORDER, shadow=True))
    ty = y + P
    if label_ or label_m:
        if label_m:
            v.append(mtxt(f"{prefix}Label", x + P, ty - 2, w - 2 * P, z + 2, label_m, 8.0, LABEL, SEMI))
        else:
            v.append(txt(f"{prefix}Label", x + P, ty - 2, w - 2 * P, z + 2, spaced(label_), 8.0, LABEL, SEMI))
        ty += 16
    if title_m:
        v.append(mtxt(f"{prefix}Title", x + P, ty, w - 2 * P, z + 3, title_m, 11.5, NAVY, SEMI))
    elif title:
        v.append(txt(f"{prefix}Title", x + P, ty, w - 2 * P, z + 3, title, 11.5, NAVY, SEMI))
    return v, ty + 24


def pill(name, x, cy, z, m, text, kind):
    bg, fg = PILL[kind]
    w = text_w(text, 8.5, True) * 0.97 + 18
    visual = {
        "visualType": "multiRowCard",
        "query": {"queryState": {"Values": {"projections": [m_proj(m)]}}},
        "objects": {
            "dataLabels": [{"properties": props(color=C(fg), fontSize=8.5, fontFamily=SEMI)}],
            "cardTitle": [{"properties": props(color=C(fg), fontSize=8.5, fontFamily=SEMI)}],
            "categoryLabels": [{"properties": props(show=False)}],
            "card": [{"properties": props(outline="None", barShow=False, barWeight=0.0, cardPadding=0.0,
                                          cardBackground=C(bg))}],
        },
        "visualContainerObjects": bp.chrome(panel=True, bg=bg, border=False, radius=9.0, pad=(1, 0, 7, 2)),
    }
    return container(name, x, cy - 10, w, 20, z, visual), w


def kpi(prefix, x, y, w, h, z, title, value_m, sub, accent, icon_kind, pill_m=None, pill_text="", pill_kind="teal",
        value_color=NAVY, title_m=None, sub_is_measure=True):
    v, _ = card(prefix, x, y, w, h, z, accent=accent)
    if title_m:
        v.append(mtxt(f"{prefix}Title", x + P, y + P - 2, w - 2 * P - 26, z + 2, title_m, 10.0, SUB, SEMI))
    else:
        v.append(txt(f"{prefix}Title", x + P, y + P - 2, w - 2 * P - 26, z + 2, title, 10.0, SUB, SEMI))
    v.append(icon(f"{prefix}Icon", x + w - P - 17, y + P - 3, 16, z + 3, icon_name(icon_kind, "kpi")))
    v.append(mtxt(f"{prefix}Value", x + P, y + 40, w - 2 * P, z + 4, value_m, 30.0, value_color, SEMI, h=62))
    sx = x + P
    if pill_m:
        pv, pw = pill(f"{prefix}Pill", sx, y + h - 20, z + 5, pill_m, pill_text, pill_kind)
        v.append(pv)
        sx += pw + 8
    if sub_is_measure:
        v.append(mtxt(f"{prefix}Sub", sx, y + h - 20 - 4, x + w - P - sx, z + 6, sub, 9.0, SUB))
    else:
        v.append(txt(f"{prefix}Sub", sx, y + h - 20 - 4, x + w - P - sx, z + 6, sub, 9.0, SUB))
    return v


def kpi_row(y, specs):
    k = len(specs)
    w = (CW - (k - 1) * GAP) / k
    v = []
    for i, s in enumerate(specs):
        v += kpi(f"kpi{i}", X0 + i * (w + GAP), y, w, KH, 100 + 20 * i, **s)
    return v


# ---------------- page furniture ----------------
def sidebar(n):
    v = [box("sbBg", 0, 0, SB_W, H, 1, NAVY),
         icon("sbLogo", 20, 26, 24, 2, "logo_sun.svg"),
         txt("sbTitle", 52, 27, 150, 3, "Hidden Power Plant", 11.0, "#FFFFFF", SEMI),
         txt("sbSub", 52, 46, 150, 4, "Generator vs solar · Nigeria", 8.0, SB_MUTED)]
    y = 96
    for i, (name, _, kind) in enumerate(PAGES):
        active = i == n
        if active:
            v += [box("sbActive", 0, y, SB_W, 38, 5, SB_ACTIVE), box("sbActiveBar", 0, y, 4, 38, 6, SOLAR)]
        col = "#FFFFFF" if active else SB_TEXT
        v.append(icon(f"sbIcon{i}", 34 - 8, y + 19 - 8, 16, 10 + i, icon_name(kind, "white" if active else "nav")))
        v.append(txt(f"sbText{i}", 56, y + 19 - 9, 140, 20 + i, NAV_LABELS[i], 10.0, col, SEMI if active else FONT))
        if not active:
            btn = {"visualType": "actionButton",
                   "objects": {"icon": [{"properties": props(show=False)}], "text": [{"properties": props(show=False)}],
                               "fill": [{"properties": props(show=False), "selector": {"id": s_}}
                                        for s_ in ("default", "hover", "press")],
                               "outline": [{"properties": props(show=False)}] + [
                                   {"properties": props(show=False), "selector": {"id": s_}}
                                   for s_ in ("default", "hover", "press")]},
                   "visualContainerObjects": {**bp.chrome(), "visualLink": [{"properties": props(
                       show=True, type="PageNavigation", navigationSection=name)}]}}
            v.append(container(f"sbNav{i}", 0, y, SB_W, 38, 40 + i, btn))
        y += 44
    v += [box("sbRule", 20, H - 70, SB_W - 40, 1, 50, SB_ACTIVE),
          mtxt("sbDataTo", 20, H - 56, 170, 51, "Sidebar Data To", 8.5, SB_MUTED, on=NAVY),
          txt("sbBy", 20, H - 38, 170, 52, "By Malik Badmus", 8.5, SB_MUTED)]
    return v


def header(title, takeaway_m):
    return [txt("pageTitle", X0, 22, 700, 60, title, 20.0, NAVY, SEMI),
            mtxt("takeaway", X0, 54, CW, 61, takeaway_m, 11.5, SUB, on=BG)]


def footer():
    return [mtxt("footSources", X0, H - 41, CW, 70, "Footnote", 8.5, FOOT, on=BG),
            txt("footCopy", X0, H - 26, CW, 71, COPYRIGHT, 8.5, FOOT)]


def map_block(prefix, x, y, w, h, z, label_m, title, measure_, display, legend, spread_l1_m, spread_l2, extremes,
              mprefix, value_suffix):
    v, top = card(prefix, x, y, w, h, z, title, label_m=label_m)
    mbox = (x + P, top + 4, w - 2 * P, h - (top - y) - 104)
    v.append(bp.shape_map(f"{prefix}Map", *mbox, z + 10, measure_, display))
    pos = bp.map_label_positions(mbox)
    v += bp.map_labels(prefix, extremes, mprefix, pos, value_suffix)
    lx, lw = x + P + 24, w - 2 * P - 48
    v += bp.legend_bar(prefix, lx, y + h - 78, lw, z + 20, legend[0], legend[1], legend[2], legend[3])
    v.append(mtxt(f"{prefix}Spread1", x + P, y + h - P - 13 - 13, w - 2 * P, z + 30, spread_l1_m, 9.0, FOOT))
    v.append(txt(f"{prefix}Spread2", x + P, y + h - P - 13, w - 2 * P, z + 31, spread_l2, 9.0, FOOT))
    return v


# ---------------- pages ----------------
def page0():
    v = sidebar(0)
    v.append(mtxt("insight", X0, 22, 600, 60, "Label P0 Insight", 9.0, SOLAR, SEMI, on=BG))
    v.append(mtxt("headline2", X0, 68, CW, 62, "Headline P0 2", 19.0, NAVY, SEMI, on=BG))
    v.append(mtxt("headline1", X0, 40, CW, 63, "Headline P0 1", 19.0, NAVY, SEMI, on=BG))
    top = 112
    g, s = mk.KWH_G["household"], mk.KWH_S["household"]
    v += kpi_row(top, [
        dict(title="Generator, ₦ per month", value_m="KPI P1 HH Value", sub="since Jan 2023", sub_is_measure=False,
             accent=GEN, icon_kind="fuel", pill_m="KPI P1 Change Value", pill_text=f"+{mk.HH_CHG:.0f}%",
             pill_kind="red"),
        dict(title="Solar + battery, ₦ per kWh", value_m="KPI P0 Solar Value", sub="KPI P0 Solar Sub", accent=SOLAR,
             icon_kind="sun", pill_m="KPI P0 Solar Pill", pill_text=f"−{mk.GAP_HH.median() * 100:.0f}%"),
        dict(title="Payback now", value_m="KPI P0 Payback Value", sub="KPI P0 Payback Sub", accent=SOLAR,
             icon_kind="clock", pill_m="KPI P0 Payback Pill", pill_text=f"−{mk.PB_PEAK - mk.PB_NOW:.1f} mo"),
        dict(title="Top priority state", value_m="Top Priority State", sub="KPI P0 Top Sub", accent=GRID,
             icon_kind="pin", pill_m="KPI P0 Top Pill", pill_text=f"Top 10 in all {mk.N_VAR}"),
    ])
    y2 = top + KH + GAP
    h2 = BOT - y2
    mw = 400
    v += map_block("p0", X0, y2, mw, h2, 200, "Label P0 Map", "Household payback by state", "Payback HH Now",
                   "Household payback, months", ("Map P3 Min Value", "Map P3 Max Value", "months (central)",
                                                 f"{mk.PB_STATE['central'].max():.1f}"),
                   "Spread Payback L1", "show the differences", bp.P3_EXTREMES, "Map P3", " Label Value")
    fx, fw = X0 + mw + GAP, CW - mw - GAP
    fv, ty = card("find", fx, y2, fw, h2, 400, "What the numbers say", "Key findings")
    v += fv
    blocks = [["Finding 1 L1", "Finding 1 L2", "Finding 1 L3"], ["Finding 2 L1", "Finding 2 L2"],
              ["Finding 3 L1", "Finding 3 L2"]]
    y = ty + 18
    heights = [len(b) * 21 for b in blocks]
    gap = min(64.0, (y2 + h2 - 70 - y - sum(heights)) / (len(blocks) - 1))
    for i, lines in enumerate(blocks, 1):
        badge = textbox(f"findNum{i}", fx + P, y - 1, 24, 24, 410 + i,
                        [para(run(str(i), 11.0, "#FFFFFF", SEMI), align="center")],
                        panel=True, bg=SOLAR, border=True, border_color=SOLAR, radius=12.0, pad=(1, 0, 0, 0))
        v.append(badge)
        for k, m in enumerate(lines):
            v.append(mtxt(f"find{i}L{k}", fx + P + 40, y + k * 21, fw - 2 * P - 40, 420 + 3 * i + k, m, 12.0))
        y += heights[i - 1] + gap
    v.append(box("findRule", fx + P, y2 + h2 - 52, fw - 2 * P, 1, 440, BORDER))
    v.append(textbox("findMethod", fx + P - 4, y2 + h2 - P - 26 - 6, fw - 2 * P + 8, 36, 441, [para(run(
        "Method: a monthly cost model for each state (fuel prices, tariffs, solar resource and system costs); "
        "central estimates with low–high ranges.", 9.0, FOOT))]))
    return v + footer()


def page1():
    v = sidebar(1) + header("The Fuel Shock", "Takeaway P1")
    top = 98
    v += kpi_row(top, [
        dict(title="Household generator, ₦ per month", value_m="KPI P1 HH Value", sub="KPI P1 HH Sub", accent=GEN,
             icon_kind="fuel", pill_m="KPI P1 Change Value", pill_text=f"+{mk.HH_CHG:.0f}%", pill_kind="red"),
        dict(title="Small-business generator, ₦ per month", value_m="KPI P1 BZ Value", sub="KPI P1 BZ Sub",
             accent=GEN, icon_kind="factory", pill_m="KPI P1 BZ Change Value", pill_text=f"+{mk.BZ_CHG:.0f}%",
             pill_kind="red"),
        dict(title="Change since January 2023", value_m="KPI P1 Change Value", sub="KPI P1 Change Sub",
             accent=ALERT, icon_kind="trend", value_color=ALERT),
    ])
    y2 = top + KH + GAP
    h2 = BOT - y2
    mw = 380
    st = mk.GL[mk.GL.user == "household"].set_index("state").running_ngn_per_month
    v += map_block("p1", X0, y2, mw, h2, 200, "Label P1 Map", "Household generator cost by state",
                   "Gen HH Central Now", "Household generator, ₦/month",
                   ("Map P1 Min Value", "Map P1 Max Value", "₦ per month", f"₦{st.max():,.0f}"),
                   "Spread P1 L1", "show the differences", bp.P1_EXTREMES, "Map P1", " Value")
    lx, lw = X0 + mw + GAP, CW - mw - GAP
    cv, ty = card("line", lx, y2, lw, h2, 400, "National median household generator cost, ₦/month", "Trend · central")
    v += cv
    v.append(mtxt("lineNote", lx + P, ty - 4, lw - 2 * P, 402, "Line P1 Note", 9.0, FOOT))
    cx, cy, cw_, ch_ = lx + P, ty + 14, lw - 2 * P - 46, h2 - (ty - y2) - 30
    v.append(bp.line_p1(cx, cy, cw_, ch_))
    px0, px1 = P1_PLOT
    xj = px0 + (px1 - px0) * 5 / 40
    v.append(txt("lineSubsidy", xj + 11, cy + 18, 260, 420, "Jun 2023: petrol subsidy removed", 10.0, ALERT, SEMI))
    return v + footer()


P1_PLOT = (X0 + 380 + GAP + P + 70, X0 + 380 + GAP + 626 - P - 46 - 12)   # x of first/last month (re-measured)


def page2():
    v = sidebar(2) + header("Generator vs Grid vs Solar", "Takeaway P2")
    top = 98
    cw = (CW - GAP) / 2
    ch = BOT - top
    for k, (uc, user) in enumerate((("HH", "household"), ("BZ", "business"))):
        x = X0 + k * (cw + GAP)
        lab = "Household · 2.5 kVA petrol" if user == "household" else "Small business · 20 kVA diesel"
        cv, ty = card(f"c{uc}", x, top, cw, ch, 100 + 100 * k, f"{lab} — ₦ per kWh", label_m="Label P2 Cost")
        v += cv
        z = 110 + 100 * k
        v.append(txt(f"sub{uc}", x + P, ty - 4, cw - 2 * P, z, "5 states with the costliest and 5 with the cheapest "
                                                               "generator power", 9.5, SUB))
        v.append(textbox(f"leg1{uc}", x + P - 4, ty + 20 - 10, cw - 2 * P, bp.text_h(9.5), z + 1, [para(
            run("■ ", 10.0, GEN), run("Generator      ", 9.5, SUB), run("■ ", 10.0, SOLAR),
            run("Solar + battery", 9.5, SUB))]))
        v.append(textbox(f"leg2{uc}", x + P - 4, ty + 38 - 10, cw - 2 * P, bp.text_h(9.5), z + 2, [para(
            run("| ", 10.0, GRID, SEMI), run("Grid tariff: price reference only      ", 9.5, SUB),
            run("◇ ", 10.0, GRID, SEMI), run("state-set tariff", 9.5, SUB))]))
        gmax = bp.GMAX[user]
        bx, by, bw, bh = x + P, ty + 66, cw - 2 * P - 16, ch - (ty - top) - 66 - 44
        v.append(bp.bars_p2(uc, bx, by, bw, bh, gmax))
        x0_, x1_ = P2_PLOT[uc]
        end = round(gmax * 1.18)
        v.append(mcard(f"bandA{uc}", x0_ + (x1_ - x0_) * bp.BAND_A / end + 3, by - 16, 110, z + 5,
                       "Ref P2 Band A Label", 8.5, GRID))
        wb = text_w(f"Band B ₦{bp.BAND_B:,.0f}", 8.5) + 6
        v.append(mcard(f"bandB{uc}", x0_ + (x1_ - x0_) * bp.BAND_B / end - wb - 3, by - 16, wb + 8, z + 6,
                       "Ref P2 Band B Label", 8.5, GRID))
        v.append(mtxt(f"range{uc}", x + P, top + ch - P - 15, cw - 2 * P, z + 7, f"Range P2 {uc}", 9.5, SUB))
    return v + footer()


P2_PLOT = {"HH": (326.0, 681.0), "BZ": (845.0, 1174.0)}   # canvas x of value 0 and of the axis end (measured)


def page3():
    v = sidebar(3) + header("Payback", "Takeaway P3")
    top = 98
    v += kpi_row(top, [
        dict(title="Household payback now", value_m="KPI P3 Now Value", sub="KPI P3 Now Sub", accent=SOLAR,
             icon_kind="clock", pill_m="KPI P3 Now Pill", pill_text=f"−{mk.PB_PEAK - mk.PB_NOW:.1f} mo vs peak"),
        dict(title="At the start, June 2023", value_m="KPI P3 Start Value", sub="KPI P3 Start Sub", accent=SOLAR,
             icon_kind="sun"),
        dict(title=None, title_m="KPI P3 Peak Title", value_m="KPI P3 Peak Value", value_color=ALERT,
             sub="naira fall raised solar costs", sub_is_measure=False, accent=ALERT, icon_kind="trend",
             pill_m="KPI P3 Peak Pill", pill_text=f"+{mk.PB_PEAK - mk.PB_START:.1f} mo", pill_kind="red"),
    ])
    y2 = top + KH + GAP
    h2 = BOT - y2
    mw, lw = 300, 360
    aw = CW - mw - lw - 2 * GAP
    v += map_block("p3", X0, y2, mw, h2, 200, "Label P3 Map", "Household payback by state", "Payback HH Now",
                   "Household payback, months", ("Map P3 Min Value", "Map P3 Max Value", "months (central)",
                                                 f"{mk.PB_STATE['central'].max():.1f}"),
                   "Spread Payback Narrow L1", "is stretched to show the differences", bp.P3_EXTREMES, "Map P3",
                   " Label Value")
    lx = X0 + mw + GAP
    cv, ty = card("line", lx, y2, lw, h2, 400, "Payback over time, months", "Trend · median of states, central")
    v += cv
    cx, cy, cw_, ch_ = lx + P, ty + 4, lw - 2 * P - 72, h2 - (ty - y2) - 24
    v.append(bp.line_p3(cx, cy, cw_, ch_))
    px0, px1, py0, py1 = P3_PLOT
    ymax = bp.P3_YMAX
    to_xy = lambda i, val: (px0 + (px1 - px0) * i / (len(bp.P3_MONTHS) - 1),  # noqa: E731
                            py0 - (py0 - py1) * val / ymax)
    pk_x, pk_y = to_xy(bp.P3_MONTHS.index(bp.P3_PEAK), mk.PB_PEAK)
    v.append(mtxt("peak1", pk_x + 6, pk_y - 40, 170, 420, "Label P3 Peak 1", 9.0, ALERT, SEMI))
    v.append(mtxt("peak2", pk_x + 6, pk_y - 26, 170, 421, "Label P3 Peak 2", 9.0, ALERT, SEMI))
    ex, ey = to_xy(len(bp.P3_MONTHS) - 1, float(mk.PC["household"].iloc[-1]))
    _, eyb = to_xy(len(bp.P3_MONTHS) - 1, float(mk.PC["business"].iloc[-1]))
    v.append(mtxt("lblHHEnd", ex + 4, ey - 16, 88, 422, "Label P3 HH End", 9.0, "#B45309", SEMI))
    v.append(mtxt("lblBZEnd", ex + 4, eyb + 2, 88, 423, "Label P3 BZ End", 9.0, GEN, SEMI))
    ax_ = lx + lw + GAP
    cv, ty = card("aff", ax_, y2, aw, h2, 500, "Upfront cost ÷ monthly spending", "Affordability · households")
    v += cv
    v.append(bp.afford_bars(ax_ + P, ty, aw - 2 * P, h2 - (ty - y2) - 44))
    v.append(mtxt("affNote", ax_ + P, y2 + h2 - P - 14, aw - 2 * P, 520, "Note P3 Afford", 9.0, SUB))
    return v + footer()


P3_PLOT = (627.0, 803.0, 625.0, 625.0 - 9.77 * bp.P3_YMAX)   # x first/last month, y of 0 and of the axis top (measured)


def top10_table(x, y, w, h):
    # rank is a column (dim_state[priority_rank]) placed first: the table's default sort is then by rank,
    # with no sort arrow in the header
    cols = [("@priority_rank", "Rank", 40.0, "left"), (None, "State", 100.0, "left"),
            ("All 12 Dot", " ", 20.0, "left"), ("Saving HH Now", "Saving ₦/month", 108.0, "right"),
            ("Payback HH Now Text", "Payback, months", 112.0, "right"),
            ("Upfront HH Now Text", "Upfront ÷ spending", 124.0, "right")]
    projs, widths, fmt = [], [], []
    for m, disp, wd, al in cols:
        if m is None:
            pr = bp.c_proj("dim_state", "state", disp)
        elif m.startswith("@"):
            pr = bp.c_proj("dim_state", m[1:], disp)
        else:
            pr = m_proj(m, disp)
        projs.append(pr)
        sel = {"metadata": pr["queryRef"]}
        widths.append({"properties": props(value=wd), "selector": sel})
        f = {"alignment": lit("Right" if al == "right" else "Left")}
        if m == "All 12 Dot":
            f["fontColor"] = color(GRID)
        fmt.append({"properties": f, "selector": sel})
    visual = {
        "visualType": "tableEx",
        "query": {"queryState": {"Values": {"projections": projs}}},
        "objects": {
            "columnHeaders": [{"properties": props(fontColor=C(SUB), backColor=C(CARD), fontSize=9.5,
                                                   fontFamily=SEMI, wordWrap=False, outline="BottomOnly",
                                                   outlineColor=C(BORDER))}],
            "values": [{"properties": props(fontColor=C(NAVY), backColor=C(CARD), backColorSecondary=C(CARD),
                                            fontColorSecondary=C(NAVY), fontSize=10.0, fontFamily=FONT,
                                            wordWrap=False, outline="None")}],
            "grid": [{"properties": props(gridHorizontal=True, gridHorizontalColor=C(BORDER), gridHorizontalWeight=1.0,
                                          gridVertical=False, rowPadding=11.0, outlineColor=C(CARD),
                                          textSize=10.0)}],
            "total": [{"properties": props(totals=False)}],
            "columnWidth": widths,
            "columnFormatting": fmt,
        },
        "visualContainerObjects": bp.chrome(),
    }
    return container("top10Table", x, y, w, h, 620, visual,
                     filter_config={"filters": [bp.top_n_filter("fTop10", "dim_state", "state", "Priority Index",
                                                                10)]})


def page4():
    v = sidebar(4) + header("Where to Go Next", "Takeaway P4")
    top = 98
    ch = BOT - top
    lw = 460
    cv, ty = card("bars", X0, top, lw, ch, 400, label_="Ranking", title_m="Card P4 Bars Title")
    v += cv
    v.append(bp.priority_bars(X0 + P, ty, lw - 2 * P - 40, ch - (ty - top) - 96))
    bp.P4_PLOT = P4_PLOT
    v += [bp.badge(i, st) for i, st in enumerate(bp.P4_ALL12)]
    v.append(textbox("indexNote", X0 + P - 4, top + ch - P - 58 - 6, lw - 2 * P + 8, 70, 450, [para(run(
        "How the index is built: geometric mean of percentile ranks of generator reliance (NLSS 2018/19), monthly ₦ "
        "saving from switching, and ability to pay (1 − MPI 2022). Shown as ranks, not precise scores. All 12 = top "
        "10 under all 3 weightings × 2 users × 2 reliance measures.", 8.5, SUB))]))
    tx, tw = X0 + lw + GAP, CW - lw - GAP
    cv, ty = card("tab", tx, top, tw, ch, 600, label_="Top 10 · central, payback low–high",
                  title_m="Card P4 Table Title")
    v += cv
    v.append(top10_table(tx + P, ty + 2, tw - 2 * P, ch - (ty - top) - 44))
    v.append(txt("tabNote", tx + P, top + ch - P - 15, tw - 2 * P, 640, "● top 10 under all 12 index variants", 9.0,
                 GRID))
    return v + footer()


P4_PLOT = (351.0, 351.0 + 239.0 * 1.15, 181.0, 531.0)   # x of value 0 and of 1.15; y of the first and last bar centre (measured)
BUILDERS = [page0, page1, page2, page3, page4]


def page_json(name, display):
    return {"$schema": bp.PAGE_SCHEMA, "name": name, "displayName": display, "displayOption": "FitToPage",
            "height": H, "width": W,
            "objects": {"background": [{"properties": {"color": color(BG), "transparency": lit(0.0)}}],
                        "outspace": [{"properties": {"color": color(BG), "transparency": lit(0.0)}}]}}


def main():
    bp.write_legend_image()
    bp.register_resources()
    register(write_icons())
    if STAGING.parent.exists():
        shutil.rmtree(STAGING.parent)
    bp.write(PAGES_DIR / "pages.json", {"$schema": bp.PAGES_SCHEMA, "pageOrder": [n for n, _, _ in PAGES],
                                        "activePageName": PAGES[0][0]})
    for (name, display, _), build in zip(PAGES, BUILDERS):
        bp.write(PAGES_DIR / name / "page.json", page_json(name, display))
        visuals = build()
        for k, vc in enumerate(visuals):          # stacking order = order added (cards first, contents on top)
            vc["position"]["z"] = (k + 1) * 10
            vc["position"]["tabOrder"] = (k + 1) * 10
        names = [vc["name"] for vc in visuals]
        dup = {n_ for n_ in names if names.count(n_) > 1}
        assert not dup, f"duplicate visual names on {display}: {dup}"
        for vc in visuals:
            p_ = vc["position"]
            assert -0.5 <= p_["x"] and p_["x"] + p_["width"] <= W + 0.5, (display, vc["name"], "x", p_)
            assert -0.5 <= p_["y"] and p_["y"] + p_["height"] <= H + 0.5, (display, vc["name"], "y", p_)
            bp.write(PAGES_DIR / name / "visuals" / vc["name"] / "visual.json", vc)
    import pbir_validate
    model_def = HERE / "report" / "HiddenPowerPlant.SemanticModel" / "definition"
    if pbir_validate.main([str(PAGES_DIR), "--model", str(model_def)]):
        sys.exit("validation failed; report not changed")
    dest = bp.REPORT / "definition" / "pages"
    shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(PAGES_DIR, dest)
    print(f"pages written: {len(PAGES)}; files: {sum(1 for _ in dest.rglob('*.json'))}")


if __name__ == "__main__":
    main()
