"""Apply model_spec.py (calculated columns, sort-by, measures) to the open HiddenPowerPlant model
through the Power BI Modeling MCP, then print the measure check table.

Check table: each DAX measure is evaluated in the open model and compared with (a) an independent
pandas recomputation from data/processed/powerbi/ (same rules as src/mockups.py) and (b) the figure
quoted in docs/phase4_audit.md or on the approved mockups. Exit code 1 on any mismatch.
Usage: python powerbi/apply_model.py [--check-only]
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import model_spec as spec  # noqa: E402
from mcp_client import PBI  # noqa: E402

DATA = HERE.parent / "data" / "processed" / "powerbi"
OPTS = {"continueOnError": False, "useTransaction": True}


def apply(pbi: PBI) -> None:
    cols = pbi.call("column_operations", operation="List")["data"]
    have_cols = {(t["tableName"], c["name"]) for t in cols for c in t["columns"]}
    new = [c for c in spec.CALC_COLUMNS if (c["tableName"], c["name"]) not in have_cols]
    old = [c for c in spec.CALC_COLUMNS if (c["tableName"], c["name"]) in have_cols]
    if new:
        print("calc columns created:", pbi.call("column_operations", operation="Create", definitions=new,
                                                options=OPTS).get("message"))
    if old:
        print("calc columns updated:", pbi.call("column_operations", operation="Update", definitions=old,
                                                options=OPTS).get("message"))
    tables = {t["name"] for t in pbi.call("table_operations", operation="List")["data"]}
    for t in getattr(spec, "CALC_TABLES", []):
        op = "Update" if t["name"] in tables else "Create"
        print(f"table {op}:", t["name"], pbi.call("table_operations", operation=op, definitions=[t],
                                                options=OPTS).get("message"))
        pbi.call("table_operations", operation="RefreshWithXMLA", refreshType="Calculate",
                 references=[{"name": t["name"]}])
    cols = pbi.call("column_operations", operation="List")["data"]
    have_cols = {(t["tableName"], c["name"]) for t in cols for c in t["columns"]}
    extra = getattr(spec, "CALC_TABLE_COLUMNS", [])
    new2 = [c for c in extra if (c["tableName"], c["name"]) not in have_cols]
    if new2:
        print("table columns created:", pbi.call("column_operations", operation="Create", definitions=new2,
                                                 options=OPTS).get("message"))
    sort_all = {**spec.SORT_BY, **getattr(spec, "CALC_TABLE_SORT", {})}
    sort = [{"tableName": t, "name": c, "sortByColumn": s} for (t, c), s in sort_all.items()]
    pbi.call("column_operations", operation="Update", definitions=sort, options=OPTS)

    listed = pbi.call("measure_operations", operation="List").get("data") or []
    have = {m["name"] for t in listed for m in t.get("measures", [])} if listed and "measures" in listed[0] \
        else {m.get("name") for m in listed}
    create, update = [], []
    for name, folder, fmt, desc, dax in spec.MEASURES:
        m = {"tableName": spec.MEASURE_TABLE, "name": name, "expression": dax, "displayFolder": folder}
        if fmt:
            m["formatString"] = fmt
        if desc:
            m["description"] = desc
        (update if name in have else create).append(m)
    if create:
        print("measures created:", len(create),
              pbi.call("measure_operations", operation="Create", definitions=create, options=OPTS).get("message"))
    if update:
        print("measures updated:", len(update),
              pbi.call("measure_operations", operation="Update", definitions=update, options=OPTS).get("message"))
    pbi.call("table_operations", operation="RefreshWithXMLA", refreshType="Calculate",
             references=[{"name": "dim_state"}])


def naira(v):
    return f"₦{v / 1e6:.1f}m" if v >= 1e6 else f"₦{v:,.0f}"


def expected() -> dict[str, tuple[str, str | None]]:
    """measure -> (pandas recomputation as text, figure quoted in audit/mockup or None)."""
    gen = pd.read_csv(DATA / "fact_generator_cost.csv", dtype={"month": str})
    sol = pd.read_csv(DATA / "fact_solar_cost.csv", dtype={"month": str})
    tar = pd.read_csv(DATA / "fact_grid_tariff.csv", dtype={"month": str})
    pay = pd.read_csv(DATA / "fact_payback.csv", dtype={"month": str})
    pri = pd.read_csv(DATA / "fact_priority_index.csv")
    L = gen.month.max()
    nat = gen.groupby(["user", "case", "month"]).running_ngn_per_month.median()
    hh = lambda c, m=L: nat[("household", c, m)]  # noqa: E731
    bz = lambda c, m=L: nat[("business", c, m)]  # noqa: E731
    st = gen[(gen.user == "household") & (gen.case == "central") & (gen.month == L)].set_index("state")
    st = st.running_ngn_per_month
    gl = gen[(gen.month == L) & (gen.case == "central")]
    sl = sol[(sol.month == L) & (sol.case == "central")]
    gk = lambda u: gl[gl.user == u].running_ngn_per_kwh  # noqa: E731
    sk = lambda u: sl[sl.user == u].lcoe_ngn_per_kwh  # noqa: E731
    pc = pay[pay.case == "central"].groupby(["user", "month"]).payback_months.median()
    p24 = pc["household"].loc["2024-01":"2024-12"]
    pl = pay[(pay.month == L) & (pay.user == "household")].pivot_table(index="state", columns="case",
                                                                      values="payback_months")
    up = pay[(pay.month == L) & (pay.user == "household") & (pay.case == "central")]
    base = pri[(pri.weighting == "equal") & (pri.gap_user == "household") &
               (pri.reliance_measure == "primary_source")].sort_values("rank")
    hh_chg = hh("central") / hh("central", "2023-01") - 1
    bz_chg = bz("central") / bz("central", "2023-01") - 1
    return {
        "Latest Month": (L, "2026-05"),
        "KPI P1 HH Value": (naira(hh("central")), "₦85,404"),
        "KPI P1 HH Sub": (f"National median, central · range {naira(hh('low'))}–{naira(hh('high'))}",
                          "National median, central · range ₦13,740–₦407,309"),
        "KPI P1 BZ Value": (naira(bz("central")), "₦1.9m"),
        "KPI P1 BZ Sub": (f"National median, central · range {naira(bz('low'))}–{naira(bz('high'))}",
                          "National median, central · range ₦813,051–₦5.3m"),
        "KPI P1 Change Value": (f"+{hh_chg * 100:.0f}%", "+521%"),
        "KPI P1 Change Sub": (f"Household (petrol) · business (diesel) +{bz_chg * 100:.0f}%",
                              "Household (petrol) · business (diesel) +294%"),
        "Map P1 Max State": (st.idxmax(), "Edo"),
        "Map P1 Max Value": (naira(st.max()), "₦92,061"),
        "Map P1 Min State": (st.idxmin(), "Adamawa"),
        "Map P1 Min Value": (naira(st.min()), "₦78,538"),
        "Map P1 Spread Note": (f"States differ by only about {(st.max() / st.min() - 1) * 100:.0f}%; the colour "
                               "scale is stretched to show the differences", None),
        "Line P1 Note": (f"Shaded band = low–high case, clipped at the top (high case reaches "
                         f"{naira(nat['household']['high'].max())})", None),
        "Gen HH First": (naira(hh("central", "2023-01")), "₦13,752"),
        "Range P2 HH": (f"All 37 states: generator {naira(gk('household').min())}–{naira(gk('household').max())}"
                        f"/kWh · solar {naira(sk('household').min())}–{naira(sk('household').max())}/kWh (central)",
                        "All 37 states: generator ₦2,231–₦2,615/kWh · solar ₦310–₦337/kWh (central)"),
        "Range P2 BZ": (f"All 37 states: generator {naira(gk('business').min())}–{naira(gk('business').max())}"
                        f"/kWh · solar {naira(sk('business').min())}–{naira(sk('business').max())}/kWh (central)",
                        "All 37 states: generator ₦1,213–₦1,627/kWh · solar ₦176–₦202/kWh (central)"),
        "Ref P2 Band A Label": (f"Band A ₦{tar[(tar.month == L) & (tar.band == 'A')].tariff_ngn_per_kwh.median():,.2f}",
                                "Band A ₦209.50"),
        "Ref P2 Band B Label": (f"Band B ₦{tar[(tar.month == L) & (tar.band == 'B')].tariff_ngn_per_kwh.median():,.0f}",
                                "Band B ₦65"),
        "KPI P3 Now Value": (f"{pc[('household', L)]:.1f} months", "10.8 months"),
        "KPI P3 Now Sub": (f"Median of states, central · states {pl['central'].min():.1f}–{pl['central'].max():.1f}; "
                           f"range {pl['low'].min():.1f}–{pl['high'].max():.1f}",
                           "Median of states, central · states 9.6–11.6; range 2.1–39.4"),
        "KPI P3 Start Value": (f"{pc[('household', '2023-06')]:.1f} months", "14.1 months"),
        "KPI P3 Start Sub": (f"Median of states, central · business {pc[('business', '2023-06')]:.1f} months",
                             "Median of states, central · business 16.5 months"),
        "KPI P3 Peak Title": (f"2024 peak ({pd.Period(p24.idxmax(), 'M').strftime('%b %Y')})", "2024 peak (Feb 2024)"),
        "KPI P3 Peak Value": (f"{p24.max():.1f} months", "28.3 months"),
        "Map P3 Max State": (pl["central"].idxmax(), "Osun"),
        "Map P3 Min State": (pl["central"].idxmin(), "Bauchi"),
        "Label P3 HH End": (f"Household {pc[('household', L)]:.1f}", "Household 10.8"),
        "Label P3 BZ End": (f"Business {pc[('business', L)]:.1f}", "Business 9.1"),
        "Note P3 Afford": (f"12 least affordable · whiskers = low–high · all-state median "
                           f"{up.upfront_months_of_consumption.median():.1f}",
                           "12 least affordable · whiskers = low–high · all-state median 2.4"),
        "Takeaway P1": ("Running a small household generator cost a median " + naira(hh("central")) +
                        f" a month in May 2026, {hh_chg * 100:.0f}% more than in January 2023 (central estimate).",
                        "Running a small household generator cost a median ₦85,404 a month in May 2026, 521% more "
                        "than in January 2023 (central estimate)."),
        "Takeaway P2": (f"In May 2026 a small petrol generator cost {naira(gk('household').min())}–"
                        f"{naira(gk('household').max())} per kWh; solar + battery {naira(sk('household').min())}–"
                        f"{naira(sk('household').max())}; grid Band A ₦209.50 where supply exists.",
                        "In May 2026 a small petrol generator cost ₦2,231–₦2,615 per kWh; solar + battery "
                        "₦310–₦337; grid Band A ₦209.50 where supply exists."),
        "Takeaway P3": (f"Solar + battery now pays back in about {pc[('household', L)]:.0f} months for a typical "
                        f"household (median, May 2026), down from {p24.max():.0f} months at the Feb 2024 peak "
                        "(central estimates).",
                        "Solar + battery now pays back in about 11 months for a typical household (median, "
                        "May 2026), down from 28 months at the Feb 2024 peak (central estimates)."),
        "Takeaway P4": (", ".join(base.state.head(2)) + " and " + base.state.iloc[2] +
                        " rank highest; Abia, Edo, FCT stay in the top 10 under all 12 index variants.",
                        "Edo, Delta and Abia rank highest; Abia, Edo, FCT stay in the top 10 under all 12 "
                        "index variants."),
    }


TOP10 = ["Edo", "Delta", "Abia", "Ondo", "Imo", "Akwa Ibom", "FCT", "Oyo", "Ekiti", "Rivers"]
TOP10_ROWS = {  # from the approved page-4 mockup / docs/phase4_audit.md
    "Edo": ("₦91,298", "10.0  (2.3–34.0)", "1.3 months"), "Delta": ("₦88,338", "10.5  (2.4–35.6)", "1.2 months"),
    "Abia": ("₦87,606", "10.5  (2.4–35.7)", "2.0 months"), "Ondo": ("₦84,654", "10.9  (2.5–37.1)", "1.7 months"),
    "Imo": ("₦84,318", "10.9  (2.4–37.1)", "1.4 months"), "Akwa Ibom": ("₦86,265", "10.9  (2.5–36.9)", "2.3 months"),
    "FCT": ("₦84,874", "10.8  (2.4–36.6)", "1.5 months"), "Oyo": ("₦86,849", "10.8  (2.4–36.6)", "1.5 months"),
    "Ekiti": ("₦84,649", "10.9  (2.4–37.0)", "2.2 months"), "Rivers": ("₦83,687", "11.2  (2.5–37.9)", "1.6 months"),
}


def check(pbi: PBI) -> bool:
    exp = expected()
    q = "EVALUATE ROW(" + ", ".join(f'"{k}", [{k}]' for k in exp) + ")"
    got = pbi.dax(q)[0]
    ok_all = True
    rows = []
    for k, (pd_v, quoted) in exp.items():
        dax_v = str(got.get(k, got.get(f"[{k}]", "")))
        if pd_v.startswith("₦") and dax_v.replace(".", "", 1).isdigit():  # numeric measure: format like naira()
            dax_v = naira(float(dax_v))
        ok = dax_v == pd_v and (quoted is None or dax_v == quoted)
        ok_all &= ok
        rows.append((k, dax_v, pd_v, quoted or "-", "OK" if ok else "MISMATCH"))
    # top 10 table
    q = ("EVALUATE TOPN(10, ADDCOLUMNS(VALUES(dim_state[state]), \"r\", [Priority Rank], \"i\", [Priority Index], "
         "\"s\", FORMAT([Saving HH Now], \"#,0\"), \"p\", [Payback HH Now Text], \"u\", [Upfront HH Now Text], "
         "\"b\", [All 12 Badge]), [r], ASC) ORDER BY [r]")
    t10 = pbi.dax(q)
    for r in t10:
        s = r.get("state")
        rank = int(float(r["r"]))
        got_row = (f"₦{r["s"]}", r["p"], r["u"])
        want = TOP10_ROWS.get(s)
        ok = TOP10[rank - 1] == s and got_row == want
        ok_all &= ok
        rows.append((f"Top10 #{rank}", f"{s} idx {float(r["i"]):.2f} | " + " | ".join(got_row) +
                     (f" | {r["b"]}" if r.get("b") else ""), "-", f"{TOP10[rank - 1]} | " +
                     " | ".join(want or ("?",)), "OK" if ok else "MISMATCH"))
    w = max(len(r[0]) for r in rows)
    print(f"\n{'Measure':<{w}}  Result")
    for k, d, p, qv, st in rows:
        print(f"{k:<{w}}  [{st}] DAX: {d}")
        if st != "OK":
            print(f"{'':<{w}}         pandas: {p}\n{'':<{w}}         quoted: {qv}")
    print(f"\n{sum(r[4] == 'OK' for r in rows)}/{len(rows)} checks OK")
    return ok_all


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    p = PBI()
    try:
        if "--check-only" not in sys.argv:
            apply(p)
        good = check(p)
    finally:
        p.close()
    sys.exit(0 if good else 1)
