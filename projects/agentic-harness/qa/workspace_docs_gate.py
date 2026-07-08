"""workspace_docs_gate.py — MASTER_PLAN F1 proof: a goal workspace gets a GOAL.md + README.md that carry the
intent.

Writes the docs into a TEMP workspace and asserts: GOAL.md contains the goal text + each resolved assumption +
the panel; README.md names the workspace and the key files; both are created; a read-only dir is handled
without raising (best-effort docs must never break a build).
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
import workspace_docs as wd   # noqa: E402


def main():
    problems = []
    goal = "A helicopter game where you hold Space to fly up"
    assumptions = [{"text": "hold Space = thrust up", "materiality": "high", "category": "controls"},
                   {"text": "dark background", "materiality": "low", "category": "visual"}]
    panel = ["prompt-architect", "game-designer"]

    with tempfile.TemporaryDirectory() as d:
        ws = os.path.join(d, "heli-game_local_0708")
        os.makedirs(ws)
        written = wd.write_workspace_docs(ws, goal, assumptions, panel, focus="webapp")
        if len(written) != 2:
            problems.append("expected 2 docs written, got %r" % written)
        gp = os.path.join(ws, "GOAL.md")
        rp = os.path.join(ws, "README.md")
        if not os.path.exists(gp) or not os.path.exists(rp):
            problems.append("GOAL.md/README.md not both present")
        else:
            g = open(gp, encoding="utf-8").read()
            if goal not in g:
                problems.append("GOAL.md missing the goal text")
            if "hold Space = thrust up" not in g or "dark background" not in g:
                problems.append("GOAL.md missing a resolved assumption")
            if "game-designer" not in g:
                problems.append("GOAL.md missing the panel")
            r = open(rp, encoding="utf-8").read()
            if "heli-game_local_0708" not in r or "GOAL.md" not in r:
                problems.append("README.md missing workspace name or file guide")

    # empty-assumptions path still writes a valid GOAL.md
    with tempfile.TemporaryDirectory() as d:
        w = wd.write_workspace_docs(d, "a tiny helper", None, None, None)
        if len(w) != 2 or "none surfaced" not in open(os.path.join(d, "GOAL.md"), encoding="utf-8").read():
            problems.append("empty-assumptions GOAL.md not handled")

    # never raises on a bogus dir (best-effort)
    try:
        wd.write_workspace_docs(os.path.join(tempfile.gettempdir(), "no_such_dir_xyz_123"), "g")
    except Exception as e:
        problems.append("write_workspace_docs raised on a missing dir: %s" % e)

    if problems:
        print("workspace-docs gate: FAIL — " + " ;; ".join(problems))
        sys.exit(1)
    print("workspace-docs gate: PASS — GOAL.md (intent + assumptions + panel) + README.md (layout) written; "
          "empty-assumptions handled; bogus dir never raises")
    sys.exit(0)


if __name__ == "__main__":
    main()
