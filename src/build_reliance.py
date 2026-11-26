"""Generator reliance by state from published NBS survey tables.

Input : docs/sources/NBS_NLSS_2018-19_Report.pdf  (NBS, Nigeria Living Standards
        Survey 2018/2019 report; https://nigerianstat.gov.ng/download/1123)
Output: data/processed/generator_reliance_state.csv

Tables used (state rows; Borno has no data in the report):
  Table 7.10  access to electricity (% of households) and primary source of
              electricity (% of households with electricity), incl. "Generator"
  Table 7.12  average hours of electricity per day in the past 7 days, by source
              (grid / generator / other), whole day and 6pm-10pm
  Table 7.18  household asset ownership (% of all households), incl. "Generator"

Table 7.12 rows with only four numbers (e.g. Kano, Benue, Yobe) have blank
"Other" cells: word x-positions on the page (checked 2026-11-26) place the 3rd
and 4th numbers under the Generator columns, so the first four numbers are
grid day, grid 6-10pm, generator day, generator 6-10pm.

Derived: generator as primary electricity source as % of ALL households
         = access % x generator share % / 100.
MICS 2021 has no published state table for generators (state values need the
microdata, variable HC7E), so it is not included here.

Run from repo root:  python src/build_reliance.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd
import pdfplumber

sys.path.insert(0, str(Path(__file__).resolve().parent))
from states import STATES, canonical_state  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "docs" / "sources" / "NBS_NLSS_2018-19_Report.pdf"
OUT = ROOT / "data" / "processed" / "generator_reliance_state.csv"


def table_rows(page_text: str) -> dict[str, list[float]]:
    out = {}
    for line in page_text.split("\n"):
        m = re.match(r"^([A-Za-z][A-Za-z ]*?)\s*((?:-?\d+(?:\.\d+)?\s*)*)$", line.strip())
        if not m:
            continue
        name = m.group(1).strip()
        st = "NIGERIA" if name.upper() == "NIGERIA" else canonical_state(name)
        if st:
            out[st] = [float(x) for x in m.group(2).split()]
    return out


def find_page(pdf, title: str) -> tuple[int, str]:
    for i, p in enumerate(pdf.pages):
        t = p.extract_text() or ""
        if title in t and re.search(r"^Abia\s+\d", t, flags=re.M):  # skip the table of contents
            return i + 1, t
    raise ValueError(f"table not found: {title}")


def main() -> None:
    with pdfplumber.open(PDF) as pdf:
        p10, t10 = find_page(pdf, "Table 7.10: Access to Electricity and Primary Source")
        p12, t12 = find_page(pdf, "Table 7.12: Average Number of Hours of Electricity")
        p18, t18 = find_page(pdf, "Table 7.18: Selected Household Asset Ownership")
    a, h, o = table_rows(t10), table_rows(t12), table_rows(t18)

    rows = []
    for st in ["NIGERIA"] + STATES:
        r10, r12, r18 = a.get(st, []), h.get(st, []), o.get(st, [])
        rec = {"state": st if st != "NIGERIA" else "Nigeria (national)"}
        rec["electricity_access_pct_hh"] = r10[0] if len(r10) == 7 else None
        rec["gen_primary_source_pct_of_electrified_hh"] = r10[3] if len(r10) == 7 else None
        rec["grid_primary_source_pct_of_electrified_hh"] = r10[1] if len(r10) == 7 else None
        rec["gen_primary_source_pct_of_all_hh"] = (round(r10[0] * r10[3] / 100, 2) if len(r10) == 7 else None)
        rec["gen_ownership_pct_hh"] = r18[7] if len(r18) == 8 else None
        rec["grid_hours_per_day"] = r12[0] if len(r12) >= 4 else None
        rec["gen_hours_per_day"] = r12[2] if len(r12) >= 4 else None
        rec["gen_hours_6pm_10pm"] = r12[3] if len(r12) >= 4 else None
        rec["data_available"] = bool(r10 or r18)
        rows.append(rec)
    df = pd.DataFrame(rows)
    df["survey"] = "Nigeria Living Standards Survey 2018/19 (NBS)"
    df["survey_year"] = "2018/19"
    df["source_pages_pdf"] = f"T7.10 p{p10}; T7.12 p{p12}; T7.18 p{p18}"
    df["note"] = ""
    df.loc[~df.data_available, "note"] = "No data in the published NLSS tables (state not covered)"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False, encoding="utf-8")
    print(df[["state", "gen_ownership_pct_hh", "gen_primary_source_pct_of_all_hh", "gen_hours_per_day"]].head(6))
    print("states without data:", df.loc[~df.data_available, "state"].tolist())


if __name__ == "__main__":
    main()
