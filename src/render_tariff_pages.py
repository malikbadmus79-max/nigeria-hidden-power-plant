"""Render the tariff-table page(s) of each downloaded NERC order to PNG for transcription.

The orders are scanned images. Pages are located with Tesseract OCR (keywords
"Tariff Class" / "Allowed Tariff" / "Approved"), then rendered at 150 dpi to
data/raw/nerc_tariffs/pages/ (gitignored). Values are transcribed by hand into
data/processed/nerc_tariff_tables_transcribed.csv with file and page number.

Run from repo root:  python src/render_tariff_pages.py
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT / "data" / "raw" / "nerc_tariffs" / "pdf"
PAGES = ROOT / "data" / "raw" / "nerc_tariffs" / "pages"
TESSERACT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
KEY = re.compile(r"(?i)(tariff\s*class|allowed\s*tariff|approved\s*(allowed\s*)?tariff|customer\s*class)")


def main() -> None:
    PAGES.mkdir(parents=True, exist_ok=True)
    for pdf_path in sorted(PDF_DIR.glob("*.pdf")):
        with pdfplumber.open(pdf_path) as pdf:
            hits = []
            for i, page in enumerate(pdf.pages):
                img = page.to_image(resolution=120).original
                tmp = PAGES / "_ocr_tmp.png"
                img.save(tmp)
                txt = subprocess.run([TESSERACT, str(tmp), "-", "--psm", "6"], capture_output=True,
                                     text=True, encoding="utf-8", errors="ignore").stdout
                if KEY.search(txt) and re.search(r"(?i)band|non.?md|MD1|R2|lifeline", txt):
                    hits.append(i)
            for i in hits:
                pdf.pages[i].to_image(resolution=150).save(PAGES / f"{pdf_path.stem}_p{i + 1}.png")
            print(pdf_path.name, "tariff pages:", [h + 1 for h in hits])
    (PAGES / "_ocr_tmp.png").unlink(missing_ok=True)


if __name__ == "__main__":
    main()
