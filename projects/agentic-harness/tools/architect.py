"""architect.py (#49) — the first-class ARCHITECTURE / decomposition step.

Today a plan builds exactly one file (MODULE_NAME -> <name>.py) and decomposition (goal -> a set of modules) is
deliberately manual — so `lathe do` drafts one flat module, the direct cause of scope-collapse (#45). This module
adds the missing front half: turn a goal (+ #48 framing) into a module -> file -> folder plan with DEPENDS_ON
edges and a stack-appropriate layout, human-confirmed to ARCHITECTURE.md, then SEED one plan per module and hand
them to the existing decompose -> build path.

Pure + deterministic here (prompt builder, JSON parse/validate, ARCHITECTURE.md render, plan seeding); the single
frontier analyst call + the human confirm live in cmd_architect.
"""
import json
import os
import re

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def decomposition_prompt(goal, framing=""):
    """The analyst prompt: decompose the goal into modules. Asks for STRICT JSON so the parse is deterministic."""
    _fr = ("\n\n--- PROJECT FRAMING (deliverable/stack/hosting shape the layout) ---\n%s" % framing) if framing else ""
    return (
        "You are the APPLICATION / SYSTEM ARCHITECT. Decompose the goal below into a clean module -> file -> "
        "folder structure a senior engineer would choose for this stack — real boundaries and public APIs, not "
        "one flat file. Prefer the SMALLEST set of modules that cleanly separates concerns.%s\n\n"
        "--- GOAL ---\n%s\n\n"
        "Reply with STRICT JSON only (no prose, no markdown fence), exactly this shape:\n"
        '{\n  "modules": [\n'
        '    {"name": "<bare_identifier>", "file": "<name>.py", "folder": "<dir or empty>",\n'
        '     "purpose": "<one line>", "public_api": ["fn_name(args) -> ret", ...],\n'
        '     "depends_on": ["<other module name>", ...]}\n  ],\n'
        '  "layout": "<one-line description of the folder layout for this stack>",\n'
        '  "notes": "<one line, optional>"\n}\n'
        "Rules: names are bare identifiers; depends_on references other module names in this list (no cycles); "
        "every module has at least one public_api entry." % (_fr, goal)
    )


def parse_decomposition(raw):
    """Extract + parse the analyst's JSON decomposition. Tolerant of a stray code fence / surrounding prose.
    Returns the dict or raises ValueError."""
    s = str(raw or "").strip()
    if "```" in s:                                        # strip a markdown fence if the model added one
        s = re.sub(r"^```[a-zA-Z]*\n?|\n?```$", "", s.strip())
    if not s.lstrip().startswith("{"):                    # grab the first {...} block
        m = re.search(r"\{.*\}", s, re.S)
        if not m:
            raise ValueError("no JSON object found in the analyst reply")
        s = m.group(0)
    d = json.loads(s)
    if not isinstance(d, dict) or not isinstance(d.get("modules"), list):
        raise ValueError("decomposition JSON has no 'modules' list")
    return d


def validate_decomposition(d):
    """(ok, reason). Structural + safety checks: bare-identifier names, unique, DEPENDS_ON references resolve and
    are acyclic, each module has a public_api. Keeps a hostile/garbled decomposition from seeding bad plans."""
    mods = (d or {}).get("modules") or []
    if not mods:
        return False, "no modules"
    names = []
    for m in mods:
        if not isinstance(m, dict):
            return False, "a module is not an object"
        n = str(m.get("name", ""))
        if not _IDENT.match(n):
            return False, "module name %r is not a bare identifier" % n
        if n in names:
            return False, "duplicate module name %r" % n
        names.append(n)
        if not (m.get("public_api") and isinstance(m["public_api"], list)):
            return False, "module %r has no public_api" % n
    nameset = set(names)
    for m in mods:
        for dep in (m.get("depends_on") or []):
            if dep not in nameset:
                return False, "module %r depends on unknown %r" % (m.get("name"), dep)
            if dep == m.get("name"):
                return False, "module %r depends on itself" % m.get("name")
    # acyclicity (Kahn)
    deps = {m["name"]: set(m.get("depends_on") or []) for m in mods}
    resolved = []
    while len(resolved) < len(deps):
        ready = [n for n, ds in deps.items() if n not in resolved and ds <= set(resolved)]
        if not ready:
            return False, "dependency cycle among modules"
        resolved.extend(sorted(ready))
    return True, ""


def should_decompose(d):
    """A single-module decomposition means the goal doesn't need the architecture step — fall through to the
    ordinary one-module path. Two or more modules => a real architecture worth confirming + seeding."""
    return len((d or {}).get("modules") or []) >= 2


def build_order(d):
    """Module names in dependency order (dependencies before dependents) — the order plans should build in."""
    deps = {m["name"]: set(m.get("depends_on") or []) for m in (d or {}).get("modules") or []}
    order = []
    while len(order) < len(deps):
        ready = sorted(n for n, ds in deps.items() if n not in order and ds <= set(order))
        if not ready:
            break
        order.extend(ready)
    return order


def _fn_name(sig):
    m = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*\(", str(sig))
    return m.group(1) if m else None


def render_architecture_md(goal, d):
    """The human-confirmed ARCHITECTURE.md: the module -> file -> folder plan, DEPENDS_ON, layout, build order."""
    mods = d.get("modules") or []
    out = ["# Architecture (goal → module/file/folder plan — #49)", "",
           "> Goal: %s" % goal, "",
           "**Layout:** %s" % (d.get("layout") or "(unspecified)")]
    if d.get("notes"):
        out.append("**Notes:** %s" % d["notes"])
    out += ["", "## Modules", ""]
    for m in mods:
        loc = ("%s/%s" % (m.get("folder"), m.get("file"))) if m.get("folder") else m.get("file", "")
        out.append("### `%s`  →  `%s`" % (m.get("name"), loc))
        out.append("- purpose: %s" % (m.get("purpose") or ""))
        out.append("- public API: %s" % ", ".join("`%s`" % a for a in (m.get("public_api") or [])))
        deps = m.get("depends_on") or []
        out.append("- depends on: %s" % (", ".join("`%s`" % x for x in deps) if deps else "—"))
        out.append("")
    out.append("**Build order:** %s" % " → ".join(build_order(d)))
    return "\n".join(out)


def seed_plans(d, base_out_dir):
    """Write ONE Lathe plan per module (in build order): MODULE_NAME, OUT_DIR (base/folder), FUNCTIONS stubbed
    from public_api (name + purpose-as-prompt + a placeholder test the spec step sharpens), and DEPENDS_ON. These
    are the plan-set the existing build/decompose path then implements. Returns the written plan paths."""
    os.makedirs(base_out_dir, exist_ok=True)
    by_file = {m["name"]: (m.get("file") or (m["name"] + ".py")) for m in d.get("modules") or []}
    written = []
    for name in build_order(d):
        m = next(x for x in d["modules"] if x["name"] == name)
        folder = (m.get("folder") or "").strip().strip("/")
        out_dir = (base_out_dir + "/" + folder) if folder else base_out_dir
        funcs = []
        for sig in (m.get("public_api") or []):
            fn = _fn_name(sig)
            if not fn:
                continue
            funcs.append({
                "name": fn,
                "prompt": "Implement %s for module '%s' (%s). Signature: %s. Output ONLY the function code."
                          % (fn, name, (m.get("purpose") or "").replace('"', "'"), str(sig).replace('"', "'")),
                # placeholder test — the SPEC step (analyst) sharpens these into real assertions before building.
                "tests": ["assert callable(%s)  # TODO(spec): replace with real behavioral assertions" % fn],
            })
        dep_files = [by_file[x] for x in (m.get("depends_on") or []) if x in by_file]
        plan = (
            "# lathe architecture-seeded plan (#49) — module %r; SPEC step must sharpen the placeholder tests.\n"
            "OUT_DIR = r%r\nMODULE_NAME = %r\nHEADER = \"\"\n"
            "DEPENDS_ON = %r\nFUNCTIONS = %s\n" % (name, out_dir.replace("\\", "/"), name, dep_files,
                                                   json.dumps(funcs, indent=2))
        )
        p = os.path.join(base_out_dir, "plan_%s.py" % name)
        with open(p, "w", encoding="utf-8") as f:
            f.write(plan)
        written.append(p)
    return written
