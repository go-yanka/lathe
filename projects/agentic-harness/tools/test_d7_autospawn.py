"""D7 standing regression test — the decider AUTO-fetches a needed-but-absent expert and injects its BODY.

Covers the claim end-to-end at the wiring level, with ONLY the GitHub network call mocked (offline-safe)
and the model never invoked (lathe._run is captured, not executed):
  1. persona_spawn.auto_spawn_for_goal: a goal whose domain has NO vendored persona -> license-gated fetch
     -> (name, md_path, BODY) with the body actually on disk.
  2. `lathe review auto` wiring: the review dispatches an extra '@<md>' lens pointing at the fetched body.
  3. planner: _expert_lenses(goal) injects the FETCHED EXPERT PERSONA body, not just a name hint.
  4. fail-closed: an unlicensed (NOASSERTION) match is NEVER fetched; hreview rejects an unreadable @path.
Run:  python projects/agentic-harness/tools/test_d7_autospawn.py     (from the repo root)
"""
import base64
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
INNER = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(INNER))
sys.path.insert(0, HERE)

PERSONA_MD = "# backend-architect\nYou are a rigorous backend architecture specialist. Hunt design flaws.\n"
LICENSE_TXT = "MIT License\n\nCopyright (c) 2025 wshobson\n"
GOAL_NONVENDORED = "backend api microservices scalability distributed systems architecture"
GOAL_VENDORED_ONLY = "security auth vulnerabilities exploit input validation permissions review"

import persona_spawn

def fake_gh_json(url):
    if url.endswith("/license"):
        return {"license": {"spdx_id": "MIT"}, "content": base64.b64encode(LICENSE_TXT.encode()).decode()}
    if "/contents/" in url:
        return {"content": base64.b64encode(PERSONA_MD.encode()).decode()}
    raise RuntimeError("unexpected url: " + url)

tmp = tempfile.mkdtemp(prefix="d7_")
persona_spawn.gh_json = fake_gh_json
persona_spawn.agent_dirs = lambda: (os.path.join(tmp, "_fetched"), os.path.join(tmp, "licenses"))

fails = []
def check(name, ok, detail=""):
    print("  %-46s %s %s" % (name, "PASS" if ok else "FAIL", detail if not ok else ""))
    if not ok:
        fails.append(name)

# 1) the decider's auto-fetch: non-vendored domain -> body pulled + license mirrored
got = persona_spawn.auto_spawn_for_goal(GOAL_NONVENDORED, 2)
check("auto_spawn returns a fetched persona", bool(got))
if got:
    name, md, body = got[0]
    check("fetched body is the real persona text", "backend architecture specialist" in body)
    check("fetched .md exists on disk", os.path.exists(md))
    check("source LICENSE mirrored (compliance)", os.path.exists(os.path.join(tmp, "licenses", "wshobson__agents.LICENSE.txt")))

# 2) fail-closed: a vendored-covered domain triggers NO fetch (vendored lenses already carry it)
got2 = persona_spawn.auto_spawn_for_goal(GOAL_VENDORED_ONLY, 2)
check("vendored-covered domain -> no fetch", all(n != "spec-analyst" for n, _, _ in got2))

# 3) fail-closed: unlicensed catalog entries are never spawn candidates
from agent_router import spawn_candidates
check("NOASSERTION is never a spawn candidate",
      spawn_candidates(["spec-analyst"], [["spec-analyst", False, "NOASSERTION"]]) == [])

# 4) `lathe review auto` WIRING: an '@<md>' lens is dispatched (model call captured, not run)
spec = importlib.util.spec_from_file_location("lathe_mod", os.path.join(ROOT, "lathe.py"))
lathe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lathe)
calls = []
lathe._run = lambda cmd, *a, **k: calls.append(cmd) or 0   # tolerate _run's real signature (cwd/timeout/env)
target = os.path.join(tmp, "backend_service.py")
open(target, "w", encoding="utf-8").write(
    "# backend api microservices scalability distributed systems architecture rest grpc\n"
    "def route(request): return {'ok': True}\n")
rc = lathe.cmd_review(["auto", target])
at_lenses = [c[2] for c in calls if len(c) > 2 and str(c[2]).startswith("@")]
check("review auto dispatches an @<md> lens", bool(at_lenses), "calls=%r" % [c[2] for c in calls if len(c) > 2])
if at_lenses:
    check("the @ lens points at a real fetched body",
          os.path.exists(at_lenses[0][1:]) and "specialist" in open(at_lenses[0][1:], encoding="utf-8").read())

# 5) planner injects the fetched BODY (not just the name)
import planner_prompt
planner_prompt.persona_spawn = persona_spawn      # not imported at module level; ensure our mocked copy is used
lens_text = planner_prompt._expert_lenses(GOAL_NONVENDORED)
check("planner injects FETCHED EXPERT PERSONA body",
      "FETCHED EXPERT PERSONA" in lens_text and "backend architecture specialist" in lens_text)

# 6) hreview rejects an unreadable @path (fail loud, rc=2)
r = subprocess.run([sys.executable, os.path.join(INNER, "hreview.py"), "@" + os.path.join(tmp, "nope.md"), target],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
check("hreview fails loud on unreadable @path", r.returncode == 2 and "unreadable" in (r.stdout + r.stderr))

shutil.rmtree(tmp, ignore_errors=True)
print("\nD7 e2e: %s" % ("ALL PASS" if not fails else "FAILED: %s" % ", ".join(fails)))
sys.exit(0 if not fails else 1)
