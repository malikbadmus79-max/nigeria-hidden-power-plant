"""Fetch PBIR JSON schemas (and every schema they $ref) from Microsoft's json-schemas repo."""
import json, re, sys, urllib.request
from pathlib import Path
BASE = "https://raw.githubusercontent.com/microsoft/json-schemas/main/fabric/item/report/definition/"
OUT = Path(__file__).resolve().parent / "schemas"
todo = ["page/2.1.0/schema.json", "pagesMetadata/1.0.0/schema.json", "visualContainer/2.8.0/schema.json",
        "report/3.2.0/schema.json", "versionMetadata/1.0.0/schema.json"]
seen = set()
while todo:
    rel = todo.pop()
    if rel in seen: continue
    seen.add(rel)
    data = urllib.request.urlopen(BASE + rel, timeout=60).read()
    p = OUT / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(data)
    for ref in set(re.findall(r'"\$ref"\s*:\s*"([^"#][^"]*)', data.decode("utf-8"))):
        parts = (Path(rel).parent / ref.split("#")[0]).as_posix().split("/")
        stack = []
        for x in parts:
            if x == "..": stack.pop()
            elif x not in (".", ""): stack.append(x)
        todo.append("/".join(stack))
print(len(seen), "schemas:", sorted(seen))
