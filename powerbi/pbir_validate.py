"""Validate PBIR JSON files against the Microsoft schemas named in their "$schema".

No third-party validator is installed (and PyPI was out of scope), so this is a small
JSON Schema draft-07 validator covering the keywords the PBIR schemas use. Schemas are read
from powerbi/schemas/ (fetched from github.com/microsoft/json-schemas by fetch_schemas.py);
"https://developer.microsoft.com/json-schemas/fabric/item/report/definition/" maps to that folder.
Any schema keyword it does not implement is reported as a warning, so gaps are visible.

Usage: python pbir_validate.py <folder> [<folder> ...]
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCHEMAS = HERE / "schemas"
PREFIX = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/"
IGNORED = {"$schema", "$id", "description", "default", "definitions", "title", "examples", "$comment",
           "deprecated", "markdownDescription"}
HANDLED = {"$ref", "type", "enum", "const", "properties", "required", "additionalProperties", "items",
           "minItems", "maxItems", "minLength", "maxLength", "pattern", "minimum", "maximum",
           "exclusiveMinimum", "exclusiveMaximum", "anyOf", "oneOf", "allOf", "not", "if", "then", "else",
           "patternProperties", "propertyNames", "uniqueItems"}

_cache: dict[Path, dict] = {}
unknown_keywords: set[str] = set()


def load(path: Path) -> dict:
    path = path.resolve()
    if path not in _cache:
        _cache[path] = json.loads(path.read_text(encoding="utf-8"))
    return _cache[path]


def resolve(ref: str, base: Path):
    file_part, _, frag = ref.partition("#")
    target = (base.parent / file_part).resolve() if file_part else base
    node = load(target)
    for part in [p for p in frag.split("/") if p]:
        node = node[part.replace("~1", "/").replace("~0", "~")]
    return node, target


def type_ok(v, t) -> bool:
    if isinstance(t, list):
        return any(type_ok(v, x) for x in t)
    return {"object": isinstance(v, dict), "array": isinstance(v, list), "string": isinstance(v, str),
            "boolean": isinstance(v, bool), "null": v is None,
            "integer": isinstance(v, int) and not isinstance(v, bool),
            "number": isinstance(v, (int, float)) and not isinstance(v, bool)}[t]


def validate(v, s, base: Path, path: str) -> list[str]:
    if s is True or s == {}:
        return []
    if s is False:
        return [f"{path}: not allowed"]
    errs: list[str] = []
    for k in s:
        if k not in HANDLED and k not in IGNORED:
            unknown_keywords.add(k)
    if "$ref" in s:
        node, b = resolve(s["$ref"], base)
        errs += validate(v, node, b, path)
    if "type" in s and not type_ok(v, s["type"]):
        return errs + [f"{path}: expected type {s['type']}, got {type(v).__name__}"]
    if "enum" in s and v not in s["enum"]:
        errs.append(f"{path}: {v!r} not in enum")
    if "const" in s and v != s["const"]:
        errs.append(f"{path}: expected const {s['const']!r}, got {v!r}")
    if isinstance(v, str):
        if "minLength" in s and len(v) < s["minLength"]:
            errs.append(f"{path}: shorter than {s['minLength']}")
        if "maxLength" in s and len(v) > s["maxLength"]:
            errs.append(f"{path}: longer than {s['maxLength']}")
        if "pattern" in s and not re.search(s["pattern"], v):
            errs.append(f"{path}: does not match pattern {s['pattern']}")
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        if "minimum" in s and v < s["minimum"]:
            errs.append(f"{path}: below minimum {s['minimum']}")
        if "maximum" in s and v > s["maximum"]:
            errs.append(f"{path}: above maximum {s['maximum']}")
        if "exclusiveMinimum" in s and v <= s["exclusiveMinimum"]:
            errs.append(f"{path}: not above {s['exclusiveMinimum']}")
        if "exclusiveMaximum" in s and v >= s["exclusiveMaximum"]:
            errs.append(f"{path}: not below {s['exclusiveMaximum']}")
    if isinstance(v, dict):
        for r in s.get("required", []):
            if r not in v:
                errs.append(f"{path}: missing required property '{r}'")
        props = s.get("properties", {})
        pats = s.get("patternProperties", {})
        for k, val in v.items():
            matched = False
            if k in props:
                matched = True
                errs += validate(val, props[k], base, f"{path}.{k}")
            for pat, sub in pats.items():
                if re.search(pat, k):
                    matched = True
                    errs += validate(val, sub, base, f"{path}.{k}")
            if not matched and "additionalProperties" in s:
                ap = s["additionalProperties"]
                if ap is False:
                    errs.append(f"{path}: unexpected property '{k}'")
                elif isinstance(ap, dict):
                    errs += validate(val, ap, base, f"{path}.{k}")
            if "propertyNames" in s:
                errs += validate(k, s["propertyNames"], base, f"{path}.<name {k}>")
    if isinstance(v, list):
        if "minItems" in s and len(v) < s["minItems"]:
            errs.append(f"{path}: fewer than {s['minItems']} items")
        if "maxItems" in s and len(v) > s["maxItems"]:
            errs.append(f"{path}: more than {s['maxItems']} items")
        if isinstance(s.get("items"), dict):
            for i, item in enumerate(v):
                errs += validate(item, s["items"], base, f"{path}[{i}]")
        elif isinstance(s.get("items"), list):
            for i, (item, sub) in enumerate(zip(v, s["items"])):
                errs += validate(item, sub, base, f"{path}[{i}]")
        if s.get("uniqueItems") and len({json.dumps(x, sort_keys=True) for x in v}) != len(v):
            errs.append(f"{path}: items not unique")
    for sub in s.get("allOf", []):
        errs += validate(v, sub, base, path)
    if "anyOf" in s:
        if not any(not validate(v, sub, base, path) for sub in s["anyOf"]):
            errs.append(f"{path}: matches none of anyOf ({_short(v)})")
    if "oneOf" in s:
        n = sum(1 for sub in s["oneOf"] if not validate(v, sub, base, path))
        if n != 1:
            errs.append(f"{path}: matches {n} of oneOf, expected 1 ({_short(v)})")
    if "not" in s and not validate(v, s["not"], base, path):
        errs.append(f"{path}: matches 'not' schema")
    if "if" in s:
        branch = "then" if not validate(v, s["if"], base, path) else "else"
        if branch in s:
            errs += validate(v, s[branch], base, path)
    return errs


def _short(v) -> str:
    t = json.dumps(v, ensure_ascii=False)
    return t if len(t) < 120 else t[:117] + "..."


def schema_path(url: str) -> Path:
    if not url.startswith(PREFIX):
        raise ValueError(f"unknown schema URL {url}")
    return SCHEMAS / url[len(PREFIX):]


def model_fields(definition: Path) -> tuple[dict[str, set[str]], set[str]]:
    cols: dict[str, set[str]] = {}
    meas: set[str] = set()
    for f in (definition / "tables").glob("*.tmdl"):
        txt = f.read_text(encoding="utf-8")
        t = re.search(r"^table ('(?:[^']|'')+'|\S+)", txt, re.M).group(1).strip("'").replace("''", "'")
        cols[t] = {c.strip("'").replace("''", "'")
                   for c in re.findall(r"^\tcolumn ('(?:[^']|'')+'|\S+)", txt, re.M)}
        meas |= {m.strip("'").replace("''", "'")
                 for m in re.findall(r"^\tmeasure ('(?:[^']|'')+'|[^=\s]+)", txt, re.M)}
    return cols, meas


def check_fields(doc, cols, meas) -> list[str]:
    """Every Measure/Column referenced by entity must exist in the semantic model."""
    errs: list[str] = []

    def walk(x, path):
        if isinstance(x, dict):
            ent = None
            for kind in ("Measure", "Column"):
                if kind in x and isinstance(x[kind], dict):
                    ent = x[kind].get("Expression", {}).get("SourceRef", {}).get("Entity")
                    prop = x[kind].get("Property")
                    if ent is not None:
                        if kind == "Measure" and prop not in meas:
                            errs.append(f"{path}: measure '{prop}' not in model")
                        if kind == "Column" and prop not in cols.get(ent, set()):
                            errs.append(f"{path}: column {ent}[{prop}] not in model")
            for k, v in x.items():
                walk(v, f"{path}.{k}")
        elif isinstance(x, list):
            for i, v in enumerate(x):
                walk(v, f"{path}[{i}]")

    walk(doc, "$")
    q = (doc.get("visual") or {}).get("query", {}).get("queryState", {}) if isinstance(doc, dict) else {}
    refs = [p["queryRef"] for role in q.values() for p in role.get("projections", [])]
    if len(refs) != len(set(refs)):
        errs.append("$: duplicate queryRef within the visual")
    return errs


def main(folders: list[str]) -> int:
    model = None
    if "--model" in folders:
        i = folders.index("--model")
        model = model_fields(Path(folders[i + 1]))
        folders = folders[:i] + folders[i + 2:]
        print(f"model: {sum(len(c) for c in model[0].values())} columns, {len(model[1])} measures")
    files = [p for f in folders for p in ([Path(f)] if Path(f).is_file() else sorted(Path(f).rglob("*.json")))]
    n_err = 0
    skipped = []
    for p in files:
        doc = json.loads(p.read_text(encoding="utf-8"))
        url = doc.get("$schema") if isinstance(doc, dict) else None
        if not url:
            skipped.append(p)
            continue
        try:
            sp = schema_path(url)
        except ValueError as e:
            skipped.append(p)
            print(f"SKIP {p}: {e}")
            continue
        if not sp.exists():
            skipped.append(p)
            print(f"SKIP {p}: schema not downloaded ({url})")
            continue
        errs = validate(doc, load(sp), sp.resolve(), "$")
        if model:
            errs += check_fields(doc, *model)
        n_err += len(errs)
        status = "OK  " if not errs else "FAIL"
        print(f"{status} {p.as_posix()}  [{url[len(PREFIX):]}]")
        for e in errs:
            print("      ", e)
    print(f"\n{len(files) - len(skipped)} files validated, {n_err} errors, {len(skipped)} without a known schema")
    if unknown_keywords:
        print("WARNING: schema keywords not checked by this validator:", sorted(unknown_keywords))
    return 1 if n_err else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
