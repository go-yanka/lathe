# lathe-generated module — do not edit by hand


def metrics_summary(rows):
    r = len(rows)
    d = {}
    d['runs'] = r
    if r == 0:
        keys = [
            'builds_ok', 'build_success_rate', 'functions_total',
            'functions_passed', 'first_pass', 'first_pass_rate', 'by_local',
            'by_claude', 'claude_calls', 'tok_total', 'avg_tries',
            'escalations'
        ]
        for k in keys:
            d[k] = 0
        return d
    builds_ok = sum(1 for row in rows if row.get('build_ok') is True)
    functions_total = sum(row.get('functions_total', 0) for row in rows)
    functions_passed = sum(row.get('functions_passed', 0) for row in rows)
    first_pass = sum(row.get('first_pass', 0) for row in rows)
    by_local = sum(row.get('by_local', 0) for row in rows)
    by_claude = sum(row.get('by_claude', 0) for row in rows)
    claude_calls = sum(row.get('claude_calls', 0) for row in rows)
    tok_total = sum(row.get('tok_total', 0) for row in rows)
    escalations = sum(1 for row in rows if row.get('failed'))
    build_success_rate = round(builds_ok / r, 3)
    first_pass_rate = round(first_pass / functions_total, 3) if functions_total else 0
    avg_tries = round(sum(row.get('avg_tries', 0) for row in rows) / r, 2)
    d['builds_ok'] = builds_ok
    d['build_success_rate'] = build_success_rate
    d['functions_total'] = functions_total
    d['functions_passed'] = functions_passed
    d['first_pass'] = first_pass
    d['first_pass_rate'] = first_pass_rate
    d['by_local'] = by_local
    d['by_claude'] = by_claude
    d['claude_calls'] = claude_calls
    d['tok_total'] = tok_total
    d['avg_tries'] = avg_tries
    d['escalations'] = escalations
    return d

