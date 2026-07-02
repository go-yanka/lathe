# lathe-generated module — do not edit by hand


def parse_config(text):
    """Parse a JSON config string into a dict."""
    import json

    # Return empty dict for None or empty input
    if not text:
        return {}

    # Try to parse the JSON string
    try:
        result = json.loads(text)
    except (json.JSONDecodeError, TypeError, ValueError):
        return {}

    # Return the result only if it's a dict
    if isinstance(result, dict):
        return result

    return {}

def pick(env_val, cfg_val, default):
    try:
        import os
        if env_val:
            return env_val
        elif cfg_val:
            return cfg_val
        else:
            return default
    except Exception:
        return default

