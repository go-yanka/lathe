"""ACCEPTANCE — issue #45: `lathe do` must not silently collapse a complex goal to trivial helpers and ship
"gated-green". The gates verify the DRAFTED spec, never the goal-vs-deliverable gap. The fix adds a
deterministic goal-vs-deliverable check at the delivery checkpoint (runs even when the Advocate is off, e.g.
autonomous --assume runs) that flags a built surface which is a trivial SUBSET of the original goal.

This tests the pure detection helpers on the EXACT reported scenario, and statically verifies the check is
wired into cmd_do's delivery path.

  Run:  python review_tests/test_goal_delivery_gap.py     (repo root)
"""
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
fails = []


def check(name, ok, detail=""):
    print("  %-66s %s %s" % (name, "PASS" if ok else "FAIL", detail if not ok else ""))
    if not ok:
        fails.append(name)


import lathe  # noqa: E402

# The reported goal (paraphrased) and the trivial subset the run actually shipped.
GOAL = ("Build expr.py to safely evaluate arithmetic expressions, evaluate(expr), a tokenizer plus a "
        "recursive-descent parser, an EvalError exception, and thorough tests.")
TRIVIAL = ["is_balanced_parens", "contains_unknown_char", "strip_expr_whitespace", "expr_str_helpers"]
REAL = ["evaluate", "tokenize", "parse_expr", "expr"]

# 1) the goal's requested capability is extracted
named = lathe._goal_named_callables(GOAL)
check("goal-named callables include the requested 'evaluate'", "evaluate" in named, str(named))

# 2) THE BUG CASE: a trivial-helper build is flagged (evaluate() was never delivered)
gap = lathe._goal_delivery_gap(GOAL, TRIVIAL)
check("trivial-subset build is flagged as under-delivery (evaluate missing)", "evaluate" in gap, str(gap))

# 3) NEGATIVE: a build that actually delivers evaluate() is NOT flagged
gap_ok = lathe._goal_delivery_gap(GOAL, REAL)
check("a build that delivers evaluate() is NOT flagged", "evaluate" not in gap_ok, str(gap_ok))

# 4) substring match keeps it conservative: 'evaluate' delivered by 'evaluate_expr' counts
gap_fuzzy = lathe._goal_delivery_gap("please add evaluate(x)", ["evaluate_expr", "helper"])
check("substring match: evaluate() delivered by evaluate_expr is NOT flagged", "evaluate" not in gap_fuzzy, str(gap_fuzzy))

# 5) _built_surface_names reads real def names from a workspace
tmp = tempfile.mkdtemp(prefix="i45_")
open(os.path.join(tmp, "expr_str_helpers.py"), "w", encoding="utf-8").write(
    "def is_balanced_parens(s):\n    return True\n\ndef strip_expr_whitespace(s):\n    return s\n")
open(os.path.join(tmp, "_itest_expr.py"), "w", encoding="utf-8").write("def evaluate(x):\n    return 0\n")  # itest ignored
surface = lathe._built_surface_names(tmp)
check("built-surface reads module def names", {"is_balanced_parens", "strip_expr_whitespace"} <= surface, str(surface))
check("built-surface IGNORES the generated itest (no false 'evaluate')", "evaluate" not in surface, str(surface))
import shutil
shutil.rmtree(tmp, ignore_errors=True)

# 6) STATIC: the check is actually WIRED into cmd_do's delivery path (not just defined)
src = open(os.path.join(ROOT, "lathe.py"), encoding="utf-8").read()
check("delivery checkpoint calls _goal_delivery_gap(goal, ...)", "_goal_delivery_gap(goal" in src)
check("under-delivery state is recorded/surfaced (under_delivery)", "under_delivery" in src)
check("Advocate delivery context is fed the goal-vs-deliverable gap", "GOAL-VS-DELIVERABLE" in src)

# 7) #45 STRICT HOLD — under LATHE_STRICT a real gap is a DETERMINISTIC hold, not just Advocate-discretion.
gap = lathe._goal_delivery_gap("build an evaluate(x) CLI", ["helper", "main"])   # 'evaluate' missing -> real gap
check("a real under-delivery gap is detected", "evaluate" in gap, str(gap))
check("#45 under LATHE_STRICT a real gap HOLDS deterministically", lathe._under_delivery_should_hold(gap, True) is True)
check("#45 without STRICT the gap does NOT hard-hold (advisory / Advocate path)", lathe._under_delivery_should_hold(gap, False) is False)
check("#45 STRICT with NO gap does not hold", lathe._under_delivery_should_hold([], True) is False)
# wired into cmd_do: the hold branch returns (blocks) on _ud_missing under STRICT
check("#45 cmd_do enforces the STRICT hold (calls _under_delivery_should_hold + returns)",
      ("_under_delivery_should_hold(_ud_missing" in src) and ("[HOLD] LATHE_STRICT" in src))

print("\ngoal-delivery-gap (#45) acceptance: %s" % ("ALL PASS" if not fails else "FAILED: %s" % ", ".join(fails)))
sys.exit(0 if not fails else 1)
