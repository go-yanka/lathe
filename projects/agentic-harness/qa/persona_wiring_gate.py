"""persona_wiring_gate.py — MASTER_PLAN E1/E3 proof: the panel always has a prompt-architect, and the decider
is HONEST about lexical vs semantic.

E1  panel_floor.with_architect() always yields the prompt-architect, FIRST, de-duplicated, without mutating.
E3  semantic_decider.decide() returns (names, how) and NEVER overclaims: lexical mode -> how='lexical';
    semantic with a working (stub) analyst -> how='semantic'; semantic with a DOWN analyst -> a lexical
    fallback whose `how` says so; rank_semantic only returns real candidate names; nothing raises.
"""
for _s in (__import__("sys").stdout, __import__("sys").stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import os
import sys

QA = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(QA), "tools"))
import panel_floor as pf         # noqa: E402
import semantic_decider as sd    # noqa: E402

CANDS = [("payments-expert", "billing, invoices, refunds"),
         ("access-control-expert", "sign-in, sessions, permissions, tokens"),
         ("pixel-artist", "sprites, palettes, animation")]


def main():
    problems = []

    # E1 — architect floor.
    got = pf.with_architect(["access-control-expert", "payments-expert"])
    if got[0] != "prompt-architect" or "access-control-expert" not in got:
        problems.append("with_architect did not put the architect first + keep the panel: %r" % got)
    if pf.with_architect(["prompt-architect", "x"]).count("prompt-architect") != 1:
        problems.append("with_architect duplicated the architect")
    src = ["a", "b"]
    pf.with_architect(src)
    if src != ["a", "b"]:
        problems.append("with_architect mutated its input")
    if pf.with_architect(None)[0] != "prompt-architect":
        problems.append("with_architect not None-safe")

    # E3 — honest lexical vs semantic.
    lex, how = sd.decide("who can sign in and manage sessions", CANDS, 2, mode="lexical")
    if how != "lexical":
        problems.append("lexical mode should report how='lexical', got %r" % how)

    sem, how = sd.decide("users get logged out and can't authenticate", CANDS, 2, mode="semantic",
                         analyst_fn=lambda pr, model=None: '["access-control-expert","payments-expert"]')
    if how != "semantic" or "access-control-expert" not in sem:
        problems.append("semantic mode with a working analyst should report how='semantic': %r" % ((sem, how),))

    # a DOWN analyst must fall back to lexical and SAY so (no silent overclaim).
    fb, how = sd.decide("who can sign in and manage sessions", CANDS, 2, mode="semantic",
                        analyst_fn=lambda pr, model=None: (_ for _ in ()).throw(RuntimeError("down")))
    if not how.startswith("lexical-fallback"):
        problems.append("a down analyst must report a lexical-fallback path, got %r" % how)

    # rank_semantic must only return REAL candidate names (ignore a hallucinated one).
    r = sd.rank_semantic("x", CANDS, 3, analyst_fn=lambda pr, model=None: '["access-control-expert","ghost-expert"]')
    if "ghost-expert" in r or "access-control-expert" not in r:
        problems.append("rank_semantic did not filter to real candidates: %r" % r)

    if problems:
        print("persona-wiring gate: FAIL — " + " ;; ".join(problems))
        sys.exit(1)
    print("persona-wiring gate: PASS — prompt-architect always in the panel; decider is honest about "
          "lexical vs semantic (fallback labeled, hallucinated names filtered)")
    sys.exit(0)


if __name__ == "__main__":
    main()
