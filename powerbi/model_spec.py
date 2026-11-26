"""Phase 5 Power BI model spec: calculated columns and DAX measures.

Single source of truth for what apply_model.py writes to the open HiddenPowerPlant model.
Every number shown on the dashboard comes from one of these measures; nothing is typed by hand.
Definitions mirror src/mockups.py (medians of state values, central case unless named) so the
dashboard matches the approved mockups and docs/phase4_audit.md.
Each colour has its own measure (no field-value colour rules). Wording follows plan section 7.
"""

MEASURE_TABLE = "_Measures"

GEN, SOL, PAY, TAR, PRI = "fact_generator_cost", "fact_solar_cost", "fact_payback", "fact_grid_tariff", \
    "fact_priority_index"


def naira(v: str) -> str:
    """DAX text for the mockup naira() rule: ₦1.9m from 1 million, else ₦85,404."""
    return f'IF ( {v} >= 1000000, "₦" & FORMAT ( {v} / 1000000, "0.0" ) & "m", "₦" & FORMAT ( {v}, "#,0" ) )'


def one(v: str) -> str:
    return f'FORMAT ( {v}, "0.0" )'


def f(table, user, case):
    return f'{table}[user] = "{user}", {table}[case] = "{case}"'


LATEST = "VAR _m = [Latest Month]\n"
AT_LATEST = "REMOVEFILTERS ( dim_month ), dim_month[month] = _m"
BASE_VARIANT = (f'{PRI}[weighting] = "equal", {PRI}[gap_user] = "household", '
                f'{PRI}[reliance_measure] = "primary_source"')

N0, N1, PCT, TXT = "₦#,0", "0.0", "+0%", None
M = []  # (name, folder, format, description, dax)


def add(name, folder, fmt, desc, dax):
    M.append((name, folder, fmt, desc, dax.strip()))


# ---------------- common ----------------
add("Latest Month", "0 Common", TXT, "Latest month with NBS fuel prices (yyyy-mm).",
    f"CALCULATE ( MAX ( {GEN}[month] ), REMOVEFILTERS () )")
add("Latest Month Label", "0 Common", TXT, "Latest month as 'May 2026'.",
    LATEST + "RETURN CALCULATE ( MAX ( dim_month[label] ), REMOVEFILTERS ( dim_month ), dim_month[month] = _m )")
add("First Month", "0 Common", TXT, "First month of the generator series (yyyy-mm).",
    f"CALCULATE ( MIN ( {GEN}[month] ), REMOVEFILTERS () )")
add("Footnote", "0 Common", TXT, "Footnote shown on every page.",
    '"Estimates with low–high ranges. Sources: NBS, NERC, CBN, Global Solar Atlas/Solargis (CC BY 4.0), '
    'geoBoundaries. Method and limits: docs/phase4_audit.md"')

# ---------------- page 1: the fuel shock ----------------
P1 = "1 Fuel shock"
for u, uc in (("household", "HH"), ("business", "BZ")):
    for c, cc in (("central", "Central"), ("low", "Low"), ("high", "High")):
        add(f"Gen {uc} {cc}", P1, N0,
            f"Generator running cost (fuel + maintenance), ₦/month, {u}, {c} case. Median of states in the "
            f"current filter (one state: that state's value).",
            f"CALCULATE ( MEDIAN ( {GEN}[running_ngn_per_month] ), {f(GEN, u, c)} )")
        add(f"Gen {uc} {cc} Now", P1, N0, f"Gen {uc} {cc} in the latest month.",
            LATEST + f"RETURN CALCULATE ( [Gen {uc} {cc}], {AT_LATEST} )")
    add(f"Gen {uc} First", P1, N0, f"Gen {uc} Central in the first month (January 2023).",
        f"VAR _m = [First Month]\nRETURN CALCULATE ( [Gen {uc} Central], {AT_LATEST} )")
    add(f"Gen {uc} Change", P1, PCT, f"Change in Gen {uc} Central from January 2023 to the latest month.",
        f"DIVIDE ( [Gen {uc} Central Now], [Gen {uc} First] ) - 1")
add("Gen HH Label Points", P1, N0, "Gen HH Central only in the first and latest month (line end labels).",
    "VAR _m = SELECTEDVALUE ( dim_month[month] )\n"
    "RETURN IF ( _m = [First Month] || _m = [Latest Month], [Gen HH Central] )")
add("Gen HH High Max", P1, N0, "Highest monthly value of the household high case (national median).",
    "CALCULATE ( MAXX ( VALUES ( dim_month[month] ), [Gen HH High] ), REMOVEFILTERS ( dim_month ) )")
add("Takeaway P1", P1, TXT, "Page 1 takeaway.",
    f'VAR _v = [Gen HH Central Now]\nRETURN "Running a small household generator cost a median " & {naira("_v")} & '
    '" a month in " & [Latest Month Label] & ", " & FORMAT ( [Gen HH Change] * 100, "0" ) & '
    '"% more than in January 2023 (central estimate)."')
add("KPI P1 HH Title", P1, TXT, "", '"Household generator, ₦/month (" & [Latest Month Label] & ")"')
add("KPI P1 HH Value", P1, TXT, "", f"VAR _v = [Gen HH Central Now]\nRETURN {naira('_v')}")
add("KPI P1 HH Sub", P1, TXT, "",
    f"VAR _l = [Gen HH Low Now]\nVAR _h = [Gen HH High Now]\n"
    f'RETURN "National median, central · range " & {naira("_l")} & "–" & {naira("_h")}')
add("KPI P1 BZ Title", P1, TXT, "", '"Small-business generator, ₦/month (" & [Latest Month Label] & ")"')
add("KPI P1 BZ Value", P1, TXT, "", f"VAR _v = [Gen BZ Central Now]\nRETURN {naira('_v')}")
add("KPI P1 BZ Sub", P1, TXT, "",
    f"VAR _l = [Gen BZ Low Now]\nVAR _h = [Gen BZ High Now]\n"
    f'RETURN "National median, central · range " & {naira("_l")} & "–" & {naira("_h")}')
add("KPI P1 Change Value", P1, TXT, "", '"+" & FORMAT ( [Gen HH Change] * 100, "0" ) & "%"')
add("KPI P1 Change Sub", P1, TXT, "",
    '"Household (petrol) · business (diesel) +" & FORMAT ( [Gen BZ Change] * 100, "0" ) & "%"')
add("Map P1 Title", P1, TXT, "", '"Household generator cost by state (" & [Latest Month Label] & ", central)"')


def state_extreme(measure, direction):
    return (f"TOPN ( 1, ALL ( dim_state[state] ), {measure}, {direction} )")


for tag, d in (("Max", "DESC"), ("Min", "ASC")):
    add(f"Map P1 {tag} State", P1, TXT, f"State with the {tag.lower()} household generator cost, latest month.",
        f"MAXX ( {state_extreme('[Gen HH Central Now]', d)}, dim_state[state] )")
    add(f"Map P1 {tag} Value", P1, TXT, "",
        f"VAR _v = {'MAXX' if tag == 'Max' else 'MINX'} ( ALL ( dim_state[state] ), [Gen HH Central Now] )\n"
        f"RETURN {naira('_v')}")
add("Map P1 Spread Note", P1, TXT, "",
    "VAR _hi = MAXX ( ALL ( dim_state[state] ), [Gen HH Central Now] )\n"
    "VAR _lo = MINX ( ALL ( dim_state[state] ), [Gen HH Central Now] )\n"
    'RETURN "States differ by only about " & FORMAT ( ( _hi / _lo - 1 ) * 100, "0" ) & '
    '"%; the colour scale is stretched to show the differences"')
add("Line P1 Note", P1, TXT, "",
    f'VAR _v = [Gen HH High Max]\nRETURN "Shaded band = low–high case, clipped at the top (high case reaches " & '
    f'{naira("_v")} & ")"')

# ---------------- page 2: generator vs grid vs solar ----------------
P2 = "2 Generator vs grid vs solar"
for u, uc in (("household", "HH"), ("business", "BZ")):
    add(f"Gen kWh {uc} Now", P2, "₦#,0", f"Generator running cost, ₦/kWh, {u}, central, latest month.",
        LATEST + f"RETURN CALCULATE ( MEDIAN ( {GEN}[running_ngn_per_kwh] ), {f(GEN, u, 'central')}, {AT_LATEST} )")
    add(f"Solar kWh {uc} Now", P2, "₦#,0", f"Solar + battery cost (LCOE), ₦/kWh, {u}, central, latest month.",
        LATEST + f"RETURN CALCULATE ( MEDIAN ( {SOL}[lcoe_ngn_per_kwh] ), {f(SOL, u, 'central')}, {AT_LATEST} )")
    add(f"Range P2 {uc}", P2, TXT, "All-state range line under each chart.",
        f"VAR _g1 = MINX ( ALL ( dim_state[state] ), [Gen kWh {uc} Now] )\n"
        f"VAR _g2 = MAXX ( ALL ( dim_state[state] ), [Gen kWh {uc} Now] )\n"
        f"VAR _s1 = MINX ( ALL ( dim_state[state] ), [Solar kWh {uc} Now] )\n"
        f"VAR _s2 = MAXX ( ALL ( dim_state[state] ), [Solar kWh {uc} Now] )\n"
        f'RETURN "All 37 states: generator " & {naira("_g1")} & "–" & {naira("_g2")} & "/kWh · solar " & '
        f'{naira("_s1")} & "–" & {naira("_s2")} & "/kWh (central)"')
for b in ("A", "B"):
    add(f"Grid Band {b} Now", P2, "₦#,0.00", f"Median Band {b} tariff across states, latest month (price reference).",
        LATEST + f'RETURN CALCULATE ( MEDIAN ( {TAR}[tariff_ngn_per_kwh] ), {TAR}[band] = "{b}", {AT_LATEST}, '
        "REMOVEFILTERS ( dim_state ) )")
add("Takeaway P2", P2, TXT, "Page 2 takeaway.",
    "VAR _g1 = MINX ( ALL ( dim_state[state] ), [Gen kWh HH Now] )\n"
    "VAR _g2 = MAXX ( ALL ( dim_state[state] ), [Gen kWh HH Now] )\n"
    "VAR _s1 = MINX ( ALL ( dim_state[state] ), [Solar kWh HH Now] )\n"
    "VAR _s2 = MAXX ( ALL ( dim_state[state] ), [Solar kWh HH Now] )\n"
    f'RETURN "In " & [Latest Month Label] & " a small petrol generator cost " & {naira("_g1")} & "–" & '
    f'{naira("_g2")} & " per kWh; solar + battery " & {naira("_s1")} & "–" & {naira("_s2")} & '
    '"; grid Band A ₦" & FORMAT ( [Grid Band A Now], "#,0.00" ) & " where supply exists."')
add("Card P2 HH Title", P2, TXT, "",
    '"Household · 2.5 kVA petrol — ₦ per kWh (" & [Latest Month Label] & ", central)"')
add("Card P2 BZ Title", P2, TXT, "",
    '"Small business · 20 kVA diesel — ₦ per kWh (" & [Latest Month Label] & ", central)"')
add("Ref P2 Band A Label", P2, TXT, "", '"Band A ₦" & FORMAT ( [Grid Band A Now], "#,0.00" )')
add("Ref P2 Band B Label", P2, TXT, "", '"Band B ₦" & FORMAT ( [Grid Band B Now], "#,0" )')

# ---------------- page 3: payback ----------------
P3 = "3 Payback"
for u, uc in (("household", "HH"), ("business", "BZ")):
    add(f"Payback {uc} Central", P3, N1,
        f"Simple payback of solar + battery, months, {u}, central. Median of states in the current filter.",
        f"CALCULATE ( MEDIAN ( {PAY}[payback_months] ), {f(PAY, u, 'central')} )")
    add(f"Payback {uc} Now", P3, N1, f"Payback {uc} Central in the latest month.",
        LATEST + f"RETURN CALCULATE ( [Payback {uc} Central], {AT_LATEST} )")
    add(f"Payback {uc} Start", P3, N1, f"Payback {uc} Central in the first solar month (June 2023, A7).",
        f"VAR _m = CALCULATE ( MIN ( {PAY}[month] ), REMOVEFILTERS () )\n"
        f"RETURN CALCULATE ( [Payback {uc} Central], {AT_LATEST} )")
for c in ("low", "high"):
    add(f"Payback HH {c.title()} Now", P3, N1, f"Household payback, {c} case, latest month (per state).",
        LATEST + f"RETURN CALCULATE ( MEDIAN ( {PAY}[payback_months] ), {f(PAY, 'household', c)}, {AT_LATEST} )")
add("Payback HH Peak 2024", P3, N1, "Highest monthly national median household payback in 2024.",
    "CALCULATE ( MAXX ( VALUES ( dim_month[month] ), [Payback HH Central] ), REMOVEFILTERS ( dim_month ), "
    "dim_month[year] = 2024 )")
add("Payback HH Peak Month", P3, TXT, "Month (yyyy-mm) of the 2024 household payback peak.",
    "CALCULATE ( MAXX ( TOPN ( 1, VALUES ( dim_month[month] ), [Payback HH Central], DESC ), dim_month[month] ), "
    "REMOVEFILTERS ( dim_month ), dim_month[year] = 2024 )")
add("Payback HH Peak Label", P3, TXT, "Month of the 2024 peak as 'Feb 2024'.",
    "VAR _m = [Payback HH Peak Month]\n"
    "RETURN CALCULATE ( MAX ( dim_month[label] ), REMOVEFILTERS ( dim_month ), dim_month[month] = _m )")
add("Payback HH Peak Point", P3, N1, "Household payback only at the 2024 peak month (red marker).",
    "IF ( SELECTEDVALUE ( dim_month[month] ) = [Payback HH Peak Month], [Payback HH Central] )")
add("Takeaway P3", P3, TXT, "Page 3 takeaway.",
    '"Solar + battery now pays back in about " & FORMAT ( [Payback HH Now], "0" ) & '
    '" months for a typical household (median, " & [Latest Month Label] & "), down from " & '
    'FORMAT ( [Payback HH Peak 2024], "0" ) & " months at the " & [Payback HH Peak Label] & '
    '" peak (central estimates)."')
add("KPI P3 Now Title", P3, TXT, "", '"Household payback now (" & [Latest Month Label] & ")"')
add("KPI P3 Now Value", P3, TXT, "", f'{one("[Payback HH Now]")} & " months"')
add("KPI P3 Now Sub", P3, TXT, "",
    "VAR _a = MINX ( ALL ( dim_state[state] ), [Payback HH Now] )\n"
    "VAR _b = MAXX ( ALL ( dim_state[state] ), [Payback HH Now] )\n"
    "VAR _l = MINX ( ALL ( dim_state[state] ), [Payback HH Low Now] )\n"
    "VAR _h = MAXX ( ALL ( dim_state[state] ), [Payback HH High Now] )\n"
    f'RETURN "Median of states, central · states " & {one("_a")} & "–" & {one("_b")} & "; range " & '
    f'{one("_l")} & "–" & {one("_h")}')
add("KPI P3 Start Value", P3, TXT, "", f'{one("[Payback HH Start]")} & " months"')
add("KPI P3 Start Sub", P3, TXT, "",
    f'"Median of states, central · business " & {one("[Payback BZ Start]")} & " months"')
add("KPI P3 Peak Title", P3, TXT, "", '"2024 peak (" & [Payback HH Peak Label] & ")"')
add("KPI P3 Peak Value", P3, TXT, "", f'{one("[Payback HH Peak 2024]")} & " months"')
add("Map P3 Title", P3, TXT, "", '"Household payback by state (" & [Latest Month Label] & ")"')
for tag, d in (("Max", "DESC"), ("Min", "ASC")):
    add(f"Map P3 {tag} State", P3, TXT, "", f"MAXX ( {state_extreme('[Payback HH Now]', d)}, dim_state[state] )")
    add(f"Map P3 {tag} Value", P3, TXT, "",
        f"VAR _v = {'MAXX' if tag == 'Max' else 'MINX'} ( ALL ( dim_state[state] ), [Payback HH Now] )\n"
        f'RETURN {one("_v")}')
add("Map P3 Spread Note", P3, TXT, "",
    "VAR _hi = MAXX ( ALL ( dim_state[state] ), [Payback HH Now] )\n"
    "VAR _lo = MINX ( ALL ( dim_state[state] ), [Payback HH Now] )\n"
    'RETURN "States differ by only about " & FORMAT ( ( _hi / _lo - 1 ) * 100, "0" ) & '
    '"%; the colour scale is stretched to show the differences"')
add("Label P3 HH End", P3, TXT, "", f'"Household " & {one("[Payback HH Now]")}')
add("Label P3 BZ End", P3, TXT, "", f'"Business " & {one("[Payback BZ Now]")}')
add("Label P3 Peak", P3, TXT, "", f'"Peak " & {one("[Payback HH Peak 2024]")} & " mo"')
for c, cc in (("central", "Central"), ("low", "Low"), ("high", "High")):
    add(f"Upfront HH {cc} Now", P3, N1,
        f"Household solar upfront cost in months of household consumption, {c} case, latest month.",
        LATEST + f"RETURN CALCULATE ( MEDIAN ( {PAY}[upfront_months_of_consumption] ), "
        f"{f(PAY, 'household', c)}, {AT_LATEST} )")
add("Note P3 Afford", P3, TXT, "",
    "VAR _m = MEDIANX ( ALL ( dim_state[state] ), [Upfront HH Central Now] )\n"
    f'RETURN "12 least affordable · whiskers = low–high · all-state median " & {one("_m")}')

# ---------------- page 4: where to go next ----------------
P4 = "4 Where to go next"
add("Priority Index", P4, "0.00",
    "Market priority index, base variant (equal weights, household saving, generator as primary source).",
    f"CALCULATE ( MAX ( {PRI}[index] ), {BASE_VARIANT} )")
add("Priority Rank", P4, "0", "Rank in the base variant (1 = highest priority).",
    f"CALCULATE ( MAX ( {PRI}[rank] ), {BASE_VARIANT} )")
add("Variants Total", P4, "0", "Number of index variants (3 weightings × 2 users × 2 reliance measures).",
    f"COUNTROWS ( SUMMARIZE ( ALL ( {PRI} ), {PRI}[weighting], {PRI}[gap_user], {PRI}[reliance_measure] ) )")
add("Variants In Top 10", P4, "0", "Number of variants in which the state ranks in the top 10.",
    f"CALCULATE ( COUNTROWS ( {PRI} ), {PRI}[rank] <= 10 )")
add("All 12 Badge", P4, TXT, "'All 12' if the state is in the top 10 under every variant.",
    'IF ( [Variants In Top 10] = [Variants Total], "All 12" )')
add("All 12 Dot", P4, TXT, "'●' if the state is in the top 10 under every variant.",
    'IF ( [Variants In Top 10] = [Variants Total], "●" )')
add("Saving HH Now", P4, N0, "Household monthly ₦ saving from switching, central, latest month.",
    LATEST + f"RETURN CALCULATE ( MEDIAN ( {PAY}[saving_ngn_per_month] ), {f(PAY, 'household', 'central')}, "
    f"{AT_LATEST} )")
add("Payback HH Now Text", P4, TXT, "Household payback, central (low–high), latest month.",
    f'IF ( NOT ISBLANK ( [Payback HH Now] ), {one("[Payback HH Now]")} & "  (" & {one("[Payback HH Low Now]")} & '
    f'"–" & {one("[Payback HH High Now]")} & ")" )')
add("Upfront HH Now Text", P4, TXT, "",
    f'IF ( NOT ISBLANK ( [Upfront HH Central Now] ), {one("[Upfront HH Central Now]")} & " months" )')
add("Takeaway P4", P4, TXT, "Page 4 takeaway.",
    "VAR _t = TOPN ( 3, ALL ( dim_state[state] ), [Priority Rank], ASC )\n"
    "VAR _r = ADDCOLUMNS ( _t, \"@r\", [Priority Rank] )\n"
    "VAR _a = FILTER ( ALL ( dim_state[state] ), [Variants In Top 10] = [Variants Total] )\n"
    "VAR _n1 = MAXX ( FILTER ( _r, [@r] = 1 ), dim_state[state] )\n"
    "VAR _n2 = MAXX ( FILTER ( _r, [@r] = 2 ), dim_state[state] )\n"
    "VAR _n3 = MAXX ( FILTER ( _r, [@r] = 3 ), dim_state[state] )\n"
    'RETURN _n1 & ", " & _n2 & " and " & _n3 & " rank highest; " & '
    'CONCATENATEX ( _a, dim_state[state], ", ", dim_state[state], ASC ) & '
    '" stay in the top 10 under all " & [Variants Total] & " index variants."')
add("Card P4 Bars Title", P4, TXT, "",
    '"Market priority index — top 15 states (" & [Latest Month Label] & ", equal weights)"')
add("Card P4 Table Title", P4, TXT, "",
    '"Top 10 at a glance — household, " & [Latest Month Label] & " (central; payback range low–high)"')

MEASURES = M

# ---------------- calculated columns ----------------
CALC_COLUMNS = [
    {"tableName": "dim_state", "name": "state_label_tariff",
     "description": "State name with a hollow diamond where the tariff is set by a state regulator (NERC rate "
                    "shown as placeholder, A1), latest month.",
     "expression": f'VAR _m = CALCULATE ( MAX ( {TAR}[month] ), REMOVEFILTERS () )\n'
                   f'VAR _ph = CALCULATE ( COUNTROWS ( {TAR} ), {TAR}[month] = _m, {TAR}[tariff_status] <> "nerc_order" )\n'
                   'RETURN IF ( _ph > 0, dim_state[state] & "  ◇", dim_state[state] )'},
    {"tableName": "dim_state", "name": "priority_rank",
     "description": "Rank in the base priority variant (equal weights, household saving, primary source).",
     "expression": f"CALCULATE ( MAX ( {PRI}[rank] ), {BASE_VARIANT} )"},
    {"tableName": "dim_state", "name": "priority_label",
     "description": "'rank  state' label for the priority bars.",
     "expression": 'FORMAT ( dim_state[priority_rank], "0" ) & "  " & dim_state[state]'},
]
SORT_BY = {("dim_state", "priority_label"): "priority_rank"}

# ---------------- page 2 row tables (top 5 · separator · bottom 5) ----------------
# Calculated tables evaluated at refresh from the checked measures: 5 states with the costliest generator
# power, a "· · ·" separator row, then the 5 cheapest (each block in descending order, as in the mockup).


def p2_rows(uc):
    return (
        f'VAR _t = ADDCOLUMNS ( VALUES ( dim_state[state] ), "@g", [Gen kWh {uc} Now] )\n'
        'VAR _top = TOPN ( 5, _t, [@g], DESC )\n'
        'VAR _bot = TOPN ( 5, _t, [@g], ASC )\n'
        'RETURN UNION (\n'
        '    SELECTCOLUMNS ( _top, "pos", RANKX ( _top, [@g],, DESC ), "state", dim_state[state] ),\n'
        '    ROW ( "pos", 6, "state", "" ),\n'
        '    SELECTCOLUMNS ( _bot, "pos", 6 + RANKX ( _bot, [@g],, DESC ), "state", dim_state[state] )\n'
        ')')


CALC_TABLES = [{"name": f"P2 Rows {uc}", "daxExpression": p2_rows(uc),
                "description": f"Page 2 chart rows ({'household' if uc == 'HH' else 'business'}): top 5, "
                               "separator, bottom 5 by generator ₦/kWh, latest month."} for uc in ("HH", "BZ")]
CALC_TABLE_COLUMNS = [
    {"tableName": f"P2 Rows {uc}", "name": "row_label",
     "expression": f"VAR _s = 'P2 Rows {uc}'[state]\n"
                   'RETURN IF ( _s = "", "· · ·", LOOKUPVALUE ( dim_state[state_label_tariff], dim_state[state], _s ) )'}
    for uc in ("HH", "BZ")]
CALC_TABLE_SORT = {(f"P2 Rows {uc}", "row_label"): "pos" for uc in ("HH", "BZ")}
for uc in ("HH", "BZ"):
    for kind, base in (("Gen", "Gen kWh"), ("Solar", "Solar kWh")):
        add(f"P2 {kind} {uc} Row", P2, "#,0;-#,0;",
            f"{base} {uc} Now for the state on the current page-2 chart row. 0 on the separator row (kept so "
            f"the '· · ·' row shows; the format string prints zero as empty).",
            f"VAR _s = SELECTEDVALUE ( 'P2 Rows {uc}'[state] ) "
            f'RETURN IF ( _s = "", 0, CALCULATE ( [{base} {uc} Now], dim_state[state] = _s ) )')
MEASURES = M

for _tag in ("Max", "Min"):
    add(f"Map P3 {_tag} Label Value", "3 Payback", None, "Map label value with unit, e.g. '9.6 mo'.",
        f'[Map P3 {_tag} Value] & " mo"')
MEASURES = M

add("Map P3 Spread Note 1", "3 Payback", None, "First line of the page-3 map note (the card does not wrap).",
    "VAR _hi = MAXX ( ALL ( dim_state[state] ), [Payback HH Now] )\n"
    "VAR _lo = MINX ( ALL ( dim_state[state] ), [Payback HH Now] )\n"
    'RETURN "States differ by only about " & FORMAT ( ( _hi / _lo - 1 ) * 100, "0" ) & "%; the colour scale is"')
MEASURES = M
