"""Extract Nigeria MPI 2022 results by state (all ages) from the NBS report.

Input : docs/sources/NBS_Nigeria_MPI_2022.pdf (NBS, Nigeria Multidimensional
        Poverty Index 2022; survey Nov 2021 - Feb 2022)
Output: data/processed/mpi_2022_state.csv

The state table is in Appendix D (all ages; columns: MPI value and 95% CI,
incidence H % and 95% CI, intensity A % and 95% CI, population share %,
number of poor people in millions). The report notes results are
representative at state level for all states except Borno.

Run from repo root:  python src/build_mpi.py
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
PDF = ROOT / "docs" / "sources" / "NBS_Nigeria_MPI_2022.pdf"
OUT = ROOT / "data" / "processed" / "mpi_2022_state.csv"
NUM = r"(-?\d+(?:\.\d+)?)"
ROW = re.compile(rf"^([A-Za-z][A-Za-z .\-]*?)\s+(0\.\d{{3}})\s+(0\.\d{{3}})\s+(0\.\d{{3}})"
                 + rf"(?:\s+{NUM}){{8}}\s*$")


def main() -> None:
    rows, pages = {}, []
    with pdfplumber.open(PDF) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            if "MPI Incidence (H, %) Intensity (A, %)" not in text or "Child MPI" in text:
                continue
            lines = text.split("\n")
            for k, line in enumerate(lines):
                # join names split over two lines (e.g. "Nassar-" / "awa 0.xxx ...")
                cand = line.strip()
                if k > 0 and re.match(r"^[a-z]+\s+0\.\d{3}", cand) and lines[k - 1].strip().endswith("-"):
                    cand = lines[k - 1].strip()[:-1] + cand
                # names wrapped around the number line: "Akwa" / "0.293 ..." / "Ibom"
                if (re.match(r"^0\.\d{3}\s", cand) and 0 < k < len(lines) - 1
                        and re.match(r"^[A-Za-z]+$", lines[k - 1].strip())
                        and re.match(r"^[A-Za-z]+$", lines[k + 1].strip())):
                    cand = f"{lines[k - 1].strip()} {lines[k + 1].strip()} {cand}"
                m = ROW.match(cand)
                if not m:
                    continue
                st = canonical_state(m.group(1).replace("FCT Abuja", "FCT"))
                if not st or st in rows:
                    continue
                nums = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", cand[len(m.group(1)):])]
                rows[st] = {
                    "state": st, "mpi": nums[0], "mpi_ci_low": nums[1], "mpi_ci_high": nums[2],
                    "headcount_pct": nums[3], "headcount_ci_low": nums[4], "headcount_ci_high": nums[5],
                    "intensity_pct": nums[6], "intensity_ci_low": nums[7], "intensity_ci_high": nums[8],
                    "population_share_pct": nums[9], "poor_people_million": nums[10],
                    "source_page_pdf": i + 1,
                }
                pages.append(i + 1)
    df = pd.DataFrame([rows[s] for s in STATES if s in rows])
    df["state_representative"] = df.state.ne("Borno")
    df["survey"] = "Nigeria MPI 2022 survey (Nov 2021 - Feb 2022)"
    df["source"] = "NBS, Nigeria Multidimensional Poverty Index (2022), Appendix D"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False, encoding="utf-8")
    missing = [s for s in STATES if s not in rows]
    print(f"{len(df)} states from PDF pages {sorted(set(pages))}; missing: {missing}")


if __name__ == "__main__":
    main()
