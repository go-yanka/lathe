# lathe-generated module — do not edit by hand


def structural_signature(source):
    if not source:
        return ''
    import ast
    try:
        tree = ast.parse(source)
    except Exception:
        return ''
    types = [type(node).__name__ for node in ast.walk(tree)]
    return ','.join(types)

