# lathe-generated module — do not edit by hand


def code_refs(code, names):
    import re
    try:
        if not code or not isinstance(code, str) or not names:
            return []
        result = []
        seen = set()
        for name in names:
            if not isinstance(name, str) or not name or name in seen:
                continue
            if re.search(r'(?<![A-Za-z0-9_])' + re.escape(name) + r'(?![A-Za-z0-9_])', code):
                seen.add(name)
                result.append(name)
        return result
    except Exception:
        return []

def pin_stale_by_deps(code, fresh_names):
    try:
        import re
        if not code or not isinstance(code, str):
            return False
        if not fresh_names:
            return False
        for name in fresh_names:
            if not name or not isinstance(name, str):
                continue
            if re.search(r'(?<![A-Za-z0-9_])' + re.escape(name) + r'(?![A-Za-z0-9_])', code):
                return True
        return False
    except Exception:
        return False

