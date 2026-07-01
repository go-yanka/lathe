# lathe-generated module — do not edit by hand
VALID_STATUSES = {'live', 'designed', 'retired'}

def _superseded_set(registry):
    result = set()
    for entry in registry.values():
        if not isinstance(entry, dict):
            continue
        if entry.get('status') not in ('live', 'designed'):
            continue
        sup = entry.get('supersedes') or []
        if isinstance(sup, str):
            sup = [sup]
        if not isinstance(sup, (list, tuple, set)):
            continue
        for name in sup:
            result.add(name)
    return result

def _norm_path(p):
    p = str(p).replace(chr(92), '/').lower()
    while '/./' in p:
        p = p.replace('/./', '/')
    if p.startswith('./'):
        p = p[2:]
    return p

def _dup_live_paths(registry):
    by_path = {}
    for name, entry in registry.items():
        if not isinstance(entry, dict):
            continue
        if entry.get('status') == 'live':
            canon = entry.get('canonical')
            if canon:
                by_path.setdefault(_norm_path(canon), []).append(name)
    return {p: sorted(n) for p, n in by_path.items() if len(n) >= 2}


def registry_violations(registry):
    if not registry:
        return []
    
    violations = []
    superseded_set = _superseded_set(registry)
    dup_dict = _dup_live_paths(registry)
    
    for name, entry in registry.items():
        if not isinstance(entry, dict):
            continue
        status = entry.get('status', '')
        if status not in VALID_STATUSES:
            violations.append(f"{name}: invalid status")
        if name in superseded_set and status == 'live':
            violations.append(f"{name}: superseded but still live")
    
    for path in sorted(dup_dict.keys()):
        names = dup_dict[path]
        violations.append(f"duplicate live canonical {path}: {', '.join(names)}")
    
    return sorted(violations)

