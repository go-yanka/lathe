# lathe-generated module — do not edit by hand


def dangling_references(used_ids, valid_ids):
    if not used_ids:
        return []
    if valid_ids is None:
        valid_set = set()
    else:
        valid_set = set(valid_ids)
    dangling = set(id_ for id_ in used_ids if id_ not in valid_set)
    return sorted(dangling)

