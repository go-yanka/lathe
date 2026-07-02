"""B4 end-to-end regression: `lathe auto`'s commit path must NOT move HEAD unless LATHE_AUTO_COMMIT=1, and must
NEVER stage harness.db. This is a CLAIM-LEVEL test (the lesson of the B4 phantom): the guard is 'fixed' only when
an executable repro proves the integration, not when the helper unit-passes. Run: python tools/test_b4_autocommit.py"""
import os
import sys
import shutil
import tempfile
import subprocess

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
import autonomy_live as A


def git(repo, *a):
    return subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True)


def main():
    repo = tempfile.mkdtemp(prefix="b4_e2e_")
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "t@t"); git(repo, "config", "user.name", "t")
    os.makedirs(os.path.join(repo, "tools"))
    open(os.path.join(repo, "tools", "x.py"), "w").write("# baseline\n")
    git(repo, "add", "-A"); git(repo, "commit", "-q", "-m", "baseline")
    head0 = git(repo, "rev-parse", "HEAD").stdout.strip()

    A._INNER = repo                                        # redirect the autonomy commit path at the scratch repo
    commit = A.make_real_deps({"max_repairs": 0}, os.path.join(repo, "board.db"))["commit"]
    fails = []

    # A) default (unset) -> HEAD must NOT move
    os.environ.pop("LATHE_AUTO_COMMIT", None)
    open(os.path.join(repo, "tools", "x.py"), "w").write("# changed A\n")
    commit("autonomy: task")
    a_ok = git(repo, "rev-parse", "HEAD").stdout.strip() == head0
    print(("  PASS  " if a_ok else "  FAIL  ") + "auto-commit OFF (unset) -> HEAD unchanged")
    a_ok or fails.append("off")

    # B) LATHE_AUTO_COMMIT=1 -> HEAD MUST move
    os.environ["LATHE_AUTO_COMMIT"] = "1"
    open(os.path.join(repo, "tools", "x.py"), "w").write("# changed B\n")
    commit("autonomy: task")
    b_ok = git(repo, "rev-parse", "HEAD").stdout.strip() != head0
    print(("  PASS  " if b_ok else "  FAIL  ") + "LATHE_AUTO_COMMIT=1 -> HEAD moved (opt-in works)")
    b_ok or fails.append("on")

    # C) harness.db must NEVER be staged, even with opt-in on
    open(os.path.join(repo, "harness.db"), "w").write("BINARYDB")
    open(os.path.join(repo, "tools", "y.py"), "w").write("# more\n")
    commit("autonomy: task2")
    c_ok = "harness.db" not in git(repo, "ls-files").stdout
    print(("  PASS  " if c_ok else "  FAIL  ") + "harness.db NOT staged (binary runtime state stays out)")
    c_ok or fails.append("db")

    os.environ.pop("LATHE_AUTO_COMMIT", None)
    shutil.rmtree(repo, ignore_errors=True)
    print("\nB4 e2e: " + ("ALL PASS" if not fails else "FAILED (%s)" % ",".join(fails)))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
