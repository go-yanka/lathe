# lathe-generated module — do not edit by hand


def parse_judge_score(txt) -> float:
    import re
    try:
        if not isinstance(txt, str):
            return -1.0
        for m in re.finditer(r'score\s*[:=]?\s*(-?\d+(?:\.\d+)?)', txt, re.IGNORECASE):
            try:
                n = float(m.group(1))
            except (ValueError, OverflowError):
                continue
            if 0 <= n <= 10:
                return float(n)
        for m in re.finditer(r'(?<![\w.-])-?\d+(?:\.\d+)?(?![\w.])', txt):
            try:
                n = float(m.group(0))
            except (ValueError, OverflowError):
                continue
            if 0 <= n <= 10:
                return float(n)
        return -1.0
    except Exception:
        return -1.0

def apply_ratings(scored, ratings):
    if not isinstance(scored, list):
        return []
    if not isinstance(ratings, dict):
        ratings = {}
    result = []
    for pair in scored:
        try:
            name, score = pair[0], pair[1]
        except Exception:
            continue
        adjusted = score
        try:
            rating = ratings.get(name)
            if isinstance(rating, (int, float)) and not isinstance(rating, bool) and 0 <= rating <= 10:
                adjusted = score * (0.5 + rating / 10.0)
        except Exception:
            adjusted = score
        result.append([name, adjusted])
    return result

