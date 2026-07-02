# lathe-generated module — do not edit by hand


def parse_assumptions(text):
    import re
    try:
        if not isinstance(text, str):
            return []
        results = []
        for line in text.splitlines():
            line = line.strip()
            m = re.match(r'\[([^\]]*)\]', line)
            if not m:
                continue
            pieces = [p.strip() for p in m.group(1).split('|')]
            if not pieces or pieces[0].lower() != 'assumption':
                continue
            rest = pieces[1:]
            raw_mat = rest[0] if len(rest) >= 1 else ''
            raw_cat = rest[1] if len(rest) >= 2 else ''
            mat_l = raw_mat.lower()
            if mat_l.startswith('h') or mat_l.startswith('crit'):
                materiality = 'high'
            elif mat_l.startswith('l'):
                materiality = 'low'
            else:
                materiality = 'med'
            category = raw_cat.lower() if raw_cat else 'general'
            body = line[m.end():].strip()
            if not body:
                continue
            results.append({'materiality': materiality, 'category': category, 'text': body})
        return results
    except Exception:
        return []

def blocking_assumptions(assumptions, policy):
    try:
        if not isinstance(assumptions, list):
            return []
        try:
            p = policy.strip().lower() if isinstance(policy, str) else ""
        except Exception:
            p = ""
        if p in ('off', 'none', 'advisory', '0', 'false'):
            return []
        elif 'all' in p or 'low' in p:
            allowed = {'high', 'med', 'low'}
        elif 'med' in p:
            allowed = {'high', 'med'}
        else:
            allowed = {'high'}
        result = []
        for a in assumptions:
            try:
                if isinstance(a, dict):
                    m = a.get('materiality')
                    if isinstance(m, str) and m.strip().lower() in ('high', 'med', 'low') and m.strip().lower() in allowed:
                        result.append(a)
            except Exception:
                continue
        return result
    except Exception:
        return []

def unconfirmed_blockers(assumptions, confirmed, policy):
    import re
    try:
        if not isinstance(assumptions, list):
            return []

        def norm(t):
            try:
                return re.sub(r"\s+", " ", str(t)).strip().lower()
            except Exception:
                return ""

        p = str(policy).strip().lower() if policy is not None else ""
        if p in ("off", "none", "advisory", "0", "false"):
            return []
        if "all" in p or "low" in p:
            levels = ("high", "med", "low")
        elif "med" in p:
            levels = ("high", "med")
        else:
            levels = ("high",)

        confirmed_set = set()
        if confirmed:
            try:
                for c in confirmed:
                    confirmed_set.add(norm(c))
            except Exception:
                pass

        out = []
        for a in assumptions:
            try:
                if isinstance(a, dict):
                    mat = str(a.get("materiality", "")).strip().lower()
                    text = a.get("text", "")
                else:
                    continue
                if mat not in levels:
                    continue
                if norm(text) in confirmed_set:
                    continue
                out.append(a)
            except Exception:
                continue
        return out
    except Exception:
        return []

def spec_digest(functions) -> str:
    import hashlib
    try:
        if not isinstance(functions, list):
            functions = []
        canonical = []
        for item in functions:
            if isinstance(item, dict):
                canonical.append((
                    item.get('name', ''),
                    item.get('prompt', ''),
                    tuple(item.get('tests') or []),
                ))
            else:
                canonical.append(('', '', ()))
        return hashlib.sha256(repr(canonical).encode('utf-8')).hexdigest()
    except Exception:
        return hashlib.sha256(b'').hexdigest()

