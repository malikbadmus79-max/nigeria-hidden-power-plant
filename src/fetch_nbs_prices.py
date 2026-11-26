"""Download NBS monthly PMS (petrol) and AGO (diesel) state price tables.

Sources (robots.txt: no restrictions; no login needed; checked 2026-11-26):
  - NBS e-library (Jan 2023 - Oct 2024): https://nigerianstat.gov.ng/elibrary
    each report page links an Excel "Download Tables" file under /resource/.
  - NBS microdata catalog (Nov 2024 onward): catalog 157 (PMS), 158 (AGO);
    files are .xlsx or .zip (report PDF + xlsx).

Files are saved under data/raw/nbs_prices/<FUEL>/ (gitignored) and an index of
what was downloaded is written to data/raw/nbs_prices/download_index.csv.

Run from repo root:  python src/fetch_nbs_prices.py
"""

from __future__ import annotations

import csv
import re
import time
import zipfile
from pathlib import Path

import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "nbs_prices"
UA = {"User-Agent": "Mozilla/5.0 (open-data research; nigeria-hidden-power-plant)"}
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august",
          "september", "october", "november", "december"]
MON_ABBR = {m[:3]: i + 1 for i, m in enumerate(MONTHS)} | {"sept": 9}
START_YEAR = 2023
PAUSE = 1.0  # seconds between requests


def get(url: str) -> bytes:
    parts = urllib.parse.urlsplit(url)
    url = urllib.parse.urlunsplit(parts._replace(path=urllib.parse.quote(parts.path)))
    req = urllib.request.Request(url, headers=UA)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except urllib.error.HTTPError:
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == 3:
                raise
            time.sleep(10 * (attempt + 1))
    raise RuntimeError("unreachable")


def month_from_text(text: str) -> list[tuple[int, int]]:
    """Return all (year, month) found in a title/filename, e.g. 'AUG_SEPT_2025' -> [(2025,8),(2025,9)]."""
    t = text.lower().replace("_", " ").replace("-", " ")
    years = re.findall(r"20\d{2}", t)
    if not years:
        return []
    year = int(years[-1])
    found = []
    for tok in re.findall(r"[a-z]+", t):
        for full in MONTHS:
            if tok == full or (len(tok) >= 3 and tok in MON_ABBR and full.startswith(tok)):
                m = MONTHS.index(full) + 1
                if (year, m) not in found:
                    found.append((year, m))
    return found


def elibrary_items(fuel: str) -> list[dict]:
    query = {"PMS": "Premium Motor Spirit", "AGO": "Automotive Gas Oil"}[fuel]
    title_re = {"PMS": r"Premium Motor Spirit \(Petrol\) Price Watch \(([A-Za-z]+) (\d{4})\)",
                "AGO": r"Automotive Gas Oil \(Diesel\) Price Watch \(([A-Za-z]+) (\d{4})\)"}[fuel]
    items, seen = [], set()
    for page in range(1, 15):
        url = (f"https://nigerianstat.gov.ng/elibrary?queries={query.replace(' ', '%20')}"
               f"&offset={(page - 1) * 10}&page={page}")
        html = get(url).decode("utf-8", "ignore")
        html = re.sub(r"events:\s*\[.*?\]", "", html, flags=re.S)
        rows = re.findall(r"<tr.*?</tr>", html, flags=re.S)
        new = 0
        for row in rows:
            m = re.search(title_re, re.sub(r"<[^>]+>", " ", row))
            ids = re.findall(r"elibrary/read/(\d+)", row)
            if m and ids:
                year, mon = int(m.group(2)), MONTHS.index(m.group(1).lower()) + 1
                if year >= START_YEAR and ids[0] not in seen:
                    seen.add(ids[0])
                    items.append({"fuel": fuel, "year": year, "month": mon, "read_id": ids[0]})
                    new += 1
        if not rows or new == 0 and page > 3:
            break
        time.sleep(PAUSE)
    return items


def elibrary_xlsx_url(read_id: str) -> str | None:
    html = get(f"https://nigerianstat.gov.ng/elibrary/read/{read_id}").decode("utf-8", "ignore")
    m = re.search(r'href="(https://nigerianstat\.gov\.ng/resource/[^"]+\.xlsx?)"', html, flags=re.I)
    return m.group(1) if m else None


def catalog_files(fuel: str) -> list[dict]:
    cat = {"PMS": 157, "AGO": 158}[fuel]
    html = get(f"https://microdata.nigerianstat.gov.ng/index.php/catalog/{cat}/related-materials").decode("utf-8", "ignore")
    out = []
    for url, name in re.findall(r'href="(https://microdata\.nigerianstat\.gov\.ng/index\.php/catalog/\d+/download/\d+)"[^>]*?'
                                r'(?:title|data-filename)="([^"]+)"', html):
        if name.lower().endswith((".xlsx", ".xls", ".zip")):
            out.append({"fuel": fuel, "url": url, "name": name, "months": month_from_text(name)})
    # de-duplicate by url
    uniq = {d["url"]: d for d in out}
    return list(uniq.values())


def main() -> None:
    index = []
    for fuel in ["PMS", "AGO"]:
        fdir = OUT / fuel
        fdir.mkdir(parents=True, exist_ok=True)

        for it in sorted(elibrary_items(fuel), key=lambda d: (d["year"], d["month"])):
            if (it["year"], it["month"]) >= (2024, 11):
                continue  # catalog covers Nov 2024 onward
            time.sleep(PAUSE)
            url = elibrary_xlsx_url(it["read_id"])
            if not url:
                index.append({**it, "source": "elibrary", "url": "", "file": "", "status": "no xlsx link"})
                continue
            fname = f"{fuel}_{it['year']}-{it['month']:02d}_elibrary.xlsx"
            if not (fdir / fname).exists():
                time.sleep(PAUSE)
                try:
                    (fdir / fname).write_bytes(get(url))
                except urllib.error.HTTPError as e:
                    index.append({**it, "source": "elibrary", "url": url, "file": "", "status": f"http {e.code}"})
                    continue
            index.append({**it, "source": "elibrary", "url": url, "file": f"{fuel}/{fname}", "status": "ok"})

        for f in catalog_files(fuel):
            safe = re.sub(r"[^A-Za-z0-9._-]+", "_", f["name"])
            path = fdir / f"catalog_{safe}"
            if not path.exists():
                time.sleep(PAUSE)
                path.write_bytes(get(f["url"]))
            files = [path]
            if path.suffix.lower() == ".zip":
                xdir = fdir / (path.stem + "_unzipped")
                with zipfile.ZipFile(path) as z:
                    members = [n for n in z.namelist() if n.lower().endswith((".xlsx", ".xls"))]
                    z.extractall(xdir, members=members)
                files = [xdir / n for n in members]
            for fp in files:
                months = month_from_text(fp.name) or f["months"]
                for (y, m) in months or [(None, None)]:
                    index.append({"fuel": fuel, "year": y, "month": m, "read_id": "", "source": "catalog",
                                  "url": f["url"], "file": str(fp.relative_to(OUT)).replace("\\", "/"),
                                  "status": "ok"})

    with open(OUT / "download_index.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["fuel", "year", "month", "read_id", "source", "url", "file", "status"])
        w.writeheader()
        w.writerows(index)
    print(f"index rows: {len(index)} -> {OUT / 'download_index.csv'}")


if __name__ == "__main__":
    main()
