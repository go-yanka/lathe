# H_persona_ratings — #39: the persona market becomes EMPIRICAL. `lathe agent rate "<need>"` gives each
# matched persona a field-relevant probe task, an independent judge scores the answer 0-10, and the rating
# is stored (agents/ratings.json — per-user runtime data, gitignored). The decider then multiplies match
# scores by a rating factor, so of two personas covering the same ground the better-PERFORMING one wins —
# selection by measured performance, not just word overlap. Pure pieces here; lathe.py wires the model I/O.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "persona_ratings"
HEADER = ""
GLUE = ""
_ONLY = "Output ONLY the Python function code — no prose, no markdown, no tests. Import inside the function."
FUNCTIONS = [
    {"name": "parse_judge_score",
     "prompt": ("Write parse_judge_score(txt) -> float. Extract the judge's numeric score from free text: find "
                "the FIRST occurrence (case-insensitive) of the pattern 'score' followed by optional spaces/colon/"
                "equals and a number (int or decimal); if found and 0 <= n <= 10 return float(n). If no such "
                "labeled score, fall back to the first standalone number in the text that is within 0..10 and "
                "return it. Clamp is NOT applied — out-of-range labeled scores are ignored and the fallback "
                "continues. If nothing usable or txt is None/non-str -> -1.0. Never raise." + "\n" + _ONLY),
     "tests": [
        "assert parse_judge_score('SCORE: 7.5') == 7.5",
        "assert parse_judge_score('score = 9') == 9.0",
        "assert parse_judge_score('I rate this 6 out of 10') == 6.0",
        "assert parse_judge_score('Score: 15 ... but honestly 8') == 8.0",
        "assert parse_judge_score('no numbers here') == -1.0",
        "assert parse_judge_score(None) == -1.0",
        "assert parse_judge_score('The score:0 is deserved') == 0.0",
        "assert parse_judge_score('scores were mixed; SCORE: 3.25') == 3.25",
     ]},
    {"name": "apply_ratings",
     "prompt": ("Write apply_ratings(scored, ratings) -> list. scored is a list of [name, score(number)] pairs "
                "(None -> []). ratings is a dict name -> rating (number 0..10; non-dict/None = {}). Return NEW "
                "[name, adjusted] pairs in the same order where adjusted = score * (0.5 + rating/10.0) when the "
                "name has a numeric rating within 0..10, else score unchanged (unrated personas are neutral, "
                "factor 1.0 — never punished for being new). Non-numeric/out-of-range ratings are ignored. Never "
                "raise." + "\n" + _ONLY),
     "tests": [
        "assert apply_ratings([['a', 2]], {'a': 10}) == [['a', 3.0]]",
        "assert apply_ratings([['a', 2]], {'a': 0}) == [['a', 1.0]]",
        "assert apply_ratings([['a', 2]], {}) == [['a', 2]]",
        "assert apply_ratings([['a', 2], ['b', 2]], {'b': 10}) == [['a', 2], ['b', 3.0]]",
        "assert apply_ratings([['a', 2]], {'a': 99}) == [['a', 2]]",
        "assert apply_ratings([['a', 2]], {'a': 'x'}) == [['a', 2]]",
        "assert apply_ratings(None, {'a': 5}) == []",
        "assert apply_ratings([['a', 4]], None) == [['a', 4]]",
        "assert apply_ratings([['a', 2]], {'a': 5}) == [['a', 2.0]]",
     ]},
]
