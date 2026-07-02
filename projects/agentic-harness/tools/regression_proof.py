# lathe-generated module — do not edit by hand


def extract_def(module_src, fn_name):
    import ast
    try:
        if not isinstance(module_src, str):
            return ''
        tree = ast.parse(module_src)
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == fn_name:
                segment = ast.get_source_segment(module_src, node)
                return segment if isinstance(segment, str) else ''
        return ''
    except Exception:
        return ''

def proof_gate(env_value, old_code, old_passes_all):
    try:
        if not isinstance(env_value, str) or env_value.strip().lower() not in ('1', 'true', 'yes', 'on'):
            return [False, 'regression-proof not required']
        if not isinstance(old_code, str) or not old_code:
            return [False, 'no prior implementation - new function']
        if old_passes_all is True:
            return [True, 'REFUSED: every new test PASSES on the old implementation - this change ships no test that reproduces the bug; add a failing-on-old-code test']
        return [False, 'proof present: >=1 new test fails on the old code']
    except Exception:
        return [False, 'regression-proof not required']

def rename_candidates(module_src, current_names):
    import ast
    if not isinstance(module_src, str):
        return []
    try:
        tree = ast.parse(module_src)
    except Exception:
        return []
    if current_names is None:
        current_names = []
    result = []
    try:
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name not in current_names:
                try:
                    seg = ast.get_source_segment(module_src, node)
                except Exception:
                    seg = None
                result.append([node.name, seg])
    except Exception:
        return []
    return result

