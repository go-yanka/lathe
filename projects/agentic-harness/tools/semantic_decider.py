"""semantic_decider.py — MASTER_PLAN E3: a REAL semantic persona matcher (LLM-ranked), honestly named.

The base decider (agent_router.select_agents_for_goal) is synonym-expanded WORD-OVERLAP — fast and free, but
NOT semantic understanding (task #42 called it "semantic", which overclaimed lexical matching). This module
adds the genuine article: it asks the analyst to READ the goal and the candidate capabilities and RANK the
best-fitting personas — real semantic reasoning, not token intersection. It is honest about which path ran:

  mode "lexical"  — agent_router word-overlap only (default; zero model cost).
  mode "semantic" — the analyst ranks; falls back to lexical if the analyst is unreachable or unparseable.
  mode "auto"     — lexical first; if lexical returns FEWER than k matches (the word-overlap blind spot), the
                    analyst fills the rest semantically. Best of both.

`decide()` always returns (names, how) where `how` states the path actually used — no silent overclaim. Reuses
the SSRF-guarded analyst client. Never raises.
"""

import json
import os
import re


def _default_analyst():
    def _f(prompt, model=None):
        import request_spec
        return request_spec.request_spec(prompt, model=model or os.environ.get("LATHE_DECIDER_MODEL", "sonnet"),
                                         timeout=int(os.environ.get("LATHE_DECIDER_TIMEOUT", "60")))
    return _f


def _lexical(goal, candidates, k):
    try:
        from agent_router import select_agents_for_goal
        return select_agents_for_goal(goal, [[c[0], c[1]] for c in candidates], k) or []
    except Exception:
        return []


_RANK_PROMPT = (
    "Pick the {k} personas whose expertise BEST fits this goal. Judge by MEANING, not shared words.\n\n"
    "GOAL: {goal}\n\nCANDIDATES (name :: what they are good at):\n{cands}\n\n"
    "Reply with ONLY a JSON array of the chosen names, best first, at most {k}: [\"name\", ...]. "
    "Choose only from the candidate names above."
)


def rank_semantic(goal, candidates, k, analyst_fn=None):
    """Ask the analyst to semantically rank candidates. Returns a list of names (<=k), or [] on outage/parse
    failure (caller falls back to lexical). `candidates` = [(name, capability), ...]. Never raises."""
    if not goal or not candidates or not k:
        return []
    analyst_fn = analyst_fn or _default_analyst()
    valid = {c[0] for c in candidates}
    cands = "\n".join("- %s :: %s" % (c[0], (c[1] or "")[:160]) for c in candidates[:60])
    try:
        reply = analyst_fn(_RANK_PROMPT.format(k=k, goal=goal, cands=cands))
    except Exception:
        return []
    m = re.search(r"\[.*\]", reply or "", re.DOTALL)
    if not m:
        return []
    try:
        names = json.loads(m.group())
    except Exception:
        return []
    out = []
    for n in names:
        if isinstance(n, str) and n in valid and n not in out:
            out.append(n)
    return out[:k]


def decide(goal, candidates, k, mode=None, analyst_fn=None):
    """Return (names, how). `mode` in {lexical, semantic, auto}; default from LATHE_DECIDER_MODE or 'lexical'.
    `how` names the path actually used, so callers never overclaim 'semantic' when lexical ran. Never raises."""
    mode = (mode or os.environ.get("LATHE_DECIDER_MODE", "lexical")).strip().lower()
    if mode == "semantic":
        sem = rank_semantic(goal, candidates, k, analyst_fn=analyst_fn)
        if sem:
            return sem, "semantic"
        return _lexical(goal, candidates, k), "lexical-fallback(analyst-unavailable)"
    if mode == "auto":
        lex = _lexical(goal, candidates, k)
        if len(lex) >= k:
            return lex[:k], "lexical"
        sem = rank_semantic(goal, candidates, k, analyst_fn=analyst_fn)
        merged = lex + [n for n in sem if n not in lex]
        return merged[:k], ("lexical+semantic" if sem else "lexical")
    return _lexical(goal, candidates, k), "lexical"
