"""env_drift_gate — the env-var registry (env_catalog.py) must not fall behind the code (PR#1 CLI-review #1).

Extracts every env var the core code actually reads (env_logic.extract_env_vars over lathe.py, engine_v2.py,
and tools/*.py) and FAILS if any user-facing one is missing from env_catalog.REGISTRY — so a new env var can't
drift in undocumented. Internal/OS vars are ignored (env_catalog.IGNORE + a base OS set). "Unused" (documented
but not found) is advisory only.

SKIPS cleanly if the expected files aren't at the repo root (some project layouts).
  python qa/env_drift_gate.py
"""
import glob
import os
import sys

QA = os.path.dirname(os.path.abspath(__file__))
INNER = os.path.dirname(QA)                                   # projects/agentic-harness
ROOT = os.path.dirname(os.path.dirname(INNER))               # repo/release root (holds lathe.py, engine_v2.py, env_catalog.py)
sys.path.insert(0, os.path.join(INNER, "tools"))

# OS / interpreter vars the code may read but that are NOT Lathe's to document.
_OS_IGNORE = {"PATH", "HOME", "USERPROFILE", "TEMP", "TMP", "TMPDIR", "PYTHONPATH", "PYTHONIOENCODING",
              "PYTHONUTF8", "SYSTEMROOT", "COMSPEC", "SSH_AUTH_SOCK", "GH_TOKEN", "GITHUB_TOKEN",
              "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "VIRTUAL_ENV", "CI"}


def main(argv):
    try:
        from env_logic import extract_env_vars, env_drift
        import importlib.util
        spec = importlib.util.spec_from_file_location("env_catalog", os.path.join(ROOT, "env_catalog.py"))
        ec = importlib.util.module_from_spec(spec); spec.loader.exec_module(ec)
    except Exception as e:
        print("env_drift_gate: dependencies unavailable (%s) — SKIPPED" % e); return 0

    files = [os.path.join(ROOT, "lathe.py"), os.path.join(ROOT, "engine_v2.py")]
    files += sorted(glob.glob(os.path.join(INNER, "tools", "*.py")))
    files = [f for f in files if os.path.exists(f)]
    if not files:
        print("env_drift_gate: core files not at root — SKIPPED"); return 0

    code_vars = set()
    for f in files:
        try:
            code_vars |= set(extract_env_vars(open(f, encoding="utf-8").read()))
        except Exception:
            continue
    ignore = set(ec.IGNORE) | _OS_IGNORE
    drift = env_drift(sorted(code_vars), sorted(ec.registry_names()), sorted(ignore))
    undocumented = drift.get("undocumented", [])
    unused = drift.get("unused", [])
    if unused:
        print("env_drift_gate: advisory — %d documented var(s) not found in code (harmless): %s"
              % (len(unused), ", ".join(unused)))
    if not undocumented:
        print("env_drift_gate: clean — all %d code-referenced env vars are documented in env_catalog.py "
              "(lathe env)" % len(code_vars - ignore))
        return 0
    print("env_drift_gate: %d env var(s) read by the code but MISSING from env_catalog.py (add them, or add to "
          "IGNORE if internal): %s" % (len(undocumented), ", ".join(undocumented)))
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
