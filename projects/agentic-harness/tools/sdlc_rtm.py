# lathe-generated module — do not edit by hand


def rtm_gaps(layers):
    import collections
    if not isinstance(layers, dict):
        return ['no layers']
    problems = []
    order = ['UC', 'BR', 'FR', 'TS']
    data = {}
    for name in order:
        val = layers.get(name)
        data[name] = val if isinstance(val, list) else []

    def valid_id(item):
        if not isinstance(item, dict):
            return None
        i = item.get('id')
        t = item.get('text')
        if isinstance(i, str) and i and isinstance(t, str) and t:
            return i
        return None

    ids_by_layer = {name: [] for name in order}
    for name in order:
        for item in data[name]:
            i = valid_id(item)
            if i is None:
                problems.append('%s: item missing id/text' % name)
            else:
                ids_by_layer[name].append(i)

    seen = set()
    for name in order:
        for i in ids_by_layer[name]:
            if i in seen:
                problems.append("duplicate id '%s'" % i)
            else:
                seen.add(i)

    id_sets = {name: set(ids_by_layer[name]) for name in order}
    parent_of = {'BR': 'UC', 'FR': 'BR', 'TS': 'FR'}
    covered = {name: set() for name in order}

    for child, parent in parent_of.items():
        parent_ids = id_sets[parent]
        for item in data[child]:
            i = valid_id(item)
            if i is None:
                continue
            refs = item.get('traces_to')
            if not isinstance(refs, list) or len(refs) == 0:
                problems.append('%s: traces to nothing' % i)
                continue
            for ref in refs:
                if isinstance(ref, str) and ref in parent_ids:
                    covered[parent].add(ref)
                else:
                    problems.append("%s: traces to unknown/wrong-layer '%s'" % (i, ref))

    coverage_msgs = {
        'UC': '%s: no BR covers this use case',
        'BR': '%s: no FR covers this requirement',
        'FR': '%s: no TS implements this requirement',
    }
    for parent in ['UC', 'BR', 'FR']:
        for i in ids_by_layer[parent]:
            if i not in covered[parent]:
                problems.append(coverage_msgs[parent] % i)

    return problems

