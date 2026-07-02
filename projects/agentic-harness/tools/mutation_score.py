# lathe-generated module — do not edit by hand


def mutate_code(code, limit):
    import ast
    import copy
    try:
        if not isinstance(code, str):
            return []
        if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
            return []
        tree = ast.parse(code)

        binop_map = {ast.Add: ast.Sub, ast.Sub: ast.Add,
                     ast.Mult: ast.Add, ast.Div: ast.Mult}
        cmp_map = {ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE,
                   ast.GtE: ast.Gt, ast.Eq: ast.NotEq, ast.NotEq: ast.Eq,
                   ast.In: ast.NotIn, ast.NotIn: ast.In,
                   ast.Is: ast.IsNot, ast.IsNot: ast.Is}
        bool_map = {ast.And: ast.Or, ast.Or: ast.And}

        def is_transformable(node):
            if isinstance(node, ast.BinOp) and type(node.op) in binop_map:
                return True
            if (isinstance(node, ast.Compare) and len(node.ops) == 1
                    and type(node.ops[0]) in cmp_map):
                return True
            if isinstance(node, ast.Constant):
                if isinstance(node.value, bool):
                    return False
                if isinstance(node.value, int):
                    return True
                if isinstance(node.value, str):
                    return True
                return False
            if isinstance(node, ast.BoolOp) and type(node.op) in bool_map:
                return True
            if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
                return True
            return False

        def apply_transform(t, node):
            if isinstance(node, ast.BinOp):
                node.op = binop_map[type(node.op)]()
                return
            if isinstance(node, ast.Compare):
                node.ops[0] = cmp_map[type(node.ops[0])]()
                return
            if isinstance(node, ast.Constant):
                if isinstance(node.value, int):
                    node.value = node.value + 1
                else:
                    node.value = node.value + '_' if node.value else 'x'
                return
            if isinstance(node, ast.BoolOp):
                node.op = bool_map[type(node.op)]()
                return
            replacement = node.operand
            for parent in ast.walk(t):
                for field, value in ast.iter_fields(parent):
                    if value is node:
                        setattr(parent, field, replacement)
                    elif isinstance(value, list):
                        for j, item in enumerate(value):
                            if item is node:
                                value[j] = replacement

        indices = [i for i, n in enumerate(ast.walk(tree)) if is_transformable(n)]
        variants = []
        for i in indices:
            if len(variants) >= limit:
                break
            try:
                t2 = copy.deepcopy(tree)
                target = list(ast.walk(t2))[i]
                apply_transform(t2, target)
                variants.append(ast.unparse(t2))
            except Exception:
                continue
        return variants
    except Exception:
        return []

def mutation_gate(env_value, killed, total):
    if env_value is None or not isinstance(env_value, str) or not env_value.strip():
        return [False, 'mutation score not required']
    try:
        threshold = float(env_value.strip())
    except (ValueError, TypeError):
        return [False, 'unrecognized LATHE_MUTATION_SCORE value - gate skipped']
    if not (0.0 <= threshold <= 1.0):
        return [False, 'unrecognized LATHE_MUTATION_SCORE value - gate skipped']
    if isinstance(total, bool) or not isinstance(total, int) or total <= 0:
        return [False, 'no mutants generated - nothing to judge']
    if isinstance(killed, bool) or not isinstance(killed, int) or killed < 0 or killed > total:
        return [True, 'REFUSED: malformed mutation-gate inputs (killed=%s total=%s) - failing closed' % (killed, total)]
    score = killed / total
    if score + 1e-9 >= threshold:
        return [False, 'mutation score ok: killed %d/%d' % (killed, total)]
    return [True, 'REFUSED: tests kill only %d/%d mutants (score %.2f < threshold %.2f) - the suite cannot distinguish the accepted code from its mutants; strengthen the tests' % (killed, total, score, threshold)]

