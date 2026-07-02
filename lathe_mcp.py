#!/usr/bin/env python3
"""lathe_mcp.py — a minimal, stdlib-only MCP (Model Context Protocol) server exposing Lathe's deterministic
build / gate / pin / review as tools over stdio JSON-RPC 2.0. Point any MCP client at it:

  { "mcpServers": { "lathe": { "command": "python", "args": ["lathe_mcp.py"] } } }

Then Claude Code / Cursor / Copilot get Lathe's hard test-gate, content-hash pinning, and provenance INSIDE the
agent they already use — Lathe becomes the build layer under any agent. LLM-INDEPENDENT: the client's model calls
these tools; Lathe runs the gate/pin locally against whatever endpoints you configured. Response framing is
harness-built + gated (tools/mcp_helpers.py)."""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "projects", "agentic-harness", "tools"))
from mcp_helpers import jsonrpc_result, jsonrpc_error, tool_text
from mcp_safe import reject_flags, is_within_root      # harness-built input guards (argument-injection + traversal)

PY = sys.executable
LATHE = os.path.join(ROOT, "lathe.py")

TOOLS = [
    {"name": "lathe_build", "description": "Build a Lathe plan: generate each function on the local model under a hard test gate; pin passing code so rebuilds are byte-identical.",
     "inputSchema": {"type": "object", "properties": {"plan": {"type": "string", "description": "path to the plan .py"}}, "required": ["plan"]}},
    {"name": "lathe_verify", "description": "Rebuild a plan from its pins and confirm reproducibility (zero model calls when pinned).",
     "inputSchema": {"type": "object", "properties": {"plan": {"type": "string"}}, "required": ["plan"]}},
    {"name": "lathe_gate", "description": "Run the six standing tree gates (stale/dups/registry/pristine/lint/docs-drift) + regression.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "lathe_review", "description": "Multi-lens CE review of files (e.g. lenses='correctness adversarial security').",
     "inputSchema": {"type": "object", "properties": {"lenses": {"type": "string"}, "files": {"type": "string"}}, "required": ["files"]}},
    {"name": "lathe_do", "description": "From a natural-language goal: draft a spec+tests, build on the local model under the gate, and pin.",
     "inputSchema": {"type": "object", "properties": {"goal": {"type": "string"}}, "required": ["goal"]}},
]


def _run(args, timeout=600):
    try:
        r = subprocess.run([PY, LATHE] + [a for a in args if a], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
        return (r.stdout or "") + (("\n" + r.stderr) if (r.stderr or "").strip() else "")
    except Exception as e:
        return "lathe error: %s" % e


def _call(name, a):
    if name in ("lathe_build", "lathe_verify"):
        plan = a.get("plan", "")
        if plan.startswith("-") or not is_within_root(ROOT, plan):   # HIGH-fix: flag-injection + path traversal
            return "refused: 'plan' must be a path inside the project (no leading '-', no '..')"
        return _run([name.split("_", 1)[1], plan])
    if name == "lathe_gate":
        return _run(["gate"])
    if name == "lathe_review":
        ok_l, lenses = reject_flags(a.get("lenses", ""))              # HIGH-fix: no client-supplied CLI flags
        ok_f, files = reject_flags(a.get("files", ""))
        if not (ok_l and ok_f):
            return "refused: arguments must not start with '-' (argument-injection guard)"
        if not files or not all(is_within_root(ROOT, f) for f in files):
            return "refused: 'files' must be paths inside the project"
        return _run(["review"] + lenses + files)
    if name == "lathe_do":
        return _run(["do", a.get("goal", "")])
    return "unknown tool: %s" % name


def _send(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()                                     # MCP over stdio hangs if stdout is buffered


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except Exception:
            continue
        mid, method, params = msg.get("id"), msg.get("method"), (msg.get("params") or {})
        if method == "initialize":
            _send(jsonrpc_result(mid, {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}},
                                       "serverInfo": {"name": "lathe", "version": "2.1.1"}}))
        elif method == "tools/list":
            _send(jsonrpc_result(mid, {"tools": TOOLS}))
        elif method == "tools/call":
            out = _call(params.get("name", ""), params.get("arguments") or {})
            _send(jsonrpc_result(mid, tool_text(out)))
        elif mid is not None:
            _send(jsonrpc_error(mid, -32601, "method not found: %s" % method))
        # notifications (no id) get no response


if __name__ == "__main__":
    main()
