"""Cost model: generator vs grid vs solar+battery, payback, affordability, priority index.

Follows docs/analysis_plan.md (v1.0 + amendments A1-A8) and docs/parameters.md.
Every result has low / central / high cases (plan 5.9):
  - generator "low" = generator parameters at their low-cost end, "high" the opposite;
  - solar "low" = solar parameters at their low-cost end, "high" the opposite.

Main measures
  - ₦/kWh at the SAME daily energy for generator and solar (central usage, plan 5.1)
  - payback months = solar upfront cost / monthly fuel+maintenance saving (A5)
  - affordability = household upfront cost / monthly household consumption (A5)
  - crossover month: supporting table only (A5)
Solar, payback, affordability and crossover start June 2023 (A7); generator from Jan 2023.

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
BENCHMARK_MONTH = "2026-10"   # month of the 2026 ₦ solar cost benchmarks (A4)
SOLAR_START = "2023-06"       # A7
HORIZON = 10                  # years (plan 5.4)

# ----------------------------------------------------------------------------
# Parameters (docs/parameters.md). Tuples are (low-cost, central, high-cost).
# ----------------------------------------------------------------------------
HH = {"rated_kw": 2.0, "f_rated_lph": (1.0, 1.2, 1.4), "a_noload": (0.15, 0.30, 0.45),
      "maint_share": (0.10, 0.15, 0.25), "purchase_ngn_2026": (265_000, 280_000, 380_000),
      "life_years": (8, 5, 3)}
BIZ = {"rated_kw": 16.0, "curve_mult": (0.95, 1.00, 1.15), "maint_share": (0.05, 0.10, 0.15),
       "purchase_ngn_2026": (None, None, None), "life_years": (12, 8, 6)}
DIESEL_CURVE = ([0.25, 0.50, 0.75, 1.00], [1.9, 2.9, 4.2, 5.8])  # RID 20 S, L/h
USAGE = {  # numeric low / central / high (plan 5.1)
    "household": {"load_kw": (0.26, 0.40, 0.57), "hours": (2, 4, 8), "days": (15, 22, 30)},
    "business": {"load_kw": (4.0, 6.4, 9.6), "hours": (6, 8, 12), "days": (22, 26, 30)},
}
SOLAR = {
    "pv_ngn_per_wp": (190, 260, 350),
    "batt_ngn_per_kwh": (160_000, 255_000, 300_000),
    "inverter_ngn": {"household": (120_000, 175_000, 300_000),        # A8
                     "business": (2_800_000, 3_500_000, 4_200_000)},
    "bos_share": (0.20, 0.30, 0.40),
    "discount": (0.10, 0.15, 0.25),
    "om_share": (0.005, 0.01, 0.02),
    "batt_life": (15, 10, 8),                                        # A3
    "night_share": {"household": (0.5, 0.7, 0.9), "business": (0.1, 0.3, 0.5)},
    "dod": 0.8, "rte": 0.90, "derate": 0.9,
}
CO2_KG_PER_L = {"PMS": 0.745 * 44.3e-3 * 69_300 / 1000, "AGO": 0.840 * 43.0e-3 * 74_100 / 1000}


def idx(case: str) -> int:
    return CASES.index(case)


def e_day(user: str) -> float:
    return USAGE[user]["load_kw"][1] * USAGE[user]["hours"][1]


def kwh_month(user: str) -> float:
    return e_day(user) * USAGE[user]["days"][1]


# ----------------------------------------------------------------------------
# Generator
# ----------------------------------------------------------------------------
def gen_fuel_lph(user: str, load_kw: float, case: str) -> float:
    if user == "household":
        f, a = HH["f_rated_lph"][idx(case)], HH["a_noload"][idx(case)]
        return f * (a + (1 - a) * load_kw / HH["rated_kw"])
    return float(np.interp(load_kw / BIZ["rated_kw"], *DIESEL_CURVE)) * BIZ["curve_mult"][idx(case)]


def generator_costs(prices: pd.DataFrame) -> pd.DataFrame:
    """For ₦/kWh the low-cost case uses the HIGH load (idle fuel spread over more kWh);
    ₦/day and ₦/month (spend view) use usage at the same end as the case."""
    rows = []
    fuel_of = {"household": "PMS", "business": "AGO"}
    for user, par in (("household", HH), ("business", BIZ)):
        pr = prices[prices.fuel == fuel_of[user]][["state", "month", "price_ngn_per_litre", "is_filled"]]
        u = USAGE[user]
        for case in CASES:
            i = idx(case)
            load_c = u["load_kw"][2 - i]
            lph = gen_fuel_lph(user, load_c, case)
            m = par["maint_share"][i]
            load_sp, hrs_sp, days_sp = u["load_kw"][i], u["hours"][i], u["days"][i]
            lph_sp = gen_fuel_lph(user, load_sp, case)
            purchase, life = par["purchase_ngn_2026"][i], par["life_years"][i]
            capex_month = (purchase / (life * 12)) if purchase else np.nan
            d = pr.copy()
            d["user"], d["case"], d["fuel"] = user, case, fuel_of[user]
            d["fuel_l_per_kwh"] = lph / load_c
            d["running_ngn_per_kwh"] = d.price_ngn_per_litre * lph * (1 + m) / load_c
            d["full_ngn_per_kwh"] = d.running_ngn_per_kwh + capex_month / kwh_month(user)
            d["running_ngn_per_day"] = d.price_ngn_per_litre * lph_sp * hrs_sp * (1 + m)
            d["running_ngn_per_month"] = d.running_ngn_per_day * days_sp
            d["full_ngn_per_month"] = d.running_ngn_per_month + capex_month
            d["full_ngn_per_day"] = d.full_ngn_per_month / days_sp
            d["fuel_l_per_month"] = lph_sp * hrs_sp * days_sp
            d["kwh_per_day"] = load_sp * hrs_sp
            rows.append(d)
    out = pd.concat(rows, ignore_index=True).rename(columns={"is_filled": "fuel_price_filled"})
    out["full_cost_note"] = np.where(out.user == "business", "not computed: no 20 kVA diesel price source", "")
    return out


# ----------------------------------------------------------------------------
# Solar + battery
# ----------------------------------------------------------------------------
def pv_factor(r: float, n: int) -> float:
    return sum(1 / (1 + r) ** t for t in range(1, n + 1))


def solar_system(pvout_min: float, fx_ratio: float, user: str, case: str, e: float | None = None) -> dict:
    """System sized for daily energy e (default: central usage of the archetype)."""
    i = idx(case)
    e = e_day(user) if e is None else e
    ns = SOLAR["night_share"][user][i]
    batt_kwh = e * ns / (SOLAR["dod"] * SOLAR["rte"])
    pv_kwp = (e * (1 - ns) + e * ns / SOLAR["rte"]) / (pvout_min * SOLAR["derate"])
    pv_cost = pv_kwp * 1000 * SOLAR["pv_ngn_per_wp"][i] * fx_ratio
    batt_cost = batt_kwh * SOLAR["batt_ngn_per_kwh"][i] * fx_ratio
    inverter = SOLAR["inverter_ngn"][user][i] * fx_ratio
    capex = (pv_cost + batt_cost) * (1 + SOLAR["bos_share"][i]) + inverter
    r, life = SOLAR["discount"][i], SOLAR["batt_life"][i]
    repl = batt_cost / (1 + r) ** life if life < HORIZON else 0.0
    om_year = SOLAR["om_share"][i] * capex
    lcoe = (capex + repl + om_year * pv_factor(r, HORIZON)) / (e * 365 * pv_factor(r, HORIZON))
    return {"lcoe_ngn_per_kwh": lcoe, "capex_ngn": capex, "pv_kwp": pv_kwp, "battery_kwh": batt_kwh,
            "inverter_ngn": inverter, "om_ngn_per_month": om_year / 12}


def solar_costs(pvout, fx, months, fx_scaling=True) -> pd.DataFrame:
    fxm = fx.set_index("month").ngn_per_usd_mean
    worst = pvout.drop_duplicates("state").set_index("state").worst_month_kwh_per_kwp_day
    rows = []
    for st in STATES:
        for m in months:
            ratio = fxm[m] / fxm[BENCHMARK_MONTH] if fx_scaling else 1.0
            for user in ("household", "business"):
                for case in CASES:
                    res = solar_system(worst[st], ratio, user, case)
                    rows.append({"state": st, "month": m, "user": user, "case": case,
                                 "pvout_worst_month": worst[st], "fx_ratio_to_benchmark": round(ratio, 4), **res,
                                 "ngn_per_day": res["lcoe_ngn_per_kwh"] * e_day(user),
                                 "ngn_per_month": res["lcoe_ngn_per_kwh"] * kwh_month(user)})
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------
# Payback and affordability (A5)
# ----------------------------------------------------------------------------
PAIR = {"low": ("low", "high"), "central": ("central", "central"), "high": ("high", "low")}  # (solar, generator)


def payback(gen: pd.DataFrame, sol: pd.DataFrame, cons: pd.DataFrame) -> pd.DataFrame:
    g = gen.set_index(["state", "month", "user", "case"]).running_ngn_per_kwh
    s = sol.set_index(["state", "month", "user", "case"])
    c = cons.set_index(["state", "month", "case"]).consumption_ngn_per_hh_month
    cons_pair = {"low": "high", "central": "central", "high": "low"}  # short payback ↔ high consumption
    rows = []
    for (st, m, user, case) in s.index:
        sc, gc = PAIR[case]
        upfront = s.loc[(st, m, user, sc), "capex_ngn"]
        om = s.loc[(st, m, user, sc), "om_ngn_per_month"]
        gen_month = g[(st, m, user, gc)] * kwh_month(user)
        saving = gen_month - om
        pb = upfront / saving if saving > 0 else np.nan
        row = {"state": st, "month": m, "user": user, "case": case, "upfront_ngn": upfront,
               "generator_fuel_maint_ngn_per_month": gen_month, "solar_om_ngn_per_month": om,
               "saving_ngn_per_month": saving, "payback_months": pb,
               "payback_note": "" if saving > 0 else "no payback (saving <= 0)"}
        if user == "household" and (st, m, cons_pair[case]) in c.index:
            hh = c[(st, m, cons_pair[case])]
            row["hh_consumption_ngn_per_month"] = hh
            row["upfront_months_of_consumption"] = upfront / hh
        else:
            row["hh_consumption_ngn_per_month"] = np.nan
            row["upfront_months_of_consumption"] = np.nan
        rows.append(row)
    out = pd.DataFrame(rows)
    out["pair"] = out.case.map(lambda k: f"solar {PAIR[k][0]} / generator {PAIR[k][1]}")
    return out


# ----------------------------------------------------------------------------
# Crossover (supporting table, A5)
# ----------------------------------------------------------------------------
def first_sustained(months: list[str], cond: list[bool], run: int = 3) -> str | None:
    for k in range(len(cond) - run + 1):
        if all(cond[k:k + run]):
            return months[k]
    return None


def crossover(gen: pd.DataFrame, sol: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (st, user), g in gen.groupby(["state", "user"]):
        sub = sol[(sol.state == st) & (sol.user == user)]
        months = sorted(set(g.month) & set(sub.month))
        s = sub.pivot(index="month", columns="case", values="lcoe_ngn_per_kwh").loc[months]
        for basis, col in (("running", "running_ngn_per_kwh"), ("full", "full_ngn_per_kwh")):
            gx = g.pivot(index="month", columns="case", values=col).loc[months]
            if gx["central"].isna().all():
                rows.append({"state": st, "user": user, "basis": basis, "crossover_month": "not computed",
                             "robust_crossover_month": "not computed", "crossover_at_series_start": None,
                             "robust_at_series_start": None, "solar_cheaper_latest_central": None,
                             "solar_cheaper_latest_robust": None, "first_month": months[0],
                             "latest_month": months[-1], "gap_latest_central_pct": None})
                continue
            c, rb = list(gx["central"] > s["central"]), list(gx["low"] > s["high"])
            cm, rm = first_sustained(months, c), first_sustained(months, rb)
            gap = (gx["central"].iloc[-1] - s["central"].iloc[-1]) / gx["central"].iloc[-1] * 100
            rows.append({"state": st, "user": user, "basis": basis,
                         "crossover_month": cm or "not yet", "robust_crossover_month": rm or "not yet",
                         "crossover_at_series_start": cm == months[0], "robust_at_series_start": rm == months[0],
                         "solar_cheaper_latest_central": bool(c[-1]), "solar_cheaper_latest_robust": bool(rb[-1]),
                         "first_month": months[0], "latest_month": months[-1],
                         "gap_latest_central_pct": round(gap, 1)})
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------
# Market priority index (plan 5.6 + A2 + A6)
# ----------------------------------------------------------------------------
WEIGHTS = {"equal": (1 / 3, 1 / 3, 1 / 3), "reliance_led": (0.5, 0.25, 0.25), "gap_led": (0.25, 0.5, 0.25)}


def pct_rank(s: pd.Series) -> pd.Series:
    return s.rank(method="average") / len(s)


def reliance_with_borno(reliance: pd.DataFrame) -> pd.DataFrame:
    rel = reliance[reliance.state.isin(STATES)].set_index("state").copy()
    ne = [s for s in STATES if ZONE_OF[s] == "North East" and s != "Borno"]
    for col in ["gen_primary_source_pct_of_all_hh", "gen_ownership_pct_hh"]:
        rel.loc["Borno", col] = round(rel.loc[ne, col].mean(), 2)
    rel["reliance_flag"] = np.where(rel.index == "Borno", "Borno: North-East zone average (A2)", "")
    return rel


def priority(reliance, mpi, pay) -> pd.DataFrame:
    rel = reliance_with_borno(reliance)
    latest = pay.month.max()
    out = []
    for user in ("household", "business"):
        sav = pay[(pay.month == latest) & (pay.case == "central") & (pay.user == user)].set_index("state").saving_ngn_per_month
        for rcol, rname in (("gen_primary_source_pct_of_all_hh", "primary_source"), ("gen_ownership_pct_hh", "ownership")):
            df = pd.DataFrame({"R_value": rel[rcol], "G_value": sav.clip(lower=0),
                               "A_value": 1 - mpi.set_index("state").headcount_pct / 100}).loc[STATES]
            for k in "RGA":
                df[f"{k}_rank"] = pct_rank(df[f"{k}_value"])
            for wname, (wr, wg, wa) in WEIGHTS.items():
                d = df.copy()
                d["index"] = d.R_rank ** wr * d.G_rank ** wg * d.A_rank ** wa
                d["rank"] = d["index"].rank(ascending=False, method="min").astype(int)
                d["group"] = pd.qcut(d["index"].rank(method="first"), 5,
                                     labels=["5 (lowest)", "4", "3", "2", "1 (highest)"]).astype(str)
                d["weighting"], d["gap_user"], d["reliance_measure"], d["month"] = wname, user, rname, latest
                d["G_measure"] = "monthly saving, NGN (A6)"
                d["reliance_flag"] = rel.loc[STATES, "reliance_flag"].values
                out.append(d.rename_axis("state").reset_index())
    return pd.concat(out, ignore_index=True)


# ----------------------------------------------------------------------------
# RQ5 (optional): national household generator petrol and CO2, range only
# ----------------------------------------------------------------------------
HOUSEHOLD_SIZE = (5.5, 5.0, 4.5)
NMDPRA_PMS_ML_PER_DAY = 56.74
PLAUSIBLE_MAX_SHARE = 0.35


def rq5(reliance, mpi, gen) -> pd.DataFrame:
    pop_m = mpi.set_index("state").poor_people_million / (mpi.set_index("state").headcount_pct / 100)
    rel = reliance_with_borno(reliance)
    month = "2025-10"
    hh_gen = gen[(gen.user == "household") & (gen.month == month)]
    rows = []
    for case in CASES:
        i = idx(case)
        share = {"low": rel.gen_primary_source_pct_of_all_hh / 100, "high": rel.gen_ownership_pct_hh / 100,
                 "central": (rel.gen_primary_source_pct_of_all_hh + rel.gen_ownership_pct_hh) / 200}[case]
        households = pop_m * 1e6 / HOUSEHOLD_SIZE[i]
        lit = hh_gen[hh_gen.case == case].set_index("state").fuel_l_per_month
        litres = (households * share * lit).sum()
        rows.append({"case": case, "month": month, "households_with_generator_m": (households * share).sum() / 1e6,
                     "petrol_bn_litres_per_month": litres / 1e9,
                     "co2_mt_per_year": litres * 12 * CO2_KG_PER_L["PMS"] / 1e9,
                     "share_of_nmdpra_pms": litres / (NMDPRA_PMS_ML_PER_DAY * 1e6 * 31)})
    df = pd.DataFrame(rows)
    df["consistent_with_national_supply"] = df.share_of_nmdpra_pms <= PLAUSIBLE_MAX_SHARE
    df["note"] = np.where(df.consistent_with_national_supply, "within plausible share of national petrol",
                          "NOT CONSISTENT with NMDPRA national petrol volume")
    df["range_publishable"] = bool(df.consistent_with_national_supply.all())
    return df


# ----------------------------------------------------------------------------
# One-at-a-time sensitivity, latest month, household, one state per zone
# ----------------------------------------------------------------------------
def tornado(prices, pvout, fx) -> pd.DataFrame:
    latest = prices.month.max()
    fxm = fx.set_index("month").ngn_per_usd_mean
    ratio = fxm[latest] / fxm[BENCHMARK_MONTH]
    worst = pvout.drop_duplicates("state").set_index("state").worst_month_kwh_per_kwp_day
    reps = {z: sorted(s for s in ZONE_OF if ZONE_OF[s] == z)[0] for z in sorted(set(ZONE_OF.values()))}
    rows = []
    for zone, st in reps.items():
        price = prices[(prices.fuel == "PMS") & (prices.state == st) & (prices.month == latest)].price_ngn_per_litre.iloc[0]

        def gen_kwh(f=1.2, a=0.30, m=0.15, load=0.40):
            return price * f * (a + (1 - a) * load / 2.0) * (1 + m) / load

        base_g = gen_kwh()
        base_s = solar_system(worst[st], ratio, "household", "central")["lcoe_ngn_per_kwh"]
        for name, (lo, hi) in {"generator F_rated (1.0-1.4 L/h)": (gen_kwh(f=1.0), gen_kwh(f=1.4)),
                               "petrol no-load fraction a (0.15-0.45)": (gen_kwh(a=0.15), gen_kwh(a=0.45)),
                               "household load (0.57-0.26 kW)": (gen_kwh(load=0.57), gen_kwh(load=0.26)),
                               "maintenance (10-25%)": (gen_kwh(m=0.10), gen_kwh(m=0.25))}.items():
            rows.append({"zone": zone, "state": st, "side": "generator", "parameter": name,
                         "low_ngn_per_kwh": lo, "base_ngn_per_kwh": base_g, "high_ngn_per_kwh": hi})
        for key in ("pv_ngn_per_wp", "batt_ngn_per_kwh", "bos_share", "discount", "batt_life", "inverter_ngn", "night_share"):
            saved = SOLAR[key]
            vals = []
            for j in (0, 2):
                if key in ("inverter_ngn", "night_share"):
                    SOLAR[key] = {**saved, "household": tuple(saved["household"][j] for _ in range(3))}
                else:
                    SOLAR[key] = tuple(saved[j] for _ in range(3))
                vals.append(solar_system(worst[st], ratio, "household", "central")["lcoe_ngn_per_kwh"])
                SOLAR[key] = saved
            rows.append({"zone": zone, "state": st, "side": "solar", "parameter": key,
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
    cons = pd.read_csv(P / "household_consumption_state_monthly.csv", dtype={"month": str})
    centroids = pd.read_csv(P / "state_centroids.csv")
    dmap = pd.read_csv(P / "disco_state_map.csv")

    gen_months = sorted(prices.month.unique())
    sol_months = [m for m in gen_months if m >= SOLAR_START]
    gen = generator_costs(prices)
    sol = solar_costs(pvout, fx, sol_months)
    pay = payback(gen, sol, cons)
    cross = crossover(gen, sol)
    cross_nofx = crossover(gen, solar_costs(pvout, fx, sol_months, fx_scaling=False))
    pri = priority(reliance, mpi, pay)
    r5 = rq5(reliance, mpi, gen)
    tor = tornado(prices, pvout, fx)

    OUT.mkdir(parents=True, exist_ok=True)
    PBI.mkdir(parents=True, exist_ok=True)
    for name, df in {"generator_cost": gen, "solar_cost": sol, "payback": pay, "crossover": cross,
                     "crossover_sensitivity_solar_2026_naira": cross_nofx, "priority_index": pri,
                     "rq5_national_range": r5, "sensitivity_tornado": tor}.items():
        df.to_csv(OUT / f"{name}.csv", index=False)

    pv = pvout.drop_duplicates("state").set_index("state")
    rel = reliance_with_borno(reliance)
    dim_state = pd.DataFrame({"state": STATES})
    dim_state["zone"] = dim_state.state.map(ZONE_OF)
    dim_state["discos"] = dim_state.state.map(dmap[dmap.disco != "APLE"].groupby("state").disco.apply(lambda s: "+".join(sorted(s))))
    dim_state["tariff_regulator_note"] = dim_state.state.map(dmap.groupby("state").regulator.apply(lambda s: "; ".join(sorted(set(s)))))
    dim_state["aba_power_note"] = np.where(dim_state.state == "Abia", "Aba ring-fenced area served by Aba Power (APLE); not averaged", "")
    dim_state = dim_state.merge(centroids[["state", "lon", "lat"]], on="state")
    dim_state["pvout_annual_mean"] = dim_state.state.map(pv.annual_mean_kwh_per_kwp_day)
    dim_state["pvout_worst_month"] = dim_state.state.map(pv.worst_month_kwh_per_kwp_day)
    dim_state["mpi_headcount_pct"] = dim_state.state.map(mpi.set_index("state").headcount_pct)
    dim_state["gen_ownership_pct_hh_nlss"] = dim_state.state.map(rel.gen_ownership_pct_hh)
    dim_state["gen_primary_source_pct_hh_nlss"] = dim_state.state.map(rel.gen_primary_source_pct_of_all_hh)
    dim_state["reliance_flag"] = dim_state.state.map(rel.reliance_flag)
    dim_state.to_csv(PBI / "dim_state.csv", index=False)

    dm = pd.DataFrame({"month": gen_months})
    per = pd.PeriodIndex(dm.month, freq="M")
    dm["date"], dm["year"], dm["month_num"] = per.to_timestamp().date, per.year, per.month
    dm["label"] = per.strftime("%b %Y")
    dm["solar_series"] = dm.month >= SOLAR_START
    dm.to_csv(PBI / "dim_month.csv", index=False)

    gen[["state", "month", "user", "case", "fuel", "price_ngn_per_litre", "fuel_price_filled", "running_ngn_per_kwh",
         "full_ngn_per_kwh", "running_ngn_per_day", "full_ngn_per_day", "running_ngn_per_month", "full_ngn_per_month",
         "fuel_l_per_month", "full_cost_note"]].to_csv(PBI / "fact_generator_cost.csv", index=False)
    tariffs.to_csv(PBI / "fact_grid_tariff.csv", index=False)
    sol[["state", "month", "user", "case", "lcoe_ngn_per_kwh", "ngn_per_day", "ngn_per_month", "pv_kwp", "battery_kwh",
         "inverter_ngn", "capex_ngn", "pvout_worst_month", "fx_ratio_to_benchmark"]].to_csv(PBI / "fact_solar_cost.csv", index=False)
    pay.to_csv(PBI / "fact_payback.csv", index=False)
    cross.to_csv(PBI / "fact_crossover.csv", index=False)
    pri.to_csv(PBI / "fact_priority_index.csv", index=False)
    print(f"generator {len(gen)} | solar {len(sol)} | payback {len(pay)} | crossover {len(cross)} | priority {len(pri)}")


if __name__ == "__main__":
    main()
