"""Minimal stdio client for the Microsoft Power BI Modeling MCP server (pinned 1.0.1).

Used because Claude Code had not loaded the server from .mcp.json. Starts the server,
connects to the open Power BI Desktop file by window title, and sends tool calls.
Set readonly=True to start the server with --readonly.
"""
from __future__ import annotations

import json
import queue
import subprocess
import threading

SERVER = "npx -y @microsoft/powerbi-modeling-mcp@1.0.1 --start"


class PBI:
    def __init__(self, title: str = "HiddenPowerPlant", readonly: bool = False):
        cmd = SERVER + (" --readonly" if readonly else "")
        self.p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, text=True, encoding="utf-8")
        self.q: queue.Queue = queue.Queue()
        threading.Thread(target=lambda: [self.q.put(l) for l in self.p.stdout], daemon=True).start()
        self._id = 0
        self._rpc("initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                                 "clientInfo": {"name": "flarewatch", "version": "1"}})
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        inst = self.call("connection_operations", operation="ListLocalInstances")["data"]
        match = [i for i in inst if i.get("parentWindowTitle") == title]
        if len(match) != 1:
            raise RuntimeError(f"expected one Power BI Desktop window titled {title!r}, found {inst}")
        self.port = match[0]["port"]
        self.call("connection_operations", operation="Connect", connectionString=match[0]["connectionString"])

    def _send(self, msg: dict) -> None:
        self.p.stdin.write(json.dumps(msg) + "\n")
        self.p.stdin.flush()

    def _rpc(self, method: str, params: dict) -> dict:
        self._id += 1
        self._send({"jsonrpc": "2.0", "id": self._id, "method": method, "params": params})
        while True:
            line = self.q.get(timeout=300)
            try:
                m = json.loads(line)
            except ValueError:
                continue
            if m.get("id") == self._id:
                if "error" in m:
                    raise RuntimeError(m["error"])
                return m["result"]

    def call(self, tool: str, **request) -> dict:
        r = self._rpc("tools/call", {"name": tool, "arguments": {"request": request}})
        out = []
        for c in r.get("content", []):
            if c.get("type") == "text":
                out.append(c["text"])
            elif c.get("type") == "resource":
                out.append(c["resource"].get("text", ""))
        text = "\n".join(out)
        if r.get("isError"):
            raise RuntimeError(f"{tool} {request.get('operation')}: {text[:2000]}")
        try:
            return json.loads(text)
        except ValueError:
            return {"text": text}

    def dax(self, query: str) -> list[dict]:
        """Run a DAX query; return rows as dicts (column names without table prefix/brackets)."""
        import csv
        import io
        r = self._rpc("tools/call", {"name": "dax_query_operations",
                                     "arguments": {"request": {"operation": "Execute", "query": query}}})
        texts = [c["resource"]["text"] for c in r.get("content", []) if c.get("type") == "resource"]
        if r.get("isError") or not texts:
            raise RuntimeError(f"DAX failed: {r.get('content')}")
        rows = list(csv.DictReader(io.StringIO(texts[0])))
        clean = lambda k: k.split("[")[-1].rstrip("]")  # noqa: E731
        return [{clean(k): v for k, v in row.items()} for row in rows]

    def close(self) -> None:
        try:
            self.p.stdin.close()
        finally:
            self.p.terminate()
