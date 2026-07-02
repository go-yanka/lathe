"""End-to-end matrix: every exposed `lathe` command, all 5 workflows, and the B1-B7 fix repros.

Requires the two mock endpoints (see mock_models.py); run_all.py starts them automatically.
Captures TRUE exit codes via file redirection (no pipe/SIGPIPE artifacts).

Run:  python review_tests/run_all.py            (recommended — manages mocks + cleanup)
      python review_tests/cli_matrix.py         (if mocks are already up)
"""
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable
ENV = dict(os.environ,
           LOCAL_OPENAI_URL="http://127.0.0.1:8089/v1/chat/completions",
           HARNESS_CLAUDE_URL="http://127.0.0.1:8787/v1/chat/completions",
           LATHE_REVIEW_USE_CLI="0")        # B3: force the pluggable-URL path (this env HAS a `claude` CLI)
ENV.pop("LATHE_AUTO_COMMIT", None)          # B4: default must be NO auto-commit

RESULTS = []


def sh(args, timeout=90, stdin=None, env=ENV):
    try:
        p = subprocess.run([PY, os.path.join(ROOT, "lathe.py")] + args, cwd=ROOT, env=env,
                           input=stdin, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout + p.stderr
    except subprocess.TimeoutExpired as e:
        return 124, (e.stdout or "") + (e.stderr or "") if isinstance(e.stdout, str) else "TIMEOUT"


def case(name, ok, note=""):
    RESULTS.append((name, bool(ok), note))
    print("  [%s] %s %s" % ("PASS" if ok else "FAIL", name, (note or "")[:90]))


def git_head():
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                          capture_output=True, text=True).stdout.strip()


def commands_matrix():
    print("\n== CLI command matrix ==")
    head0 = git_head()

    rc, out = sh(["help"]); case("help", rc == 0 and "Usage" in out)
    rc, out = sh(["plans"]); case("plans", rc == 0 and "M01" in out)
    rc, out = sh(["status"]); case("status", rc == 0 and "implementer" in out)
    rc, out = sh(["decompose"]); case("decompose (seeds board)", rc == 0 and "seeded" in out)
    rc, out = sh(["board"]); case("board", rc == 0 and "M01" in out)
    rc, out = sh(["whatis"]); case("whatis", rc == 0 and "sandbox" in out)
    rc, out = sh(["whatis", "sandbox"]); case("whatis sandbox", rc == 0 and "live" in out)
    rc, out = sh(["gate"]); case("gate (regression, 6 checks)", rc == 0 and "FAIL" not in out, out.strip().splitlines()[-1] if out else "")
    rc, out = sh(["wait", "M01_token_overlap", "sig1"]); case("wait (park dormant)", rc == 0)
    rc, out = sh(["waiting"]); case("waiting (lists dormant)", rc == 0 and "sig1" in out)
    rc, out = sh(["resume", "M01_token_overlap", "sig1"]); case("resume (deliver signal)", rc == 0 and "RESUMED" in out)
    rc, out = sh(["lint-spec", "projects/agentic-harness/plans/M01_token_overlap.py"])
    case("lint-spec (mutation probe)", rc == 0 and "OK" in out)
    rc, out = sh(["dups"]); case("dups", rc == 0)
    rc, out = sh(["clean", "--dry"]); case("clean --dry", rc == 0)
    rc, out = sh(["checkpoint", "list"]); case("checkpoint list", rc == 0)
    rc, out = sh(["build", "examples/hello.py"])
    case("build (pinned offline)", rc == 0 and "REUSED (pinned)" in out)
    case("B5 fix: integration label 'n/a (no INTEGRATION defined)'", "n/a (no INTEGRATION defined)" in out,
         "" if "n/a" in out else out[-200:])
    rc, out = sh(["verify", "examples/hello.py"]); case("verify (pin reuse)", rc == 0 and "REUSED" in out)
    rc, out = sh(["do", "a function that parses a duration like 2h30m into seconds"], timeout=120)
    case("do (analyst+implementer end-to-end)", rc == 0 and "DONE" in out, out.strip().splitlines()[-1] if out else "")
    rc, out = sh(["chat"], stdin="status\nquit\n", timeout=60); case("chat (REPL)", rc == 0)
    rc, out = sh(["auto", "build a small helper"], timeout=120)
    case("auto (self-feed loop)", rc == 0 and "built=" in out)
    case("B4 fix: auto did NOT git-commit (opt-in now)", git_head() == head0,
         "HEAD moved!" if git_head() != head0 else "")
    rc, out = sh(["run", "1"], timeout=120)
    case("run (dispatcher)", rc == 0)
    case("B7 fix: no raw Traceback in dispatcher output", "Traceback (most recent call last)" not in out)
    rc, out = sh(["metrics"]); case("metrics", rc == 0)
    rc, out = sh(["metrics", "summary"]); case("metrics summary", rc == 0 and "build success" in out)
    rc, out = sh(["logs", "--tail"]); case("logs --tail", rc == 0)
    rc, out = sh(["issues"]); case("issues", rc == 0)
    rc, out = sh(["review", "correctness", "lathe.py"], timeout=90)
    case("B3 fix: review completes via HARNESS_CLAUDE_URL (no claude CLI)", rc == 0 and "REVIEW FINDINGS" in out,
         "rc=%s" % rc)
    rc, out = sh(["map", "lathe.py"], timeout=30)
    case("map (graceful without ctags)", rc in (0, 1) and ("ctags" in out or "def " in out))
    rc, out = sh(["gate", "h3"]); case("gate h3 (graceful: consumer-only)", rc == 2 and "not found" in out)
    rc, out = sh(["checkin"], timeout=60)
    case("checkin (gated; reports blockers or clean)", rc in (0, 1) and ("blocker" in out.lower() or "clean" in out.lower() or "green" in out.lower()), out.strip().splitlines()[-1] if out.strip() else "")
    rc, out = sh(["selftest"], timeout=180)
    case("selftest", "capabilities confirmed" in out, out.strip().splitlines()[-1] if out.strip() else "")
    case("B6 fix: selftest label reflects configured model (no '35B')", "35B" not in out)
    case("B2 fix: selftest regression sub-check green on fresh board", "[FAIL] regression" not in out)


def fix_repros():
    print("\n== B1/B2 direct repros ==")
    # B1: plan with no OUT_DIR must build into the plan's own dir, no placeholder dir.
    calc_dir = os.path.join(ROOT, "examples", "calc")
    for junk in (os.path.join(ROOT, "<LATHE_ROOT>\\game_out"),):
        shutil.rmtree(junk, ignore_errors=True)
    for f in ("calc.py", ".pins.json", "RUN_REPORT.md"):
        p = os.path.join(calc_dir, f)
        if os.path.exists(p):
            os.unlink(p)
    p = subprocess.run([PY, os.path.join(ROOT, "engine_v2.py"),
                        os.path.join(calc_dir, "plan_add.py"), "openai:local", "3"],
                       cwd=ROOT, env=ENV, capture_output=True, text=True, timeout=120)
    built_in_place = os.path.exists(os.path.join(calc_dir, "calc.py"))
    placeholder = os.path.exists(os.path.join(ROOT, "<LATHE_ROOT>\\game_out"))
    case("B1 fix: no-OUT_DIR plan builds into plan's own dir", built_in_place and not placeholder,
         "calc.py in plan dir=%s, placeholder dir=%s" % (built_in_place, placeholder))
    p2 = subprocess.run([PY, os.path.join(ROOT, "engine_v2.py"),
                         os.path.join(calc_dir, "plan_add.py"), "openai:local", "3"],
                        cwd=ROOT, env=ENV, capture_output=True, text=True, timeout=120)
    case("pin reuse on rebuild (reproducibility)", "REUSED (pinned)" in p2.stdout)
    case("B6 fix: run labels say 'local' not 'qwen'", "(qwen)" not in p.stdout and "local" in p.stdout)

    # B2: fresh-clone state (no harness.db) must not FAIL the registry gate.
    db = os.path.join(ROOT, "projects", "agentic-harness", "harness.db")
    saved = None
    if os.path.exists(db):
        saved = db + ".save"
        shutil.move(db, saved)
    g = subprocess.run([PY, os.path.join(ROOT, "projects", "agentic-harness", "qa", "run_gates.py")],
                       cwd=os.path.join(ROOT, "projects", "agentic-harness"),
                       capture_output=True, text=True, timeout=120)
    case("B2 fix: registry gate green with missing runtime DB", g.returncode == 0 and "FAIL" not in g.stdout,
         [l for l in g.stdout.splitlines() if "capability_registry" in l][:1])
    if saved:
        shutil.move(saved, db)


def workflows_matrix():
    print("\n== workflows (all 5): contract + dry view + --run verdict ==")
    for name in ("bug-fix", "code-review", "doc-review", "enhancement", "new-project"):
        rc, out = sh(["flow", name], timeout=30)
        case("flow %s (dry: contract shown)" % name,
             rc == 0 and "deliverable:" in out and "done when:" in out)
    # --run with a real target: doc-review over README (automatable steps + fail-loud verdict)
    rc, out = sh(["flow", "doc-review", "README.md", "--run"], timeout=300)
    verdict = [l for l in out.splitlines() if l.startswith("verdict:")]
    case("flow doc-review --run README.md (fail-loud verdict emitted)", bool(verdict),
         verdict[0] if verdict else "no verdict line; rc=%s" % rc)
    # --run with a missing target must be BLOCKED, never a silent pass
    rc, out = sh(["flow", "code-review", "--run"], timeout=120)
    case("flow --run w/o target -> BLOCKED (no false green)", rc != 0 and "BLOCKED" in out)


def main():
    commands_matrix()
    fix_repros()
    workflows_matrix()
    bad = [r for r in RESULTS if not r[1]]
    print("\ncli_matrix: %d/%d checks pass" % (len(RESULTS) - len(bad), len(RESULTS)))
    if bad:
        print("failing:")
        for n, _, note in bad:
            print("  - %s %s" % (n, note))
    json.dump([{"name": n, "ok": o, "note": str(x)} for n, o, x in RESULTS],
              open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_cli_results.json"), "w"), indent=1)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
