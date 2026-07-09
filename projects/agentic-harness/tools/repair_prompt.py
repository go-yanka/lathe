"""repair_prompt.py — loop #2 (TARGETED REPAIR): turn a gate failure into a precise fix, not a blind re-roll.

Best-of-N regenerates the whole artifact from the SAME prompt every attempt — so a model that ignored the
physics or crashed on an edge case just fails three different ways and never converges. This builds a repair
prompt that hands the model back ITS OWN failed file plus the EXACT gate failure ("held Space, the craft went
DOWN dy=143.8; the spec says thrust must overcome gravity") and asks it to fix precisely that, keeping what
already works. Pure string builder + a standing gate; the engine feeds it the banked (code, reason) per attempt.
"""

_CONTRACT = ("OUTPUT CONTRACT (hard rule): your ENTIRE reply is the raw, COMPLETE corrected file and NOTHING "
             "else — the first character of your reply is the first character of the file. No preamble, no "
             "explanation, no markdown fences.\n\n")


def build(original_prompt, failed_code, failure_reason, is_skeleton=False, max_code=16000):
    """Construct a targeted-repair prompt from the previous failed candidate and the specific gate failure.
    Truncates generously to stay in context. Returns a self-contained prompt (its own output contract)."""
    task = (original_prompt or "").strip()
    reason = (failure_reason or "unknown failure").strip()
    code = (failed_code or "").strip()
    if len(code) > max_code:
        code = code[:max_code] + "\n/* ...truncated... */"
    return (
        _CONTRACT +
        "You already wrote the file below for this task, but it FAILED a specific automated test. Fix ONLY the "
        "problem the test reports. Keep everything that already works — do NOT rewrite from scratch, do NOT "
        "change unrelated behavior. If the failure names concrete values from the spec (e.g. required physics "
        "numbers), honor them EXACTLY.\n\n"
        "=== THE TASK (the spec you must satisfy) ===\n" + task[:4000] + "\n\n"
        "=== THE EXACT FAILURE TO FIX ===\n" + reason[:2000] + "\n\n"
        "=== YOUR PREVIOUS FILE (correct THIS, do not start over) ===\n" + code + "\n\n"
        "Now output the COMPLETE corrected file."
    )


def reason_from(structural_fails, functional_detail, structural_ok):
    """Compose a single failure-reason string from the engine's gate results (structural vs functional)."""
    if not structural_ok and structural_fails:
        return "STRUCTURAL checks failed: " + "; ".join(str(x) for x in structural_fails[:5])
    return "FUNCTIONAL/behavioral test failed: " + (functional_detail or "(no detail)").strip()
