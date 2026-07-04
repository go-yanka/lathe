# lathe-generated module — do not edit by hand


def resolve_mode(interactive, config_mode):
    try:
        if interactive:
            return 'interactive'
        if isinstance(config_mode, str) and config_mode.strip().lower() == 'interactive':
            return 'interactive'
        return 'auto'
    except Exception:
        return 'auto'

def apply_selection_overrides(proposed, drop, add, mandatory):
    def _iter(x):
        try:
            return list(x) if not isinstance(x, (str, bytes)) and x is not None else []
        except Exception:
            return []
    result = []
    seen = set()
    dropset = set(n for n in _iter(drop) if isinstance(n, str))
    def _push(name):
        if isinstance(name, str) and name not in seen:
            seen.add(name)
            result.append(name)
    if isinstance(proposed, list):
        for n in proposed:
            if isinstance(n, str) and n not in dropset:
                _push(n)
    for n in _iter(add):
        _push(n)
    for n in _iter(mandatory):
        _push(n)
    return result

