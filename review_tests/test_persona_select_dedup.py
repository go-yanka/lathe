"""ACCEPTANCE — #38: the dead `select_personas` duplicate is gone; there is ONE live selection path.

`persona_select.select_personas` had no live caller (the live decider, `persona_orchestrator.select_live`,
re-implements ranking inline and tie-breaks by RELEVANCE rank, while the dead copy tie-broke by name — the
two disagreed). It is removed from BOTH the generated module and its plan, in sync; the shared primitive
`ucb1` (the one thing `select_live` actually imports) is kept byte-identical.

Model-free. Run:  python review_tests/test_persona_select_dedup.py     (repo root)
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "projects", "agentic-harness", "tools")
sys.path.insert(0, TOOLS)
fails = []


def check(name, ok, detail=""):
    print("  %-64s %s %s" % (name, "PASS" if ok else "FAIL", detail if not ok else ""))
    if not ok:
        fails.append(name)


import persona_select as PS  # noqa: E402

# 1) the dead duplicate is gone
check("select_personas removed from persona_select", not hasattr(PS, "select_personas"))

# 2) the shared primitive the live path uses is kept + still correct
check("ucb1 still present (the live shared primitive)", hasattr(PS, "ucb1"))
check("ucb1 unseen -> +inf", PS.ucb1(0.5, 0, 100, 1.4) == float("inf"))
check("ucb1 pure-exploit (c=0) -> mean", PS.ucb1(0.8, 10, 100, 0.0) == 0.8)

# 3) the live decider path exists and imports ucb1 (not the dead duplicate)
import persona_orchestrator as PO  # noqa: E402
check("select_live is the live selection path", hasattr(PO, "select_live"))
osrc = open(os.path.join(TOOLS, "persona_orchestrator.py"), encoding="utf-8").read()
check("select_live imports ucb1 (shared primitive), not select_personas",
      ("from persona_select import ucb1" in osrc) and ("select_personas" not in osrc))

# 4) plan and generated module are IN SYNC — neither names select_personas anymore (no drift)
psrc = open(os.path.join(ROOT, "projects", "agentic-harness", "plans", "H_persona_select.py"), encoding="utf-8").read()
msrc = open(os.path.join(TOOLS, "persona_select.py"), encoding="utf-8").read()
check("plan no longer specifies select_personas", "select_personas" not in psrc)
check("generated module no longer defines select_personas", "select_personas" not in msrc)

# 5) nothing anywhere in the tree still references the dead symbol
import subprocess
hits = []
for base, _dirs, files in os.walk(ROOT):
    if os.sep + ".git" in base:
        continue
    for fn in files:
        if fn.endswith(".py") and fn != os.path.basename(__file__):
            try:
                if "select_personas" in open(os.path.join(base, fn), encoding="utf-8", errors="ignore").read():
                    hits.append(os.path.relpath(os.path.join(base, fn), ROOT))
            except OSError:
                pass
check("no file in the tree references select_personas anymore", not hits, str(hits))

print("\npersona-select dedup (#38) acceptance: %s" % ("ALL PASS" if not fails else "FAILED: %s" % ", ".join(fails)))
sys.exit(0 if not fails else 1)
