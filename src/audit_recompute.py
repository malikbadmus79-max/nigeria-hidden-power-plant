"""Phase 4 audit, item 1: independent recomputation of 10 random state-month-user rows.

Written separately from src/model.py: parameters are re-entered here from
docs/parameters.md and the amendments; nothing is imported from model.py. Inputs are
the Phase 2 processed tables. For each sampled row and each case (low / central /
high) it recomputes:
  generator running ₦/kWh, solar upfront cost, solar LCOE, monthly saving, payback
  months and (households) upfront cost in months of consumption,
and compares them with data/processed/model/{generator_cost,solar_cost,payback}.csv.

Output: data/processed/model/audit_recompute.csv ; exits non-zero on any mismatch.
Run from repo root:  python src/audit_recompute.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
SEED, N, TOL = 20261127, 10, 1e-6

# --- parameters re-entered by hand (docs/parameters.md, A3, A8) ---------------------
# order: low-cost, central, high-cost
PETROL = dict(f=[1.0, 1.2, 1.4], a=[0.15, 0.30, 0.45], maint=[0.10, 0.15, 0.25], rated=2.0)
DIESEL_PTS = [(0.25, 1.9), (0.50, 2.9), (0.75, 4.2), (1.00, 5.8)]
DIESEL = dict(mult=[0.95, 1.0, 1.15], maint=[0.05, 0.10, 0.15], rated=16.0)
LOAD = {"household": [0.26, 0.40, 0.57], "business": [4.0, 6.4, 9.6]}
CENTRAL_KWH_DAY = {"household": 0.40 * 4, "business": 6.4 * 8}
CENTRAL_DAYS = {"household": 22, "business": 26}
PV_WP = [190, 260, 350]
BATT_KWH = [160_000, 255_000, 300_000]
INVERTER = {"household": [120_000, 175_000, 300_000], "business": [2_800_000, 3_500_000, 4_200_000]}
BOS = [0.20, 0.30, 0.40]
RATE = [0.10, 0.15, 0.25]
OM = [0.005, 0.01, 0.02]
BLIFE = [15, 10, 8]
NIGHT = {"household": [0.5, 0.7, 0.9], "business": [0.1, 0.3, 0.5]}
CASE = {"low": 0, "central": 1, "high": 2}


def diesel_lph(lf: float) -> float:
    for (x0, y0), (x1, y1) in zip(DIESEL_PTS, DIESEL_PTS[1:]):
        if x0 <= lf <= x1:
            return y0 + (y1 - y0) * (lf - x0) / (x1 - x0)
    raise ValueError(lf)


def gen_kwh(user: str, price: float, k: int) -> float:
    load = LOAD[user][2 - k]                       # low-cost case uses the high load
    if user == "household":
        lph = PETROL["f"][k] * (PETROL["a"][k] + (1 - PETROL["a"][k]) * load / PETROL["rated"])
        return price * lph * (1 + PETROL["maint"][k]) / load
    lph = diesel_lph(load / DIESEL["rated"]) * DIESEL["mult"][k]
    return price * lph * (1 + DIESEL["maint"][k]) / load


def solar(user: str, pvout_min: float, fxr: float, k: int) -> tuple[float, float, float]:
    e = CENTRAL_KWH_DAY[user]
    ns = NIGHT[user][k]
    batt = e * ns / (0.8 * 0.9)
    pv = (e * (1 - ns) + e * ns / 0.9) / (pvout_min * 0.9)
    pv_c, b_c = pv * 1000 * PV_WP[k] * fxr, batt * BATT_KWH[k] * fxr
    capex = (pv_c + b_c) * (1 + BOS[k]) + INVERTER[user][k] * fxr
    r = RATE[k]
    ann = sum((1 + r) ** -t for t in range(1, 11))
    repl = b_c * (1 + r) ** -BLIFE[k] if BLIFE[k] < 10 else 0.0
    lcoe = (capex + repl + OM[k] * capex * ann) / (e * 365 * ann)
    return capex, lcoe, OM[k] * capex / 12


def main() -> None:
    prices = pd.read_csv(P / "fuel_prices_state_monthly.csv", dtype={"month": str}).set_index(["fuel", "state", "month"]).price_ngn_per_litre
    fx = pd.read_csv(P / "fx_ngn_usd_monthly.csv", dtype={"month": str}).set_index("month").ngn_per_usd_mean
    pvout = pd.read_csv(P / "solar_pvout_state_monthly.csv").groupby("state").pvout_kwh_per_kwp_day.min()
    cons = pd.read_csv(P / "household_consumption_state_monthly.csv", dtype={"month": str}).set_index(["state", "month", "case"]).consumption_ngn_per_hh_month
    gen = pd.read_csv(P / "model" / "generator_cost.csv", dtype={"month": str}).set_index(["state", "month", "user", "case"])
    sol = pd.read_csv(P / "model" / "solar_cost.csv", dtype={"month": str}).set_index(["state", "month", "user", "case"])
    pay = pd.read_csv(P / "model" / "payback.csv", dtype={"month": str}).set_index(["state", "month", "user", "case"])

    keys = pay.reset_index()[["state", "month", "user"]].drop_duplicates().sample(N, random_state=SEED)
    rows, bad = [], 0
    for _, kr in keys.iterrows():
        st, m, user = kr.state, kr.month, kr.user
        fuel = "PMS" if user == "household" else "AGO"
        fxr = fx[m] / fx["2026-10"]
        for case, k in CASE.items():
            g = gen_kwh(user, prices[(fuel, st, m)], k)
            capex, lcoe, om = solar(user, pvout[st], fxr, k)
            # payback pairs: low = solar low-cost with generator high-cost, high = the reverse
            ks, kg = {"low": (0, 2), "central": (1, 1), "high": (2, 0)}[case]
            capex_p, _, om_p = solar(user, pvout[st], fxr, ks)
            saving = gen_kwh(user, prices[(fuel, st, m)], kg) * CENTRAL_KWH_DAY[user] * CENTRAL_DAYS[user] - om_p
            pb = capex_p / saving
            aff = capex_p / cons[(st, m, {"low": "high", "central": "central", "high": "low"}[case])] if user == "household" else float("nan")
            checks = {
                "generator_running_ngn_per_kwh": (g, gen.loc[(st, m, user, case), "running_ngn_per_kwh"]),
                "solar_capex_ngn": (capex, sol.loc[(st, m, user, case), "capex_ngn"]),
                "solar_lcoe_ngn_per_kwh": (lcoe, sol.loc[(st, m, user, case), "lcoe_ngn_per_kwh"]),
                "saving_ngn_per_month": (saving, pay.loc[(st, m, user, case), "saving_ngn_per_month"]),
                "payback_months": (pb, pay.loc[(st, m, user, case), "payback_months"]),
                "upfront_months_of_consumption": (aff, pay.loc[(st, m, user, case), "upfront_months_of_consumption"]),
            }
            for name, (mine, theirs) in checks.items():
                both_nan = pd.isna(mine) and pd.isna(theirs)
                ok = both_nan or abs(mine - theirs) <= TOL * max(1.0, abs(theirs))
                bad += not ok
                rows.append({"state": st, "month": m, "user": user, "case": case, "measure": name,
                             "independent": mine, "model": theirs, "match": ok})
    out = pd.DataFrame(rows)
    out.to_csv(P / "model" / "audit_recompute.csv", index=False)
    print(keys.to_string(index=False))
    print(f"{len(out)} values compared, {bad} mismatches")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
