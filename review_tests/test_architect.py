"""ACCEPTANCE — issue #49: the architecture / decomposition step turns a goal into a module→file→folder plan
with DEPENDS_ON, and SEEDS one valid plan per module for the build path. Tests the pure architect helpers
(parse/validate/order/render/seed) + static wiring of `lathe architect`. Model-free.

  Run:  python review_tests/test_architect.py     (repo root)
"""
import ast
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "projects", "agentic-harness", "tools"))
fails = []


def check(name, ok, detail=""):
    print("  %-66s %s %s" % (name, "PASS" if ok else "FAIL", detail if not ok else ""))
    if not ok:
        fails.append(name)


import architect as A  # noqa: E402

DECOMP = {
    "modules": [
        {"name": "tokenizer", "file": "tokenizer.py", "folder": "src", "purpose": "lex the expression",
         "public_api": ["tokenize(expr) -> list"], "depends_on": []},
        {"name": "parser", "file": "parser.py", "folder": "src", "purpose": "build an AST",
         "public_api": ["parse(tokens) -> ast"], "depends_on": ["tokenizer"]},
        {"name": "evaluator", "file": "evaluator.py", "folder": "src", "purpose": "evaluate the AST",
         "public_api": ["evaluate(expr) -> float"], "depends_on": ["parser"]},
    ],
    "layout": "src/ package (Python)", "notes": "classic pipeline",
}

# 1) parse — tolerant of a markdown fence / surrounding prose
import json  # noqa: E402
raw_fenced = "here you go:\n```json\n" + json.dumps(DECOMP) + "\n```\n"
check("parse_decomposition tolerates a code fence + prose", A.parse_decomposition(raw_fenced).get("modules"), "")

# 2) validate — accepts a good decomposition, rejects the bad shapes
check("validate accepts a good decomposition", A.validate_decomposition(DECOMP)[0], A.validate_decomposition(DECOMP)[1])
bad_name = {"modules": [{"name": "not ok!", "public_api": ["x()"]}]}
check("validate rejects a non-identifier module name", not A.validate_decomposition(bad_name)[0])
cyc = {"modules": [{"name": "a", "public_api": ["x()"], "depends_on": ["b"]},
                   {"name": "b", "public_api": ["y()"], "depends_on": ["a"]}]}
check("validate rejects a dependency cycle", not A.validate_decomposition(cyc)[0])
unk = {"modules": [{"name": "a", "public_api": ["x()"], "depends_on": ["ghost"]}]}
check("validate rejects an unknown dependency", not A.validate_decomposition(unk)[0])
nopub = {"modules": [{"name": "a", "public_api": []}]}
check("validate rejects a module with no public_api", not A.validate_decomposition(nopub)[0])

# 3) should_decompose + build_order
check("should_decompose is True for >=2 modules", A.should_decompose(DECOMP))
check("should_decompose is False for a single module",
      not A.should_decompose({"modules": [{"name": "solo", "public_api": ["f()"]}]}))
check("build_order respects dependencies (tokenizer before parser before evaluator)",
      A.build_order(DECOMP) == ["tokenizer", "parser", "evaluator"], str(A.build_order(DECOMP)))

# 4) render
md = A.render_architecture_md("an evaluator", DECOMP)
check("render_architecture_md lists modules + build order", ("## Modules" in md) and ("Build order" in md), md[:80])

# 5) seed_plans — writes one VALID plan per module, in build order, with MODULE_NAME/DEPENDS_ON/FUNCTIONS
tmp = tempfile.mkdtemp(prefix="i49_")
plans = A.seed_plans(DECOMP, tmp)
check("seed_plans writes one plan per module", len(plans) == 3, str([os.path.basename(p) for p in plans]))
allgood, detail = True, ""
seen_modnames = []
for p in plans:
    txt = open(p, encoding="utf-8").read()
    try:
        ast.parse(txt)                                     # every seeded plan is valid Python
    except SyntaxError as e:
        allgood, detail = False, "%s: %s" % (os.path.basename(p), e)
        break
    ns = {}
    exec(compile(txt, p, "exec"), ns)                      # and defines the expected plan globals
    if not (ns.get("MODULE_NAME") and isinstance(ns.get("FUNCTIONS"), list) and ns["FUNCTIONS"]):
        allgood, detail = False, "%s: missing MODULE_NAME/FUNCTIONS" % os.path.basename(p)
        break
    seen_modnames.append(ns["MODULE_NAME"])
check("every seeded plan is valid Python with MODULE_NAME + FUNCTIONS", allgood, detail)
check("seeded plans cover all modules", set(seen_modnames) == {"tokenizer", "parser", "evaluator"}, str(seen_modnames))
# the parser plan carries its DEPENDS_ON edge (on tokenizer.py)
parser_txt = open(os.path.join(tmp, "plan_parser.py"), encoding="utf-8").read()
check("seeded parser plan wires DEPENDS_ON = ['tokenizer.py']", "tokenizer.py" in parser_txt and "DEPENDS_ON" in parser_txt, parser_txt[:200])
# the function name is extracted from the public_api signature
check("seeded function name extracted from public_api ('parse')", '"name": "parse"' in parser_txt, parser_txt[:400])
shutil.rmtree(tmp, ignore_errors=True)

# 6) STATIC: `lathe architect` is wired
src = open(os.path.join(ROOT, "lathe.py"), encoding="utf-8").read()
check("cmd_architect defined + registered in dispatch", ("def cmd_architect(" in src) and ('"architect": cmd_architect' in src))
check("cmd_architect uses architect.decomposition + seed_plans", ("decomposition_prompt" in src) and ("seed_plans" in src))

print("\narchitect (#49) acceptance: %s" % ("ALL PASS" if not fails else "FAILED: %s" % ", ".join(fails)))
sys.exit(0 if not fails else 1)
