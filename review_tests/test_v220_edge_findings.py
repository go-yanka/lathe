"""INDEPENDENT REVIEW REPRO — v2.2.0 mutation-score gate edge findings (LATHE_REVIEW_V2.md §16).

Runnable evidence for the four defects reported in the adversarial pass. Every assertion here is the
executable form of a claim in §16, so the findings can be reproduced (and will regress-catch a fix):

  E1  the gate emits ZERO mutants for string/list/dict/boolean/membership/is-None/format functions
      -> "no mutants generated - nothing to judge" -> silent PASS (fails OPEN).
  E2  equivalent mutants FALSELY lower the score: a constant-with-slack function yields mutants no test
      can kill, so a PERFECT suite scores below STRICT's 0.5 -> a correct function would be BLOCKED.
  E3  STRICT requires CRITERIA only for FUNCTIONS plans; an ARTIFACTS-only plan is ungated.
  E4  regression-proof is name-keyed: renaming the fixed function reads as "new function" -> exempt.

Pure-logic only (no model/endpoint needed) — imports the shipped v2.2.0 tools directly.
Run:  python review_tests/test_v220_edge_findings.py     (repo root)

NOTE ON INTENT: this test PASSES while the defects are PRESENT (it asserts the buggy behavior, and prints
the §16 finding id). Once E1/E2/E3/E4 are fixed per §16.1, the corresponding asserts here should be inverted
(or this file retired in favor of review_tests/test_mutation_equiv.py + test_mutation_coverage.py). It exists
so the findings are checked-in, runnable evidence rather than prose.
"""
import ast
import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "projects", "agentic-harness", "tools")


def _load(mod):
    p = os.path.join(TOOLS, mod + ".py")
    spec = importlib.util.spec_from_file_location(mod, p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


ms = _load("mutation_score")
sm = _load("strict_mode")
rp = _load("regression_proof")

fails = []


def check(finding, name, ok, detail=""):
    tag = "PASS" if ok else "FAIL"
    print("  [%s] %-56s %s %s" % (finding, name, tag, detail if not ok else ""))
    if not ok:
        fails.append("%s/%s" % (finding, name))


def equivalent_mutants(code, limit=8, sample=None):
    """Return (n_mutants, indices of mutants behaviorally identical to the original over `sample`)."""
    if sample is None:
        sample = list(range(-20, 21))
    muts = ms.mutate_code(code, limit)
    ns0 = {}
    exec(code, ns0)
    fn = [v for k, v in ns0.items() if callable(v)][0]
    equiv = []
    for i, u in enumerate(muts):
        nsm = {}
        try:
            exec(u, nsm)
            fm = [v for k, v in nsm.items() if callable(v)][0]
            if all(fm(x) == fn(x) for x in sample):
                equiv.append(i)
        except Exception:
            pass
    return muts, equiv


print("\n=== E1 — gate free-passes non-arithmetic functions (fails OPEN) ===")
NO_MUTANT_FUNCS = {
    "string methods": "def up(s):\n    return s.strip().upper()\n",
    "list/dict build": "def pair(a, b):\n    return {'a': a, 'b': b}\n",
    "boolean logic": "def both(a, b):\n    return a and b\n",
    "membership": "def has(x, xs):\n    return x in xs\n",
    "is None": "def empty(x):\n    return x is None\n",
    "format": "def fmt(n):\n    return 'id=%s' % n\n",
}
for label, code in NO_MUTANT_FUNCS.items():
    muts = ms.mutate_code(code, 8)
    blocked, why = ms.mutation_gate("0.5", 0, len(muts))
    # DEFECT: zero mutants AND the gate does not block (free pass) even with a zero-kill suite.
    check("E1", "%s -> 0 mutants, gate passes" % label, len(muts) == 0 and not blocked, "muts=%d blocked=%s" % (len(muts), blocked))
# contrast: an arithmetic function DOES get mutated (sanity — the gate works where it can)
check("E1", "arithmetic baseline DOES mutate (contrast)", len(ms.mutate_code("def f(x):\n    return x + 1\n", 8)) > 0)


print("\n=== E2 — equivalent mutants would falsely BLOCK correct, complete code ===")
CODE = "def scale(x):\n    n = 5\n    if n > 0:\n        return x * 2\n    return -x\n"
muts, equiv = equivalent_mutants(CODE)
killable = len(muts) - len(equiv)
best_possible = killable / len(muts) if muts else 1.0
# DEFECT: >=1 equivalent mutant exists, and the best-possible score is below STRICT's 0.5 -> false block.
check("E2", "constant-guard function has equivalent mutants", len(equiv) >= 1, "equiv=%s of %d" % (equiv, len(muts)))
check("E2", "a PERFECT suite scores below 0.5 (=> false block)", best_possible < 0.5, "best=%.2f (killable %d/%d)" % (best_possible, killable, len(muts)))
# and the gate, given the best-possible kill count, REFUSES:
blocked, why = ms.mutation_gate("0.5", killable, len(muts))
check("E2", "gate REFUSES even the best-possible suite", blocked, why)


print("\n=== E3 — STRICT ungates ARTIFACTS-only plans ===")
gaps_fn = sm.strict_plan_gaps("1", True, None)     # FUNCTIONS plan, no CRITERIA -> should gap
gaps_art = sm.strict_plan_gaps("1", False, None)   # ARTIFACTS-only plan -> DEFECT: no gap
check("E3", "FUNCTIONS plan without CRITERIA is gapped", gaps_fn != [])
check("E3", "ARTIFACTS-only plan is NOT gapped (defect)", gaps_art == [])


print("\n=== E4 — regression-proof bypassed by renaming the fixed function ===")
old_src = "def parse_v1(s):\n    return int(s)\n"
extracted = rp.extract_def(old_src, "parse_v2")            # renamed in the 'fix'
blocked, why = rp.proof_gate("1", extracted, True)          # would-be no-repro change
check("E4", "renamed function extracts as '' ", extracted == "")
check("E4", "proof_gate treats it as new -> EXEMPT (defect)", blocked is False and "new function" in why, why)


print("\nv2.2.0 edge findings repro: %s" % ("ALL PRESENT (findings reproduced)" if not fails else "UNEXPECTED: %s" % ", ".join(fails)))
sys.exit(0 if not fails else 1)
