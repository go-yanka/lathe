# lathe-generated module — do not edit by hand


def distribution_anomalies(values, dominance=0.9):
    try:
        if not values:
            return ['empty output']
        if len(values) == 1:
            return []
        counts = {}
        for v in values:
            key = str(v)
            counts[key] = counts.get(key, 0) + 1
        if len(set(counts.keys())) == 1:
            return ['collapsed: all values identical']
        total = len(values)
        max_count = max(counts.values())
        fraction = max_count / total
        if fraction >= dominance:
            return ['dominant value: %d%% identical' % round(100 * fraction)]
        return []
    except Exception:
        return []

