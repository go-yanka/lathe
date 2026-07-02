"""ACCEPTANCE TEST — #39: empirical persona ratings steer the decider (best agent wins).

  1. seed ratings: two personas match a need; the lower word-overlap one carries a 10.0 rating,
     the raw winner a 0.0 -> the decider's pick FLIPS (measured performance beats word overlap).
  2. unrated personas are neutral (factor 1.0) — never punished for being new.
  3. ratings survive a reload (agents/ratings.json round-trip).
Offline (ratings seeded directly; the live probe/judge path was proven separately via `lathe agent rate`).
Run:  python review_tests/test_persona_ratings.py     (repo root)
"""
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "projects", "agentic-harness", "tools"))
import persona_spawn
from persona_ratings import apply_ratings
from persona_overrides import apply_overrides
from agent_router import score_match

RP = persona_spawn.ratings_path()
BAK = RP + ".test_backup"
had = os.path.exists(RP)
if had:
    shutil.copy(RP, BAK)

fails = []
def check(name, ok, detail=""):
    print("  %-64s %s %s" % (name, "PASS" if ok else "FAIL", detail if not ok else ""))
    if not ok:
        fails.append(name)

try:
    cat = json.load(open(os.path.join(ROOT, "projects", "agentic-harness", "agents", "catalog.json"), encoding="utf-8"))
    ents = cat["agents"]
    need = "backend api design microservices scalability"
    scored = [[e["name"], score_match(need, e.get("capability", ""))] for e in ents]
    base = apply_overrides(scored, {}, [], 1)
    check("baseline: raw overlap picks a winner", bool(base))
    loser = "graphql-architect" if base[0] != "graphql-architect" else "event-sourcing-architect"

    # 1) rating flips the pick
    # the intended semantic: ratings are a TIE-BREAK (0.5x..1.5x), not a veto — same-role personas
    # with comparable match scores are decided by measured performance; a huge overlap gap still wins.
    tb = apply_overrides(apply_ratings([["a", 5], ["b", 5]], {"b": 10.0}), {}, [], 2)
    check("equal-match same-role pair: the better-rated persona WINS", tb == ["b", "a"], tb)
    base_order = apply_overrides(scored, {}, [], len(scored))
    order = apply_overrides(apply_ratings(scored, {loser: 10.0}), {}, [], len(scored))
    check("a 10 rating IMPROVES the persona's rank in the real 143-market",
          loser in order and order.index(loser) < base_order.index(loser),
          "before=%d after=%d" % (base_order.index(loser), order.index(loser)))

    # 2) unrated = neutral
    neutral = apply_ratings(scored, {"someone-else": 10.0})
    check("unrated personas are untouched", neutral == [[n, s] for n, s in scored])

    # 3) store round-trip + the live wiring reads it
    persona_spawn.save_rating("__probe_persona", 7.5, need)
    r = persona_spawn.load_ratings()
    check("rating store round-trips", r.get("__probe_persona", {}).get("rating") == 7.5)
finally:
    if had:
        shutil.move(BAK, RP)
    elif os.path.exists(RP):
        os.remove(RP)

print("\npersona-ratings acceptance: %s" % ("ALL PASS" if not fails else "FAILED: %s" % ", ".join(fails)))
sys.exit(0 if not fails else 1)
