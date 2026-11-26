"""Build the monthly state fuel price panel (PMS petrol, AGO diesel) from NBS tables.

Input : data/raw/nbs_prices/** (downloaded by src/fetch_nbs_prices.py)
Output: data/processed/fuel_prices_state_monthly.csv
        data/processed/fuel_price_revisions.csv  (same month reported differently
                                                  in later releases)

Gap-filling follows docs/analysis_plan.md section 5.8, in order:
  rule1  value for the missing month taken from a later NBS release
         (previous-month, year-ago or history column)
  rule2  linear interpolation within the state, gaps of up to 2 months
  rule3  national month-on-month change applied to the state's last known value
Every filled value is flagged. The series ends at the latest month reported as
a release's current month; nothing is extrapolated forward.

Run from repo root:  python src/build_prices.py
"""

from __future__ import annotations

import datetime as dt
import re
import sys
import warnings
from pathlib import Path

import openpyxl
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from states import STATES, canonical_state  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "nbs_prices"
OUT = ROOT / "data" / "processed" / "fuel_prices_state_monthly.csv"
OUT_REV = ROOT / "data" / "processed" / "fuel_price_revisions.csv"
START = pd.Period("2023-01", "M")
MON = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}


def header_period(v) -> pd.Period | None:
    """Parse a header cell into a month: a date, or text such as 'Average of Apr-23'."""
    if isinstance(v, (dt.datetime, dt.date)):
        return pd.Period(v, "M")
    if isinstance(v, str):
        m = re.search(r"([A-Za-z]{3})[A-Za-z]*[\s\-']*(\d{2}|\d{4})\b", v)
        if m and m.group(1).lower() in MON:
            y = int(m.group(2))
            y = y + 2000 if y < 100 else y
            if 2010 <= y <= 2030:
                return pd.Period(year=y, month=MON[m.group(1).lower()], freq="M")
    return None


# Files whose header month labels were verified to be wrong. Shift (in months) is
# added to every header month. Evidence is recorded in docs/phase2_results.md.
HEADER_SHIFT = {
    # Labels read Mar-23 / Feb-24 / Mar-24, but the "Feb-24" column equals the
    # March 2024 release exactly and the "Mar-24" column equals the April 2024
    # value in the May 2024 release: the data are Apr-23 / Mar-24 / Apr-24.
    "AGO/AGO_2024-04_elibrary.xlsx": 1,
}
OTHER_FUEL_SHEET = {"PMS": ("diesel", "ago"), "AGO": ("pms", "petrol", "premium")}


def parse_sheet(ws, shift: int = 0) -> list[dict]:
    rows = list(ws.iter_rows(max_row=200, values_only=True))
    # header row: the row (within the first 40) with the most month-like cells
    best, best_n = None, 0
    for i, r in enumerate(rows[:40]):
        cols = {j: header_period(v) for j, v in enumerate(r)}
        cols = {j: p for j, p in cols.items() if p is not None}
        if len(cols) > best_n:
            best, best_n = (i, cols), len(cols)
    if not best:
        return []
    hi, colmap = best
    colmap = {j: p + shift for j, p in colmap.items()}
    release = max(colmap.values())

    # split date columns into side-by-side blocks; each block's state label sits
    # to the left of its first date column
    blocks, cur = [], []
    for j in sorted(colmap):
        if cur and j - cur[-1] > 1:
            blocks.append(cur)
            cur = []
        cur.append(j)
    blocks.append(cur)

    out, stopped = [], set()
    for r in rows[hi + 1:]:
        for b, cols in enumerate(blocks):
            if b in stopped:
                continue
            label_cols = [c for c in range(cols[0] - 1, max(cols[0] - 4, -1), -1)]
            labels = [r[c] if c < len(r) else None for c in label_cols]
            # summary lists ("STATES WITH THE HIGHEST ...") end the table for this block
            if any(isinstance(v, str) and "states with" in v.lower() for v in labels[:1]):
                stopped.add(b)
                continue
            state = next((canonical_state(v) for v in labels if canonical_state(v)), None)
            if not state:
                continue
            for j in cols:
                v = r[j] if j < len(r) else None
                if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0:
                    out.append({"state": state, "month": colmap[j], "price": float(v), "release": release})
    return out


def load_all() -> pd.DataFrame:
    recs = []
    for f in sorted(RAW.glob("*/**/*.xls*")):
        fuel = f.relative_to(RAW).parts[0]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            wb = openpyxl.load_workbook(f, read_only=True, data_only=True)
        rel = f.relative_to(RAW).as_posix()
        for ws in wb.worksheets:
            if any(k in ws.title.lower() for k in OTHER_FUEL_SHEET[fuel]):
                continue  # e.g. a diesel sheet inside a petrol workbook
            for rec in parse_sheet(ws, HEADER_SHIFT.get(rel, 0)):
                recs.append({**rec, "fuel": fuel, "file": rel, "sheet": ws.title})
        wb.close()
    df = pd.DataFrame(recs)
    # drop exact duplicates (same file reported in two sheets)
    df = df.drop_duplicates(["fuel", "state", "month", "release", "price"])
    df["role"] = "history"
    df.loc[df.month == df.release, "role"] = "current"
    df.loc[df.month == df.release - 1, "role"] = "previous_month"
    df.loc[df.month == df.release - 12, "role"] = "year_ago"
    return df


def build(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    latest = df[df.role == "current"].groupby("fuel").month.max()
    out, revisions = [], []
    for fuel in ["PMS", "AGO"]:
        months = pd.period_range(START, latest[fuel], freq="M")
        d = df[df.fuel == fuel]
        cur = (d[d.role == "current"].sort_values("release")
               .groupby(["state", "month"]).agg(price=("price", "first"), file=("file", "first")))
        later = d[d.role != "current"].sort_values("release")
        # revisions: same month reported in a later release with a different value
        if not later.empty and not cur.empty:
            j = later.merge(cur.reset_index(), on=["state", "month"], suffixes=("", "_cur"))
            j = j[(j.price - j.price_cur).abs() > 0.01]
            for _, r in j.iterrows():
                revisions.append({"fuel": fuel, "state": r.state, "month": str(r.month),
                                  "current_release_price": r.price_cur, "later_release": str(r.release),
                                  "later_role": r.role, "later_price": r.price})

        grid = pd.MultiIndex.from_product([STATES, months], names=["state", "month"])
        p = pd.DataFrame(index=grid).join(cur)
        p["value_type"] = p.price.notna().map({True: "reported", False: None})
        p["source_release"] = p.index.get_level_values("month").astype(str).where(p.price.notna())

        # rule 1: later release (closest later release first)
        miss = p.price.isna()
        if miss.any():
            lat = later[later.month >= START]
            for (st, mo) in p.index[miss]:
                cand = lat[(lat.state == st) & (lat.month == mo) & (lat.release > mo)]
                if not cand.empty:
                    c = cand.sort_values("release").iloc[0]
                    p.loc[(st, mo), ["price", "file", "value_type", "source_release"]] = [
                        c.price, c.file, f"filled_rule1_{c.role}", str(c.release)]

        # rule 2: interpolate within state, gaps <= 2 months
        for st in STATES:
            s = p.loc[st, "price"].astype(float)
            if s.isna().any():
                interp = s.interpolate(limit=2, limit_area="inside")
                # only fill runs of length <= 2
                runs = s.isna().astype(int).groupby(s.notna().cumsum()).transform("sum")
                fill = s.isna() & interp.notna() & (runs <= 2)
                for mo in s.index[fill]:
                    p.loc[(st, mo), ["price", "value_type"]] = [round(interp[mo], 2), "filled_rule2_interpolation"]

        # rule 3: national month-on-month change applied to last known state value
        nat = p.price.groupby(level="month").mean()
        for st in STATES:
            s = p.loc[st, "price"]
            for k, mo in enumerate(months):
                if pd.isna(p.loc[(st, mo), "price"]) and k > 0:
                    prev = p.loc[(st, months[k - 1]), "price"]
                    if pd.notna(prev) and pd.notna(nat[mo]) and pd.notna(nat[months[k - 1]]):
                        p.loc[(st, mo), ["price", "value_type"]] = [
                            round(prev * nat[mo] / nat[months[k - 1]], 2), "filled_rule3_national_change"]

        p = p.reset_index()
        p.insert(0, "fuel", fuel)
        out.append(p)

    res = pd.concat(out, ignore_index=True)
    res["month"] = res.month.astype(str)
    res["is_filled"] = res.value_type.fillna("").str.startswith("filled")
    res["product"] = res.fuel.map({"PMS": "Premium Motor Spirit (petrol)", "AGO": "Automotive Gas Oil (diesel)"})
    res["source"] = "NBS Price Watch"
    res = res.rename(columns={"price": "price_ngn_per_litre", "file": "source_file"})
    cols = ["fuel", "product", "state", "month", "price_ngn_per_litre", "value_type", "is_filled",
            "source_release", "source", "source_file"]
    rev_cols = ["fuel", "state", "month", "current_release_price", "later_release", "later_role", "later_price"]
    return res[cols], pd.DataFrame(revisions, columns=rev_cols)


def main() -> None:
    df = load_all()
    panel, rev = build(df)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(OUT, index=False, encoding="utf-8")
    rev.to_csv(OUT_REV, index=False, encoding="utf-8")
    print(panel.groupby(["fuel", "value_type"], dropna=False).size())
    print("months:", panel.groupby("fuel").month.agg(["min", "max", "nunique"]))
    print("missing after fill:", panel.price_ngn_per_litre.isna().sum(), "| revisions:", len(rev))


if __name__ == "__main__":
    main()
