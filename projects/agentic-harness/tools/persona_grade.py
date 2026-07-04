# lathe-generated module — do not edit by hand


def finding_score(result, min_conf):
    if not isinstance(result, dict):
        return None
    if not result.get('pass'):
        return None
    try:
        c = float(result.get('confidence', 0.0))
    except Exception:
        c = 0.0
    if c < 0.0:
        c = 0.0
    if c > 1.0:
        c = 1.0
    try:
        mc = float(min_conf)
    except Exception:
        mc = 0.0
    if c < mc:
        return None
    return c

def grade_update(prior, prior_weight, scores):
    try:
        p = float(prior)
    except Exception:
        p = 0.5
    if p < 0.0:
        p = 0.0
    if p > 1.0:
        p = 1.0
    try:
        w = float(prior_weight)
        if w < 0:
            w = 1.0
    except Exception:
        w = 1.0
    vals = []
    try:
        for s in scores:
            if isinstance(s, bool):
                continue
            if isinstance(s, (int, float)):
                v = float(s)
                if v < 0.0:
                    v = 0.0
                if v > 1.0:
                    v = 1.0
                vals.append(v)
    except Exception:
        vals = []
    if not vals:
        return p
    g = (p * w + sum(vals)) / (w + len(vals))
    if g < 0.0:
        g = 0.0
    if g > 1.0:
        g = 1.0
    return g

