# lathe-generated module — do not edit by hand


def usage_record(persona, run_id, considered, fired, raised, confirmed, model):
    try:
        def _count(v):
            if isinstance(v, bool):
                return 0
            if isinstance(v, (int, float)) and v >= 0:
                return int(v)
            return 0

        raised_n = _count(raised)
        confirmed_n = min(_count(confirmed), raised_n)
        return {
            'persona': str(persona) if persona is not None else '',
            'run': str(run_id) if run_id is not None else '',
            'considered': bool(considered),
            'fired': bool(fired),
            'raised': raised_n,
            'confirmed': confirmed_n,
            'model': str(model) if model is not None else '',
        }
    except Exception:
        return {
            'persona': '',
            'run': '',
            'considered': False,
            'fired': False,
            'raised': 0,
            'confirmed': 0,
            'model': '',
        }

def parse_usage(text):
    import json
    if not isinstance(text, str):
        return []
    records = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if isinstance(obj, dict):
            records.append(obj)
    return records

def never_fired(records, all_names):
    try:
        fired_set = set()
        try:
            for rec in records:
                try:
                    if isinstance(rec, dict) and rec.get('fired'):
                        fired_set.add(rec.get('persona'))
                except Exception:
                    continue
        except TypeError:
            pass
        try:
            names = list(all_names)
        except TypeError:
            names = []
        return sorted([n for n in names if isinstance(n, str) and n not in fired_set])
    except Exception:
        return []

def persona_stats(records, persona):
    import numbers
    stats = {'considered': 0, 'fired': 0, 'raised': 0, 'confirmed': 0, 'hit_rate': 0.0}
    try:
        if not isinstance(records, list):
            return stats
        for record in records:
            try:
                if not isinstance(record, dict) or record.get('persona') != persona:
                    continue
                if record.get('considered'):
                    stats['considered'] += 1
                if record.get('fired'):
                    stats['fired'] += 1
                for key in ('raised', 'confirmed'):
                    val = record.get(key, 0)
                    if isinstance(val, numbers.Number) and not isinstance(val, bool):
                        stats[key] += int(val)
            except Exception:
                continue
        if stats['raised'] > 0:
            stats['hit_rate'] = stats['confirmed'] / stats['raised']
    except Exception:
        pass
    return stats

