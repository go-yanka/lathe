# lathe-generated module — do not edit by hand


def ucb1(mean, count, total, c):
    import math
    try:
        if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
            return float('inf')
        try:
            m = float(mean)
        except Exception:
            m = 0.0
        try:
            t = int(total)
        except Exception:
            t = 1
        if t < 1:
            t = 1
        cc = 1.4 if isinstance(c, bool) else c
        try:
            cc = float(cc)
        except Exception:
            cc = 1.4
        return m + cc * math.sqrt(math.log(t) / count)
    except Exception:
        return float('inf')

def select_personas(names, counts, grades, k, c):
    import math
    if not isinstance(names, (list, tuple)):
        return []
    counts = counts if isinstance(counts, dict) else {}
    grades = grades if isinstance(grades, dict) else {}
    if isinstance(k, bool):
        return []
    try:
        kk = int(k)
    except Exception:
        return []
    if kk <= 0:
        return []
    total = 0
    for v in counts.values():
        if isinstance(v, bool):
            continue
        if isinstance(v, int) and v > 0:
            total += v
    if total < 1:
        total = 1
    cc = 1.4 if isinstance(c, bool) else c
    try:
        cc = float(cc)
    except Exception:
        cc = 1.4
    scored = []
    for name in names:
        if not isinstance(name, str):
            continue
        cnt = counts.get(name)
        if isinstance(cnt, bool) or not isinstance(cnt, int) or cnt <= 0:
            score = float('inf')
        else:
            try:
                g = float(grades.get(name, 0.0))
            except Exception:
                g = 0.0
            score = g + cc * math.sqrt(math.log(total) / cnt)
        scored.append((score, name))
    scored.sort(key=lambda t: (0 if t[0] == float('inf') else 1, 0.0 if t[0] == float('inf') else -t[0], t[1]))
    return [name for _, name in scored[:kk]]

