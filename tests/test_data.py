"""Checks on the Phase 2 processed data (data/processed/*.csv).

Run from repo root:  python -m pytest -q
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from states import STATES  # noqa: E402

P = ROOT / "data" / "processed"
START, END = "2023-01", "2026-05"
MONTHS = [str(m) for m in pd.period_range(START, END, freq="M")]
DISCOS = ["AEDC", "BEDC", "EEDC", "EKEDP", "IBEDC", "IE", "JED", "KAEDC", "KEDCO", "PHED", "YEDC"]


def load(name):
    path = P / name
    if not path.exists():
        pytest.skip(f"{name} not built; run the src/ scripts first")
    return pd.read_csv(path, dtype={"month": str})


# ---------- fuel prices ----------
@pytest.fixture(scope="module")
def prices():
    return load("fuel_prices_state_monthly.csv")


def test_prices_37_states_every_month(prices):
    for fuel in ["PMS", "AGO"]:
        d = prices[prices.fuel == fuel]
        counts = d.groupby("month").state.nunique()
        assert list(counts.index) == MONTHS, f"{fuel}: months {counts.index.min()}..{counts.index.max()}"
        assert (counts == 37).all(), counts[counts != 37]
        assert set(d.state) == set(STATES)


def test_prices_no_duplicates(prices):
    assert not prices.duplicated(["fuel", "state", "month"]).any()


def test_prices_positive_and_plausible(prices):
    p = prices.price_ngn_per_litre
    assert p.notna().all() and (p > 0).all()
    # each state within 0.5x-2x of the national median for that fuel-month
    ratio = p / prices.groupby(["fuel", "month"]).price_ngn_per_litre.transform("median")
    assert ratio.between(0.5, 2.0).all(), prices[~ratio.between(0.5, 2.0)]


def test_every_filled_value_flagged(prices):
    filled = prices.value_type.str.startswith("filled")
    assert (prices.is_filled == filled).all()
    assert prices.loc[filled, "source_release"].notna().all() or prices.loc[filled, "value_type"].str.contains("rule2|rule3").all()
    assert prices.value_type.isin(["reported", "filled_rule1_previous_month", "filled_rule1_year_ago",
                                   "filled_rule1_history", "filled_rule2_interpolation",
                                   "filled_rule3_national_change"]).all()
    # reported values come from that month's own release
    rep = prices[prices.value_type == "reported"]
    assert (rep.source_release == rep.month).all()


# ---------- tariffs ----------
@pytest.fixture(scope="module")
def tariffs():
    return load("grid_tariff_disco_monthly.csv")


def test_tariff_months_complete(tariffs):
    for (disco, band), g in tariffs.groupby(["disco", "band"]):
        assert sorted(g.month) == MONTHS, (disco, band)
    assert set(tariffs.disco) == set(DISCOS)
    # every DisCo has bands A-D; all but YEDC have E
    for d in DISCOS:
        bands = set(tariffs[tariffs.disco == d].band)
        assert bands == (set("ABCD") if d == "YEDC" else set("ABCDE")), (d, bands)


def test_tariffs_positive_no_duplicates(tariffs):
    assert (tariffs.tariff_ngn_per_kwh > 0).all()
    assert not tariffs.duplicated(["disco", "band", "month"]).any()


def test_band_a_policy_values(tariffs):
    a = tariffs[tariffs.band == "A"].set_index(["disco", "month"]).tariff_ngn_per_kwh
    for d in DISCOS:
        assert a[(d, "2024-04")] == 225.00
        assert a[(d, "2024-05")] == a[(d, "2024-06")] == 206.80
        assert a[(d, "2024-07")] == a[(d, END)] == 209.50
        assert a[(d, "2023-01")] == a[(d, "2024-03")] < 80  # frozen pre-April-2024 rate


def test_state_tariffs_cover_all_states_months():
    s = load("grid_tariff_state_monthly.csv")
    assert set(s.state) == set(STATES)
    for st, g in s.groupby("state"):
        assert sorted(g.month.unique()) == MONTHS, st
    assert not s.duplicated(["state", "month", "band"]).any()
    assert s.tariff_status.isin(["nerc_order", "nerc_rate_placeholder_state_regulated",
                                 "nerc_rate_placeholder_transfer_date_unknown"]).all()


def test_disco_map_covers_all_states():
    m = load("disco_state_map.csv")
    assert set(m.state) == set(STATES)
    assert set(m.disco) - {"APLE"} == set(DISCOS)


# ---------- other tables ----------
def test_mpi_37_states():
    m = load("mpi_2022_state.csv")
    assert sorted(m.state) == sorted(STATES)
    assert m.headcount_pct.between(0, 100).all()
    assert abs(m.population_share_pct.sum() - 100) < 1.0


def test_reliance_table():
    r = load("generator_reliance_state.csv")
    states = r[r.state != "Nigeria (national)"]
    assert sorted(states.state) == sorted(STATES)
    have = states[states.data_available]
    assert set(states.state) - set(have.state) == {"Borno"}  # not covered by NLSS 2018/19
    assert have.gen_ownership_pct_hh.between(0, 100).all()
    assert have.gen_primary_source_pct_of_all_hh.between(0, 100).all()


def test_fx_monthly():
    fx = load("fx_ngn_usd_monthly.csv")
    assert not fx.month.duplicated().any()
    assert set(MONTHS) <= set(fx.month)
    assert (fx.ngn_per_usd_mean > 0).all()
    assert (fx.ngn_per_usd_min <= fx.ngn_per_usd_mean).all() and (fx.ngn_per_usd_mean <= fx.ngn_per_usd_max).all()


def test_state_centroids_inside_nigeria():
    c = load("state_centroids.csv")
    assert sorted(c.state) == sorted(STATES)
    assert c.lon.between(2.6, 14.7).all() and c.lat.between(4.2, 13.9).all()


def test_solar_pvout_state_monthly():
    s = load("solar_pvout_state_monthly.csv")
    assert sorted(s.state.unique()) == sorted(STATES)
    assert sorted(s.month_of_year.unique()) == list(range(1, 13))
    assert not s.duplicated(["state", "month_of_year"]).any()
    assert s.pvout_kwh_per_kwp_day.between(2.0, 7.0).all()
    assert (s.worst_month_kwh_per_kwp_day <= s.pvout_kwh_per_kwp_day).all()
    assert s.source.str.contains("Global Solar Atlas").all()
