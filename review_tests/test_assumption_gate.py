"""ACCEPTANCE TEST — the ASSUMPTION GATE: surface + confirm the LLM's silent guesses before the build.

  1. pure fns (parse_assumptions / blocking_assumptions / unconfirmed_blockers / spec_digest).
  2. `lathe assume <plan>` AUDIT mode with a MOCKED auditor (no endpoint): parses a ranked ledger, writes
     .assumptions.json + ASSUMPTIONS.md, computes the HIGH blockers.
  3. `lathe assume <plan> --confirm --yes`: confirming the blockers clears them (build unblocks).
  4. the ENGINE GATE DECISION (same logic the engine runs): a matching-digest ledger with an unconfirmed HIGH
     blocks; once confirmed / spec-changed it does not.
Offline (auditor mocked). Run:  python review_tests/test_assumption_gate.py     (repo root)
"""
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "projects", "agentic-harness", "tools")
sys.path.insert(0, TOOLS)
from assumption_logic import parse_assumptions, blocking_assumptions, unconfirmed_blockers, spec_digest

fails = []
def check(name, ok, detail=""):
    print("  %-58s %s %s" % (name, "PASS" if ok else "FAIL", detail if not ok else ""))
    if not ok:
        fails.append(name)

# 1) pure functions
led = parse_assumptions("[ASSUMPTION | high | data] Input is UTF-8.\n[ASSUMPTION | low | behavior] Order preserved.")
check("parse: 2 assumptions", len(led) == 2 and led[0]["materiality"] == "high" and led[0]["category"] == "data")
check("parse: critical -> high", parse_assumptions("[ASSUMPTION | critical | x] y")[0]["materiality"] == "high")
check("blocking: high-only policy", [b["text"] for b in blocking_assumptions(led, "high")] == ["Input is UTF-8."])
check("unconfirmed: confirming clears the blocker",
      unconfirmed_blockers(led, ["input is utf-8."], "high") == [])
check("scrutiny dial: 'off'/'advisory' blocks nothing (user-governed down)",
      unconfirmed_blockers(led, [], "off") == [] and blocking_assumptions(led, "advisory") == [])
check("scrutiny dial: 'all' blocks every level (user-governed up)",
      len(blocking_assumptions(led, "all")) == 2)
check("spec_digest stable + sensitive",
      spec_digest([{"name": "f", "prompt": "p", "tests": ["t"]}]) ==
      spec_digest([{"name": "f", "prompt": "p", "tests": ["t"]}]) !=
      spec_digest([{"name": "f", "prompt": "q", "tests": ["t"]}]))

# ---- build a throwaway plan + mock the auditor, then drive cmd_assume ----
LEDGER_TEXT = ("Here is my audit:\n"
               "[ASSUMPTION | high | data] Input CSV is UTF-8; other encodings raise.\n"
               "[ASSUMPTION | high | behavior] The first row is treated as a header.\n"
               "[ASSUMPTION | low | behavior] Output preserves input row order.\n")
fake = types.ModuleType("request_spec")
fake.request_spec = lambda p: LEDGER_TEXT
sys.modules["request_spec"] = fake

spec = importlib.util.spec_from_file_location("lathe_mod", os.path.join(ROOT, "lathe.py"))
lathe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lathe)

tmp = tempfile.mkdtemp(prefix="assume_")
plan_path = os.path.join(tmp, "H_demo.py")
open(plan_path, "w", encoding="utf-8").write(
    'OUT_DIR="x"\nMODULE_NAME="demo"\nHEADER=""\nGLUE=""\n'
    'FUNCTIONS=[{"name":"parse","prompt":"parse a csv","tests":["assert parse"]}]\n')

# 2) AUDIT mode
rc = lathe.cmd_assume([plan_path])
check("assume audit exits 0", rc == 0, "rc=%r" % rc)
asm_file = os.path.join(tmp, ".assumptions.json")
check(".assumptions.json written", os.path.exists(asm_file))
check("ASSUMPTIONS.md written", os.path.exists(os.path.join(tmp, "ASSUMPTIONS.md")))
data = json.loads(open(asm_file, encoding="utf-8").read())
entry = data.get("H_demo.py", {})
check("ledger has 3 assumptions", len(entry.get("ledger", [])) == 3)
check("2 HIGH blockers, unconfirmed", len(unconfirmed_blockers(entry["ledger"], entry.get("confirmed"), "high")) == 2)

# 4) ENGINE GATE DECISION — replicate exactly what engine_v2 computes
def gate_blocks(plan_fns, plan_dir, key):
    d = json.loads(open(os.path.join(plan_dir, ".assumptions.json"), encoding="utf-8").read())
    e = d.get(key)
    if not isinstance(e, dict) or e.get("digest") != spec_digest(plan_fns):
        return True                                        # no current audit -> blocked
    return bool(unconfirmed_blockers(e.get("ledger"), e.get("confirmed"), e.get("policy", "high")))

FNS = [{"name": "parse", "prompt": "parse a csv", "tests": ["assert parse"]}]
check("gate BLOCKS with unconfirmed HIGH", gate_blocks(FNS, tmp, "H_demo.py") is True)

# 3) CONFIRM mode (--yes auto-confirms the blockers)
rc = lathe.cmd_assume([plan_path, "--confirm", "--yes"])
check("assume --confirm --yes exits 0", rc == 0, "rc=%r" % rc)
check("gate now UNBLOCKED after confirm", gate_blocks(FNS, tmp, "H_demo.py") is False)

# a spec change must RE-OPEN the audit (stale confirmations don't carry)
CHANGED = [{"name": "parse", "prompt": "parse a JSON file instead", "tests": ["assert parse"]}]
check("gate re-BLOCKS after spec change (digest mismatch)", gate_blocks(CHANGED, tmp, "H_demo.py") is True)

del sys.modules["request_spec"]
shutil.rmtree(tmp, ignore_errors=True)
print("\nassumption-gate acceptance: %s" % ("ALL PASS" if not fails else "FAILED: %s" % ", ".join(fails)))
sys.exit(0 if not fails else 1)
