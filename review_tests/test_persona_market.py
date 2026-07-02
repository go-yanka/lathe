"""ACCEPTANCE TEST — persona library governance (owner directive): buckets + CE floor + user defaults.

  1. bucket_of: representative agents land in the expected when-to-invoke bucket (pure logic).
  2. every catalog entry carries a bucket (the library is organized).
  3. ensure_ce_floor: a non-CE selection gains a CE reviewer; a selection that already has one is untouched.
  4. WIRED: the planner's _expert_lenses always includes a CE reviewer, even for a non-CE goal.
  5. WIRED: review's default lenses are CE personas (correctness + adversarial) — the review CE floor.
Offline, no model.
Run:  python review_tests/test_persona_market.py     (repo root)
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "projects", "agentic-harness", "tools"))
from persona_market import bucket_of, ensure_ce_floor

fails = []
def check(name, ok, detail=""):
    print("  %-62s %s %s" % (name, "PASS" if ok else "FAIL", detail if not ok else ""))
    if not ok:
        fails.append(name)

check("bucket: reviewer -> review", bucket_of("correctness-reviewer", "logic bugs", "reviewer") == "review")
check("bucket: rust-pro -> language", bucket_of("rust-pro", "systems memory safety", "implementer") == "language")
check("bucket: kubernetes-architect -> devops-cloud", bucket_of("kubernetes-architect", "helm deploy", "analyst") == "devops-cloud")
check("bucket: ml-engineer -> data-ai", bucket_of("ml-engineer", "model training", "analyst") == "data-ai")

cat = json.load(open(os.path.join(ROOT, "projects", "agentic-harness", "agents", "catalog.json"), encoding="utf-8"))
ents = cat["agents"]
check("every catalog entry has a bucket", all(e.get("bucket") for e in ents), "%d missing" % sum(1 for e in ents if not e.get("bucket")))
check("143 agents present", len(ents) == 143, str(len(ents)))

ce = [e["name"] for e in ents if e.get("source", "").startswith("EveryInc")]
check("12 vendored CE personas identified", len(ce) == 12, str(len(ce)))
check("CE floor adds a reviewer to a non-CE pick", ensure_ce_floor(["rust-pro"], ce, "correctness-reviewer")[0] == "correctness-reviewer")
check("CE floor leaves a CE-containing pick untouched",
      ensure_ce_floor(["adversarial-reviewer", "rust-pro"], ce, "correctness-reviewer") == ["adversarial-reviewer", "rust-pro"])

from planner_prompt import _expert_lenses
lens = _expert_lenses("rust systems memory ownership performance concurrency")
check("WIRED: planner floors a CE reviewer for a non-CE goal", "correctness-reviewer" in lens)

# review CE floor: the default lenses are CE personas
import importlib.util
spec = importlib.util.spec_from_file_location("lathe_mod", os.path.join(ROOT, "lathe.py"))
lathe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lathe)
check("WIRED: review default lenses are CE (correctness + adversarial)",
      "correctness" in lathe._DEFAULT_LENSES and "adversarial" in lathe._DEFAULT_LENSES, str(lathe._DEFAULT_LENSES))

print("\npersona-market acceptance: %s" % ("ALL PASS" if not fails else "FAILED: %s" % ", ".join(fails)))
sys.exit(0 if not fails else 1)
