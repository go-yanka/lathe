"""ACCEPTANCE TEST — the requirements LIAISON: interrogate for clarity before the harness thinks.

  1. goal_vagueness (pure): a vague goal needs clarify; a clear input+output goal does not.
  2. parse_questions (pure): pulls numbered/bulleted/'?'-ending questions, strips enumerators.
  3. `lathe clarify` e2e with a MOCKED liaison (no endpoint): asks the mocked questions, consumes a scripted
     --answers file, writes CLARIFIED_GOAL.md containing the refined brief. The goal text must NOT contain
     the --answers/--out paths (arg-parse fix).
  4. 'NO QUESTIONS' path: a clear goal -> the liaison asks nothing but still emits a brief.
Offline (liaison mocked). Run:  python review_tests/test_clarify.py     (repo root)
"""
import importlib.util
import os
import shutil
import sys
import tempfile
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "projects", "agentic-harness", "tools"))
from clarify_logic import goal_vagueness, parse_questions, parse_options

fails = []
def check(name, ok, detail=""):
    print("  %-58s %s %s" % (name, "PASS" if ok else "FAIL", detail if not ok else ""))
    if not ok:
        fails.append(name)

# 1) vagueness
check("vague goal needs clarify", goal_vagueness("build a tool for data")[0] is True)
check("input+output goal is clear enough",
      goal_vagueness("a function that takes a string input and returns the vowel count")[0] is False)
# 2) question parsing
check("parse numbered questions", parse_questions("1. What input?\n2. What output?") == ["What input?", "What output?"])
check("parse ignores prose", parse_questions("Some prose.\n- An edge case?") == ["An edge case?"])
# 2b) options-in-a-question parsing
check("parse_options splits options + default",
      parse_options("Which format? [options: CSV | JSON] (default: CSV)") == ["Which format?", ["CSV", "JSON"], "CSV"])
check("parse_options open-ended question has no options",
      parse_options("What should it be named?") == ["What should it be named?", [], ""])

# 3) e2e with a mocked liaison
Q = "1. What are the inputs?\n2. What is the output format?\n3. Any size limits?"
BRIEF = ("Refined goal: a CLI that merges CSVs.\n- Assumptions: ...\n- Acceptance criteria: merges two CSVs "
         "into one deduped file.\n- Non-goals: no cloud.")
seq = [Q, BRIEF]
fake = types.ModuleType("request_spec")
fake.request_spec = lambda p: seq.pop(0) if seq else ""
sys.modules["request_spec"] = fake

spec = importlib.util.spec_from_file_location("lathe_mod", os.path.join(ROOT, "lathe.py"))
lathe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lathe)

tmp = tempfile.mkdtemp(prefix="clar_")
ans = os.path.join(tmp, "ans.txt")
# #48: the PROJECT FRAMING round asks the un-prefilled framing dimensions FIRST; a vague goal prefills none,
# so scripted answers begin with one line per framing dimension (blank = skip) before the functional answers.
from framing import FRAMING as _FR
_fr_skip = "\n" * len(_FR)
open(ans, "w", encoding="utf-8").write(_fr_skip + "two CSV files\none merged CSV\nno limit\n")
rc = lathe.cmd_clarify(["combine some data files", "--answers", ans, "--out", tmp])
check("clarify exits 0", rc == 0, "rc=%r" % rc)
brief_path = os.path.join(tmp, "CLARIFIED_GOAL.md")
check("CLARIFIED_GOAL.md written", os.path.exists(brief_path))
if os.path.exists(brief_path):
    txt = open(brief_path, encoding="utf-8").read()
    check("brief contains the refined goal", "Refined goal" in txt and "merges CSVs" in txt)
    check("goal text is clean (no --answers/--out paths leaked)", ".txt" not in txt.split("Refined goal")[0].split("Original:")[1])

# 3b) options-to-select path: the liaison offers options; a numeric answer PICKS, an empty answer takes the DEFAULT
capd = []
Q2 = ("1. Which input format? [options: CSV | JSON | TSV] (default: CSV)\n"
      "2. Overwrite existing output? [options: yes | no] (default: no)")
def _mock2(p):
    if not capd:                       # first call -> the questions
        capd.append(("q", p)); return Q2
    capd.append(("brief", p))          # second call -> synthesize the brief (prompt carries the resolved Q&A)
    return "Refined goal: a CSV importer.\n- Acceptance criteria: imports a CSV file."
fake.request_spec = _mock2
tmp3 = tempfile.mkdtemp(prefix="clar3_")
ans3 = os.path.join(tmp3, "ans.txt")
open(ans3, "w", encoding="utf-8").write(_fr_skip + "2\n\n")   # framing skipped; then Q1 -> pick option 2 (JSON); Q2 -> Enter => default (no)
rc = lathe.cmd_clarify(["import records from a feed", "--answers", ans3, "--out", tmp3])
check("options path exits 0", rc == 0, "rc=%r" % rc)
brief_prompt = next((p for k, p in capd if k == "brief"), "")
check("numeric pick resolved to the option text (JSON)", "A: JSON" in brief_prompt)
check("empty answer resolved to the default (no)", "A: no" in brief_prompt)
check("raw selection index is NOT recorded as the answer", "A: 2" not in brief_prompt)
shutil.rmtree(tmp3, ignore_errors=True)

# 4) NO QUESTIONS path
seq2 = ["NO QUESTIONS", "Refined goal: identity. Acceptance: returns input unchanged."]
fake.request_spec = lambda p: seq2.pop(0) if seq2 else ""
tmp2 = tempfile.mkdtemp(prefix="clar2_")
rc = lathe.cmd_clarify(["a function that takes x input and returns x output", "--out", tmp2])
check("NO QUESTIONS path still emits a brief", rc == 0 and os.path.exists(os.path.join(tmp2, "CLARIFIED_GOAL.md")))

del sys.modules["request_spec"]
shutil.rmtree(tmp, ignore_errors=True); shutil.rmtree(tmp2, ignore_errors=True)
print("\nclarify acceptance: %s" % ("ALL PASS" if not fails else "FAILED: %s" % ", ".join(fails)))
sys.exit(0 if not fails else 1)
