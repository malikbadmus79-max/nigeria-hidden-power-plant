"""Checks on the Phase 3 model outputs and logic.

Run from repo root:  python -m pytest -q   (after: python src/model.py)
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import model  # noqa: E402
from states import STATES, ZONE_OF  # noqa: E402

M = ROOT / "data" / "processed" / "model"
PBI = ROOT / "data" / "processed" / "powerbi"


def load(path):
    if not path.exists():
        pytest.skip(f"{path.name} not built; run python src/model.py")
    return pd.read_csv(path, dtype={"month": str})


@pytest.fixture(scope="module")
def gen():
    return load(M / "generator_cost.csv")


@pytest.fixture(scope="module")
def sol():
    return load(M / "solar_cost.csv")


@pytest.fixture(scope="module")
def pay():
    return load(M / "payback.csv")


def test_every_state_month_present(gen, sol, pay):
    gen_months = sorted(gen.month.unique())
    sol_months = [m for m in gen_months if m >= "2023-06"]  # A7
    assert gen_months[0] == "2023-01" and sorted(sol.month.unique()) == sol_months
    for df, months in ((gen, gen_months), (sol, sol_months), (pay, sol_months)):
        assert len(df) == len(STATES) * len(months) * 2 * 3
        assert not df.duplicated(["state", "month", "user", "case"]).any()
        assert (df.groupby(["month", "user", "case"]).state.nunique() == 37).all()


def _ordered(df, value):
    w = df.pivot_table(index=["state", "month", "user"], columns="case", values=value)
    w = w.dropna()
    return ((w["low"] <= w["central"] + 1e-9) & (w["central"] <= w["high"] + 1e-9)).all()


@pytest.mark.parametrize("col", ["running_ngn_per_kwh", "full_ngn_per_kwh", "running_ngn_per_day",
                                 "running_ngn_per_month", "full_ngn_per_month"])
def test_generator_low_le_central_le_high(gen, col):
    assert _ordered(gen, col)


@pytest.mark.parametrize("col", ["lcoe_ngn_per_kwh", "ngn_per_day", "capex_ngn", "inverter_ngn"])
def test_solar_low_le_central_le_high(sol, col):
    assert _ordered(sol, col)


@pytest.mark.parametrize("col", ["payback_months", "upfront_ngn", "upfront_months_of_consumption"])
def test_payback_low_le_central_le_high(pay, col):
    assert _ordered(pay, col)


def test_payback_consistent(pay):
    assert (pay.saving_ngn_per_month > 0).all()
    calc = pay.upfront_ngn / pay.saving_ngn_per_month
    assert np.allclose(calc, pay.payback_months)
    hh = pay[pay.user == "household"]
    assert hh.upfront_months_of_consumption.notna().all()
    assert pay[pay.user == "business"].upfront_months_of_consumption.isna().all()


def test_no_negative_costs(gen, sol):
    for c in ["running_ngn_per_kwh", "running_ngn_per_day", "running_ngn_per_month", "fuel_l_per_month"]:
        assert (gen[c] >= 0).all()
    assert (gen.full_ngn_per_kwh.dropna() >= 0).all()
    for c in ["lcoe_ngn_per_kwh", "ngn_per_day", "capex_ngn", "pv_kwp", "battery_kwh", "inverter_ngn"]:
        assert (sol[c] > 0).all()


def test_business_full_cost_not_invented(gen):
    b = gen[gen.user == "business"]
    assert b.full_ngn_per_kwh.isna().all()


# ---------- crossover logic on a hand-made example ----------
def test_first_sustained_hand_example():
    months = ["2024-01", "2024-02", "2024-03", "2024-04", "2024-05", "2024-06"]
    # true in Feb only, then from Apr for 3 months -> crossover Apr
    assert model.first_sustained(months, [False, True, False, True, True, True]) == "2024-04"
    # never 3 in a row -> None
    assert model.first_sustained(months, [True, True, False, True, True, False]) is None
    # true from the start
    assert model.first_sustained(months, [True] * 6) == "2024-01"


def test_crossover_function_hand_example():  # noqa: D103
    months = ["2024-01", "2024-02", "2024-03", "2024-04", "2024-05"]
    gen_vals = {"low": [50, 80, 120, 130, 140], "central": [100, 200, 210, 220, 90],
                "high": [150, 300, 320, 330, 340]}
    sol_vals = {"low": [10, 10, 10, 10, 10], "central": [150, 150, 150, 150, 150],
                "high": [100, 100, 100, 100, 100]}
    g = pd.DataFrame([{"state": "X", "user": "household", "month": m, "case": c,
                       "running_ngn_per_kwh": v[i], "full_ngn_per_kwh": v[i] + 1}
                      for c, v in gen_vals.items() for i, m in enumerate(months)])
    s = pd.DataFrame([{"state": "X", "user": "household", "month": m, "case": c, "lcoe_ngn_per_kwh": v[i]}
                      for c, v in sol_vals.items() for i, m in enumerate(months)])
    r = model.crossover(g, s)
    run = r[r.basis == "running"].iloc[0]
    # central gen > central solar in Feb, Mar, Apr -> crossover Feb
    assert run.crossover_month == "2024-02"
    # robust: gen low > solar high in Mar, Apr, May -> robust crossover Mar
    assert run.robust_crossover_month == "2024-03"
    assert not run.solar_cheaper_latest_central  # May: 90 < 150
    assert run.solar_cheaper_latest_robust


def test_crossover_table_complete():
    c = load(M / "crossover.csv")
    assert len(c) == 37 * 2 * 2
    assert (c.first_month == "2023-06").all()  # A7
    ok = c.crossover_month.str.match(r"^\d{4}-\d{2}$") | c.crossover_month.isin(["not yet", "not computed"])
    assert ok.all()


# ---------- priority index ----------
def test_index_ranks_complete():
    p = load(M / "priority_index.csv")
    for key, g in p.groupby(["weighting", "gap_user", "reliance_measure"]):
        assert sorted(g.state) == sorted(STATES), key
        assert g["rank"].min() == 1 and g["rank"].max() <= 37, key
        for k in "RGA":
            assert g[f"{k}_rank"].between(1 / 37 - 1e-9, 1).all(), key
        assert g["index"].notna().all() and (g["index"] > 0).all()
    assert set(p.weighting) == {"equal", "reliance_led", "gap_led"}


def test_borno_reliance_is_zone_average():
    p = load(M / "priority_index.csv")
    r = pd.read_csv(ROOT / "data" / "processed" / "generator_reliance_state.csv").set_index("state")
    ne = [s for s in STATES if ZONE_OF[s] == "North East" and s != "Borno"]
    b = p[(p.state == "Borno") & (p.reliance_measure == "primary_source")].R_value.iloc[0]
    assert b == pytest.approx(r.loc[ne, "gen_primary_source_pct_of_all_hh"].mean(), abs=0.01)


def test_lcoe_formula_hand_check():
    # 1 kWh/day, night share 0.7 (central household), worst-month PVOUT 4.0, no FX change
    r = model.solar_system(4.0, 1.0, "household", "central", e=1.0)
    batt = 0.7 / (0.8 * 0.9)
    pv = (0.3 + 0.7 / 0.9) / (4.0 * 0.9)
    capex = (pv * 1000 * 260 + batt * 255_000) * 1.3 + 175_000  # A8 inverter
    pvf = sum(1 / 1.15 ** t for t in range(1, 11))
    expected = (capex + 0.01 * capex * pvf) / (365 * pvf)  # battery life 10 = horizon: no replacement
    assert r["capex_ngn"] == pytest.approx(capex, rel=1e-9)
    assert r["lcoe_ngn_per_kwh"] == pytest.approx(expected, rel=1e-9)


# ---------- Power BI tables ----------
@pytest.mark.parametrize("name,keys", [
    ("dim_state", ["state"]), ("dim_month", ["month"]),
    ("fact_generator_cost", ["state", "month", "user", "case"]),
    ("fact_grid_tariff", ["state", "month", "band"]),
    ("fact_solar_cost", ["state", "month", "user", "case"]),
    ("fact_payback", ["state", "month", "user", "case"]),
    ("fact_crossover", ["state", "user", "basis"]),
    ("fact_priority_index", ["state", "weighting", "gap_user", "reliance_measure"]),
])
def test_powerbi_tables(name, keys):
    d = load(PBI / f"{name}.csv")
    assert not d.duplicated(keys).any()
    assert set(d.state) == set(STATES) if "state" in d else True
