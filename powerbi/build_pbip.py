"""Write the starter PBIP (semantic model + empty report + theme) to powerbi/report/.

The model reads the CSVs in data/processed/powerbi/ through one Power Query text parameter,
DataFolder. Power Query has no relative paths, so DataFolder holds the absolute path of
data/processed/powerbi/ on this machine. It is the only value to change on another machine
(Power BI Desktop: Transform data > Edit parameters), or re-run this script there.

Run with Power BI Desktop closed. Existing measures in _Measures.tmdl are kept unless --fresh.
Usage: python powerbi/build_pbip.py [--fresh]
"""
from __future__ import annotations

import json
import shutil
import sys
import uuid
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed" / "powerbi"
OUT = ROOT / "powerbi" / "report"
NAME = "HiddenPowerPlant"
SM = OUT / f"{NAME}.SemanticModel"
RP = OUT / f"{NAME}.Report"
FLARE_BASE_THEME = Path(r"C:/Users/badmu/Downloads/FlareWatch.Report/StaticResources/SharedResources/BaseThemes/CY26SU04.json")
THEME_NAME = "Hidden_Power_Plant.json"

TABLES = ["dim_state", "dim_month", "fact_generator_cost", "fact_grid_tariff", "fact_solar_cost",
          "fact_payback", "fact_crossover", "fact_priority_index"]
# text columns that look numeric or boolean but must stay text (keys, codes, flags with blanks)
FORCE_TEXT = {"month", "crossover_month", "robust_crossover_month", "first_month", "latest_month"}
RELATIONSHIPS = [(t, "state", "dim_state", "state") for t in TABLES[2:]] + \
                [(t, "month", "dim_month", "month") for t in
                 ["fact_generator_cost", "fact_grid_tariff", "fact_solar_cost", "fact_payback"]]

LF = "\n"


def gid() -> str:
    return str(uuid.uuid4())


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def col_type(name: str, s: pd.Series) -> tuple[str, str, str | None]:
    """(TMDL dataType, M type, formatString)."""
    if name in FORCE_TEXT:
        return "string", "type text", None
    if name == "date":
        return "dateTime", "type date", "Short Date"
    v = s.dropna()
    if v.empty:
        return "string", "type text", None
    if s.dtype == bool or (v.isin([True, False]).all() and s.notna().all() and s.dtype == object):
        return "boolean", "type logical", '"""TRUE"";""TRUE"";""FALSE"""'
    if pd.api.types.is_integer_dtype(s):
        return "int64", "Int64.Type", "0"
    if pd.api.types.is_float_dtype(s):
        return "double", "type number", "#,##0.00"
    return "string", "type text", None


def table_tmdl(t: str) -> str:
    df = pd.read_csv(DATA / f"{t}.csv", keep_default_na=True)
    lines = [f"table {t}", f"\tlineageTag: {gid()}", ""]
    mtypes = []
    for c in df.columns:
        dt, mt, fmt = col_type(c, df[c])
        mtypes.append(f'{{"{c}", {mt}}}')
        lines += [f"\tcolumn {c}", f"\t\tdataType: {dt}"]
        if fmt:
            lines.append(f"\t\tformatString: {fmt}")
        lines += [f"\t\tlineageTag: {gid()}", "\t\tsummarizeBy: none", f"\t\tsourceColumn: {c}", "",
                  "\t\tannotation SummarizationSetBy = Automatic", ""]
    m = [
        "let",
        f'    Source = Csv.Document(File.Contents(DataFolder & "{t}.csv"), [Delimiter=",", Columns={len(df.columns)}, Encoding=65001, QuoteStyle=QuoteStyle.Csv]),',
        '    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),',
        f'    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers", {{{", ".join(mtypes)}}}, "en-US")',
        "in",
        '    #"Changed Type"',
    ]
    lines += [f"\tpartition {t} = m", "\t\tmode: import", "\t\tsource ="]
    lines += [f"\t\t\t\t{x}" for x in m]
    lines += ["", "\tannotation PBI_ResultType = Table", ""]
    return LF.join(lines)


MEASURES_SHELL = """/// Holds the model's measures. No data.
table _Measures
\tlineageTag: {tag}

\tcolumn _
\t\tisHidden
\t\tlineageTag: {tag2}
\t\tisNameInferred
\t\tsourceColumn: [_]

\tpartition _Measures = calculated
\t\tmode: import
\t\tsource = ROW("_", BLANK())

\tannotation PBI_Id = {tag3}
"""

THEME = {
    "name": "Hidden Power Plant",
    "dataColors": ["#F59E0B", "#475569", "#0D9488", "#DC2626", "#0F1B2D", "#B45309", "#94A3B8", "#FDE68A"],
    "foreground": "#0F1B2D", "foregroundNeutralSecondary": "#4B5563", "foregroundNeutralTertiary": "#6B7280",
    "background": "#FFFFFF", "backgroundLight": "#F6F7F9", "backgroundNeutral": "#E5E7EB",
    "tableAccent": "#F59E0B", "good": "#0D9488", "neutral": "#475569", "bad": "#DC2626",
    "maximum": "#B45309", "center": "#F59E0B", "minimum": "#FEF3C7",
    "textClasses": {
        "callout": {"fontFace": "Segoe UI Semibold", "fontSize": 28, "color": "#0F1B2D"},
        "title": {"fontFace": "Segoe UI Semibold", "fontSize": 11, "color": "#0F1B2D"},
        "header": {"fontFace": "Segoe UI Semibold", "fontSize": 10, "color": "#0F1B2D"},
        "label": {"fontFace": "Segoe UI", "fontSize": 9, "color": "#4B5563"},
        "largeTitle": {"fontFace": "Segoe UI Semibold", "fontSize": 16, "color": "#0F1B2D"},
    },
    "visualStyles": {
        "*": {"*": {
            "background": [{"show": True, "color": {"solid": {"color": "#FFFFFF"}}, "transparency": 0}],
            "border": [{"show": True, "color": {"solid": {"color": "#E5E7EB"}}, "radius": 8}],
            "dropShadow": [{"show": False}],
            "title": [{"fontFamily": "Segoe UI Semibold", "fontSize": 11, "fontColor": {"solid": {"color": "#0F1B2D"}}}],
            "categoryAxis": [{"fontFamily": "Segoe UI", "fontSize": 9, "labelColor": {"solid": {"color": "#4B5563"}},
                              "gridlineColor": {"solid": {"color": "#E5E7EB"}}}],
            "valueAxis": [{"fontFamily": "Segoe UI", "fontSize": 9, "labelColor": {"solid": {"color": "#4B5563"}},
                           "gridlineColor": {"solid": {"color": "#E5E7EB"}}}],
            "labels": [{"fontFamily": "Segoe UI", "fontSize": 9, "color": {"solid": {"color": "#0F1B2D"}}}],
            "legend": [{"fontFamily": "Segoe UI", "fontSize": 9, "labelColor": {"solid": {"color": "#4B5563"}}}],
        }},
        "page": {"*": {
            "background": [{"color": {"solid": {"color": "#F6F7F9"}}, "transparency": 0}],
            "outspace": [{"color": {"solid": {"color": "#F6F7F9"}}, "transparency": 0}],
        }},
    },
}


def platform(kind: str) -> str:
    return json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": kind, "displayName": NAME},
        "config": {"version": "2.0", "logicalId": gid()}}, indent=2)


def main(fresh: bool) -> None:
    folder = str(DATA).replace("/", "\\") + "\\"
    defn = SM / "definition"
    keep_measures = (defn / "tables" / "_Measures.tmdl").read_text(encoding="utf-8") \
        if (defn / "tables" / "_Measures.tmdl").exists() and not fresh else None

    write(OUT / f"{NAME}.pbip", json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
        "version": "1.0", "artifacts": [{"report": {"path": f"{NAME}.Report"}}],
        "settings": {"enableAutoRecovery": True}}, indent=2))

    # ---- semantic model
    if not (SM / ".platform").exists():
        write(SM / ".platform", platform("SemanticModel"))
    write(SM / "definition.pbism", json.dumps({"version": "4.2", "settings": {}}, indent=2))
    write(defn / "database.tmdl", "database\n\tcompatibilityLevel: 1600\n\n")
    write(defn / "cultures" / "en-US.tmdl", "cultureInfo en-US\n\n")
    write(defn / "expressions.tmdl", LF.join([
        "/// Absolute path of data/processed/powerbi/ (with trailing backslash). The only value to change on another machine.",
        f'expression DataFolder = "{folder}" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]',
        f"\tlineageTag: {gid()}", "", "\tannotation PBI_ResultType = Text", ""]))
    order = json.dumps(["DataFolder"] + TABLES)
    write(defn / "model.tmdl", LF.join([
        "model Model", "\tculture: en-US", "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
        "\tsourceQueryCulture: en-GB", "\tdataAccessOptions", "\t\tlegacyRedirects", "\t\treturnErrorValuesAsNull", "",
        f"annotation PBI_QueryOrder = {order}", "",
        'annotation PBI_ProTooling = ["MCP-PBIModeling","DevMode"]', ""]
        + [f"ref table {t}" for t in TABLES + ["_Measures"]] + ["", "ref cultureInfo en-US", ""]))
    for t in TABLES:
        write(defn / "tables" / f"{t}.tmdl", table_tmdl(t))
    write(defn / "tables" / "_Measures.tmdl",
          keep_measures or MEASURES_SHELL.format(tag=gid(), tag2=gid(), tag3=gid()))
    write(defn / "relationships.tmdl", LF.join(
        [LF.join([f"relationship {gid()}", f"\tfromColumn: {f}.{fc}", f"\ttoColumn: {t}.{tc}", ""])
         for f, fc, t, tc in RELATIONSHIPS]))

    # ---- report shell (pages are written later by build_pages.py)
    if not (RP / ".platform").exists():
        write(RP / ".platform", platform("Report"))
    write(RP / "definition.pbir", json.dumps(
        {"version": "4.0", "datasetReference": {"byPath": {"path": f"../{NAME}.SemanticModel"}}}, indent=2))
    rd = RP / "definition"
    write(rd / "version.json", json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json",
        "version": "2.0.0"}, indent=2))
    imp = {"visual": "2.8.0", "report": "3.2.0", "page": "2.3.1"}
    write(rd / "report.json", json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/3.2.0/schema.json",
        "themeCollection": {
            "baseTheme": {"name": "CY26SU04", "reportVersionAtImport": imp, "type": "SharedResources"},
            "customTheme": {"name": THEME_NAME, "reportVersionAtImport": imp, "type": "RegisteredResources"}},
        "resourcePackages": [
            {"name": "SharedResources", "type": "SharedResources",
             "items": [{"name": "CY26SU04", "path": "BaseThemes/CY26SU04.json", "type": "BaseTheme"}]},
            {"name": "RegisteredResources", "type": "RegisteredResources",
             "items": [{"name": THEME_NAME, "path": THEME_NAME, "type": "CustomTheme"}]}],
        "settings": {"useStylableVisualContainerHeader": True, "exportDataMode": "AllowSummarized",
                     "defaultDrillFilterOtherVisuals": True, "allowChangeFilterTypes": True,
                     "useEnhancedTooltips": True, "useDefaultAggregateDisplayName": True}}, indent=2))
    base = RP / "StaticResources" / "SharedResources" / "BaseThemes" / "CY26SU04.json"
    if not base.exists():
        base.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(FLARE_BASE_THEME, base)
    write(RP / "StaticResources" / "RegisteredResources" / THEME_NAME, json.dumps(THEME, indent=2))
    pages = rd / "pages"
    if not (pages / "pages.json").exists():
        pid = "p1_fuel_shock"
        write(pages / "pages.json", json.dumps({
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json",
            "pageOrder": [pid], "activePageName": pid}, indent=2))
        write(pages / pid / "page.json", json.dumps({
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json",
            "name": pid, "displayName": "1  The Fuel Shock", "displayOption": "FitToPage",
            "height": 720, "width": 1280}, indent=2))
    print("PBIP written:", OUT / f"{NAME}.pbip")


if __name__ == "__main__":
    main("--fresh" in sys.argv)
