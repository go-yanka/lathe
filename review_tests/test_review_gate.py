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

# CONDITIONAL lenses are named for the decider's ACTUAL lens vocabulary (api/data/ui/perf) — a mandatory lens
# must match a lens hreview really emits findings for, else scan_findings_dir can never satisfy it. So API code
# makes the 'api' lens mandatory, migration + persistence both make 'data' mandatory, async UI makes 'ui'.
api = "from fastapi import FastAPI\napp = FastAPI()\n@app.get('/x')\ndef handler():\n    return 1\n"
check("API code makes the 'api' lens mandatory", "api" in RG.applicable(api), str(RG.applicable(api)))

mig = "def up():\n    op.execute('ALTER TABLE users ADD COLUMN age int')\n"
check("migration code makes the 'data' lens mandatory", "data" in RG.applicable(mig), str(RG.applicable(mig)))

db = "import sqlite3\nc = sqlite3.connect('x'); c.cursor().execute('INSERT INTO t VALUES (1)'); c.commit()\n"
check("persistence code makes the 'data' lens mandatory", "data" in RG.applicable(db), str(RG.applicable(db)))

ui = "el.addEventListener('click', async () => { await fetch('/x'); })\n"
check("async UI makes the 'ui' lens mandatory", "ui" in RG.applicable(ui), str(RG.applicable(ui)))

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

# 6) BEHAVIORAL (#51 core): REAL hreview-format findings files (WORD severities, not P-codes) driven through
#    scan_findings_dir -> max_severity -> verdict. This is the path the live gate runs; the OLD gate (P-code-only
#    max_severity + persona-named CONDITIONAL) fails EVERY assertion here.
_panel = list(RG.ALWAYS_CORE)
# (a) a real 'high | file | issue | fix' finding must BLOCK (word severity parsed)
_tb = tempfile.mkdtemp(prefix="rgb_")
for _l in _panel:
    _txt = ("high | auth.py:login | unsanitized input reaches exec() | parameterize\n"
            if _l == "security" else "no findings — clean\n")
    open(os.path.join(_tb, "review_%s.txt" % _l), "w", encoding="utf-8").write(_txt)
_vb = RG.verdict(RG.scan_findings_dir(_tb, _panel), applicable_lenses=_panel)
check("a real 'high | …' finding BLOCKS the gate (word severity parsed, not just P-codes)",
      _vb["blocked"] and ("security", "P1") in _vb["blockers"], str(_vb))
# (b) all-clean word-format findings PASS
_tp = tempfile.mkdtemp(prefix="rgp_")
for _l in _panel:
    open(os.path.join(_tp, "review_%s.txt" % _l), "w", encoding="utf-8").write("no findings — clean\n")
_vp = RG.verdict(RG.scan_findings_dir(_tp, _panel), applicable_lenses=_panel)
check("all-clean findings PASS the gate", not _vp["blocked"], str(_vp))
# (c) a mandatory lens whose file is absent BLOCKS (missing) — and the operator override clears it
_vm = RG.verdict(RG.scan_findings_dir(_tp, _panel + ["api"]), applicable_lenses=_panel + ["api"])
check("a mandatory lens with no findings file BLOCKS (missing)", _vm["blocked"] and "api" in _vm["missing"], str(_vm))
_vw = RG.verdict(RG.scan_findings_dir(_tp, _panel + ["api"]), applicable_lenses=_panel + ["api"], waive=["api"])
check("LATHE_REVIEW_WAIVE operator override clears a stuck mandatory lens", not _vw["blocked"], str(_vw))
# (d) the lens an API build makes mandatory is a REAL token, so review_<lens>.txt is actually writable (no over-block)
_api_extra = [l for l in RG.applicable(api) if l not in RG.ALWAYS_CORE]
check("API build's mandatory lens is a real lens token ('api') hreview can write a file for",
      _api_extra == ["api"], str(_api_extra))
for _d in (_tb, _tp):
    shutil.rmtree(_d, ignore_errors=True)

print("\nreview-gate (#51) acceptance: %s" % ("ALL PASS" if not fails else "FAILED: %s" % ", ".join(fails)))
sys.exit(0 if not fails else 1)
