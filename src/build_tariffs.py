"""Build monthly grid tariff panels by DisCo and by state (Non-MD customers, bands A-E).

Inputs (tracked, hand-entered from NERC orders; see docs/data_dictionary.md):
  data/manual/nerc_tariff_tables_transcribed.csv  tariff tables by period
  data/manual/disco_state_map.csv                 DisCo-to-state map with regulator dates
Outputs:
  data/processed/grid_tariff_disco_monthly.csv
  data/processed/grid_tariff_state_monthly.csv
  data/processed/disco_state_map.csv              (copy of the map with a YTTS flag)

Rules
- Jan 2023 - Mar 2024: the Jan-Mar 2024 rates. NERC's January 2024 MYTO order
  states tariffs were frozen for all customers at the rates payable since
  December 2022, so the same rates apply throughout 2023 (basis =
  "frozen_since_dec_2022").
- From Apr 2024: the periods in Table 3 of the June 2026 orders.
- State value: simple mean of the DisCos serving the state (plan 5.3). Aba Power
  (APLE) is listed but not averaged into Abia: its tariff is known only for
  Jan-Feb 2025.
- Where tariff oversight has passed to a state regulator, NERC rates are kept as
  a placeholder and flagged; the state regulator's own tariff has not been
  collected (listed for manual download).

Run from repo root:  python src/build_tariffs.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MAN = ROOT / "data" / "manual"
OUT = ROOT / "data" / "processed"
START, END = pd.Period("2023-01", "M"), pd.Period("2026-05", "M")  # same months as the price panel
DISCOS = ["AEDC", "BEDC", "EEDC", "EKEDP", "IBEDC", "IE", "JED", "KAEDC", "KEDCO", "PHED", "YEDC"]


def disco_panel(tab: pd.DataFrame) -> pd.DataFrame:
    rows = []
    t = tab[tab.disco.isin(DISCOS)]
    for (disco, band), g in t.groupby(["disco", "band"]):
        for m in pd.period_range(START, END, freq="M"):
            if m < pd.Period("2024-01", "M"):
                hit = g[g.period_start == "2024-01"]
                basis = "frozen_since_dec_2022"
            else:
                ps = g.period_start.map(lambda x: pd.Period(x, "M"))
                pe = g.period_end.map(lambda x: pd.Period(x, "M"))
                hit = g[(ps <= m) & (pe >= m)]
                basis = "order_period"
            if len(hit) != 1:
                raise ValueError(f"{disco} {band} {m}: {len(hit)} matching periods")
            h = hit.iloc[0]
            rows.append({"disco": disco, "band": band, "month": str(m), "tariff_ngn_per_kwh": h.tariff_ngn_per_kwh,
                         "basis": basis, "source_file": h.source_file, "page": h.page})
    return pd.DataFrame(rows)


def state_panel(dp: pd.DataFrame, smap: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for state, g in smap.groupby("state"):
        discos = [d for d in g.disco if d in DISCOS]
        for m in pd.period_range(START, END, freq="M"):
            ms = str(m)
            sub = dp[(dp.disco.isin(discos)) & (dp.month == ms)]
            # regulator status for the month
            status = "nerc_order"
            for _, r in g[g.disco.isin(discos)].iterrows():
                if r.in_nerc_ytts_jun2026:
                    continue
                if r.regulator_from == "unknown":
                    if m >= pd.Period("2024-04", "M"):
                        status = "nerc_rate_placeholder_transfer_date_unknown"
                elif isinstance(r.regulator_from, str) and m >= pd.Period(r.regulator_from, "M"):
                    status = "nerc_rate_placeholder_state_regulated"
            for band, b in sub.groupby("band"):
                rows.append({"state": state, "month": ms, "band": band,
                             "tariff_ngn_per_kwh": round(b.tariff_ngn_per_kwh.mean(), 2),
                             "tariff_min": b.tariff_ngn_per_kwh.min(), "tariff_max": b.tariff_ngn_per_kwh.max(),
                             "discos": "+".join(sorted(b.disco)), "n_discos": len(b),
                             "tariff_status": status, "basis": b.basis.iloc[0]})
    return pd.DataFrame(rows)


def main() -> None:
    tab = pd.read_csv(MAN / "nerc_tariff_tables_transcribed.csv", dtype={"period_start": str, "period_end": str})
    smap = pd.read_csv(MAN / "disco_state_map.csv", dtype=str).fillna("")
    smap["in_nerc_ytts_jun2026"] = (smap.regulator == "NERC") | smap.note.str.contains("Still listed")
    dp = disco_panel(tab)
    sp = state_panel(dp, smap)
    OUT.mkdir(parents=True, exist_ok=True)
    dp.to_csv(OUT / "grid_tariff_disco_monthly.csv", index=False, encoding="utf-8")
    sp.to_csv(OUT / "grid_tariff_state_monthly.csv", index=False, encoding="utf-8")
    smap.to_csv(OUT / "disco_state_map.csv", index=False, encoding="utf-8")
    print(f"DisCo panel: {len(dp)} rows; state panel: {len(sp)} rows, {sp.state.nunique()} states")
    print(sp.groupby("tariff_status").state.nunique())


if __name__ == "__main__":
    main()
