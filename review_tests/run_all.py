"""Orchestrator: run the ENTIRE independent Lathe test system with one command.

  python review_tests/run_all.py

Phases:
  1. battery_security   — validator/sandbox/spec-lint adversarial cases (no model needed)
  2. unit_functions     — direct tests of every pure toolchain + generated-ledger function
  3. review_tests       — review_tests/test_*.py (offline acceptance suite; model-gated ones skipped)
  4. repo's own tests   — projects/agentic-harness/tools/test_*.py
  5. ledger rebuild     — the multi-plan demo rebuilds offline from pins (scaling claim)
  6. CI steps           — the three .github/workflows/ci.yml checks, run locally
  7. cli_matrix         — every CLI command, all 5 workflows, B1-B7 repros (starts mock models)

Exit 0 = every phase green. Leaves the tree as it found it (kills mocks, restores state).
"""
import glob
import os
import re
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PY = sys.executable
PHASES = []


def run(name, args, cwd=ROOT, timeout=900, env=None):
    t0 = time.time()
    p = subprocess.run(args, cwd=cwd, env=env or os.environ.copy(),
                       capture_output=True, text=True, timeout=timeout)
    ok = p.returncode == 0
    PHASES.append((name, ok, "%.0fs" % (time.time() - t0)))
    print(p.stdout)
    if p.stderr.strip():
        print(p.stderr[-2000:])
    print(">>> phase %-22s %s\n" % (name, "GREEN" if ok else "RED (rc=%s)" % p.returncode))
    return ok


def _tree_snapshot():
    """Return the set of `git status --porcelain` lines, or None if not a git tree."""
    try:
        p = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                           capture_output=True, text=True, timeout=30)
        if p.returncode != 0:
            return None
        return set(l for l in p.stdout.splitlines() if l.strip())
    except Exception:
        return None


def _tree_restore(pre):
    """Undo any tree change a phase introduced since `pre` (best-effort, git-based).

    Tracked files modified during the phase are checked out; files that became
    untracked are removed. A no-op when `pre` is None (not a git checkout)."""
    if pre is None:
        return
    post = _tree_snapshot()
    if post is None:
        return
    for line in post - pre:
        status, path = line[:2], line[3:].strip().strip('"')
        try:
            if "?" in status:  # newly untracked -> remove
                fp = os.path.join(ROOT, path)
                if os.path.isfile(fp):
                    os.remove(fp)
            else:               # newly modified/added tracked -> restore
                subprocess.run(["git", "checkout", "--", path], cwd=ROOT,
                               capture_output=True, text=True, timeout=30)
        except Exception:
            pass


def wait_up(url, tries=20):
    for _ in range(tries):
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except Exception:
            time.sleep(0.3)
    return False


def main():
    print("=" * 70)
    print("Lathe independent test system — full sweep")
    print("=" * 70)
    # GUARANTEE (2026-07-12): enroll this run in a Windows kill-on-close Job Object
    # so that if the run dies for ANY reason (timeout, exception, terminal/session
    # teardown) the OS reaps EVERY descendant — cli_matrix's lathe builds, run_gates,
    # the lane gates, Playwright and Chromium. Windows has no process groups; without
    # this an interrupted full sweep orphans its whole subprocess tree.
    sys.path.insert(0, ROOT)
    try:
        import procguard
        _armed = procguard.arm()
    except Exception:
        _armed = False
    print("procguard: kill-on-close job %s\n" % ("ARMED — no orphan can outlive this run"
                                                 if _armed else "UNAVAILABLE (run in foreground!)"))

    run("battery_security", [PY, os.path.join(HERE, "battery_security.py")])
    run("unit_functions", [PY, os.path.join(HERE, "unit_functions.py")])

    # review_tests acceptance suite (offline). Runs BEFORE the heavy cli_matrix so a
    # fast failure surfaces early. Each test runs with cwd=ROOT and stdin CLOSED so the
    # #48 isatty/clarify path cannot block the suite. Model/endpoint-gated tests are
    # skipped by name (they need a live implementer/analyst/GitHub or only self-skip
    # offline — cli_matrix and the ledger phase cover the live paths).
    REVIEW_MODEL_GATED = {
        "test_api.py",             # posts to a live analyst endpoint; hangs offline
        "test_persona_fetch.py",   # fetches personas from GitHub (network)
        "test_regression_proof.py",  # e2e: needs a live implementer; only self-skips offline
        "test_reproducibility.py",   # e2e pin/rebuild: needs a live implementer; self-skips offline
    }
    rt_ok, rt_ran, rt_names = True, 0, []
    rt_pre = _tree_snapshot()
    for t in sorted(glob.glob(os.path.join(HERE, "test_*.py"))):
        base = os.path.basename(t)
        if base in REVIEW_MODEL_GATED:
            continue
        p = subprocess.run([PY, t], cwd=ROOT, stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, timeout=300)
        rt_ran += 1
        rt_names.append(base)
        if p.returncode != 0:
            rt_ok = False
            print("  [FAIL] %s\n%s" % (base, (p.stdout + p.stderr)[-500:]))
        else:
            print("  [PASS] %s" % base)
    _tree_restore(rt_pre)  # leave the tree as it found it (suite is non-hermetic)
    print("  ran %d review_tests: %s" % (rt_ran, ", ".join(rt_names)))
    PHASES.append(("review_tests (%d files)" % rt_ran, rt_ok, ""))
    print(">>> phase %-22s %s\n" % ("review_tests", "GREEN" if rt_ok else "RED"))

    # repo's own tests
    ok_all, ran = True, 0
    inner = os.path.join(ROOT, "projects", "agentic-harness")
    tools = os.path.join(inner, "tools")
    for t in sorted(glob.glob(os.path.join(tools, "test_*.py"))):
        # cwd=inner: test_autonomy_loop.py resolves "tools/..." relative to the harness root
        p = subprocess.run([PY, t], cwd=inner, capture_output=True, text=True, timeout=300)
        ran += 1
        if p.returncode != 0:
            ok_all = False
            print("  [FAIL] %s\n%s" % (os.path.basename(t), (p.stdout + p.stderr)[-500:]))
        else:
            print("  [PASS] %s" % os.path.basename(t))
    PHASES.append(("repo_own_tests (%d files)" % ran, ok_all, ""))
    print(">>> phase %-22s %s\n" % ("repo_own_tests", "GREEN" if ok_all else "RED"))

    # ledger multi-plan demo rebuild (offline, from pins)
    ledger_ok = True
    for plan in ("01_core.py", "02_stats.py", "03_summarize.py"):
        p = subprocess.run([PY, os.path.join(ROOT, "engine_v2.py"),
                            os.path.join(ROOT, "examples", "ledger", plan), "openai:local", "3"],
                           cwd=ROOT, capture_output=True, text=True, timeout=180)
        pinned = "REUSED (pinned)" in p.stdout
        zero_calls = '"tok_total": 0' in p.stdout
        ledger_ok &= (p.returncode == 0 and pinned and zero_calls)
        print("  [%s] ledger %s pinned=%s zero-model-calls=%s"
              % ("PASS" if pinned and zero_calls else "FAIL", plan, pinned, zero_calls))
    PHASES.append(("ledger_offline_rebuild", ledger_ok, ""))
    print(">>> phase %-22s %s\n" % ("ledger_rebuild", "GREEN" if ledger_ok else "RED"))

    # CI steps, locally
    ci_ok = True
    try:
        import ast
        for f in glob.glob(os.path.join(ROOT, "**", "*.py"), recursive=True):
            ast.parse(open(f, encoding="utf-8").read())
        print("  [PASS] CI step 1: every module parses")
    except Exception as e:
        ci_ok = False
        print("  [FAIL] CI step 1: %s" % e)
    sys.path.insert(0, os.path.join(ROOT, "projects", "agentic-harness", "tools"))
    try:
        from plan_validator import is_valid_plan
        assert is_valid_plan(open(os.path.join(ROOT, "examples", "hello.py"), encoding="utf-8").read())["ok"]
        assert not is_valid_plan('import os\nos.system("x")\nFUNCTIONS=[]\n')["ok"]
        print("  [PASS] CI step 2: validator accepts data / rejects code")
    except Exception as e:
        ci_ok = False
        print("  [FAIL] CI step 2: %s" % e)
    p = subprocess.run([PY, os.path.join(ROOT, "lathe.py"), "build", "examples/hello.py"],
                       cwd=ROOT, capture_output=True, text=True, timeout=180)
    m = re.search(r"METRICS_JSON_BEGIN===\s*(\{.*?\})\s*===METRICS_JSON_END", p.stdout, re.S)
    try:
        import json
        d = json.loads(m.group(1))
        assert d["build_ok"] and d["by_pinned"] >= 1 and d["tok_total"] == 0
        print("  [PASS] CI step 3: offline pinned rebuild, zero model calls")
    except Exception as e:
        ci_ok = False
        print("  [FAIL] CI step 3: %s" % e)
    PHASES.append(("ci_steps_local", ci_ok, ""))
    print(">>> phase %-22s %s\n" % ("ci_steps_local", "GREEN" if ci_ok else "RED"))

    # CLI matrix with mock models
    mocks = []
    try:
        for role, port in (("impl", 8089), ("analyst", 8787)):
            mocks.append(subprocess.Popen([PY, os.path.join(HERE, "mock_models.py"), role, str(port)],
                                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        assert wait_up("http://127.0.0.1:8089") and wait_up("http://127.0.0.1:8787"), "mocks failed to start"
        run("cli_matrix", [PY, os.path.join(HERE, "cli_matrix.py")], timeout=1800)
    finally:
        for m_ in mocks:
            m_.kill()

    print("=" * 70)
    bad = [p for p in PHASES if not p[1]]
    for name, ok, t in PHASES:
        print("  %-28s %s %s" % (name, "GREEN" if ok else "RED", t))
    print("\nOVERALL: %s (%d/%d phases green)"
          % ("GREEN" if not bad else "RED", len(PHASES) - len(bad), len(PHASES)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
