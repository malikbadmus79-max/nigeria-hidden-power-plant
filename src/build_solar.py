"""Monthly mean PV output (PVOUT) per state from Global Solar Atlas rasters.

Inputs (gitignored, downloaded by hand):
  data/raw/gsa/Nigeria_GISdata_LTAy_AvgDailyTotals_GlobalSolarAtlas-v2_GEOTIFF/monthly/PVOUT_01..12.tif
      long-term (1994-2018) monthly average of daily PV output, kWh/kWp per day,
      EPSG:4326, 30 arc-second cells.
      Licence: CC BY 4.0 with the mandatory GSA additions (WIPO mediation/arbitration clause).
  data/raw/geoboundaries/geoBoundaries-NGA-ADM1.geojson  (src/fetch_boundaries.py)

Output: data/processed/solar_pvout_state_monthly.csv
  state, month_of_year (1-12), pvout_kwh_per_kwp_day (mean of cells whose centre is
  inside the state), n_cells, plus each state's annual mean and worst month.

Cells are averaged without area weighting. In lon/lat, cell area varies by under 2%
across Nigeria's latitudes (4-14 N), so the effect is negligible.

Credit: © The World Bank, Source: Global Solar Atlas 2.0, Solar resource data: Solargis.

Run from repo root:  python src/build_solar.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.features import geometry_mask

sys.path.insert(0, str(Path(__file__).resolve().parent))
from states import STATES, canonical_state  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
GSA = ROOT / "data" / "raw" / "gsa"
GJ = ROOT / "data" / "raw" / "geoboundaries" / "geoBoundaries-NGA-ADM1.geojson"
OUT = ROOT / "data" / "processed" / "solar_pvout_state_monthly.csv"
CREDIT = "© The World Bank, Source: Global Solar Atlas 2.0, Solar resource data: Solargis (CC BY 4.0)"


def main() -> None:
    files = sorted(GSA.glob("*/monthly/PVOUT_[0-9][0-9].tif"))
    if len(files) != 12:
        raise SystemExit(f"expected 12 monthly PVOUT files, found {len(files)}")
    feats = json.loads(GJ.read_text(encoding="utf-8"))["features"]
    shapes = {}
    for f in feats:
        st = canonical_state(f["properties"]["shapeName"].replace("Federal Capital Territory", "FCT"))
        shapes[st] = f["geometry"]
    assert set(shapes) == set(STATES), set(STATES) ^ set(shapes)

    rows = []
    masks = None
    for path in files:
        month = int(path.stem.split("_")[1])
        with rasterio.open(path) as r:
            arr = r.read(1).astype("float64")
            if masks is None:
                masks = {st: geometry_mask([g], out_shape=arr.shape, transform=r.transform, invert=True)
                         for st, g in shapes.items()}
        for st, m in masks.items():
            vals = arr[m]
            vals = vals[np.isfinite(vals)]
            rows.append({"state": st, "month_of_year": month,
                         "pvout_kwh_per_kwp_day": round(float(vals.mean()), 4), "n_cells": int(vals.size)})
    df = pd.DataFrame(rows)
    g = df.groupby("state").pvout_kwh_per_kwp_day
    df["annual_mean_kwh_per_kwp_day"] = df.state.map(g.mean().round(4))
    df["worst_month_kwh_per_kwp_day"] = df.state.map(g.min())
    df["worst_month"] = df.state.map(df.loc[g.idxmin(), ["state", "month_of_year"]].set_index("state").month_of_year)
    df["source"] = CREDIT
    df.sort_values(["state", "month_of_year"]).to_csv(OUT, index=False, encoding="utf-8")
    s = df.drop_duplicates("state").sort_values("annual_mean_kwh_per_kwp_day")
    print(s[["state", "annual_mean_kwh_per_kwp_day", "worst_month_kwh_per_kwp_day", "worst_month"]].iloc[[0, 1, -2, -1]])
    print("min cells per state:", df.n_cells.min())


if __name__ == "__main__":
    main()
