# lathe-generated module — do not edit by hand


def role_usage(roles):
    def _coerce(v):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or v < 0:
            return 0
        try:
            return int(v)
        except (ValueError, OverflowError):
            return 0

    by_role = {}
    calls_by_role = {}
    total_p = total_e = total_calls = uninstrumented = 0

    if isinstance(roles, dict):
        for name, info in roles.items():
            if not isinstance(name, str) or not isinstance(info, dict):
                continue
            p = _coerce(info.get('p'))
            e = _coerce(info.get('e'))
            c = _coerce(info.get('calls'))
            src = info.get('src')
            by_role[name] = {
                'prompt': p,
                'completion': e,
                'total': p + e,
                'source': src if isinstance(src, str) else 'n/a',
            }
            calls_by_role[name] = c
            total_p += p
            total_e += e
            total_calls += c
            if c > 0 and p + e == 0:
                uninstrumented += c

    result = {
        'tokens': {
            'prompt': total_p,
            'completion': total_e,
            'total': total_p + total_e,
            'by_role': by_role,
            'completeness': {
                'all_calls_attributed': uninstrumented == 0,
                'uninstrumented_calls': uninstrumented,
            },
        },
        'calls': {'total': total_calls},
    }
    result['calls'].update(calls_by_role)
    return result

def imputed_cost(roles, prices):
    def _tok(v):
        if isinstance(v, bool):
            return 0
        try:
            n = int(v)
        except (TypeError, ValueError):
            return 0
        return n if n >= 0 else 0

    def _price(v):
        if isinstance(v, bool):
            return None
        try:
            f = float(v)
        except (TypeError, ValueError):
            return None
        if f != f or f in (float('inf'), float('-inf')) or f < 0:
            return None
        return f

    if not isinstance(roles, dict):
        return {'imputed_by_role': {}, 'imputed_total': 0.0}

    by_role = {}
    total = 0.0
    for role, usage in roles.items():
        p = e = 0
        if isinstance(usage, dict):
            p = _tok(usage.get('p'))
            e = _tok(usage.get('e'))
        cost = 0.0
        if isinstance(prices, dict) and isinstance(prices.get(role), dict):
            pr = prices[role]
            rate_in = _price(pr.get('in_per_mtok'))
            rate_out = _price(pr.get('out_per_mtok'))
            if rate_in is not None and rate_out is not None:
                cost = round(p / 1e6 * rate_in + e / 1e6 * rate_out, 6)
        by_role[role] = cost
        total += cost
    return {'imputed_by_role': by_role, 'imputed_total': round(total, 6)}

def manifest_hash(manifest) -> str:
    try:
        import copy as _copy
        import hashlib
        import json
        if not isinstance(manifest, dict):
            return ''
        m = _copy.deepcopy(manifest)
        if isinstance(m.get('integrity'), dict):
            m['integrity']['manifest_sha256'] = ''
        serialized = json.dumps(m, sort_keys=True, separators=(',', ':'), default=str)
        return 'sha256:' + hashlib.sha256(serialized.encode('utf-8')).hexdigest()
    except Exception:
        return ''

