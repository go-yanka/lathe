# lathe-generated module — do not edit by hand


def model_class(model):
    import re
    if model is None or not isinstance(model, str) or model == '':
        return 'local-small'
    s = model.lower()
    if any(k in s for k in ('claude', 'fable', 'opus', 'sonnet', 'gpt', 'gemini')):
        return 'frontier'
    m = re.search(r'(\d+(?:\.\d+)?)\s*[bB]\b', s)
    if m:
        return 'local-large' if float(m.group(1)) >= 27 else 'local-small'
    return 'local-small'

