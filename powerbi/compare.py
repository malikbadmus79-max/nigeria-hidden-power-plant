"""Crop the report canvas from a Power BI Desktop screenshot and place it next to the mockup.

The canvas is found as the bounding box of the page background colour (#F6F7F9) left of the panes.
Usage: python powerbi/compare.py <screenshot.png> <page number 1-4> <out.png> [--canvas-only out_canvas.png]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BG = np.array([0xF6, 0xF7, 0xF9])


def canvas_box(img: Image.Image) -> tuple[int, int, int, int]:
    a = np.asarray(img.convert("RGB")).astype(int)
    mask = (np.abs(a - BG).sum(axis=2) <= 3)
    mask[:, int(a.shape[1] * 0.64):] = False        # ignore the Filters/Visualizations/Data panes
    rows = np.where(mask.sum(axis=1) > a.shape[1] * 0.25)[0]
    cols = np.where(mask[rows[0]:rows[-1]].sum(axis=0) > (rows[-1] - rows[0]) * 0.25)[0]
    x0, x1, y0, y1 = cols[0], cols[-1] + 1, rows[0], rows[-1] + 1
    # keep the 16:9 canvas (outspace above/below may share the colour)
    h = round((x1 - x0) * 9 / 16)
    if y1 - y0 > h:
        y0 += ((y1 - y0) - h) // 2
        y1 = y0 + h
    return x0, y0, x1, y1


def main(shot: str, page: int, out: str, canvas_out: str | None = None) -> None:
    img = Image.open(shot)
    box = canvas_box(img)
    can = img.crop(box).resize((1280, 720), Image.LANCZOS)
    if canvas_out:
        can.save(canvas_out)
    mock = Image.open(ROOT / "figures" / "mockups" / f"page{page}.png").convert("RGB").resize((1280, 720),
                                                                                             Image.LANCZOS)
    pair = Image.new("RGB", (1280, 1450), "white")
    pair.paste(mock, (0, 0))
    pair.paste(can, (0, 730))
    pair.save(out)
    print(f"canvas box {box}; saved {out}")


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], int(a[1]), a[2], a[a.index("--canvas-only") + 1] if "--canvas-only" in a else None)
