"""docs_drift_gate — the command reference must not fall behind the code. Every command in the CLI's dispatch
table (lathe.py) must appear in LATHE_COMMANDS.md, or this gate fails. So you can't add a command and forget to
document it (with an example). Uses the harness-built pure checker `undocumented_commands`.

SKIPS cleanly if lathe.py / LATHE_COMMANDS.md aren't at the expected root (some project layouts).
  python qa/docs_drift_gate.py
"""
import ast
import os
import sys

QA = os.path.dirname(os.path.abspath(__file__))
INNER = os.path.dirname(QA)                                   # projects/agentic-harness
ROOT = os.path.dirname(os.path.dirname(INNER))               # repo/release root (holds lathe.py + LATHE_COMMANDS.md)
sys.path.insert(0, os.path.join(INNER, "tools"))
try:
    from undocumented_commands import undocumented_commands   # harness-built pure checker
except Exception:
    def undocumented_commands(names, doc_text):
        return []


def _table_commands(src):
    for n in ast.walk(ast.parse(src)):
        if (isinstance(n, ast.Assign) and any(getattr(x, "id", "") == "table" for x in n.targets)
                and isinstance(n.value, ast.Dict)):
            return [k.value for k in n.value.keys if isinstance(k, ast.Constant) and isinstance(k.value, str)]
    return []


def main(argv):
    lathe, doc = os.path.join(ROOT, "lathe.py"), os.path.join(ROOT, "LATHE_COMMANDS.md")
    if not (os.path.exists(lathe) and os.path.exists(doc)):
        print("docs_drift_gate: lathe.py or LATHE_COMMANDS.md not at root — SKIPPED"); return 0
    cmds = _table_commands(open(lathe, encoding="utf-8").read())
    missing = undocumented_commands(cmds, open(doc, encoding="utf-8").read())
    if not missing:
        print("docs_drift_gate: clean — all %d CLI commands documented in LATHE_COMMANDS.md" % len(cmds)); return 0
    print("docs_drift_gate: %d command(s) undocumented (add an example to LATHE_COMMANDS.md): %s"
          % (len(missing), ", ".join(missing)))
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
