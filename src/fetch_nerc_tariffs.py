"""Index NERC tariff orders and transfer-of-oversight orders; download the ones used.

Source: nerc.gov.ng resource categories "myto" and "orders" (robots.txt allows;
checked 2026-11-26). The order PDFs are scanned images, so tariff tables are
transcribed from rendered pages (see src/render_tariff_pages.py and
data/processed/nerc_tariff_tables_transcribed.csv).

Outputs (gitignored):
  data/raw/nerc_tariffs/index_all_orders.csv   every PDF linked from the two categories
  data/raw/nerc_tariffs/pdf/*.pdf              orders used in this project

Run from repo root:  python src/fetch_nerc_tariffs.py
"""

from __future__ import annotations

import csv
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "nerc_tariffs"
UA = {"User-Agent": "Mozilla/5.0 (open-data research; nigeria-hidden-power-plant)"}
DISCOS = ["AEDC", "BEDC", "EEDC", "EKEDP", "IBEDC", "IE", "JED", "KAEDC", "KEDCO", "PHED", "YEDC"]
ALIASES = {"EKEDC": "EKEDP", "IKEDC": "IE", "JEDC": "JED", "PHEDC": "PHED", "APLE": "APLE",
           "ABUJA": "AEDC", "BENIN": "BEDC", "ENUGU": "EEDC", "EKO": "EKEDP", "IBADAN": "IBEDC",
           "IKEJA": "IE", "JOS": "JED", "KADUNA": "KAEDC", "KANO": "KEDCO", "PORTHARCOURT": "PHED",
           "YOLA": "YEDC"}
MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]

# Orders whose tariff tables are transcribed (see docs/phase2_results.md):
#  - April 2024 supplementary orders: tariffs in force before and from April 2024
#  - June 2026 orders: tariff history April 2024 - June 2026 (Table 3)
#  - Aba Power (APLE) February 2025 order
USED = [f"2024/04/April-2024-Supplementary-Order-to-MYTO-{d}" for d in
        ["AEDC", "BEDC", "EEDC-1", "EKEDP-1", "IBEDC-1", "IKEDC", "JED-1", "KAEDC-1", "KEDCO-1", "PHED-1", "YEDC-1"]]
USED += [f"2026/07/{d}_MYTO_JUNE_2026" for d in DISCOS]
USED += ["2025/02/APLE-MYTO_-FEB-2025_014"]


def get(url: str) -> bytes:
    parts = urllib.parse.urlsplit(url)
    url = urllib.parse.urlunsplit(parts._replace(path=urllib.parse.quote(parts.path)))
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180) as r:
                return r.read()
        except Exception:
            if attempt == 3:
                raise
            time.sleep(10 * (attempt + 1))
    raise RuntimeError


def classify(name: str) -> dict:
    up = re.sub(r"[^A-Z]", " ", name.upper())
    disco = next((ALIASES.get(t, t) for t in up.split() if t in DISCOS or t in ALIASES), "")
    low = name.lower().replace("_", " ").replace("-", " ")
    ym = re.search(r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s*(20\d{2})", low)
    month = f"{ym.group(2)}-{MONTHS.index(ym.group(1)) + 1:02d}" if ym else ""
    kind = ("transfer_of_oversight" if re.search(r"transfer|transition|oversight|bureau|regulatory commission", low)
            else "tariff_order" if re.search(r"myto|supplementary|holdco|\d{4} \d{3}", low) or (disco and month)
            else "other")
    return {"disco": disco, "order_month": month, "kind": kind}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    links = set()
    for cat in ["myto", "orders"]:
        for page in range(1, 80):
            try:
                html = get(f"https://nerc.gov.ng/resource-category/{cat}/page/{page}/").decode("utf-8", "ignore")
            except Exception:
                break  # the site returns an error past the last page
            found = set(re.findall(r"https://nerc\.gov\.ng/wp-content/uploads/[^\"']+\.pdf", html))
            if not found:
                break
            links |= found
            time.sleep(0.7)
    rows = []
    for u in sorted(links):
        rel = u.split("/uploads/")[1]
        rows.append({"upload_path": rel, "url": u, **classify(Path(rel).stem)})
    with open(OUT / "index_all_orders.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["upload_path", "url", "disco", "order_month", "kind"])
        w.writeheader()
        w.writerows(rows)

    pdir = OUT / "pdf"
    pdir.mkdir(exist_ok=True)
    for stem in USED:
        u = f"https://nerc.gov.ng/wp-content/uploads/{stem}.pdf"
        dest = pdir / (Path(stem).name + ".pdf")
        if not dest.exists():
            dest.write_bytes(get(u))
            time.sleep(0.7)
    print(f"indexed {len(rows)} PDFs; downloaded {len(USED)} orders to {pdir}")


if __name__ == "__main__":
    main()
