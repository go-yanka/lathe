# lathe-generated module — do not edit by hand


def trim_for_context(text, max_chars) -> str:
    try:
        import builtins
        if text is None:
            return ''
        if not isinstance(text, str):
            text = str(text)
        if len(text) <= max_chars:
            return text
        trimmed = text[:max_chars].rstrip()
        return trimmed + '\n...[truncated for context budget]'
    except Exception:
        return ''

