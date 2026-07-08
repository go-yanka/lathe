"""outcome_feedback.py — MASTER_PLAN E4: persona ratings learn from REVIEW OUTCOMES, not just `agent rate`.

Today a persona's rating comes only from a dedicated `lathe agent rate` run (a probe + judge). E4 closes the
loop: when a lens actually reviews real code, that OUTCOME nudges its rating automatically. Reuses the existing
grade math (persona_grade.grade_update / finding_score) and the existing ratings store — the persistence
functions are INJECTED so this is pure + testable and the store format never forks.

Honest about the signal: a single review is a COARSE signal, so it is EWMA-blended with a heavy prior_weight —
one review moves a rating a little, a consistent pattern moves it a lot. The signal per lens:
  "material"    the lens produced anchored, non-trivial findings -> engaged well          (0.85)
  "engaged"     the lens ran and produced a valid review (found issues OR clean)           (0.70)
  "clean"       ran, explicitly nothing material (also correct, but less evidence)         (0.60)
  "inoperative" the lens could not run / returned a non-review (D5b) -> NO signal          (None -> skipped)
"""

SCORE = {"material": 0.85, "engaged": 0.70, "clean": 0.60, "inoperative": None, "error": None}


def score_verdict(verdict):
    """Map a per-lens review verdict to a 0-1 outcome score, or None (no usable signal). Unknown -> None."""
    return SCORE.get((verdict or "").strip().lower())


def record_review_outcomes(lens_verdicts, load_ratings, save_rating, prior_weight=5, grade_fn=None):
    """For each (lens -> verdict), blend the outcome score into the lens's prior rating and persist it.
    `load_ratings() -> {name: {"rating": float, ...}}`; `save_rating(name, score, need) -> ...` (injected).
    Returns {lens: new_rating} for the lenses actually updated. Never raises."""
    if grade_fn is None:
        try:
            from persona_grade import grade_update as grade_fn
        except Exception:
            def grade_fn(prior, w, scores):                      # minimal EWMA fallback if the module is absent
                p = float(prior);
                for s in scores:
                    p = (p * w + float(s)) / (w + 1)
                return p
    try:
        ratings = load_ratings() or {}
    except Exception:
        ratings = {}
    out = {}
    for lens, verdict in (lens_verdicts or {}).items():
        if not isinstance(lens, str) or not lens or lens.startswith("@"):   # skip fetched-by-path lenses
            continue
        s = score_verdict(verdict)
        if s is None:
            continue
        try:
            prior = float((ratings.get(lens) or {}).get("rating", 0.5))
        except Exception:
            prior = 0.5
        try:
            new = float(grade_fn(prior, prior_weight, [s]))
        except Exception:
            continue
        new = 0.0 if new < 0 else (1.0 if new > 1 else new)
        try:
            save_rating(lens, new, "review-outcome")
            out[lens] = round(new, 3)
        except Exception:
            continue
    return out
