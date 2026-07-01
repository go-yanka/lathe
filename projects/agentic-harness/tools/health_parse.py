# lathe-generated module — do not edit by hand


def parse_health_response(status_code, body):
    import json
    
    if status_code != 200:
        return {'ok': False, 'reason': 'http ' + str(status_code)}
    
    if status_code == 200:
        if body and body.strip():
            try:
                parsed = json.loads(body)
                if isinstance(parsed, dict) and 'status' in parsed:
                    value = parsed['status']
                    s = str(value).lower()
                    if s in ('ok', 'healthy', 'up', 'ready'):
                        return {'ok': True, 'reason': 'healthy'}
                    else:
                        return {'ok': False, 'reason': 'status: ' + str(value)}
            except (json.JSONDecodeError, TypeError, ValueError):
                pass
        
        return {'ok': True, 'reason': 'healthy'}

