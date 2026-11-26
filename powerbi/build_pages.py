"""Write the 4 report pages (PBIR JSON) of the HiddenPowerPlant dashboard.

Layout, titles, takeaways, footnotes and colours follow the approved mockups (src/mockups.py,
figures/mockups/page1-4.png). Every number comes from a DAX measure in model_spec.py.
Each series colour has its own measure; colours are fixed per series, never field-value rules.
Run with Power BI Desktop closed; pages are written to pbir_staging/, validated, then copied
into report/HiddenPowerPlant.Report/definition/.
Usage: python powerbi/build_pages.py
"""
from __future__ import annotations

import json
import math
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = ROOT / "data" / "processed" / "powerbi"
REPORT = HERE / "report" / "HiddenPowerPlant.Report"
STAGING = HERE / "pbir_staging" / "definition"
PAGES_DIR = STAGING / "pages"
RES = REPORT / "StaticResources" / "RegisteredResources"

SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition"
PAGE_SCHEMA = f"{SCHEMA}/page/2.1.0/schema.json"
PAGES_SCHEMA = f"{SCHEMA}/pagesMetadata/1.0.0/schema.json"
VC_SCHEMA = f"{SCHEMA}/visualContainer/2.8.0/schema.json"

# ---- design system (src/mockups.py) ----
W, H = 1280, 720
BG, CARD, BORDER = "#F6F7F9", "#FFFFFF", "#E5E7EB"
NAVY, SUB, FOOT = "#0F1B2D", "#4B5563", "#6B7280"
SOLAR, GEN, GRID, ALERT, GRIDLINE = "#F59E0B", "#475569", "#0D9488", "#DC2626", "#E5E7EB"
BAND = "#F1F5F9"
SEQ_LO, SEQ_HI = "#FEF3C7", "#B45309"
M, GAP, R = 24, 16, 8.0
FONT = "'Segoe UI', wf_segoe-ui_normal, helvetica, arial, sans-serif"
SEMI = "'Segoe UI Semibold', wf_segoe-ui_semibold, helvetica, arial, sans-serif"

PAGES = [("p1_fuel_shock", "1  The Fuel Shock", "The Fuel Shock"),
         ("p2_gen_grid_solar", "2  Generator vs Grid vs Solar", "Generator vs Grid vs Solar"),
         ("p3_payback", "3  Payback", "Payback"),
         ("p4_where_next", "4  Where to Go Next", "Where to Go Next")]
MAP_NAME = "nigeria_states_geoboundaries.json"
LEGEND_IMG = "legend_amber_seq.png"


def text_h(pt: float, lines: int = 1) -> int:
    return math.ceil(pt * 4 / 3 * 1.35 * lines) + 6


# ---------- expression helpers ----------
def lit_value(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return f"{v}L"
    if isinstance(v, float):
        return f"{v}D"
    return "'" + str(v).replace("'", "''") + "'"


def lit(v):
    return {"expr": {"Literal": {"Value": lit_value(v)}}}


def color(hex_):
    return {"solid": {"color": lit(hex_)}}


def C(h):
    return "@" + h


def props(**kw):
    out = {}
    for k, v in kw.items():
        if isinstance(v, str) and v.startswith("@#"):
            out[k] = color(v[1:])
        elif isinstance(v, dict):
            out[k] = v
        else:
            out[k] = lit(v)
    return out


def measure(name, source=None):
    ref = {"Source": source} if source else {"Entity": "_Measures"}
    return {"Measure": {"Expression": {"SourceRef": ref}, "Property": name}}


def mexpr(name):
    return {"expr": measure(name)}


def column(table, col):
    return {"Column": {"Expression": {"SourceRef": {"Entity": table}}, "Property": col}}


def proj(field, query_ref, display=None):
    p = {"field": field, "queryRef": query_ref, "nativeQueryRef": query_ref.split(".", 1)[1]}
    if display:
        p["displayName"] = display
    return p


def m_proj(name, display=None):
    return proj(measure(name), f"_Measures.{name}", display)


def c_proj(table, col, display=None):
    return proj(column(table, col), f"{table}.{col}", display)


def meta(name):
    return {"metadata": f"_Measures.{name}"}


def resource(item):
    return {"expr": {"ResourcePackageItem": {"PackageName": "RegisteredResources", "PackageType": 1,
                                             "ItemName": item}}}


def top_n_filter(name, table, col, m, n, ascending=False):
    return {
        "name": name, "field": column(table, col), "type": "TopN",
        "filter": {"Version": 2, "From": [
            {"Name": "subquery", "Expression": {"Subquery": {"Query": {
                "Version": 2,
                "From": [{"Name": "d", "Entity": table, "Type": 0}, {"Name": "m", "Entity": "_Measures", "Type": 0}],
                "Select": [{"Column": {"Expression": {"SourceRef": {"Source": "d"}}, "Property": col},
                            "Name": "field"}],
                "OrderBy": [{"Direction": 1 if ascending else 2, "Expression": measure(m, source="m")}],
                "Top": n}}}, "Type": 2},
            {"Name": "d", "Entity": table, "Type": 0}],
            "Where": [{"Condition": {"In": {
                "Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "d"}}, "Property": col}}],
                "Table": {"SourceRef": {"Source": "subquery"}}}}}]},
        "howCreated": "User"}


# ---------- containers ----------
def chrome(panel=False, bg=CARD, border=True, border_color=BORDER, radius=R, pad=(0, 0, 0, 0)):
    return {
        "background": [{"properties": props(show=panel, color=C(bg), transparency=0.0)}],
        "border": [{"properties": props(show=panel and border, color=C(border_color), radius=radius, width=1.0)}],
        "dropShadow": [{"properties": props(show=False)}],
        "visualHeader": [{"properties": props(show=False)}],
        "padding": [{"properties": props(top=float(pad[0]), bottom=float(pad[1]), left=float(pad[2]),
                                         right=float(pad[3]))}],
        "title": [{"properties": props(show=False)}],
        "subTitle": [{"properties": props(show=False)}],
    }


def container(name, x, y, w, h, z, visual, filter_config=None):
    vc = {"$schema": VC_SCHEMA, "name": name,
          "position": {"x": round(x, 1), "y": round(y, 1), "z": z, "height": round(h, 1), "width": round(w, 1),
                       "tabOrder": z},
          "visual": visual}
    if filter_config:
        vc["filterConfig"] = filter_config
    return vc


def run(text, size=10.0, color_=NAVY, font=FONT):
    return {"value": text, "textStyle": {"fontFamily": font, "fontSize": f"{size}pt", "color": color_}}


def para(*runs, align="left"):
    return {"textRuns": list(runs), "horizontalTextAlignment": align}


def textbox(name, x, y, w, h, z, paragraphs, panel=False, bg=CARD, border=True, border_color=BORDER, radius=R,
            pad=(0, 0, 0, 0)):
    visual = {"visualType": "textbox", "objects": {"general": [{"properties": {"paragraphs": paragraphs}}]},
              "visualContainerObjects": chrome(panel, bg, border, border_color, radius, pad)}
    return container(name, x, y, w, h, z, visual)


def label(name, x, y, w, z, text, size, color_=NAVY, font=FONT, align="left", lines=1):
    return textbox(name, x, y, w, text_h(size, lines), z, [para(run(text, size, color_, font), align=align)])


def card_box(name, x, y, w, h, z):
    """White card with #E5E7EB border, radius 8."""
    return textbox(name, x, y, w, h, z, [para(run(" ", 1.0))], panel=True)


def mcard(name, x, y, w, z, m, size, color_=NAVY, font=FONT, align="left", lines=1, h=None, bg=None, on=CARD):
    """Measure text shown as plain text (multi-row card, no labels, no chrome). A text field is drawn as
    the card title, so cardTitle and dataLabels get the same style. Multi-row cards are left-aligned only:
    for align='center'/'right' the box is narrowed to the estimated text width and shifted."""
    style = props(color=C(color_), fontSize=float(size), fontFamily=font)
    visual = {
        "visualType": "multiRowCard",
        "query": {"queryState": {"Values": {"projections": [m_proj(m)]}}},
        "objects": {
            "dataLabels": [{"properties": style}],
            "cardTitle": [{"properties": style}],
            "categoryLabels": [{"properties": props(show=False)}],
            "card": [{"properties": props(outline="None", barShow=False, barWeight=0.0, cardPadding=0.0,
                                          cardBackground=C(bg or on))}],
        },
        "visualContainerObjects": {**chrome(panel=bool(bg), bg=bg or CARD, border=False, radius=4.0),
                                   **({} if bg else {"background": [{"properties": props(show=False)}]})},
    }
    return container(name, x, y, w, h or text_h(size, lines) + 4, z, visual)


def text_w(text: str, pt: float, semi=False) -> float:
    """Approximate rendered width in px of Segoe UI text."""
    return len(text) * pt * 4 / 3 * (0.56 if semi else 0.53)


def image(name, x, y, w, h, z, item):
    visual = {"visualType": "image",
              "objects": {"general": [{"properties": {"imageUrl": resource(item)}}],
                          "imageScaling": [{"properties": props(imageScalingType="Fill")}]},
              "visualContainerObjects": chrome()}
    return container(name, x, y, w, h, z, visual)


# ---------- page furniture ----------
def tabs(current):
    v, x = [], W - M
    widths = [len(t) * 6.3 + 24 for _, t, _ in PAGES]
    for i in reversed(range(len(PAGES))):
        name, text, _ = PAGES[i]
        w = widths[i]
        x -= w
        active = name == current
        v.append(textbox(f"tab{i + 1}", x, M, w, 26, 900 + i,
                         [para(run(text, 9.0, "#FFFFFF" if active else SUB, SEMI if active else FONT),
                               align="center")],
                         panel=True, bg=NAVY if active else CARD, border_color=NAVY if active else BORDER,
                         pad=(4, 0, 0, 0)))
        if not active:
            btn = {"visualType": "actionButton",
                   "objects": {"icon": [{"properties": props(show=False)}],
                               "text": [{"properties": props(show=False)}],
                               "fill": [{"properties": props(show=False), "selector": {"id": s}}
                                        for s in ("default", "hover", "press")],
                               "outline": [{"properties": props(show=False)}] + [
                                   {"properties": props(show=False), "selector": {"id": s}}
                                   for s in ("default", "hover", "press")]},
                   "visualContainerObjects": {**chrome(), "visualLink": [{"properties": props(
                       show=True, type="PageNavigation", navigationSection=name)}]}}
            v.append(container(f"tabNav{i + 1}", x, M, w, 26, 950 + i, btn))
        x -= 8
    return v


def header(page, title, takeaway_measure):
    return ([label("pageTitle", M - 4, M - 6, 640, 10, title, 22.0, NAVY, SEMI),
             mcard("takeaway", M - 4, M + 33, W - 2 * M + 8, 11, takeaway_measure, 13.0, SUB, on=BG)]
            + tabs(page)
            + [mcard("footnote", M - 4, H - M - 13, 1180, 12, "Footnote", 9.0, FOOT, on=BG)])


# ---------- data-derived axis limits (same rules as the mockups) ----------
gen = pd.read_csv(DATA / "fact_generator_cost.csv", dtype={"month": str})
NAT_HH = gen[gen.user == "household"].groupby(["case", "month"]).running_ngn_per_month.median().unstack("case")
YCAP_P1 = float(round(NAT_HH["central"].max() * 1.9))


# ---------- visuals ----------
def kpi(prefix, x, y, w, h, title_m, value_m, sub_m, value_color=NAVY, title_text=None):
    v = [card_box(f"{prefix}Card", x, y, w, h, 100)]
    if title_text:
        v.append(label(f"{prefix}Title", x + GAP - 4, y + GAP - 6, w - 2 * GAP, 101, title_text, 12.0, NAVY, SEMI))
    else:
        v.append(mcard(f"{prefix}Title", x + GAP - 4, y + GAP - 6, w - 2 * GAP, 101, title_m, 12.0, NAVY, SEMI))
    v.append(mcard(f"{prefix}Value", x + GAP - 4, y + GAP + 14, w - 2 * GAP, 102, value_m, 28.0, value_color, SEMI))
    v.append(mcard(f"{prefix}Sub", x + GAP - 4, y + h - GAP - 18, w - 2 * GAP, 103, sub_m, 10.0, SUB))
    return v


def shape_map(name, x, y, w, h, z, m, display):
    geo = {"geoJson": {"type": lit("packaged"), "name": lit(MAP_NAME.removesuffix(".json")),
                       "content": resource(MAP_NAME)}}
    visual = {
        "visualType": "shapeMap",
        "query": {"queryState": {
            "Category": {"projections": [c_proj("dim_state", "state", "State")]},
            "Value": {"projections": [m_proj(m, display)]},
        }},
        "objects": {
            "shape": [{"properties": {"map": geo, "projectionEnum": lit("mercator")}}],
            "dataPoint": [{"properties": {"fillRule": {"linearGradient2": {
                "min": {"color": lit(SEQ_LO)}, "max": {"color": lit(SEQ_HI)},
                "nullColoringStrategy": {"strategy": lit("asZero")}}}},
                }],
            "defaultColors": [{"properties": props(defaultShow=True, defaultColor=C("#E5E7EB"),
                                                   borderColor=C("#FFFFFF"), borderThickness=0.6)}],
            "legend": [{"properties": props(show=False)}],
            "zoom": [{"properties": props(autoZoom=True, selectionZoom=False, manualZoom=False)}],
        },
        "visualContainerObjects": chrome(),
    }
    return container(name, x, y, w, h, z, visual)


def legend_bar(prefix, x, y, w, z, min_m, max_m, unit, max_text=""):
    return [image(f"{prefix}LegendBar", x, y, w, 8, z, LEGEND_IMG),
            mcard(f"{prefix}LegendMin", x - 4, y + 10, 120, z + 1, min_m, 9.0, SUB),
            label(f"{prefix}LegendUnit", x + w / 2 - 80, y + 10, 160, z + 2, unit, 9.0, SUB, align="center"),
            mcard(f"{prefix}LegendMax", x + w - text_w(max_text, 9.0) - 2, y + 10, text_w(max_text, 9.0) + 16, z + 3,
                  max_m, 9.0, SUB)]


def page1(page):
    v = header(page, "The Fuel Shock", "Takeaway P1")
    top, kw = 104, (W - 2 * M - 2 * GAP) / 3
    v += kpi("kpiHH", M, top, kw, 110, "KPI P1 HH Title", "KPI P1 HH Value", "KPI P1 HH Sub")
    v += kpi("kpiBZ", M + kw + GAP, top, kw, 110, "KPI P1 BZ Title", "KPI P1 BZ Value", "KPI P1 BZ Sub")
    v += kpi("kpiChg", M + 2 * (kw + GAP), top, kw, 110, None, "KPI P1 Change Value", "KPI P1 Change Sub",
             ALERT, title_text="Change since January 2023")

    y2 = top + 110 + GAP
    h2 = H - M - 22 - y2
    mw = 470
    v.append(card_box("mapCard", M, y2, mw, h2, 200))
    v.append(mcard("mapTitle", M + GAP - 4, y2 + GAP - 6, mw - 2 * GAP, 201, "Map P1 Title", 12.0, NAVY, SEMI))
    v.append(shape_map("mapP1", M + GAP, y2 + 40, mw - 2 * GAP, h2 - 112, 210, "Gen HH Central Now",
                       "Household generator, ₦/month"))
    v += legend_bar("p1", M + GAP + 60, y2 + h2 - 62, mw - 2 * GAP - 120, 220, "Map P1 Min Value",
                    "Map P1 Max Value", "₦ per month", P1_EXTREMES["Max"][1])
    v.append(mcard("mapSpread", M + GAP - 4, y2 + h2 - 26, mw - GAP, 230, "Map P1 Spread Note", 9.0, FOOT))
    v += map_labels("p1", P1_EXTREMES, "Map P1")

    lx = M + mw + GAP
    lw = W - M - lx
    v.append(card_box("lineCard", lx, y2, lw, h2, 300))
    v.append(label("lineTitle", lx + GAP - 4, y2 + GAP - 6, lw - 2 * GAP, 301,
                   "National median household generator cost, ₦/month (central and low–high band)", 12.0, NAVY,
                   SEMI))
    v.append(mcard("lineNote", lx + GAP - 4, y2 + 34, lw - 2 * GAP, 302, "Line P1 Note", 9.0, FOOT))
    v.append(line_p1(lx + GAP, y2 + 56, lw - 2 * GAP - 40, h2 - 64))
    v.append(label("lineSubsidy", lx + GAP + 136, y2 + 66, 260, 320, "Jun 2023: petrol subsidy removed", 10.0,
                   ALERT, SEMI))
    return v


def map_labels(prefix, extremes, mprefix, pos=None, value_suffix=" Value"):
    """Two-line labels (state, value) on a white chip, centred on the state's position on the map.
    extremes: {'Max': (state, value text), 'Min': (...)} computed from the data (positioning only; the text
    itself comes from the measures)."""
    v = []
    for tag, (state, value_text) in extremes.items():
        lx, ly = (pos or MAP_LABEL_POS)[state]
        w = max(text_w(state, 8.0, True), text_w(value_text, 8.0, True)) + 8
        v.append(mcard(f"{prefix}Lbl{tag}State", lx - w / 2, ly - 16, w, 240, f"{mprefix} {tag} State", 8.0, NAVY,
                       SEMI, h=16, bg=CARD))
        v.append(mcard(f"{prefix}Lbl{tag}Value", lx - w / 2, ly - 1, w, 241, f"{mprefix} {tag}{value_suffix}", 8.0, NAVY,
                       SEMI, h=16, bg=CARD))
    return v


_st = gen[(gen.user == "household") & (gen.case == "central") & (gen.month == gen.month.max())]
_st = _st.set_index("state").running_ngn_per_month
P1_EXTREMES = {"Max": (_st.idxmax(), f"₦{_st.max():,.0f}"), "Min": (_st.idxmin(), f"₦{_st.min():,.0f}")}


MAP_LABEL_POS = {}  # filled in main() from the TopoJSON (screen position of a state's label)


def error_range(series, upper, lower, band=False, bar_color=GEN):
    """Power BI error bars on one series (format read back from Power BI Desktop's own save).
    band=True: shaded #F1F5F9 low-high band (lines); False: whiskers (bars)."""
    style = (props(enabled=True, barShow=False, shadeShow=True, shadeMatchSeriesColor=False, shadeColor=C(BAND),
                   shadeTransparency=0.0, markerShow=False, labelShow=False, tooltipShow=True) if band else
             props(enabled=True, barShow=True, barMatchSeriesColor=False, barColor=C(bar_color), barWidth=1.0,
                   barBorderSize=0, shadeShow=False, markerShow=False, labelShow=False, tooltipShow=True))
    return [{"properties": style, "selector": meta(series)},
            {"properties": {"errorRange": {"kind": "ErrorRange", "explicit": {
                "isRelative": lit(False), "lowerBound": mexpr(lower), "upperBound": mexpr(upper)}}},
             "selector": {"data": [{"dataViewWildcard": {"matchingOption": 0}}], **meta(series),
                          "highlightMatching": 1}}]


def line_p1(x, y, w, h):
    central, pts = "Gen HH Central", "Gen HH Label Points"
    visual = {
        "visualType": "lineChart",
        "query": {"queryState": {
            "Category": {"projections": [c_proj("dim_month", "date", "Month")]},
            "Y": {"projections": [m_proj(central, "Central"), m_proj(pts, "Label")]},
        },
            "sortDefinition": {"sort": [{"field": column("dim_month", "date"), "direction": "Ascending"}],
                               "isDefaultSort": False}},
        "objects": {
            "categoryAxis": [{"properties": props(axisType="Scalar", show=True, showAxisTitle=False,
                                                  labelColor=C(SUB), fontSize=10.0, fontFamily=FONT,
                                                  gridlineShow=False)}],
            "valueAxis": [{"properties": props(show=True, showAxisTitle=False, start=0.0, end=YCAP_P1, labelDisplayUnits=1.0,
                                               labelColor=C(SUB), fontSize=10.0, fontFamily=FONT,
                                               gridlineShow=True, gridlineColor=C(GRIDLINE),
                                               gridlineStyle="solid")}],
            "legend": [{"properties": props(show=False)}],
            "dataPoint": [{"properties": {"fill": color(GEN)}, "selector": meta(central)},
                          {"properties": {"fill": color(GEN)}, "selector": meta(pts)}],
            "lineStyles": [
                {"properties": props(strokeWidth=3.0, showMarker=False, lineStyle="solid"),
                 "selector": meta(central)},
                {"properties": props(strokeWidth=0.0, showMarker=False), "selector": meta(pts)}],
            "labels": [{"properties": props(show=True, color=C(GEN), fontSize=10.0, fontFamily=FONT,
                                            labelDisplayUnits=1.0, labelPosition="Right")},
                       {"properties": props(showSeries=False), "selector": meta(central)},
                       {"properties": props(showSeries=True), "selector": meta(pts)}],
            "error": error_range(central, "Gen HH High", "Gen HH Low", band=True),
            "xAxisReferenceLine": [{"properties": {
                "show": lit(True), "displayName": lit("Petrol subsidy removed"),
                "value": {"expr": {"Literal": {"Value": "datetime'2023-06-01T00:00:00'"}}},
                "lineColor": color(ALERT), "transparency": lit(0.0), "style": lit("dashed"),
                "width": lit(1.0), "position": lit("front"), "dataLabelShow": lit(False)},
                "selector": {"id": "1"}}],
        },
        "visualContainerObjects": chrome(),
    }
    return container("lineP1", x, y, w, h, 310, visual)


# ---------------- page 2 ----------------
_tar = pd.read_csv(DATA / "fact_grid_tariff.csv", dtype={"month": str})
_tl = _tar[_tar.month == _tar.month.max()]
BAND_A = float(_tl[_tl.band == "A"].tariff_ngn_per_kwh.median())
BAND_B = float(_tl[_tl.band == "B"].tariff_ngn_per_kwh.median())
_gl = gen[(gen.month == gen.month.max()) & (gen.case == "central")]
GMAX = {u: float(_gl[_gl.user == u].running_ngn_per_kwh.max()) for u in ("household", "business")}


def ref_line(idx, value, text, style, h_pos):
    return {"properties": {
        "show": lit(True), "displayName": lit(text), "value": lit(float(value)), "lineColor": color(GRID),
        "transparency": lit(0.0), "style": lit(style), "width": lit(1.5), "position": lit("front"),
        "dataLabelShow": lit(False)},
        "selector": {"id": str(idx)}}


def bars_p2(uc, x, y, w, h, gmax):
    t, g, sol = f"P2 Rows {uc}", f"P2 Gen {uc} Row", f"P2 Solar {uc} Row"
    visual = {
        "visualType": "clusteredBarChart",
        "query": {"queryState": {
            "Category": {"projections": [c_proj(t, "row_label", "State")]},
            "Y": {"projections": [m_proj(g, "Generator"), m_proj(sol, "Solar + battery")]},
        },
            "sortDefinition": {"sort": [{"field": column(t, "row_label"), "direction": "Ascending"}],
                               "isDefaultSort": False}},
        "objects": {
            "categoryAxis": [{"properties": props(show=True, showAxisTitle=False, labelColor=C(NAVY), fontSize=10.0,
                                                  fontFamily=FONT, innerPadding=28.0, concatenateLabels=False)}],
            "valueAxis": [{"properties": props(show=True, showAxisTitle=False, start=0.0, end=round(gmax * 1.18),
                                               labelColor=C(SUB), fontSize=10.0, fontFamily=FONT,
                                               labelDisplayUnits=1.0, gridlineShow=True, gridlineColor=C(GRIDLINE),
                                               gridlineStyle="solid")}],
            "legend": [{"properties": props(show=False)}],
            "dataPoint": [{"properties": {"fill": color(GEN)}, "selector": meta(g)},
                          {"properties": {"fill": color(SOLAR)}, "selector": meta(sol)}],
            "labels": [{"properties": props(show=True, fontSize=9.0, fontFamily=FONT, labelDisplayUnits=1.0,
                                            labelPosition="OutsideEnd")},
                       {"properties": props(color=C(GEN)), "selector": meta(g)},
                       {"properties": props(color=C(NAVY)), "selector": meta(sol)}],
            "y1AxisReferenceLine": [ref_line(1, BAND_A, f"Band A ₦{BAND_A:,.2f}", "solid", "right"),
                                    ref_line(2, BAND_B, f"Band B ₦{BAND_B:,.0f}", "dashed", "left")],
        },
        "visualContainerObjects": chrome(),
    }
    return container(f"bars{uc}", x, y, w, h, 120, visual)


P2_PLOT = {"HH": (112.0, 112.0 + (567 - 112) * 3086 / 3000), "BZ": (736.0, 736.0 + (1102 - 736) * 1920 / 1500)}


def page2(page):
    v = header(page, "Generator vs Grid vs Solar", "Takeaway P2")
    top = 104
    cw, ch = (W - 2 * M - GAP) / 2, H - M - 22 - top
    for k, (uc, user) in enumerate((("HH", "household"), ("BZ", "business"))):
        x = M + k * (cw + GAP)
        v.append(card_box(f"card{uc}", x, top, cw, ch, 100))
        v.append(mcard(f"title{uc}", x + GAP - 4, top + GAP - 6, cw - 2 * GAP, 101, f"Card P2 {uc} Title", 12.0,
                       NAVY, SEMI))
        v.append(label(f"sub{uc}", x + GAP - 4, top + 36, cw - 2 * GAP, 102,
                       "5 states with the costliest and 5 with the cheapest generator power", 10.0, SUB))
        v.append(textbox(f"legend{uc}", x + GAP - 4, top + 62, cw - 2 * GAP, text_h(10.0), 103, [para(
            run("■ ", 10.0, GEN), run("Generator     ", 10.0, SUB),
            run("■ ", 10.0, SOLAR), run("Solar + battery     ", 10.0, SUB),
            run("| ", 10.0, GRID, SEMI), run("Grid tariff: price reference only     ", 10.0, SUB),
            run("◇ ", 10.0, GRID, SEMI), run("state-set tariff", 10.0, SUB))]))
        v.append(bars_p2(uc, x + GAP, top + 112, cw - 2 * GAP - 20, ch - 112 - 38, GMAX[user]))
        # band labels next to the constant lines; plot-area x of value 0 and of the axis end were measured
        # on the rendered chart and depend only on this fixed layout
        x0, x1 = P2_PLOT[uc]
        end = round(GMAX[user] * 1.18)
        v.append(mcard(f"bandA{uc}", x0 + (x1 - x0) * BAND_A / end + 3, top + 98, 110, 105, "Ref P2 Band A Label",
                       9.0, GRID))
        wb = text_w(f"Band B ₦{BAND_B:,.0f}", 9.0) + 6
        v.append(mcard(f"bandB{uc}", x0 + (x1 - x0) * BAND_B / end - wb - 3, top + 98, wb + 8, 106,
                       "Ref P2 Band B Label", 9.0, GRID))
        v.append(mcard(f"range{uc}", x + GAP - 4, top + ch - GAP - 18, cw - 2 * GAP, 104, f"Range P2 {uc}", 10.0,
                       SUB))
    return v


# ---------------- page 3 ----------------
_pay = pd.read_csv(DATA / "fact_payback.csv", dtype={"month": str})
_pl = _pay[(_pay.month == _pay.month.max()) & (_pay.user == "household") & (_pay.case == "central")].set_index("state")
P3_EXTREMES = {"Max": (_pl.payback_months.idxmax(), f"{_pl.payback_months.max():.1f} mo"),
               "Min": (_pl.payback_months.idxmin(), f"{_pl.payback_months.min():.1f} mo")}
_nat = _pay[_pay.case == "central"].groupby(["user", "month"]).payback_months.median().unstack("user")
P3_YMAX = float(round(_nat.max().max() * 1.18, 1))
P3_MONTHS = list(_nat.index)
P3_PEAK = _nat["household"].loc["2024-01":"2024-12"].idxmax()
_up = _pay[(_pay.month == _pay.month.max()) & (_pay.user == "household") & (_pay.case == "high")]
P3_XMAX = float(np.ceil(_up.upfront_months_of_consumption.max()))
MAP_LABEL_POS3 = {}
P3_MAP = (M + GAP, 230 + 40, 360 - 2 * GAP, 444 - 128)
# plot area of the payback line chart on the canvas: x of first/last month, y of 0 and of the axis top.
# Measured on the rendered chart; depends only on this fixed layout.
P3_PLOT = (474.0, 718.0, 636.0, 636.0 - 324.0 * P3_YMAX / 30)


def line_p3(x, y, w, h):
    hh, bz, pk = "Payback HH Central", "Payback BZ Central", "Payback HH Peak Point"
    visual = {
        "visualType": "lineChart",
        "query": {"queryState": {
            "Category": {"projections": [c_proj("dim_month", "date", "Month")]},
            "Y": {"projections": [m_proj(hh, "Household"), m_proj(bz, "Business"), m_proj(pk, "2024 peak")]},
        },
            "sortDefinition": {"sort": [{"field": column("dim_month", "date"), "direction": "Ascending"}],
                               "isDefaultSort": False}},
        "objects": {
            "categoryAxis": [{"properties": props(axisType="Scalar", show=True, showAxisTitle=False,
                                                  labelColor=C(SUB), fontSize=10.0, fontFamily=FONT,
                                                  gridlineShow=False)}],
            "valueAxis": [{"properties": props(show=True, showAxisTitle=True, titleText="months", titleColor=C(SUB),
                                               titleFontSize=10.0, titleFontFamily=FONT, start=0.0, end=P3_YMAX,
                                               labelColor=C(SUB), fontSize=10.0, fontFamily=FONT,
                                               labelDisplayUnits=1.0, gridlineShow=True, gridlineColor=C(GRIDLINE),
                                               gridlineStyle="solid")}],
            "legend": [{"properties": props(show=False)}],
            "dataPoint": [{"properties": {"fill": color(SOLAR)}, "selector": meta(hh)},
                          {"properties": {"fill": color(GEN)}, "selector": meta(bz)},
                          {"properties": {"fill": color(ALERT)}, "selector": meta(pk)}],
            "lineStyles": [
                {"properties": props(strokeWidth=3.0, showMarker=False), "selector": meta(hh)},
                {"properties": props(strokeWidth=2.0, showMarker=False), "selector": meta(bz)},
                {"properties": props(strokeWidth=0.0, showMarker=True, markerSize=6.0, markerShape="circle"),
                 "selector": meta(pk)}],
            "labels": [{"properties": props(show=False)}],
        },
        "visualContainerObjects": chrome(),
    }
    flt = {"filters": [{"name": "fSolarSeries", "field": column("dim_month", "solar_series"), "type": "Categorical",
                        "filter": {"Version": 2, "From": [{"Name": "d", "Entity": "dim_month", "Type": 0}],
                                   "Where": [{"Condition": {"In": {"Expressions": [{"Column": {"Expression": {
                                       "SourceRef": {"Source": "d"}}, "Property": "solar_series"}}],
                                       "Values": [[{"Literal": {"Value": "true"}}]]}}}]},
                        "howCreated": "User"}]}
    return container("lineP3", x, y, w, h, 310, visual, filter_config=flt)


def afford_bars(x, y, w, h):
    c, lo, hi = "Upfront HH Central Now", "Upfront HH Low Now", "Upfront HH High Now"
    visual = {
        "visualType": "clusteredBarChart",
        "query": {"queryState": {
            "Category": {"projections": [c_proj("dim_state", "state", "State")]},
            "Y": {"projections": [m_proj(c, "Upfront / monthly spending")]},
        },
            "sortDefinition": {"sort": [{"field": measure(c), "direction": "Descending"}], "isDefaultSort": False}},
        "objects": {
            "categoryAxis": [{"properties": props(show=True, showAxisTitle=False, labelColor=C(NAVY), fontSize=10.0,
                                                  fontFamily=FONT, innerPadding=32.0)}],
            "valueAxis": [{"properties": props(show=True, showAxisTitle=False, start=0.0, end=P3_XMAX,
                                               labelColor=C(SUB), fontSize=10.0, fontFamily=FONT,
                                               gridlineShow=True, gridlineColor=C(GRIDLINE), gridlineStyle="solid")}],
            "legend": [{"properties": props(show=False)}],
            "dataPoint": [{"properties": {"fill": color(SOLAR)}, "selector": meta(c)}],
            "labels": [{"properties": props(show=True, color=C(NAVY), fontSize=9.0, fontFamily=SEMI,
                                            labelPosition="InsideBase", labelPrecision=1)}],
            "error": error_range(c, hi, lo, band=False),
        },
        "visualContainerObjects": chrome(),
    }
    return container("affordBars", x, y, w, h, 410, visual,
                     filter_config={"filters": [top_n_filter("fTop12", "dim_state", "state", c, 12)]})


def page3(page):
    v = header(page, "Payback", "Takeaway P3")
    top, kw = 104, (W - 2 * M - 2 * GAP) / 3
    v += kpi("kpiNow", M, top, kw, 110, "KPI P3 Now Title", "KPI P3 Now Value", "KPI P3 Now Sub")
    v += kpi("kpiStart", M + kw + GAP, top, kw, 110, None, "KPI P3 Start Value", "KPI P3 Start Sub",
             title_text="At the start, June 2023")
    v += kpi("kpiPeak", M + 2 * (kw + GAP), top, kw, 110, "KPI P3 Peak Title", "KPI P3 Peak Value",
             "KPI P3 Peak Value", ALERT)
    v = [vc for vc in v if vc["name"] != "kpiPeakSub"]
    v.append(label("kpiPeakSubText", M + 2 * (kw + GAP) + GAP - 4, top + 110 - GAP - 18, kw - 2 * GAP, 103,
                   "Naira fall raised solar costs before petrol prices caught up", 10.0, SUB))

    y2 = top + 110 + GAP
    h2 = H - M - 22 - y2
    mw, lw = 360, 420
    aw = W - 2 * M - mw - lw - 2 * GAP
    v.append(card_box("mapCard", M, y2, mw, h2, 200))
    v.append(mcard("mapTitle", M + GAP - 4, y2 + GAP - 6, mw - 2 * GAP, 201, "Map P3 Title", 12.0, NAVY, SEMI))
    v.append(shape_map("mapP3", *P3_MAP, 210, "Payback HH Now", "Household payback, months"))
    v += legend_bar("p3", M + GAP + 30, y2 + h2 - 76, mw - 2 * GAP - 60, 220, "Map P3 Min Value",
                    "Map P3 Max Value", "months (central)", P3_EXTREMES["Max"][1].replace(" mo", ""))
    v.append(mcard("mapSpread", M + GAP - 4, y2 + h2 - 44, mw - GAP, 230, "Map P3 Spread Note 1", 9.0, FOOT))
    v.append(label("mapSpread2", M + GAP - 4, y2 + h2 - 27, mw - GAP, 231, "stretched to show the differences", 9.0,
                   FOOT))
    v += map_labels("p3", P3_EXTREMES, "Map P3", MAP_LABEL_POS3, " Label Value")

    lx = M + mw + GAP
    v.append(card_box("lineCard", lx, y2, lw, h2, 300))
    v.append(label("lineTitle", lx + GAP - 4, y2 + GAP - 6, lw - GAP + 4, 301,
                   "Payback over time, months (median of states, central)", 12.0, NAVY, SEMI))
    px0, px1, py0, py1 = P3_PLOT

    def to_xy(i, val):
        return px0 + (px1 - px0) * i / (len(P3_MONTHS) - 1), py0 - (py0 - py1) * val / P3_YMAX

    v.append(line_p3(lx + GAP, y2 + 40, lw - 2 * GAP - 70, h2 - 48))
    pxk, pyk = to_xy(P3_MONTHS.index(P3_PEAK), float(_nat["household"].loc[P3_PEAK]))
    v.append(mcard("lblPeak", pxk - 40, pyk - 30, 110, 320, "Label P3 Peak", 10.0, ALERT, SEMI))
    ex, ey = to_xy(len(P3_MONTHS) - 1, float(_nat["household"].iloc[-1]))
    _, eyb = to_xy(len(P3_MONTHS) - 1, float(_nat["business"].iloc[-1]))
    v.append(mcard("lblHHEnd", ex + 4, ey - 18, 96, 321, "Label P3 HH End", 9.0, "#B45309", SEMI))
    v.append(mcard("lblBZEnd", ex + 4, eyb + 2, 96, 322, "Label P3 BZ End", 9.0, GEN, SEMI))

    ax = lx + lw + GAP
    v.append(card_box("affordCard", ax, y2, aw, h2, 400))
    v.append(label("affordTitle", ax + GAP - 4, y2 + GAP - 6, aw - 2 * GAP, 401,
                   "Upfront cost in months of household spending", 12.0, NAVY, SEMI))
    v.append(afford_bars(ax + GAP, y2 + 40, aw - 2 * GAP, h2 - 80))
    v.append(mcard("affordNote", ax + GAP - 4, y2 + h2 - GAP - 18, aw - 2 * GAP, 402, "Note P3 Afford", 9.0, SUB))
    return v


# ---------------- page 4 ----------------
_pri = pd.read_csv(DATA / "fact_priority_index.csv")
_base = _pri[(_pri.weighting == "equal") & (_pri.gap_user == "household") &
             (_pri.reliance_measure == "primary_source")].sort_values("rank")
_n_var = _pri.groupby(["weighting", "gap_user", "reliance_measure"]).ngroups
_freq = _pri[_pri["rank"] <= 10].groupby("state").size()
P4_ALL12 = [st for st in _base.state.head(15) if _freq.get(st, 0) == _n_var]
P4_TOP15 = list(_base.state.head(15))
P4_INDEX = dict(zip(_base.state, _base["index"]))
# bar plot area on the canvas (x of value 0 and of the axis end 1.15; y of first and last bar centre).
# Measured on the rendered chart; depends only on this fixed layout.
P4_PLOT = (137.0, 137.0 + 368.0 * 1.15, 168.0, 551.0)


def state_filter(name, st):
    return {"filters": [{"name": name, "field": column("dim_state", "state"), "type": "Categorical",
                         "filter": {"Version": 2, "From": [{"Name": "d", "Entity": "dim_state", "Type": 0}],
                                    "Where": [{"Condition": {"In": {"Expressions": [{"Column": {"Expression": {
                                        "SourceRef": {"Source": "d"}}, "Property": "state"}}],
                                        "Values": [[{"Literal": {"Value": lit_value(st)}}]]}}}]},
                         "howCreated": "User"}]}


def priority_bars(x, y, w, h):
    m = "Priority Index"
    visual = {
        "visualType": "clusteredBarChart",
        "query": {"queryState": {
            "Category": {"projections": [c_proj("dim_state", "priority_label", "State")]},
            "Y": {"projections": [m_proj(m, "Priority index")]},
        },
            "sortDefinition": {"sort": [{"field": column("dim_state", "priority_label"), "direction": "Ascending"}],
                               "isDefaultSort": False}},
        "objects": {
            "categoryAxis": [{"properties": props(show=True, showAxisTitle=False, labelColor=C(NAVY), fontSize=10.0,
                                                  fontFamily=FONT, innerPadding=30.0)}],
            "valueAxis": [{"properties": props(show=True, showAxisTitle=False, start=0.0, end=1.15,
                                               labelColor=C(SUB), fontSize=10.0, fontFamily=FONT,
                                               gridlineShow=True, gridlineColor=C(GRIDLINE), gridlineStyle="solid")}],
            "legend": [{"properties": props(show=False)}],
            "dataPoint": [{"properties": {"fill": color(SOLAR)}, "selector": meta(m)}],
            "labels": [{"properties": props(show=True, color=C(NAVY), fontSize=9.0, fontFamily=FONT,
                                            labelPosition="OutsideEnd", labelPrecision=2)}],
        },
        "visualContainerObjects": chrome(),
    }
    return container("priorityBars", x, y, w, h, 120, visual,
                     filter_config={"filters": [top_n_filter("fTop15", "dim_state", "state", m, 15)]})


def badge(i, st):
    """'All 12' chip after the bar's value label; text from the All 12 Badge measure for that state."""
    x0, x1, yt, yb = P4_PLOT
    k = P4_TOP15.index(st)
    xv = x0 + (x1 - x0) * P4_INDEX[st] / 1.15
    yc = yt + (yb - yt) * k / (len(P4_TOP15) - 1)
    visual = {
        "visualType": "multiRowCard",
        "query": {"queryState": {"Values": {"projections": [m_proj("All 12 Badge")]}}},
        "objects": {
            "dataLabels": [{"properties": props(color=C(GRID), fontSize=8.0, fontFamily=SEMI)}],
            "cardTitle": [{"properties": props(color=C(GRID), fontSize=8.0, fontFamily=SEMI)}],
            "categoryLabels": [{"properties": props(show=False)}],
            "card": [{"properties": props(outline="None", barShow=False, barWeight=0.0, cardPadding=0.0,
                                          cardBackground=C(CARD))}],
        },
        "visualContainerObjects": {**chrome(panel=True, bg=CARD, border=True, border_color=GRID, radius=4.0,
                                            pad=(0, 0, 3, 0))},
    }
    return container(f"badge{i}", xv + 35, yc - 6, 40, 18, 130 + i, visual,
                     filter_config=state_filter(f"fBadge{i}", st))


def top10_table(x, y, w, h):
    cols = [("Priority Rank", "Rank", 44.0, "left"), (None, "State", 96.0, "left"),
            ("All 12 Dot", " ", 22.0, "left"), ("Saving HH Now", "Saving ₦/month", 112.0, "right"),
            ("Payback HH Now Text", "Payback, months", 140.0, "right"),
            ("Upfront HH Now Text", "Upfront ÷ monthly spending", 190.0, "right")]  # 604 px in total
    projs, widths, fmt = [], [], []
    for m, disp, wd, al in cols:
        pr = c_proj("dim_state", "state", disp) if m is None else m_proj(m, disp)
        projs.append(pr)
        sel = {"metadata": pr["queryRef"]}
        widths.append({"properties": props(value=wd), "selector": sel})
        f = {"alignment": lit("Right" if al == "right" else "Left")}
        if m == "All 12 Dot":
            f["fontColor"] = color(GRID)
        fmt.append({"properties": f, "selector": sel})
    visual = {
        "visualType": "tableEx",
        "query": {"queryState": {"Values": {"projections": projs}},
                  "sortDefinition": {"sort": [{"field": measure("Priority Rank"), "direction": "Ascending"}],
                                     "isDefaultSort": False}},
        "objects": {
            "columnHeaders": [{"properties": props(fontColor=C(SUB), backColor=C(CARD), fontSize=10.0,
                                                   fontFamily=SEMI, wordWrap=False, outline="BottomOnly",
                                                   outlineColor=C(BORDER))}],
            "values": [{"properties": props(fontColor=C(NAVY), backColor=C(CARD), backColorSecondary=C(CARD),
                                            fontColorSecondary=C(NAVY), fontSize=10.0, fontFamily=FONT,
                                            wordWrap=False, outline="None")}],
            "grid": [{"properties": props(gridHorizontal=True, gridHorizontalColor=C(BORDER), gridHorizontalWeight=1.0,
                                          gridVertical=False, rowPadding=9.0, outlineColor=C(CARD),
                                          textSize=10.0)}],
            "total": [{"properties": props(totals=False)}],
            "columnWidth": widths,
            "columnFormatting": fmt,
        },
        "visualContainerObjects": chrome(),
    }
    return container("top10Table", x, y, w, h, 220, visual,
                     filter_config={"filters": [top_n_filter("fTop10", "dim_state", "state", "Priority Index", 10)]})


def page4(page):
    v = header(page, "Where to Go Next", "Takeaway P4")
    top = 104
    ch = H - M - 22 - top
    lw = 560
    v.append(card_box("barsCard", M, top, lw, ch, 100))
    v.append(mcard("barsTitle", M + GAP - 4, top + GAP - 6, lw - 2 * GAP, 101, "Card P4 Bars Title", 12.0, NAVY,
                   SEMI))
    v.append(priority_bars(M + GAP, top + 40, lw - 2 * GAP, ch - 112))
    v += [badge(i, st) for i, st in enumerate(P4_ALL12)]
    v.append(textbox("indexNote", M + GAP - 4, top + ch - GAP - 46, lw - GAP, 50, 140, [
        para(run("How the index is built: geometric mean of percentile ranks of generator reliance (NLSS 2018/19),",
                 9.0, SUB)),
        para(run("monthly ₦ saving from switching, and ability to pay (1 − MPI 2022). Shown as ranks, not precise "
                 "scores.", 9.0, SUB)),
        para(run("All 12 = in the top 10 under all 3 weightings × 2 users × 2 reliance measures.", 9.0, SUB))]))

    tx = M + lw + GAP
    tw = W - M - tx
    v.append(card_box("tableCard", tx, top, tw, ch, 200))
    v.append(mcard("tableTitle", tx + GAP - 4, top + GAP - 6, tw - 2 * GAP, 201, "Card P4 Table Title", 12.0, NAVY,
                   SEMI))
    v.append(top10_table(tx + GAP, top + 40, tw - 2 * GAP, ch - 100))
    v.append(label("tableNote", tx + GAP - 4, top + ch - GAP - 18, tw - 2 * GAP, 202,
                   "● top 10 under all 12 index variants", 9.0, GRID))
    return v


def placeholder_page(page, title, takeaway):
    return header(page, title, takeaway)


BUILDERS = {"p1_fuel_shock": page1, "p2_gen_grid_solar": page2, "p3_payback": page3, "p4_where_next": page4}
TAKEAWAY = {"p1_fuel_shock": "Takeaway P1", "p2_gen_grid_solar": "Takeaway P2", "p3_payback": "Takeaway P3",
            "p4_where_next": "Takeaway P4"}


# ---------- map label positions + legend image ----------
def map_label_positions(box):
    """Screen position of each state's label in a map box (x, y, w, h), assuming the Shape Map fits the
    Mercator-projected outline to the box (centred, aspect kept)."""
    topo = json.loads((RES / MAP_NAME).read_text(encoding="utf-8"))
    sx, sy = topo["transform"]["scale"]
    tx, ty = topo["transform"]["translate"]
    merc = lambda lat: math.degrees(math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)))  # noqa: E731
    rings = {}
    for g in topo["objects"]["states"]["geometries"]:
        polys = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]]
        best = None
        for poly in polys:
            a = np.cumsum(np.array(topo["arcs"][poly[0][0]]), axis=0)
            pts = np.column_stack([a[:, 0] * sx + tx, [merc(v) for v in a[:, 1] * sy + ty]])
            if best is None or len(pts) > len(best):
                best = pts
        rings[g["properties"]["name"]] = best
    allp = np.vstack(list(rings.values()))
    x0, x1, y0, y1 = allp[:, 0].min(), allp[:, 0].max(), allp[:, 1].min(), allp[:, 1].max()
    bx, by, bw, bh = box
    k = min(bw / (x1 - x0), bh / (y1 - y0))
    ox, oy = bx + (bw - k * (x1 - x0)) / 2, by + (bh - k * (y1 - y0)) / 2
    return {s: (ox + k * (r[:, 0].mean() - x0), oy + k * (y1 - r[:, 1].mean())) for s, r in rings.items()}


def write_legend_image():
    from PIL import Image
    lo = np.array([int(SEQ_LO[i:i + 2], 16) for i in (1, 3, 5)], float)
    hi = np.array([int(SEQ_HI[i:i + 2], 16) for i in (1, 3, 5)], float)
    t = np.linspace(0, 1, 512)[:, None]
    row = (lo + (hi - lo) * t).round().astype(np.uint8)
    Image.fromarray(np.repeat(row[None, :, :], 16, axis=0)).save(RES / LEGEND_IMG)


def register_resources():
    rj = REPORT / "definition" / "report.json"
    rep = json.loads(rj.read_text(encoding="utf-8"))
    pkg = next(p for p in rep["resourcePackages"] if p["name"] == "RegisteredResources")
    want = [{"name": MAP_NAME, "path": MAP_NAME, "type": "ShapeMap"},
            {"name": LEGEND_IMG, "path": LEGEND_IMG, "type": "Image"}]
    names = {i["name"] for i in pkg["items"]}
    pkg["items"] += [w for w in want if w["name"] not in names]
    rj.write_text(json.dumps(rep, indent=2) + "\n", encoding="utf-8")


# ---------- write ----------
def page_json(name, display):
    return {"$schema": PAGE_SCHEMA, "name": name, "displayName": display, "displayOption": "FitToPage",
            "height": H, "width": W,
            "objects": {"background": [{"properties": {"color": color(BG), "transparency": lit(0.0)}}],
                        "outspace": [{"properties": {"color": color(BG), "transparency": lit(0.0)}}]}}


def write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    write_legend_image()
    register_resources()
    p1_map = (M + GAP, 104 + 110 + GAP + 40, 470 - 2 * GAP, (H - M - 22 - (104 + 110 + GAP)) - 112)
    MAP_LABEL_POS.update(map_label_positions(p1_map))
    MAP_LABEL_POS3.update(map_label_positions(P3_MAP))
    if STAGING.parent.exists():
        shutil.rmtree(STAGING.parent)
    write(PAGES_DIR / "pages.json", {"$schema": PAGES_SCHEMA, "pageOrder": [n for n, _, _ in PAGES],
                                     "activePageName": PAGES[0][0]})
    for name, display, title in PAGES:
        write(PAGES_DIR / name / "page.json", page_json(name, display))
        visuals = BUILDERS.get(name, lambda p, t=title: placeholder_page(p, t, TAKEAWAY[p]))(name)
        names = [vc["name"] for vc in visuals]
        assert len(names) == len(set(names)), f"duplicate visual names on {display}"
        for vc in visuals:
            p = vc["position"]
            assert 0 <= p["x"] and p["x"] + p["width"] <= W + 0.5, (display, vc["name"], "x")
            assert 0 <= p["y"] and p["y"] + p["height"] <= H + 0.5, (display, vc["name"], "y")
            write(PAGES_DIR / name / "visuals" / vc["name"] / "visual.json", vc)
    # validate, then replace the report's pages
    import pbir_validate  # noqa: E402
    model_def = HERE / "report" / "HiddenPowerPlant.SemanticModel" / "definition"
    if pbir_validate.main([str(PAGES_DIR), "--model", str(model_def)]):
        sys.exit("validation failed; report not changed")
    dest = REPORT / "definition" / "pages"
    shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(PAGES_DIR, dest)
    print(f"pages written: {len(PAGES)}; files: {sum(1 for _ in dest.rglob('*.json'))}")


if __name__ == "__main__":
    sys.path.insert(0, str(HERE))
    main()
