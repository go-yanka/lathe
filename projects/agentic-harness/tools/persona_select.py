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
