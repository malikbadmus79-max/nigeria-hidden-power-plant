"""Monthly household consumption by state, for the affordability measure (plan 5.5, A5).

Inputs
- docs/sources/NBS_download_1094.pdf : NBS, Consumption Expenditure Pattern in Nigeria
  (2019), Table 12 "Total Household Expenditure Combined by States" (annual ₦, NLSS
  2018/19, fieldwork Sep 2018 - Oct 2019). Borno is not in the table (not surveyed).
- data/processed/mpi_2022_state.csv : population by state = poor people / headcount
  ratio (MPI 2022, survey 2021/22).
- NBS CPI, all items, monthly (gitignored raw files):
    data/raw/nbs_cpi/cpi_1NewDec2024.xlsx  base Nov 2009 = 100 (history to Dec 2024)
    data/raw/nbs_cpi/CPI_OCTOBER_2026/cpi_1New_October2026.xlsx  base 2024 = 100 (Jan 2023 on)
  The two are chained by the mean ratio over their overlap (Jan - Dec 2023; the old-base
  file ends Dec 2023; ratio range 9.90-10.27).

Method
  annual household consumption (2018/19 ₦) = total expenditure / (population / household size)
  monthly consumption in month m = that / 12 x CPI(m) / mean CPI(Sep 2018 - Oct 2019)
  Household size 4.5 / 5.0 / 5.5 gives low / central / high consumption per household.
  Borno: North-East zone average per-household consumption, flagged.

Limits (flagged in outputs): population is from 2021/22, not 2019 (so per-household
consumption is somewhat understated); national CPI is applied to every state.

Output: data/processed/household_consumption_state_monthly.csv

Run from repo root:  python src/build_consumption.py
"""

from __future__ import annotations

import re
import sys
import warnings
from pathlib import Path

import openpyxl
import pandas as pd
import pdfplumber

sys.path.insert(0, str(Path(__file__).resolve().parent))
from states import STATES, ZONE_OF, canonical_state  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "docs" / "sources" / "NBS_download_1094.pdf"
CPI_OLD = ROOT / "data" / "raw" / "nbs_cpi" / "cpi_1NewDec2024.xlsx"
CPI_NEW = ROOT / "data" / "raw" / "nbs_cpi" / "CPI_OCTOBER_2026" / "cpi_1New_October2026.xlsx"
OUT = ROOT / "data" / "processed" / "household_consumption_state_monthly.csv"
HH_SIZE = {"low": 4.5, "central": 5.0, "high": 5.5}
MON = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]


def table12() -> dict[str, float]:
    with pdfplumber.open(PDF) as pdf:
        page = next(p for p in pdf.pages if "Table 12: Total Household Expenditure Combined by States" in (p.extract_text() or ""))
        text = page.extract_text()
    out = {}
    for line in text.split("\n"):
        m = re.match(r"^\d+\.\s+([A-Za-z][A-Za-z ]*?)\s+(\d.*)$", line.strip())
        if not m:
            continue
        # left entry ends where the right-hand ranked entry ("NN. Name") starts
        left = re.split(r"\s\d+\.\s+[A-Z]", m.group(2), maxsplit=1)[0]
        compact = left.replace(" ", "")
        num = re.match(r"^([\d,]+\.00)", compact)
        st = canonical_state(m.group(1))
        if st and num:
            out[st] = float(num.group(1).replace(",", ""))
    return out


def cpi_series(path: Path) -> pd.Series:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ws = openpyxl.load_workbook(path, read_only=True, data_only=True)["Table1"]
    year, vals = None, {}
    for r in ws.iter_rows(values_only=True):
        cells = list(r)
        if not cells:
            continue
        if len(cells) < 3:
            continue
        # rows look like [year, 'Jan', index, ...] or [None, 'Feb', index, ...]
        if isinstance(cells[0], (int, float)) and 1990 <= cells[0] <= 2035:
            year = int(cells[0])
        mon, idx = cells[1], cells[2]
        if not (year and isinstance(mon, str) and mon.strip()[:3].lower() in MON):
            continue
        m = MON.index(mon.strip()[:3].lower()) + 1
        if isinstance(idx, (int, float)):
            vals[pd.Period(year=year, month=m, freq="M")] = float(idx)
    return pd.Series(vals).sort_index()


def main() -> None:
    tot = table12()
    mpi = pd.read_csv(ROOT / "data" / "processed" / "mpi_2022_state.csv").set_index("state")
    pop = mpi.poor_people_million / (mpi.headcount_pct / 100) * 1e6

    old, new = cpi_series(CPI_OLD), cpi_series(CPI_NEW)
    overlap = old.index.intersection(new.index)
    overlap = overlap[(overlap >= pd.Period("2023-01", "M")) & (overlap <= pd.Period("2024-12", "M"))]
    link = (old[overlap] / new[overlap]).mean()
    chained = pd.concat([old[old.index < pd.Period("2023-01", "M")], new * link]).sort_index()
    ref = chained[(chained.index >= pd.Period("2018-09", "M")) & (chained.index <= pd.Period("2019-10", "M"))].mean()

    rows = []
    for st in STATES:
        for case, size in HH_SIZE.items():
            if st in tot:
                annual = tot[st] / (pop[st] / size)
                flag = ""
            else:
                ne = [s for s in STATES if ZONE_OF[s] == ZONE_OF[st] and s in tot]
                annual = sum(tot[s] / (pop[s] / size) for s in ne) / len(ne)
                flag = f"{st}: not in NBS 2019 table; {ZONE_OF[st]} zone average"
            for per in new.index:
                rows.append({"state": st, "month": str(per), "case": case, "household_size": size,
                             "consumption_2019_ngn_per_hh_year": round(annual, 0),
                             "cpi_factor_vs_2018_19": round(chained[per] / ref, 4),
                             "consumption_ngn_per_hh_month": round(annual / 12 * chained[per] / ref, 0),
                             "flag": flag})
    df = pd.DataFrame(rows)
    df["source"] = ("NBS Consumption Expenditure Pattern in Nigeria 2019 Table 12; MPI 2022 population; "
                    "NBS CPI all items (chained)")
    df.to_csv(OUT, index=False, encoding="utf-8")
    print(f"Table 12 states: {len(tot)} (missing: {[s for s in STATES if s not in tot]}); total NGN {sum(tot.values())/1e12:.2f} trn")
    print(f"CPI link factor {link:.3f} over {len(overlap)} months; chained CPI factor May 2026 vs 2018/19: {chained[pd.Period('2026-05','M')]/ref:.2f}")
    c = df[(df.case == "central") & (df.month == "2026-05")]
    print(c.consumption_ngn_per_hh_month.describe().round(0).to_dict())


if __name__ == "__main__":
    main()
