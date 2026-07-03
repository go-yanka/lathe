# lathe-generated module — do not edit by hand


def bearer_token(header) -> str:
    if not isinstance(header, str):
        return ''
    import re
    m = re.match(r'(?i)bearer (.+)', header.strip())
    return m.group(1) if m else ''

def auth_ok(header, expected) -> bool:
    import hmac
    try:
        if not expected or not isinstance(expected, str):
            return False
        if not header or not isinstance(header, str):
            return False
        parts = header.split(" ", 1)
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return False
        token = parts[1]
        return hmac.compare_digest(token, expected)
    except Exception:
        return False

def env_allowlist(env, allow):
    try:
        if not isinstance(env, dict):
            return {}
        try:
            allow_set = set(allow) if allow is not None else set()
        except TypeError:
            allow_set = set()
        return {k: str(v) for k, v in env.items() if k in allow_set}
    except Exception:
        return {}

def classify_build_body(body):
    try:
        if not isinstance(body, dict):
            return [False, '', '', 'body must be a JSON object']
        p = body.get('plan')
        p = p if isinstance(p, str) and p else None
        g = body.get('goal')
        g = g if isinstance(g, str) and g else None
        if p and g:
            return [False, '', '', 'provide exactly one of plan or goal, not both']
        if not p and not g:
            return [False, '', '', 'provide a plan (path) or a goal (string)']
        if p:
            return [True, 'plan', p, '']
        return [True, 'goal', g, '']
    except Exception:
        return [False, '', '', 'body must be a JSON object']

def job_view(job):
    try:
        if not isinstance(job, dict) or 'status' not in job:
            return {'status': 'unknown'}
        status = job['status']
        if status in ('done', 'failed') and 'result' in job:
            return {'status': status, 'result': job['result']}
        return {'status': status}
    except Exception:
        return {'status': 'unknown'}

