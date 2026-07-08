"""panel_floor.py — MASTER_PLAN E1: guarantee a PROMPT-ARCHITECT lens in the intake panel.

A1 wired a goal-matched panel + a correctness-reviewer floor. E1 adds the MODERATOR the design always intended:
a prompt-architect whose job is to turn the panel's raw questions into ONE sharp thinking brief for the analyst
(craft the prompt per goal, not from a template). This helper guarantees that lens is in the room — pure and
testable, so lathe.py just calls it and a gate proves the panel can never ship without the architect.
"""

ARCHITECT = "prompt-architect"


def with_architect(names, architect=ARCHITECT):
    """Return names with the architect present and FIRST (the moderator opens the brief), order otherwise
    preserved, de-duplicated. Never mutates the input; None/empty-safe."""
    seen = set()
    out = [architect]
    seen.add(architect)
    for n in (names or []):
        if isinstance(n, str) and n and n not in seen:
            out.append(n)
            seen.add(n)
    return out
