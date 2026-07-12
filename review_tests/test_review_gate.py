"""ACCEPTANCE — issue #51: CE review is a stage-wired, CONDITIONAL-MANDATORY, SEVERITY-ROUTED gate — not an
optional read-only end-step. Tests the pure routing (always-core + triggered conditionals), the severity-routed
fail-closed verdict (P0/P1 block; a missing mandatory lens blocks), and the `lathe review --gate` wiring.
Model-free.

  Run:  python review_tests/test_review_gate.py     (repo root)
"""
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


import review_gate as RG  # noqa: E402

# 1) CONDITIONAL-MANDATORY applicability
plain = "def add(a, b):\n    return a + b\n"
must_plain = RG.applicable(plain)
check("always-core always applies", set(RG.ALWAYS_CORE) <= set(must_plain), str(must_plain))
check("plain code triggers NO conditionals (no noise)", set(must_plain) == set(RG.ALWAYS_CORE), str(must_plain))

api = "from fastapi import FastAPI\napp = FastAPI()\n@app.get('/x')\ndef handler():\n    return 1\n"
check("API code triggers api-contract (mandatory here)", "api-contract" in RG.applicable(api), str(RG.applicable(api)))

mig = "def up():\n    op.execute('ALTER TABLE users ADD COLUMN age int')\n"
check("migration code triggers data-migration", "data-migration" in RG.applicable(mig), str(RG.applicable(mig)))

db = "import sqlite3\nc = sqlite3.connect('x'); c.cursor().execute('INSERT INTO t VALUES (1)'); c.commit()\n"
check("persistence code triggers data-integrity-guardian", "data-integrity-guardian" in RG.applicable(db))

ui = "el.addEventListener('click', async () => { await fetch('/x'); })\n"
check("async UI triggers julik-frontend-races", "julik-frontend-races" in RG.applicable(ui))

check("release adds project-standards to the mandatory set", "project-standards" in RG.applicable(plain, release=True))

# 2) severity scan
check("max_severity returns the most severe P-level", RG.max_severity("some P2 and a P0 here") == "P0")
check("max_severity None when nothing flagged", RG.max_severity("all clean, no findings") is None)

# 3) severity-routed verdict — FAIL-CLOSED on P0/P1, passes on P2/P3
findings_block = {"correctness": "found a P1 off-by-one", "security": "clean", "adversarial": "clean",
                  "maintainability": "clean", "reliability": "clean", "testing": "clean"}
v = RG.verdict(findings_block, applicable_lenses=RG.ALWAYS_CORE)
check("verdict BLOCKS on a P1 finding", v["blocked"] and ("correctness", "P1") in v["blockers"], str(v))

findings_ok = {k: ("a P3 nit" if k == "maintainability" else "clean") for k in RG.ALWAYS_CORE}
v2 = RG.verdict(findings_ok, applicable_lenses=RG.ALWAYS_CORE)
check("verdict PASSES when only P2/P3 present", not v2["blocked"], str(v2))

# a mandatory lens that DID NOT run is not a silent pass — it blocks
v3 = RG.verdict({"correctness": "clean"}, applicable_lenses=RG.ALWAYS_CORE)
check("verdict BLOCKS when a mandatory lens didn't run", v3["blocked"] and "security" in v3["missing"], str(v3))

# 4) scan_findings_dir reads hreview's per-lens files
tmp = tempfile.mkdtemp(prefix="i51_")
open(os.path.join(tmp, "review_correctness.txt"), "w", encoding="utf-8").write("correctness: found a P0 logic bug")
open(os.path.join(tmp, "review_security.txt"), "w", encoding="utf-8").write("security: clean")
scanned = RG.scan_findings_dir(tmp, ["correctness", "security", "reliability"])
check("scan_findings_dir reads per-lens findings that exist", set(scanned) == {"correctness", "security"}, str(list(scanned)))
check("scanned findings feed the verdict (P0 blocks)", RG.verdict(scanned, ["correctness", "security"])["blocked"])
shutil.rmtree(tmp, ignore_errors=True)

# 5) STATIC: `lathe review --gate` is wired
src = open(os.path.join(ROOT, "lathe.py"), encoding="utf-8").read()
check("cmd_review has a --gate mode", '_gate = "--gate" in args' in src)
check("cmd_review uses review_gate (applicable + verdict, fail-closed)",
      ("import review_gate" in src) and ("_RG.applicable(" in src) and ("_RG.verdict(" in src))

print("\nreview-gate (#51) acceptance: %s" % ("ALL PASS" if not fails else "FAILED: %s" % ", ".join(fails)))
sys.exit(0 if not fails else 1)
