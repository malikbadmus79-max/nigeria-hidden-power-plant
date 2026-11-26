"""Phase 3 cost model: generator vs grid vs solar+battery, crossover, priority index.

Follows docs/analysis_plan.md (v1.0 + amendments A1-A4) and docs/parameters.md.
Every result has low / central / high cases (plan 5.9):
  - generator "low" = all generator parameters at their low-cost end, "high" the opposite;
  - solar "low" = all solar parameters at their low-cost end, "high" the opposite.

Comparison metric: Naira per kWh delivered, at the SAME daily energy for both options
(daily energy = average load x running hours, plan 5.1). ₦/day and ₦/month are also
reported.

Inputs : data/processed/*.csv (Phase 2) ; Outputs: data/processed/model/*.csv and
data/processed/powerbi/*.csv

Run from repo root:  python src/model.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from states import STATES, ZONE_OF  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
OUT = P / "model"
PBI = P / "powerbi"
CASES = ["low", "central", "high"]
BENCHMARK_MONTH = "2026-10"  # month of the 2026 Naira solar cost benchmarks (A4)
HORIZON = 10                  # years (plan 5.4)

# ----------------------------------------------------------------------------
# Parameters (docs/parameters.md).  Each tuple is (low-cost, central, high-cost)
# value, i.e. already ordered by COST, not by numeric size.
# ----------------------------------------------------------------------------
HH = {  # household, small petrol generator, 2.5 kVA (~2.0 kW rated)
    "rated_kw": 2.0,
    "f_rated_lph": (1.0, 1.2, 1.4),
    "a_noload": (0.15, 0.30, 0.45),          # A3
    "maint_share": (0.10, 0.15, 0.25),
    "purchase_ngn_2026": (265_000, 280_000, 380_000),
    "life_years": (8, 5, 3),                 # A3 (longer life = lower cost)
}
BIZ = {  # small business, diesel 20 kVA prime (16 kW)
    "rated_kw": 16.0,
    "curve_mult": (0.95, 1.00, 1.15),
    "maint_share": (0.05, 0.10, 0.15),
    "purchase_ngn_2026": (None, None, None),  # no source (parameters.md gap)
    "life_years": (12, 8, 6),
}
DIESEL_CURVE = ([0.25, 0.50, 0.75, 1.00], [1.9, 2.9, 4.2, 5.8])  # RID 20 S, L/h

# Usage (plan 5.1): numeric low / central / high
USAGE = {
    "household": {"load_kw": (0.26, 0.40, 0.57), "hours": (2, 4, 8), "days": (15, 22, 30)},
    "business": {"load_kw": (4.0, 6.4, 9.6), "hours": (6, 8, 12), "days": (22, 26, 30)},
}
SOLAR = {  # (low-cost, central, high-cost)
    "pv_ngn_per_wp": (190, 260, 350),
    "batt_ngn_per_kwh": (160_000, 255_000, 300_000),
    "bos_share": (0.20, 0.30, 0.40),
    "discount": (0.10, 0.15, 0.25),
    "om_share": (0.005, 0.01, 0.02),
    "batt_life": (15, 10, 8),                # A3
    "night_share": {"household": (0.5, 0.7, 0.9), "business": (0.1, 0.3, 0.5)},
    "dod": 0.8, "rte": 0.90, "derate": 0.9,
}
CO2_KG_PER_L = {  # IPCC 2006 CO2 factor x NCV x density (parameters.md section 3)
    "PMS": 0.745 * 44.3e-3 * 69_300 / 1000,   # ≈ 2.287 kg/L
    "AGO": 0.840 * 43.0e-3 * 74_100 / 1000,   # ≈ 2.676 kg/L
}


def idx(case: str) -> int:
    return CASES.index(case)


# ----------------------------------------------------------------------------
# Generator
# ----------------------------------------------------------------------------
def gen_fuel_lph(user: str, load_kw: float, case: str) -> float:
    if user == "household":
        f, a = HH["f_rated_lph"][idx(case)], HH["a_noload"][idx(case)]
        return f * (a + (1 - a) * load_kw / HH["rated_kw"])
    lf = load_kw / BIZ["rated_kw"]
    return float(np.interp(lf, *DIESEL_CURVE)) * BIZ["curve_mult"][idx(case)]


def generator_costs(prices: pd.DataFrame) -> pd.DataFrame:
    """Per state x month x user x case: running and full cost, ₦/day, ₦/month, ₦/kWh.

    For ₦/kWh the low-cost case uses the HIGH load (idle fuel spread over more kWh);
    ₦/day and ₦/month use usage at the same end as cost (low = low use).
    """
    rows = []
    fuel_of = {"household": "PMS", "business": "AGO"}
    for user, P_ in (("household", HH), ("business", BIZ)):
        pr = prices[prices.fuel == fuel_of[user]][["state", "month", "price_ngn_per_litre", "is_filled"]]
        u = USAGE[user]
        for case in CASES:
            i = idx(case)
            # energy-matched metric uses central hours/days, load at cost-favourable end
            load_kwh_case = u["load_kw"][2 - i]          # low cost -> high load
            lph = gen_fuel_lph(user, load_kwh_case, case)
            m = P_["maint_share"][i]
            # spend view: usage at the same end as the case
            load_sp, hrs_sp, days_sp = u["load_kw"][i], u["hours"][i], u["days"][i]
            lph_sp = gen_fuel_lph(user, load_sp, case)
            purchase, life = P_["purchase_ngn_2026"][i], P_["life_years"][i]
            capex_month = (purchase / (life * 12)) if purchase else np.nan
            d = pr.copy()
            d["user"], d["case"], d["fuel"] = user, case, fuel_of[user]
            d["fuel_l_per_kwh"] = lph / load_kwh_case
            d["running_ngn_per_kwh"] = d.price_ngn_per_litre * lph * (1 + m) / load_kwh_case
            # full cost per kWh at central usage: capex spread over central monthly kWh
            kwh_month_c = u["load_kw"][1] * u["hours"][1] * u["days"][1]
            d["full_ngn_per_kwh"] = d.running_ngn_per_kwh + capex_month / kwh_month_c
            d["running_ngn_per_day"] = d.price_ngn_per_litre * lph_sp * hrs_sp * (1 + m)
            d["running_ngn_per_month"] = d.running_ngn_per_day * days_sp
            d["full_ngn_per_month"] = d.running_ngn_per_month + capex_month
            d["full_ngn_per_day"] = d.full_ngn_per_month / days_sp
            d["fuel_l_per_month"] = lph_sp * hrs_sp * days_sp
            d["kwh_per_day"] = load_sp * hrs_sp
            rows.append(d)
    out = pd.concat(rows, ignore_index=True)
    out = out.rename(columns={"is_filled": "fuel_price_filled"})
    out["full_cost_note"] = np.where(out.user == "business", "not computed: no 20 kVA diesel price source", "")
    return out


# ----------------------------------------------------------------------------
# Solar + battery
# ----------------------------------------------------------------------------
def crf_pv(r: float, n: int) -> float:
    return sum(1 / (1 + r) ** t for t in range(1, n + 1))


def solar_lcoe_ngn_per_kwh(pvout_min: float, fx_ratio: float, user: str, case: str) -> dict:
    """LCOE for a system sized for 1 kWh/day (LCOE is independent of size)."""
    i = idx(case)
    ns = SOLAR["night_share"][user][i]
    e = 1.0
    batt_kwh = e * ns / (SOLAR["dod"] * SOLAR["rte"])
    pv_kwp = (e * (1 - ns) + e * ns / SOLAR["rte"]) / (pvout_min * SOLAR["derate"])
    pv_cost = pv_kwp * 1000 * SOLAR["pv_ngn_per_wp"][i] * fx_ratio
    batt_cost = batt_kwh * SOLAR["batt_ngn_per_kwh"][i] * fx_ratio
    capex = (pv_cost + batt_cost) * (1 + SOLAR["bos_share"][i])
    r, life = SOLAR["discount"][i], SOLAR["batt_life"][i]
    repl = batt_cost / (1 + r) ** life if life < HORIZON else 0.0
    om = SOLAR["om_share"][i] * capex * crf_pv(r, HORIZON)
    energy_pv = e * 365 * crf_pv(r, HORIZON)
    return {"lcoe_ngn_per_kwh": (capex + repl + om) / energy_pv, "capex_ngn_per_kwh_day": capex,
            "pv_kwp_per_kwh_day": pv_kwp, "batt_kwh_per_kwh_day": batt_kwh}


def solar_costs(pvout: pd.DataFrame, fx: pd.DataFrame, months: list[str], fx_scaling: bool = True) -> pd.DataFrame:
    """fx_scaling=True applies A4 (constant US$ price); False holds 2026 Naira prices (sensitivity)."""
    fxm = fx.set_index("month").ngn_per_usd_mean
    worst = pvout.drop_duplicates("state").set_index("state").worst_month_kwh_per_kwp_day
    rows = []
    for st in STATES:
        for m in months:
            ratio = fxm[m] / fxm[BENCHMARK_MONTH] if fx_scaling else 1.0  # A4: constant US$ price
            for user in ("household", "business"):
                e_day = USAGE[user]["load_kw"][1] * USAGE[user]["hours"][1]
                for case in CASES:
                    res = solar_lcoe_ngn_per_kwh(worst[st], ratio, user, case)
                    rows.append({"state": st, "month": m, "user": user, "case": case,
                                 "pvout_worst_month": worst[st], "fx_ratio_to_benchmark": round(ratio, 4),
                                 **res, "ngn_per_day": res["lcoe_ngn_per_kwh"] * e_day,
                                 "ngn_per_month": res["lcoe_ngn_per_kwh"] * e_day * USAGE[user]["days"][1],
                                 "pv_kwp": res["pv_kwp_per_kwh_day"] * e_day,
                                 "battery_kwh": res["batt_kwh_per_kwh_day"] * e_day,
                                 "capex_ngn": res["capex_ngn_per_kwh_day"] * e_day})
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------
# Crossover (plan 5.5)
# ----------------------------------------------------------------------------
def first_sustained(months: list[str], cond: list[bool], run: int = 3) -> str | None:
    """First month from which `cond` holds for `run` consecutive months."""
    for k in range(len(cond) - run + 1):
        if all(cond[k:k + run]):
            return months[k]
    return None


def crossover(gen: pd.DataFrame, sol: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (st, user), g in gen.groupby(["state", "user"]):
        months = sorted(g.month.unique())
        gc = g.pivot(index="month", columns="case", values="running_ngn_per_kwh").loc[months]
        gf = g.pivot(index="month", columns="case", values="full_ngn_per_kwh").loc[months]
        s = sol[(sol.state == st) & (sol.user == user)].pivot(index="month", columns="case",
                                                                values="lcoe_ngn_per_kwh").loc[months]
        for basis, gx in (("running", gc), ("full", gf)):
            if gx["central"].isna().all():
                rows.append({"state": st, "user": user, "basis": basis, "crossover_month": "not computed",
                             "robust_crossover_month": "not computed", "crossover_at_series_start": None,
                             "robust_at_series_start": None, "solar_cheaper_latest_central": None,
                             "solar_cheaper_latest_robust": None, "latest_month": months[-1],
                             "gap_latest_central_pct": None})
                continue
            c = list(gx["central"] > s["central"])
            rb = list(gx["low"] > s["high"])
            cm, rm = first_sustained(months, c), first_sustained(months, rb)
            gap = (gx["central"].iloc[-1] - s["central"].iloc[-1]) / gx["central"].iloc[-1] * 100
            rows.append({"state": st, "user": user, "basis": basis,
                         "crossover_month": cm or "not yet", "robust_crossover_month": rm or "not yet",
                         "crossover_at_series_start": cm == months[0],
                         "robust_at_series_start": rm == months[0],
                         "solar_cheaper_latest_central": bool(c[-1]), "solar_cheaper_latest_robust": bool(rb[-1]),
                         "latest_month": months[-1], "gap_latest_central_pct": round(gap, 1)})
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------
# Market priority index (plan 5.6 + A2)
# ----------------------------------------------------------------------------
WEIGHTS = {"equal": (1 / 3, 1 / 3, 1 / 3), "reliance_led": (0.5, 0.25, 0.25), "gap_led": (0.25, 0.5, 0.25)}


def pct_rank(s: pd.Series) -> pd.Series:
    return s.rank(method="average") / len(s)


def priority(reliance: pd.DataFrame, mpi: pd.DataFrame, gen: pd.DataFrame, sol: pd.DataFrame) -> pd.DataFrame:
    rel = reliance[reliance.state.isin(STATES)].set_index("state")
    rel["zone"] = rel.index.map(ZONE_OF)
    # A2: Borno takes the North-East zone average (other NE states), flagged
    for col in ["gen_primary_source_pct_of_all_hh", "gen_ownership_pct_hh"]:
        ne = rel[(rel.zone == "North East") & rel[col].notna()][col].mean()
        rel.loc["Borno", col] = round(ne, 2)
    rel["reliance_flag"] = np.where(rel.index == "Borno", "Borno: North-East zone average (A2)", "")
    latest = gen.month.max()
    out = []
    for user in ("household", "business"):
        g = gen[(gen.month == latest) & (gen.case == "central") & (gen.user == user)].set_index("state").running_ngn_per_kwh
        s = sol[(sol.month == latest) & (sol.case == "central") & (sol.user == user)].set_index("state").lcoe_ngn_per_kwh
        gap = ((g - s) / g).clip(lower=0)
        for rcol, rname in (("gen_primary_source_pct_of_all_hh", "primary_source"), ("gen_ownership_pct_hh", "ownership")):
            df = pd.DataFrame({"R_value": rel[rcol], "G_value": gap, "A_value": 1 - mpi.set_index("state").headcount_pct / 100})
            df = df.loc[STATES]
            for k in "RGA":
                df[f"{k}_rank"] = pct_rank(df[f"{k}_value"])
            for wname, (wr, wg, wa) in WEIGHTS.items():
                d = df.copy()
                d["index"] = d.R_rank ** wr * d.G_rank ** wg * d.A_rank ** wa
                d["rank"] = d["index"].rank(ascending=False, method="min").astype(int)
                d["group"] = pd.qcut(d["index"].rank(method="first"), 5, labels=["5 (lowest)", "4", "3", "2", "1 (highest)"])
                d["weighting"], d["gap_user"], d["reliance_measure"] = wname, user, rname
                d["reliance_flag"] = rel.loc[STATES, "reliance_flag"]
                d["month"] = latest
                out.append(d.reset_index().rename(columns={"index": "state"} if "state" not in d.reset_index() else {}))
    res = pd.concat(out, ignore_index=True)
    if "level_0" in res:
        res = res.drop(columns="level_0")
    return res


# ----------------------------------------------------------------------------
# RQ5 (optional): national household generator petrol use and CO2, range only
# ----------------------------------------------------------------------------
HOUSEHOLD_SIZE = (5.5, 5.0, 4.5)            # persons per household (J; fewer households at low end)
NMDPRA_PMS_ML_PER_DAY = 56.74               # NMDPRA Fact Sheet Oct 2025, average daily PMS consumption
PLAUSIBLE_MAX_SHARE = 0.35                  # J: households' generators <= 35% of national petrol


def rq5(reliance: pd.DataFrame, mpi: pd.DataFrame, gen: pd.DataFrame) -> pd.DataFrame:
    pop_m = (mpi.set_index("state").poor_people_million / (mpi.set_index("state").headcount_pct / 100))
    rel = reliance[reliance.state.isin(STATES)].set_index("state")
    ne = rel.loc[[s for s in ZONE_OF if ZONE_OF[s] == "North East" and s != "Borno"]]
    rel.loc["Borno", "gen_primary_source_pct_of_all_hh"] = ne.gen_primary_source_pct_of_all_hh.mean()
    rel.loc["Borno", "gen_ownership_pct_hh"] = ne.gen_ownership_pct_hh.mean()
    month = "2025-10"
    hh_gen = gen[(gen.user == "household") & (gen.month == month)]
    rows = []
    for case, share_col in (("low", "gen_primary_source_pct_of_all_hh"), ("central", None), ("high", "gen_ownership_pct_hh")):
        i = idx(case)
        if share_col:
            share = rel[share_col] / 100
        else:
            share = (rel.gen_primary_source_pct_of_all_hh + rel.gen_ownership_pct_hh) / 200
        households = pop_m * 1e6 / HOUSEHOLD_SIZE[i]
        lit = hh_gen[hh_gen.case == case].set_index("state").fuel_l_per_month
        litres_month = (households * share * lit).sum()
        rows.append({"case": case, "month": month, "households_with_generator_m": (households * share).sum() / 1e6,
                     "petrol_bn_litres_per_month": litres_month / 1e9,
                     "co2_mt_per_year": litres_month * 12 * CO2_KG_PER_L["PMS"] / 1e9,
                     "share_of_nmdpra_pms": litres_month / (NMDPRA_PMS_ML_PER_DAY * 1e6 * 31)})
    df = pd.DataFrame(rows)
    df["consistent_with_national_supply"] = df.share_of_nmdpra_pms <= PLAUSIBLE_MAX_SHARE
    df["note"] = np.where(df.consistent_with_national_supply, "within plausible share of national petrol",
                          "NOT CONSISTENT with NMDPRA national petrol volume")
    df["range_publishable"] = bool(df.consistent_with_national_supply.all())
    return df


# ----------------------------------------------------------------------------
# One-at-a-time sensitivity (plan 5.9), latest month, household, one state per zone
# ----------------------------------------------------------------------------
def tornado(prices: pd.DataFrame, pvout: pd.DataFrame, fx: pd.DataFrame) -> pd.DataFrame:
    latest = prices.month.max()
    fxm = fx.set_index("month").ngn_per_usd_mean
    ratio = fxm[latest] / fxm[BENCHMARK_MONTH]
    worst = pvout.drop_duplicates("state").set_index("state").worst_month_kwh_per_kwp_day
    reps = {}
    for z in sorted(set(ZONE_OF.values())):
        reps[z] = sorted(s for s in ZONE_OF if ZONE_OF[s] == z)[0]
    rows = []
    for zone, st in reps.items():
        price = prices[(prices.fuel == "PMS") & (prices.state == st) & (prices.month == latest)].price_ngn_per_litre.iloc[0]

        def gen_kwh(f=1.2, a=0.30, m=0.15, load=0.40):
            return price * f * (a + (1 - a) * load / 2.0) * (1 + m) / load

        base_g = gen_kwh()
        base_s = solar_lcoe_ngn_per_kwh(worst[st], ratio, "household", "central")["lcoe_ngn_per_kwh"]
        tests = {
            "generator F_rated (1.0-1.4 L/h)": [gen_kwh(f=1.0), gen_kwh(f=1.4)],
            "petrol no-load fraction a (0.15-0.45)": [gen_kwh(a=0.15), gen_kwh(a=0.45)],
            "household load (0.57-0.26 kW)": [gen_kwh(load=0.57), gen_kwh(load=0.26)],
            "maintenance (10-25%)": [gen_kwh(m=0.10), gen_kwh(m=0.25)],
        }
        for name, (lo, hi) in tests.items():
            rows.append({"zone": zone, "state": st, "side": "generator", "parameter": name,
                         "low_ngn_per_kwh": lo, "base_ngn_per_kwh": base_g, "high_ngn_per_kwh": hi})
        saved = {k: SOLAR[k] for k in ("pv_ngn_per_wp", "batt_ngn_per_kwh", "bos_share", "discount", "batt_life")}
        for key in saved:
            vals = []
            for j in (0, 2):
                SOLAR[key] = tuple(saved[key][j] for _ in range(3))
                vals.append(solar_lcoe_ngn_per_kwh(worst[st], ratio, "household", "central")["lcoe_ngn_per_kwh"])
                SOLAR[key] = saved[key]
            rows.append({"zone": zone, "state": st, "side": "solar", "parameter": key,
                         "low_ngn_per_kwh": vals[0], "base_ngn_per_kwh": base_s, "high_ngn_per_kwh": vals[1]})
        ns0 = SOLAR["night_share"]["household"]
        vals = []
        for j in (0, 2):
            SOLAR["night_share"]["household"] = tuple(ns0[j] for _ in range(3))
            vals.append(solar_lcoe_ngn_per_kwh(worst[st], ratio, "household", "central")["lcoe_ngn_per_kwh"])
        SOLAR["night_share"]["household"] = ns0
        rows.append({"zone": zone, "state": st, "side": "solar", "parameter": "night share (0.5-0.9)",
                     "low_ngn_per_kwh": vals[0], "base_ngn_per_kwh": base_s, "high_ngn_per_kwh": vals[1]})
    t = pd.DataFrame(rows)
    t["swing"] = (t.high_ngn_per_kwh - t.low_ngn_per_kwh).abs()
    t["month"] = latest
    return t


# ----------------------------------------------------------------------------
def main() -> None:
    prices = pd.read_csv(P / "fuel_prices_state_monthly.csv", dtype={"month": str})
    tariffs = pd.read_csv(P / "grid_tariff_state_monthly.csv", dtype={"month": str})
    pvout = pd.read_csv(P / "solar_pvout_state_monthly.csv")
    fx = pd.read_csv(P / "fx_ngn_usd_monthly.csv", dtype={"month": str})
    reliance = pd.read_csv(P / "generator_reliance_state.csv")
    mpi = pd.read_csv(P / "mpi_2022_state.csv")
    centroids = pd.read_csv(P / "state_centroids.csv")
    dmap = pd.read_csv(P / "disco_state_map.csv")

    months = sorted(prices.month.unique())
    gen = generator_costs(prices)
    sol = solar_costs(pvout, fx, months)
    cross = crossover(gen, sol)
    cross_nofx = crossover(gen, solar_costs(pvout, fx, months, fx_scaling=False))
    pri = priority(reliance, mpi, gen, sol)
    r5 = rq5(reliance, mpi, gen)
    tor = tornado(prices, pvout, fx)

    OUT.mkdir(parents=True, exist_ok=True)
    PBI.mkdir(parents=True, exist_ok=True)
    gen.to_csv(OUT / "generator_cost.csv", index=False)
    sol.to_csv(OUT / "solar_cost.csv", index=False)
    cross.to_csv(OUT / "crossover.csv", index=False)
    cross_nofx.to_csv(OUT / "crossover_sensitivity_solar_2026_naira.csv", index=False)
    pri.to_csv(OUT / "priority_index.csv", index=False)
    r5.to_csv(OUT / "rq5_national_range.csv", index=False)
    tor.to_csv(OUT / "sensitivity_tornado.csv", index=False)

    # ---- Power BI tables ----
    pv = pvout.drop_duplicates("state").set_index("state")
    rel = reliance.set_index("state")
    dim_state = pd.DataFrame({"state": STATES})
    dim_state["zone"] = dim_state.state.map(ZONE_OF)
    dim_state["discos"] = dim_state.state.map(
        dmap[dmap.disco != "APLE"].groupby("state").disco.apply(lambda s: "+".join(sorted(s))))
    dim_state["tariff_regulator_note"] = dim_state.state.map(
        dmap.groupby("state").regulator.apply(lambda s: "; ".join(sorted(set(s)))))
    dim_state = dim_state.merge(centroids[["state", "lon", "lat"]], on="state")
    dim_state["pvout_annual_mean"] = dim_state.state.map(pv.annual_mean_kwh_per_kwp_day)
    dim_state["pvout_worst_month"] = dim_state.state.map(pv.worst_month_kwh_per_kwp_day)
    dim_state["mpi_headcount_pct"] = dim_state.state.map(mpi.set_index("state").headcount_pct)
    dim_state["gen_ownership_pct_hh_nlss"] = dim_state.state.map(rel.gen_ownership_pct_hh)
    dim_state["gen_primary_source_pct_hh_nlss"] = dim_state.state.map(rel.gen_primary_source_pct_of_all_hh)
    dim_state.to_csv(PBI / "dim_state.csv", index=False)

    dm = pd.DataFrame({"month": months})
    per = pd.PeriodIndex(dm.month, freq="M")
    dm["date"], dm["year"], dm["month_num"] = per.to_timestamp().date, per.year, per.month
    dm["label"] = per.strftime("%b %Y")
    dm.to_csv(PBI / "dim_month.csv", index=False)

    keep_g = ["state", "month", "user", "case", "fuel", "price_ngn_per_litre", "fuel_price_filled",
              "running_ngn_per_kwh", "full_ngn_per_kwh", "running_ngn_per_day", "full_ngn_per_day",
              "running_ngn_per_month", "full_ngn_per_month", "fuel_l_per_month", "full_cost_note"]
    gen[keep_g].to_csv(PBI / "fact_generator_cost.csv", index=False)
    tariffs.to_csv(PBI / "fact_grid_tariff.csv", index=False)
    sol[["state", "month", "user", "case", "lcoe_ngn_per_kwh", "ngn_per_day", "ngn_per_month", "pv_kwp",
         "battery_kwh", "capex_ngn", "pvout_worst_month", "fx_ratio_to_benchmark"]].to_csv(PBI / "fact_solar_cost.csv", index=False)
    cross.to_csv(PBI / "fact_crossover.csv", index=False)
    pri.to_csv(PBI / "fact_priority_index.csv", index=False)
    print("generator rows", len(gen), "| solar rows", len(sol), "| crossover rows", len(cross), "| priority rows", len(pri))
    print(r5.to_string(index=False))


if __name__ == "__main__":
    main()
