"""project_layout_gate.py — MASTER_PLAN F4 proof: multi-file projects get a correct code/docs/scripts/config
layout, and a lone artifact does NOT.

Proves: classify() buckets files by role; is_multifile_project() triggers ONLY on 2+ code files (a single
artifact + its docs is not a project); organize(apply=False) plans moves + writes a PROJECT.md map without
touching files; organize(apply=True) actually relocates them into bucket subdirs; nothing raises.
"""
for _s in (__import__("sys").stdout, __import__("sys").stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import os
import sys
import tempfile

QA = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(QA), "tools"))
import project_layout as pl   # noqa: E402


def main():
    problems = []

    # classify
    cases = {"app.py": "code", "index.html": "code", "README.md": "docs", "GOAL.md": "docs",
             "build.sh": "scripts", "deploy.ps1": "scripts", "config.json": "config",
             "Dockerfile": "config", "settings.yaml": "config", "notes.txt": "docs"}
    for f, want in cases.items():
        got = pl.classify(f)
        if got != want:
            problems.append("classify(%s)=%s, want %s" % (f, got, want))

    # is_multifile_project: a lone artifact + docs is NOT a project; 2+ code files IS.
    if pl.is_multifile_project(["game.html", "GOAL.md", "README.md"]):
        problems.append("single artifact + docs wrongly flagged as a multi-file project")
    if not pl.is_multifile_project(["app.py", "utils.py", "index.html", "config.json"]):
        problems.append("a genuine multi-code-file project was not detected")

    # organize apply=False: plans moves + writes PROJECT.md, does NOT move files.
    with tempfile.TemporaryDirectory() as d:
        files = []
        for n in ("app.py", "utils.py", "README.md", "build.sh", "config.json"):
            p = os.path.join(d, n); open(p, "w").write("x"); files.append(p)
        res = pl.organize(d, files, apply=False)
        if not res["project_md"] or not os.path.exists(res["project_md"]):
            problems.append("PROJECT.md not written on plan")
        else:
            pm = open(res["project_md"], encoding="utf-8").read()
            for want in ("code/", "docs/", "scripts/", "config/", "app.py", "build.sh"):
                if want not in pm:
                    problems.append("PROJECT.md missing %r" % want)
        if any(not os.path.exists(f) for f in files):
            problems.append("apply=False moved files (must not)")

    # organize apply=True: files land in bucket subdirs.
    with tempfile.TemporaryDirectory() as d:
        files = []
        for n in ("app.py", "utils.py", "README.md", "config.json"):
            p = os.path.join(d, n); open(p, "w").write("x"); files.append(p)
        pl.organize(d, files, apply=True)
        if not os.path.exists(os.path.join(d, "code", "app.py")):
            problems.append("apply=True did not move code into code/")
        if not os.path.exists(os.path.join(d, "docs", "README.md")):
            problems.append("apply=True did not move docs into docs/")
        if not os.path.exists(os.path.join(d, "config", "config.json")):
            problems.append("apply=True did not move config into config/")

    if problems:
        print("project-layout gate: FAIL — " + " ;; ".join(problems))
        sys.exit(1)
    print("project-layout gate: PASS — files bucket into code/docs/scripts/config; only genuine multi-code "
          "projects trigger; plan writes PROJECT.md without moving; apply relocates correctly")
    sys.exit(0)


if __name__ == "__main__":
    main()
