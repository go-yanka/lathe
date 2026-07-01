"""repomap.py — a real, multi-language CODE-STRUCTURE MAP via universal-ctags (the OSS C tool).

Instead of a big LLM reading every full file to understand a codebase, it reads the STRUCTURE — names, kinds,
signatures, scopes — which is far smaller and cuts context + tool calls. This is the "repo map" idea (as in
Aider), built on the actual `ctags` binary (we SHELL OUT to it — GPL2, NOT vendored, so no license
contamination). It REPLACES the old Python-ast-only `_existing_inventory` (Python-only, names-only) with the
real thing: Python AND JavaScript AND ~150 languages, WITH signatures.

If ctags isn't installed, callers fall back to the stdlib-ast inventory so the harness still runs (portable).

  lathe map <path...>          # print the structure map
  code_structure(paths)        # -> {file: [ {name,kind,signature,scope,line} ]}
  render_map(paths)            # -> compact text map for the analyst / planner prompt
"""
import json
import os
import shutil
import subprocess


def ctags_available():
    return shutil.which("ctags") is not None


def code_structure(paths, timeout=60):
    """Per-file definitions via ctags JSON. Returns {path: [def dicts]}; empty dict if ctags is missing/fails."""
    files = [p for p in paths if os.path.isfile(p)]
    dirs = [p for p in paths if os.path.isdir(p)]
    if not ctags_available() or not (files or dirs):
        return {}
    argv = ["ctags", "--output-format=json", "--fields=+nKSl"]
    if dirs:
        argv.append("-R")
    argv += ["-f", "-"] + files + dirs
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except Exception:
        return {}
    out = {}
    for line in (r.stdout or "").splitlines():
        try:
            t = json.loads(line)
        except Exception:
            continue
        if t.get("_type") != "tag":
            continue
        out.setdefault(t.get("path", ""), []).append({
            "name": t.get("name", ""), "kind": t.get("kind", ""),
            "signature": t.get("signature", ""), "scope": t.get("scope", ""),
            "line": t.get("line", 0)})
    return out


def render_map(paths, max_per_file=60):
    """A compact text repo-map for an LLM prompt: each file -> its definitions with signatures + scope."""
    struct = code_structure(paths)
    if not struct:
        return ""
    lines = []
    for path in sorted(struct):
        defs = sorted(struct[path], key=lambda x: x.get("line", 0))[:max_per_file]
        lines.append(os.path.basename(path) + ":")
        for d in defs:
            sc = (" (in %s)" % d["scope"]) if d.get("scope") else ""
            lines.append("  %s %s%s%s" % (d.get("kind", ""), d.get("name", ""), d.get("signature", ""), sc))
    return "\n".join(lines)
