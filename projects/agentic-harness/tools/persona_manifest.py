# lathe-generated module — do not edit by hand


def build_manifest(goal, considered, selected, contributions):
    rows = []
    if isinstance(considered, list):
        for d in considered:
            if not isinstance(d, dict):
                continue
            try:
                gr = float(d.get('grade', 0.0))
            except Exception:
                gr = 0.0
            rows.append({'name': str(d.get('name', '')), 'grade': gr, 'picked': bool(d.get('picked')), 'reason': str(d.get('reason', ''))})
    sel = [x for x in selected if isinstance(x, str)] if isinstance(selected, list) else []
    contrib = {}
    if isinstance(contributions, dict):
        for k, v in contributions.items():
            if isinstance(v, bool):
                continue
            if isinstance(v, (int, float)) and v >= 0:
                contrib[str(k)] = int(v)
    contributed = sum(1 for v in contrib.values() if v > 0)
    return {'goal': str(goal) if goal is not None else '', 'considered': rows, 'selected': sel, 'contributions': contrib, 'summary': {'considered': len(rows), 'selected': len(sel), 'contributed': contributed}}

def render_manifest(manifest):
    try:
        if not isinstance(manifest, dict):
            return ''
        goal = manifest.get('goal', '')
        lines = ['# Persona run manifest', '', '> goal: ' + str(goal), '', '## Considered', '', '| persona | grade | picked | reason |', '|---|---|---|---|']
        for r in manifest.get('considered', []) or []:
            if not isinstance(r, dict):
                continue
            lines.append('| %s | %s | %s | %s |' % (r.get('name', ''), r.get('grade', ''), 'yes' if r.get('picked') else 'no', r.get('reason', '')))
        lines += ['', '## Selected', '', ', '.join(str(x) for x in (manifest.get('selected', []) or []))]
        lines += ['', '## Contributions', '']
        for k, v in (manifest.get('contributions', {}) or {}).items():
            lines.append('- %s: %s' % (k, v))
        return chr(10).join(lines) + chr(10)
    except Exception:
        return ''

