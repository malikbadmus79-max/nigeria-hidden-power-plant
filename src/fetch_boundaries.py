"""Download Nigeria state (ADM1) boundaries from geoBoundaries and derive state centroids.

Source: geoBoundaries gbOpen NGA ADM1 (boundaryID NGA-ADM1-27671186; source GRID3,
year represented 2022; licence CC BY 4.0). API: https://www.geoboundaries.org/api/current/gbOpen/NGA/ADM1/
robots.txt allows (checked 2026-11-26).

Outputs:
  data/raw/geoboundaries/geoBoundaries-NGA-ADM1.geojson  (gitignored)
  data/raw/geoboundaries/metadata.json                    (gitignored)
  data/processed/state_centroids.csv  area-weighted centroid (lon/lat) of each state

Centroids are computed in plain lon/lat (planar shoelace formula), which is
adequate for picking a representative point per state; they are not used for
area calculations. Zonal statistics for solar resource are a later step once the
Global Solar Atlas GIS files are downloaded by hand (see docs/phase2_results.md).

Run from repo root:  python src/fetch_boundaries.py
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from states import STATES, canonical_state  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "geoboundaries"
OUT = ROOT / "data" / "processed" / "state_centroids.csv"
API = "https://www.geoboundaries.org/api/current/gbOpen/NGA/ADM1/"
UA = {"User-Agent": "Mozilla/5.0 (open-data research)"}


def get(url: str) -> bytes:
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300).read()


def ring_centroid(ring):
    a = cx = cy = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        f = x1 * y2 - x2 * y1
        a += f
        cx += (x1 + x2) * f
        cy += (y1 + y2) * f
    a /= 2
    return (cx / (6 * a), cy / (6 * a), abs(a)) if a else (ring[0][0], ring[0][1], 0.0)


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    meta = json.loads(get(API))
    (RAW / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    gj_path = RAW / "geoBoundaries-NGA-ADM1.geojson"
    if not gj_path.exists():
        gj_path.write_bytes(get(meta["gjDownloadURL"]))
    gj = json.loads(gj_path.read_text(encoding="utf-8"))

    rows = []
    for feat in gj["features"]:
        name = feat["properties"].get("shapeName")
        st = canonical_state(name.replace("Federal Capital Territory", "FCT")) if name else None
        geom = feat["geometry"]
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        sx = sy = sa = 0.0
        for poly in polys:
            x, y, a = ring_centroid([tuple(p[:2]) for p in poly[0]])  # outer ring
            sx, sy, sa = sx + x * a, sy + y * a, sa + a
        rows.append({"state": st, "source_name": name, "lon": round(sx / sa, 5), "lat": round(sy / sa, 5)})
    df = pd.DataFrame(rows)
    unmatched = df[df.state.isna()].source_name.tolist()
    missing = [s for s in STATES if s not in set(df.state)]
    df["boundary_source"] = f"geoBoundaries {meta['boundaryID']} ({meta['boundarySource']}, {meta['boundaryYearRepresented']}), {meta['boundaryLicense']}"
    df.sort_values("state").to_csv(OUT, index=False, encoding="utf-8")
    print(f"{len(df)} features; unmatched names: {unmatched}; states missing: {missing}")


if __name__ == "__main__":
    main()
