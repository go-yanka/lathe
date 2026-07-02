# lathe-generated module — do not edit by hand


def goal_vagueness(goal):
    try:
        if not isinstance(goal, str) or len(goal.split()) < 6:
            return [True, ['too brief']]
        g = goal.lower()
        aspects = [
            ('inputs', ['input', 'given', 'from', 'accept', 'take', 'parameter', 'arg']),
            ('outputs', ['return', 'output', 'produce', 'result', 'emit', 'generate']),
            ('constraints', ['must', 'should', 'only', 'limit', 'constraint', 'at most', 'no more', 'required', 'cannot']),
            ('examples', ['example', 'e.g', 'like', 'such as', '->']),
            ('edge_cases', ['empty', 'none', 'null', 'invalid', 'error', 'edge', 'zero', 'negative', 'boundary']),
        ]
        missing = [name for name, kws in aspects if not any(kw in g for kw in kws)]
        needs_clarify = 'inputs' in missing or 'outputs' in missing
        return [needs_clarify, missing]
    except Exception:
        return [True, ['too brief']]

def parse_questions(text):
    import re
    if not isinstance(text, str):
        return []
    try:
        keep_re = re.compile(r'^(?:\d+[.)]|[-*]|Q\d+)')
        strip_re = re.compile(r'^(?:\d+[.)]\s*|[-*]\s*|Q\d+[:.]?\s*)')
        seen = set()
        out = []
        for line in text.splitlines():
            s = line.strip()
            if not s:
                continue
            if not (s.endswith('?') or keep_re.match(s)):
                continue
            s = strip_re.sub('', s, count=1).strip()
            if not s or s in seen:
                continue
            seen.add(s)
            out.append(s)
        return out
    except Exception:
        return []

