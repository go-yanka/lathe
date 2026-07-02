# hand-maintained spine — NOT harness-regeneratable (this is an authored prompt template, not a TDD-discoverable
# pure function). Its origin plan T4_planner_prompt.py builds only a bare skeleton and has been RETIRED to
# _archive/ so it can never overwrite this file. Edit DIRECTLY. The engine refuses to overwrite it (_CORE_INFRA).
import ast
import os


def _mods_via_ctags(tools_dir):
    """Module names that expose a public def, via the REAL repo-map (universal-ctags — multi-language). Returns
    None if ctags isn't available so the caller falls back to the stdlib-ast scan (portable)."""
    try:
        from repomap import ctags_available, code_structure
    except Exception:
        return None
    if not ctags_available():
        return None
    struct = code_structure([tools_dir])
    if not struct:
        return None
    mods = []
    for path, defs in struct.items():
        b = os.path.basename(path)
        if not b.endswith(".py") or b.startswith(("_", "test_")):
            continue
        if any(not d.get("name", "").startswith("_") and not d.get("scope") for d in defs):   # a public TOP-LEVEL def
            mods.append(b[:-3])
    return sorted(mods)


def _existing_inventory(tools_dir=None):
    """Build an EXISTING-CODE inventory (module names with a public def) + known shared RESOURCES, so the planner
    REUSES/EXTENDS what's there instead of duplicating. Prefers the REAL multi-language repo-map (ctags); falls
    back to a stdlib-ast scan (Python-only) when ctags is absent. Returns a prompt block string."""
    tools_dir = tools_dir or os.path.dirname(os.path.abspath(__file__))
    mods = _mods_via_ctags(tools_dir)               # the real OSS tool (multi-language)
    if mods is None:                                # ctags absent -> stdlib-ast fallback (Python only)
      mods = []
      try:
        for fn in sorted(os.listdir(tools_dir)):
            if not fn.endswith(".py") or fn.startswith(("_", "test_")):
                continue
            try:
                tree = ast.parse(open(os.path.join(tools_dir, fn), encoding="utf-8").read())
            except Exception:
                continue
            # count async defs and classes too — a module exposing only `async def` or a class used to be invisible
            # to the inventory, so the planner was told it didn't exist and licensed to build a duplicate.
            if any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                   and not n.name.startswith("_") for n in tree.body):
                mods.append(fn[:-3])                         # module NAMES only (the ALREADY-DONE list carries the fn names)
      except Exception:
        mods = []
    # The SHARED RESOURCES line below is unconditional (a fresh/empty tools/ used to lose it and the planner would
    # propose harness2.db). EXISTING MODULES is conditional on mods. NO truncation (the old mods[:80] cap silently
    # reintroduced the exact duplication bug this inventory exists to prevent once tools/ grew past 80).
    parts = []
    if mods:
        parts.append("EXISTING MODULES (extend one of these if your feature fits it; do NOT make a near-duplicate "
                     "module): " + ", ".join(mods) + ".")
    parts.append("EXISTING SHARED RESOURCES (reuse; do NOT create a second): harness.db = the task board "
                 "(one canonical DB).")
    return "\n".join(parts)


def _expert_lenses(goal):
    """Decider: pick the expert personas most relevant to THIS goal and tell the analyst to think through their
    lenses — so the thinking harness auto-spawns the right experts per goal. Selection is harness-built
    (agent_router.select_agents_for_goal) over agents/catalog.json. Token-lean (names + capabilities). Best-effort."""
    try:
        import sys, json
        _here = os.path.dirname(os.path.abspath(__file__))
        if _here not in sys.path:
            sys.path.insert(0, _here)
        from agent_router import select_agents_for_goal
        cat = json.load(open(os.path.join(os.path.dirname(_here), "agents", "catalog.json"), encoding="utf-8"))
        ents = cat.get("agents", [])
        names = select_agents_for_goal(goal, [[e["name"], e.get("capability", "")] for e in ents], 3)
        try:                                    # CE FLOOR (owner directive): the Compound-Engineering reviewers
            from persona_market import ensure_ce_floor        # are the strongest — guarantee >=1 in every selection
            _ce = [e["name"] for e in ents if e.get("source", "").startswith("EveryInc")]
            names = ensure_ce_floor(names, _ce, "correctness-reviewer")
        except Exception:
            pass
        if not names:
            return ""
        by = {e["name"]: e for e in ents}
        out = ["EXPERT LENSES (think through these specialists for THIS goal — adopt their concerns in the spec + tests):"]
        out += ["- %s: %s" % (n, by[n].get("capability", "")) for n in names]
        try:                                    # D7: a needed-but-absent expert is FETCHED (license-gated) and its
            from persona_spawn import auto_spawn_for_goal      # BODY injected — not just its name as a hint
            for _n, _md, _body in auto_spawn_for_goal(goal, 2):
                out.append("\nFETCHED EXPERT PERSONA — %s (auto-spawned for this goal; adopt this specialist's "
                           "approach in the spec + tests):\n%s" % (_n, _body.strip()[:1800]))
        except Exception:
            pass                                # best-effort — the name+capability hints above still stand
        return "\n".join(out)
    except Exception:
        return ""


def build_planner_prompt(objective, done_list, last_blocker=None):
    lines = []
    lines.append("OBJECTIVE: " + objective)
    if not done_list:
        lines.append("ALREADY DONE: (nothing yet)")
    else:
        lines.append("ALREADY DONE (do NOT re-propose these):")
        for item in done_list:
            lines.append("- " + item)
    _inv = _existing_inventory()
    if _inv:
        lines.append("")
        lines.append(_inv)
    _lenses = _expert_lenses(objective)                # decider: auto-select expert lenses for THIS goal
    if _lenses:
        lines.append("")
        lines.append(_lenses)
    if last_blocker is not None and last_blocker != "":
        lines.append("LAST BLOCKER (fix this): " + last_blocker)
    # STRICT output contract — the analyst's reply is saved verbatim as a Python plan file and parsed by a
    # data-only validator. Loose output (prose, markdown fences, multiple files, smart-quotes/em-dashes,
    # f-strings) is rejected and wastes a repair cycle, so spell the format out exactly.
    lines.append(
        "\nREUSE-FIRST PRE-FLIGHT (do this BEFORE choosing a function): scan ALREADY DONE and EXISTING MODULES "
        "above. If the capability you'd write already exists, or fits inside an existing module, DON'T duplicate "
        "it — pick a DIFFERENT genuinely-missing helper from the OBJECTIVE instead. Never introduce a second "
        "database or resource; the canonical store already exists. Only propose code that does not already exist.\n"
        "\nReturn EXACTLY ONE plan for ONE new small helper module. OUTPUT RULES — follow precisely:\n"
        "- Output RAW PYTHON ONLY. No prose, no commentary, no markdown fences (no ```), no file paths,\n"
        "  do NOT try to write files. Your entire reply must be the plan file's text and nothing else.\n"
        "- ASCII ONLY. Never use em-dashes or smart quotes; use plain - and straight ' \" .\n"
        "- Exactly these top-level assignments, in this shape (string literals only, NO f-strings, NO + concat):\n"
        "    OUT_DIR = \"projects/agentic-harness/tools\"\n"   # RELATIVE + forward-slash -> portable across Windows AND POSIX (backslashes broke on Linux/macOS)
        "    MODULE_NAME = \"<snake_case_identifier>\"\n"
        "    HEADER = \"\"\n"
        "    GLUE = \"\"\n"
        "    FUNCTIONS = [ {\"name\": \"<identifier>\", \"prompt\": \"<plain string>\", "
        "\"tests\": [\"assert ...\", \"assert ...\", \"assert ...\", \"assert ...\"]} ]\n"
        "- FUNCTIONS is a LITERAL list of LITERAL dicts. Every 'name' is a valid Python identifier. Every\n"
        "  function needs at least 4 plain-string assert tests (include edge cases: empty, None, 0).\n"
        "- Keep it to ONE small PURE function (no I/O, no graph/recursion/parsing). Prompts may use implicit\n"
        "  string-literal concatenation across lines ( \"a\" \"b\" ) but never f-strings or the + operator."
    )
    return "\n".join(lines)

