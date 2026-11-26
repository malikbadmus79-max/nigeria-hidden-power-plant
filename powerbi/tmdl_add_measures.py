"""Add measures from model_spec.py that are missing in the PBIP TMDL (_Measures.tmdl).
Used while Power BI Desktop is closed. Existing measures are never changed; the file's
line endings (CRLF or LF) are preserved.
Usage: python tmdl_add_measures.py <path to _Measures.tmdl>"""
from __future__ import annotations

import re
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import model_spec as spec  # noqa: E402

CRLF, LF = "\r\n", "\n"


def tmdl_name(n: str) -> str:
    return "'" + n.replace("'", "''") + "'"


def block(name, folder, fmt, desc, dax) -> str:
    lines = [f"\t/// {desc}"]
    expr = dax.split(LF)
    if len(expr) == 1:
        lines.append(f"\tmeasure {tmdl_name(name)} = {expr[0]}")
    else:
        lines.append(f"\tmeasure {tmdl_name(name)} =")
        lines += [f"\t\t\t{x}" for x in expr]
    if fmt:  # text-returning helpers have no format string
        lines.append(f"\t\tformatString: {fmt}")
    lines += [f"\t\tdisplayFolder: {folder}", f"\t\tlineageTag: {uuid.uuid4()}", ""]
    return LF.join(lines) + LF


def main(path: str) -> None:
    p = Path(path)
    raw = p.read_bytes().decode("utf-8")
    eol = CRLF if CRLF in raw else LF
    txt = raw.replace(CRLF, LF)
    have = {m.strip("'").replace("''", "'") for m in re.findall(r"^\tmeasure ('(?:[^']|'')+'|\S+)", txt, re.M)}
    missing = [m for m in spec.MEASURES if m[0] not in have]
    if not missing:
        print("nothing to add")
        return
    anchor = "\tcolumn _" + LF
    assert txt.count(anchor) == 1, "anchor not found"
    txt = txt.replace(anchor, "".join(block(*m) for m in missing) + anchor)
    p.write_bytes(txt.replace(LF, eol).encode("utf-8"))
    print("added:", [m[0] for m in missing])


if __name__ == "__main__":
    main(sys.argv[1])
