# lathe-generated module — do not edit by hand


def jsonrpc_result(rid, result):
    import json
    try:
        return {'jsonrpc': '2.0', 'id': rid, 'result': result}
    except Exception:
        return {}

def jsonrpc_error(rid, code, message):
    """Build a JSON-RPC 2.0 error response dict without raising."""
    try:
        import json as _json
    except Exception:
        _json = None

    return {
        'jsonrpc': '2.0',
        'id': rid,
        'error': {
            'code': int(code),
            'message': str(message),
        }
    }

def tool_text(text) -> dict:
    try:
        if text is None:
            return {'content': [{'type': 'text', 'text': ''}]}
        return {'content': [{'type': 'text', 'text': str(text)}]}
    except Exception:
        return {'content': [{'type': 'text', 'text': ''}]}

