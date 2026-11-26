"""Build the Shape Map TopoJSON of Nigeria's 36 states + FCT from geoBoundaries ADM1.

Source: geoBoundaries NGA ADM1 (ID NGA-ADM1-27671186, GRID3 2022), CC BY 4.0.
Runfola et al. (2020) geoBoundaries: A global database of political administrative
boundaries. PLoS ONE 15(4): e0231866.

Steps: rename shapeName to the project's canonical state names (property "name", matching
dim_state[state]), quantise to a 2500 x 2500 grid (shared borders snap to identical points), drop
repeated and collinear points, and write TopoJSON (one arc per ring). Pure Python, no extra packages.
Output: the report's RegisteredResources, used by the Shape Map visuals.
Usage: python powerbi/build_topojson.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from states import STATES, canonical_state  # noqa: E402

RAW = ROOT / "data" / "raw" / "geoboundaries" / "geoBoundaries-NGA-ADM1.geojson"
OUT = (ROOT / "powerbi" / "report" / "HiddenPowerPlant.Report" / "StaticResources" / "RegisteredResources"
       / "nigeria_states_geoboundaries.json")


def main() -> None:
    g = json.loads(RAW.read_text(encoding="utf-8"))
    feats = []
    for f in g["features"]:
        raw = f["properties"]["shapeName"]
        name = canonical_state(raw.replace("Abuja Federal Capital Territory", "FCT")
                               .replace("Federal Capital Territory", "FCT"))
        feats.append({"type": "Feature", "properties": {"name": name}, "geometry": f["geometry"]})
    names = sorted(f["properties"]["name"] for f in feats)
    assert names == sorted(STATES), set(names) ^ set(STATES)
    # bounding box -> quantisation transform
    xs, ys = [], []
    for f in feats:
        for poly in polygons(f["geometry"]):
            for ring in poly:
                xs += [p[0] for p in ring]
                ys += [p[1] for p in ring]
    x0, y0 = min(xs), min(ys)
    sx, sy = (max(xs) - x0) / (Q - 1), (max(ys) - y0) / (Q - 1)

    arcs, geoms, n_in, n_out = [], [], 0, 0
    for f in sorted(feats, key=lambda f: f["properties"]["name"]):
        out_polys = []
        for poly in polygons(f["geometry"]):
            out_rings = []
            for k, ring in enumerate(poly):
                n_in += len(ring)
                q = thin([(round((x - x0) / sx), round((y - y0) / sy)) for x, y, *_ in ring])
                if len(q) < 4:      # ring collapsed at this resolution (tiny islet): drop
                    continue
                # d3 (used by Shape Map) needs clockwise exterior rings and anticlockwise holes;
                # geoBoundaries follows RFC 7946 (the opposite), so fix the winding here
                if (signed_area(q) > 0) == (k == 0):
                    q = q[::-1]
                n_out += len(q)
                delta = [list(q[0])] + [[b[0] - a[0], b[1] - a[1]] for a, b in zip(q, q[1:])]
                out_rings.append([len(arcs)])
                arcs.append(delta)
            if out_rings:
                out_polys.append(out_rings)
        geom = ({"type": "Polygon", "arcs": out_polys[0]} if len(out_polys) == 1
                else {"type": "MultiPolygon", "arcs": out_polys})
        geom["properties"] = f["properties"]
        geoms.append(geom)
    topo = {"type": "Topology", "transform": {"scale": [sx, sy], "translate": [x0, y0]},
            "objects": {"states": {"type": "GeometryCollection", "geometries": geoms}}, "arcs": arcs}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(topo, separators=(",", ":")), encoding="utf-8")
    print(f"TopoJSON written: {OUT.name}, {len(geoms)} shapes, points {n_in} -> {n_out}, "
          f"{OUT.stat().st_size / 1024:.0f} KB")


Q = 2500  # grid cells per axis (about 0.5 km over Nigeria); shared borders snap to the same points


def polygons(geom):
    return geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]


def signed_area(pts):
    """Shoelace area; > 0 means anticlockwise (x east, y north)."""
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pts, pts[1:])) / 2


def thin(pts):
    """Drop repeated and collinear points of a closed quantised ring (keeps it closed)."""
    out = []
    for p in pts:
        if out and p == out[-1]:
            continue
        if len(out) >= 2:
            (ax, ay), (bx, by) = out[-2], out[-1]
            if (bx - ax) * (p[1] - ay) - (by - ay) * (p[0] - ax) == 0:
                out[-1] = p
                continue
        out.append(p)
    if out and out[0] != out[-1]:
        out.append(out[0])
    return out


if __name__ == "__main__":
    main()
