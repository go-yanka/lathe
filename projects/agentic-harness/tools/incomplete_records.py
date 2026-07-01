# lathe-generated module — do not edit by hand


def incomplete_records(records, required_fields):
    if not records:
        return []
    if not required_fields:
        required_fields = []
    result = []
    for i, record in enumerate(records):
        if not isinstance(record, dict):
            result.append(i)
            continue
        incomplete = False
        for f in required_fields:
            if f not in record:
                incomplete = True
                break
            if record[f] is None or record[f] == '':
                incomplete = True
                break
        if incomplete:
            result.append(i)
    return sorted(result)

