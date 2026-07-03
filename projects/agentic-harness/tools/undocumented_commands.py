# lathe-generated module — do not edit by hand


def undocumented_commands(names, doc_text):
    import re
    if not names:
        return []
    if not isinstance(doc_text, str):
        doc_text = ''
    result = [
        name for name in names
        if isinstance(name, str)
        and not re.search(r'(?<![A-Za-z0-9_])' + re.escape(name) + r'(?![A-Za-z0-9_])', doc_text)
    ]
    return sorted(result)

