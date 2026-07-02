# lathe-generated module — do not edit by hand


def reject_flags(s):
    try:
        if s is None:
            return [True, []]
        tokens = [t for t in s.split() if t]
        if any(t.startswith('-') for t in tokens):
            return [False, tokens]
        return [True, tokens]
    except Exception:
        return [True, []]

def is_within_root(root, path):
    import os
    try:
        if not path:
            return False
        if os.path.isabs(path):
            resolved = os.path.abspath(path)
        else:
            joined = os.path.join(root, path)
            resolved = os.path.abspath(joined)
        abs_root = os.path.abspath(root)
        if resolved == abs_root:
            return True
        return resolved.startswith(abs_root + os.sep)
    except Exception:
        return False

