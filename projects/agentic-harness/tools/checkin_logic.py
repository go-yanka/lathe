# lathe-generated module — do not edit by hand


def is_relic(path: str) -> bool:
    try:
        if path is None:
            return False
        if not isinstance(path, str):
            return False
        lower = path.lower()
        if '__pycache__' in lower:
            return True
        if '/_fn_fails/' in lower:
            return True
        basename = path.split('/')[-1] if '/' in path else path
        basename_lower = basename.lower()
        for ext in ('.pyc', '.pyo', '.log', '.tmp', '.orig', '.bak', '.db-journal', '.rej'):
            if basename_lower.endswith(ext):
                return True
        if basename_lower == 'run_report.md':
            return True
        return False
    except Exception:
        return False

def checkin_blockers(gate_green, behind, relics):
    import warnings
    blockers = []
    try:
        if not gate_green:
            blockers.append('gates not green')
        if isinstance(behind, int) and not isinstance(behind, bool) and behind > 0:
            blockers.append('remote ahead by %d (pull first)' % behind)
        if relics and hasattr(relics, '__len__'):
            blockers.append('relics: %d' % len(relics))
    except Exception as e:
        warnings.warn('checkin_blockers failed: %s' % e)
    return blockers

