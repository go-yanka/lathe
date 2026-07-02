# lathe-generated module — do not edit by hand


def apply_overrides(scored, priority, mandatory, k):
    try:
        if not isinstance(priority, dict):
            priority = {}
        if not isinstance(mandatory, list):
            mandatory = []

        adjusted = []
        if isinstance(scored, list):
            for pair in scored:
                try:
                    name, score = pair[0], pair[1]
                    if not isinstance(name, str) or not name:
                        continue
                    mult = priority.get(name, 1.0)
                    if not isinstance(mult, (int, float)) or isinstance(mult, bool):
                        mult = 1.0
                    if not isinstance(score, (int, float)) or isinstance(score, bool):
                        continue
                    adj = score * mult
                    if adj > 0:
                        adjusted.append((name, adj))
                except Exception:
                    continue

        ranked = []
        try:
            if isinstance(k, (int, float)) and not isinstance(k, bool) and k > 0:
                order = sorted(range(len(adjusted)), key=lambda i: (-adjusted[i][1], i))
                ranked = [adjusted[i][0] for i in order[:int(k)]]
        except Exception:
            ranked = []

        result = []
        seen = set()
        for name in mandatory:
            if isinstance(name, str) and name and name not in seen:
                seen.add(name)
                result.append(name)
        for name in ranked:
            if name not in seen:
                seen.add(name)
                result.append(name)
        return result
    except Exception:
        return []

