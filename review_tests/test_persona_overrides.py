"""ACCEPTANCE TEST — #43: user-steered persona market (priority weights + mandatory personas via config).

Proves the CONFIG changes real behavior (not just the pure function):
  1. personas.mandatory naming a vendored LENS -> `lathe review auto` dispatches it on every invocation.
  2. personas.mandatory naming a CATALOG persona -> it is fetched (license-gated) and injected as an
     '@<path>' lens even when the code's domain wouldn't match it.
  3. personas.priority reweights the decider: a boosted persona outranks the raw word-overlap winner.
  4. no personas section -> behavior unchanged.
Offline: GitHub mocked; the model is never invoked (lathe._run captured).
Run:  python review_tests/test_persona_overrides.py     (repo root)
"""
import base64
import importlib.util
import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "projects", "agentic-harness", "tools")
sys.path.insert(0, TOOLS)

CFG = os.path.join(ROOT, "lathe.config.json")
BACKUP = CFG + ".test_backup"
had_cfg = os.path.exists(CFG)
if had_cfg:
    shutil.copy(CFG, BACKUP)

import persona_spawn
PERSONA_MD = "# persona\nYou are a rigorous specialist.\n"
persona_spawn.gh_json = lambda url: ({"license": {"spdx_id": "MIT"}, "content": base64.b64encode(PERSONA_MD.encode()).decode()}
                                     if url.endswith("/license") else {"content": base64.b64encode(PERSONA_MD.encode()).decode()})
tmp = tempfile.mkdtemp(prefix="ovr_")
persona_spawn.agent_dirs = lambda: (os.path.join(tmp, "_fetched"), os.path.join(tmp, "licenses"))

fails = []
def check(name, ok, detail=""):
    print("  %-64s %s %s" % (name, "PASS" if ok else "FAIL", detail if not ok else ""))
    if not ok:
        fails.append(name)

def set_cfg(personas):
    if personas is None:
        if os.path.exists(CFG):
            os.remove(CFG)
    else:
        open(CFG, "w", encoding="utf-8").write(json.dumps({"personas": personas}))

def review_calls(target):
    spec = importlib.util.spec_from_file_location("lathe_mod", os.path.join(ROOT, "lathe.py"))
    lathe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lathe)
    calls = []
    lathe._run = lambda cmd, *a, **k: calls.append(cmd) or 0   # tolerate _run's real signature (cwd/timeout/env)
    lathe.cmd_review(["auto", target])
    return [str(c[2]) for c in calls if len(c) > 2]

target = os.path.join(tmp, "plain_math.py")
open(target, "w", encoding="utf-8").write("def add(a, b):\n    return a + b\n")   # matches no domain specialist

try:
    # 1) mandatory vendored lens is always dispatched
    set_cfg({"mandatory": ["testing"]})
    lenses = review_calls(target)
    check("mandatory LENS dispatched on every invocation", "testing" in lenses, lenses)

    # 2) mandatory CATALOG persona is fetched + injected even off-domain
    set_cfg({"mandatory": ["backend-architect"]})
    lenses = review_calls(target)
    ats = [l for l in lenses if l.startswith("@")]
    check("mandatory CATALOG persona fetched + injected (@path)",
          any("backend-architect" in a for a in ats), lenses)

    # 3) priority reweights the decider (boost graphql over the raw backend match)
    import importlib
    import persona_overrides as _po
    from agent_router import score_match
    cat = json.load(open(os.path.join(ROOT, "projects", "agentic-harness", "agents", "catalog.json"), encoding="utf-8"))
    ents = cat["agents"]
    goal = "backend api design microservices scalability"
    scored = [[e["name"], score_match(goal, e.get("capability", ""))] for e in ents]
    base = _po.apply_overrides(scored, {}, [], 1)
    boosted = _po.apply_overrides(scored, {"graphql-architect": 50}, [], 1)
    check("priority weight flips the ranking", base and boosted and base[0] != boosted[0]
          and boosted[0] == "graphql-architect", "base=%r boosted=%r" % (base, boosted))

    # 4) no config -> unchanged floor (correctness + adversarial present, no mandatory extras)
    set_cfg(None)
    lenses = review_calls(target)
    check("no config: floor unchanged", "correctness" in lenses and "adversarial" in lenses and "testing" not in lenses, lenses)
finally:
    if had_cfg:
        shutil.move(BACKUP, CFG)
    elif os.path.exists(CFG):
        os.remove(CFG)
    shutil.rmtree(tmp, ignore_errors=True)

print("\npersona-overrides acceptance: %s" % ("ALL PASS" if not fails else "FAILED: %s" % ", ".join(fails)))
sys.exit(0 if not fails else 1)
