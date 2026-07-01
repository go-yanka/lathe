# lathe-generated module — do not edit by hand


def redact_secrets(text):
    import re
    if not isinstance(text, str):
        return ''
    
    def replace_sk(match):
        return '***REDACTED***'
    
    def replace_bearer(match):
        return 'Bearer ***REDACTED***'
    
    def replace_sensitive(match):
        key_part = match.group(1)
        sep = match.group(2)
        return f"{key_part}{sep}***REDACTED***"
    
    text = re.sub(r'sk-[A-Za-z0-9]{12,}', replace_sk, text)
    
    text = re.sub(r'\bBearer\s+[^\s]{16,}', replace_bearer, text)
    
    text = re.sub(
        r'((?:api_key|apikey|token|secret|password)(?:\s)*=[\s]*|[^\s]*(?:api_key|apikey|token|secret|password)(?:\s)*=[\s]*|[^\s]*(?:api_key|apikey|token|secret|password)(?:\s)*:[\s]*)([^\s]*)',
        lambda m: f"{m.group(1)}***REDACTED***",
        text,
        flags=re.IGNORECASE
    )
    
    return text

