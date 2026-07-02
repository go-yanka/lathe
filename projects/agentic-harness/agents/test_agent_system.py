"""Comprehensive test of the on-demand agent system: router logic, catalog, CLI match/spawn/refill,
the compliance gate, and offline fallback. Run from the repo root:  python projects/agentic-harness/agents/test_agent_system.py"""
import os, sys, json, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
INNER = os.path.dirname(HERE)                       # projects/agentic-harness
ROOT = os.path.dirname(os.path.dirname(INNER))      # repo root
TOOLS = os.path.join(INNER, "tools")
sys.path.insert(0, TOOLS); sys.path.insert(0, ROOT)

fails = []
def check(cond, msg):
    print(("  PASS  " if cond else "  FAIL  ") + msg)
    if not cond:
        fails.append(msg)

# --- 1. decider logic (agent_router) ---
from agent_router import score_match, license_ok, pick_best
check(score_match("api design", "scalable api design patterns") == 2, "score_match: word overlap")
check(score_match(None, "x") == 0, "score_match: None-safe")
check(all(license_ok(x) for x in ["MIT", "Apache-2.0", "apache 2.0", "BSD-3-Clause", "ISC"]), "license_ok: permissive allowed")
check(not any(license_ok(x) for x in ["GPL-3.0", "AGPL-3.0", "NOASSERTION", "", None]), "license_ok: non-permissive blocked")
check(pick_best("backend api", [["a", "backend api design"], ["b", "css styling"]]) == "a", "pick_best: best match")
check(pick_best("zzz", [["a", "api"]]) == "" and pick_best("x", []) == "", "pick_best: no-match -> ''")

# --- 1b. decider-in-thinking: goal -> expert lenses, and the planner injects them ---
from agent_router import select_agents_for_goal
check(select_agents_for_goal("backend api", [["backend-architect", "backend api design"], ["css", "frontend css"]], 3) == ["backend-architect"],
      "select_agents_for_goal: goal -> relevant experts")
from planner_prompt import build_planner_prompt
_pp = build_planner_prompt("build a backend api with security auth", [], None)
check("EXPERT LENSES" in _pp and "backend-architect" in _pp, "planner: a goal auto-injects expert lenses into the thinking prompt")

# --- 2. catalog ---
cat = json.load(open(os.path.join(INNER, "agents", "catalog.json"), encoding="utf-8"))
ents = cat.get("agents", [])
check(isinstance(ents, list) and len(ents) > 0, "catalog: loads with agents")
check(all("license" in e and "capability" in e for e in ents), "catalog: every entry has license + capability")

# --- 3. CLI: match / compliance / vendored ---
def cli(*a):
    r = subprocess.run([sys.executable, "lathe.py", "agent", *a], cwd=ROOT, capture_output=True, text=True, timeout=60)
    return r.stdout + r.stderr
check("backend-architect" in cli("backend api design microservices") and "MIT" in cli("backend api design microservices"),
      "CLI: matches a fetchable MIT agent")
check("NOT auto-fetchable" in cli("requirements analysis user stories", "--spawn"),
      "CLI: compliance gate REFUSES unlicensed (NOASSERTION) source")
check("VENDORED" in cli("logic errors correctness edge cases"), "CLI: matches a vendored persona")

# --- 4. offline fallback (source unreachable) ---
import lathe as L
cache, _ = L._agent_dirs()
os.makedirs(cache, exist_ok=True)
open(os.path.join(cache, "__probe.md"), "w", encoding="utf-8").write("cached persona body")
md, how = L._spawn_one({"name": "__probe", "repo": "nonexistent/repo-xyz-000", "path": "x.md", "license": "MIT"})
check(md is not None and "cache" in how.lower(), "fallback: unreachable source -> uses local cached copy")
os.remove(os.path.join(cache, "__probe.md"))
md2, _ = L._spawn_one({"name": "__none", "repo": "nonexistent/repo-xyz-000", "path": "x.md", "license": "MIT"})
check(md2 is None, "fallback: unreachable + no cache -> refuses (no fabrication)")

print("\nRESULT: " + ("ALL PASS" if not fails else "%d FAILED" % len(fails)))
sys.exit(1 if fails else 0)
