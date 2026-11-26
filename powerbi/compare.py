"""Crop the report canvas from a Power BI Desktop screenshot and place it under the mockup.

The canvas is found as the bounding box of the page background (#F6F7F9) and the v2 sidebar navy (#0F1B2D),
left of the panes. --check-title exits with code 2 if the page title area is still blank (page not rendered yet).
Usage: python powerbi/compare.py <screenshot.png> <page 0-4> <out.png> [--canvas-only out_canvas.png]
       [--mockups figures/mockups_v2] [--check-title]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BG = np.array([0xF6, 0xF7, 0xF9])
NAVY = np.array([0x0F, 0x1B, 0x2D])


def canvas_box(img: Image.Image) -> tuple[int, int, int, int]:
    a = np.asarray(img.convert("RGB")).astype(int)
    mask = (np.abs(a - BG).sum(axis=2) <= 3) | (np.abs(a - NAVY).sum(axis=2) <= 6)
    mask[:, int(a.shape[1] * 0.64):] = False        # ignore the Filters/Visualizations/Data panes
    mask[:200, :] = False                            # ignore the ribbon
    rows = np.where(mask.sum(axis=1) > a.shape[1] * 0.25)[0]
    cols = np.where(mask[rows[0]:rows[-1]].sum(axis=0) > (rows[-1] - rows[0]) * 0.25)[0]
    x0, x1, y0, y1 = cols[0], cols[-1] + 1, rows[0], rows[-1] + 1
    h = round((x1 - x0) * 9 / 16)
    if y1 - y0 > h:
        y0 += ((y1 - y0) - h) // 2
        y1 = y0 + h
    return x0, y0, x1, y1


def title_visible(canvas: Image.Image) -> bool:
    """True if the page title area (x 234-650, y 16-56 on the 1280x720 canvas) has dark text pixels."""
    a = np.asarray(canvas.convert("RGB")).astype(int)[16:56, 234:650]
    return int(((a.sum(axis=2) < 250)).sum()) > 60


def main(argv) -> int:
    shot, page, out = argv[0], int(argv[1]), argv[2]
    mock_dir = ROOT / (argv[argv.index("--mockups") + 1] if "--mockups" in argv else "figures/mockups_v2")
    img = Image.open(shot)
    box = canvas_box(img)
    can = img.crop(box).resize((1280, 720), Image.LANCZOS)
    if "--check-title" in argv and not title_visible(can):
        print("title not visible yet")
        return 2
    if "--canvas-only" in argv:
        can.save(argv[argv.index("--canvas-only") + 1])
    mock = Image.open(mock_dir / f"page{page}.png").convert("RGB").resize((1280, 720), Image.LANCZOS)
    pair = Image.new("RGB", (1280, 1450), "white")
    pair.paste(mock, (0, 0))
    pair.paste(can, (0, 730))
    pair.save(out)
    print(f"canvas box {box}; saved {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
