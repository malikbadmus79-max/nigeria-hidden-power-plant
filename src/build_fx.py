"""Monthly average official NGN/USD exchange rate from the Central Bank of Nigeria.

Source: CBN exchange-rate data behind https://www.cbn.gov.ng/rates/ExchRateByCurrency.html,
served at https://www.cbn.gov.ng/api/GetAllExchangeRates (robots.txt allows /api/;
only *.asp pages are disallowed; checked 2026-11-26). Saved raw to
data/raw/cbn/GetAllExchangeRates.json (gitignored).

Output: data/processed/fx_ngn_usd_monthly.csv
  monthly mean, min and max of the daily CBN *central* rate for "US DOLLAR",
  number of trading days, Jan 2023 to the latest complete month.

Note: Nigeria unified its official exchange-rate windows in June 2023, so the
official rate roughly doubled that month. Rates before and after are not like
for like; the series is reported as published.

Run from repo root:  python src/build_fx.py   (use --refresh to re-download)
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "cbn" / "GetAllExchangeRates.json"
OUT = ROOT / "data" / "processed" / "fx_ngn_usd_monthly.csv"
URL = "https://www.cbn.gov.ng/api/GetAllExchangeRates"


def main() -> None:
    if "--refresh" in sys.argv or not RAW.exists():
        RAW.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 (open-data research)"})
        RAW.write_bytes(urllib.request.urlopen(req, timeout=600).read())
    data = pd.DataFrame(json.loads(RAW.read_text(encoding="utf-8")))
    usd = data[data.currency.str.strip().str.upper() == "US DOLLAR"].copy()
    usd["date"] = pd.to_datetime(usd.ratedate)
    usd["central"] = pd.to_numeric(usd.centralrate, errors="coerce")
    usd = usd.dropna(subset=["central"]).drop_duplicates("date")
    usd = usd[usd.date >= "2023-01-01"]
    usd["month"] = usd.date.dt.to_period("M")
    last_complete = (pd.Timestamp.today().to_period("M") - 1)
    usd = usd[usd.month <= last_complete]
    m = usd.groupby("month").central.agg(["mean", "min", "max", "count"]).reset_index()
    m.columns = ["month", "ngn_per_usd_mean", "ngn_per_usd_min", "ngn_per_usd_max", "n_days"]
    m["month"] = m.month.astype(str)
    m["ngn_per_usd_mean"] = m.ngn_per_usd_mean.round(4)
    m["source"] = "CBN official exchange rate (central rate, US DOLLAR), daily, averaged by month"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    m.to_csv(OUT, index=False, encoding="utf-8")
    print(m.iloc[[0, 5, 6, -1]].to_string(index=False))
    print(f"{len(m)} months {m.month.min()}..{m.month.max()}; min trading days {m.n_days.min()}")


if __name__ == "__main__":
    main()
