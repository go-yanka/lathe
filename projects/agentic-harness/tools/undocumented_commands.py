# lathe-generated module — do not edit by hand


def undocumented_commands(names, doc_text):
    if not names:
        return []
    if not isinstance(doc_text, str):
        doc_text = ''
    result = [name for name in names if isinstance(name, str) and name not in doc_text]
    return sorted(result)

