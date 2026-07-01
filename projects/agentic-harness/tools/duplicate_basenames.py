# lathe-generated module — do not edit by hand


def duplicate_basenames(paths):
    try:
        import os
    except ImportError:
        import posixpath as os
    if not paths:
        return {}
    result = {}
    parents_set = set()
    for p in paths:
        try:
            bn = os.path.basename(p).lower()
            parent = os.path.dirname(p)
        except Exception:
            continue
        if bn in result:
            result[bn].append(p)
        else:
            result[bn] = [p]
        parents_set.add(parent)
    # Keep only entries where multiple distinct parents exist
    final = {}
    for bn, path_list in result.items():
        # We need to check how many distinct parents are in THIS group
        group_parents = set()
        for pp in path_list:
            try:
                group_parents.add(os.path.dirname(pp))
            except Exception:
                pass
        if len(group_parents) >= 2:
            sorted_paths = sorted(path_list)
            final[bn] = sorted_paths
    return final

