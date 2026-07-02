# lathe-generated module — do not edit by hand


def mutate_code(code, limit):
    import ast
    import copy
    try:
        if not isinstance(code, str):
            return []
        if not isinstance(limit, (int, float)) or isinstance(limit, bool) or limit <= 0:
            return []
        tree = ast.parse(code)
        binop_map = {ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.Add, ast.Div: ast.Mult}
        cmp_map = {ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE,
                   ast.GtE: ast.Gt, ast.Eq: ast.NotEq, ast.NotEq: ast.Eq}

        def is_mutable(node):
            if isinstance(node, ast.BinOp) and type(node.op) in binop_map:
                return True
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in cmp_map:
                return True
            if isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool):
                return True
            return False

        results = []
        nodes = list(ast.walk(tree))
        for i, node in enumerate(nodes):
            if not is_mutable(node):
                continue
            try:
                tree_copy = copy.deepcopy(tree)
                target = list(ast.walk(tree_copy))[i]
                if isinstance(target, ast.BinOp):
                    target.op = binop_map[type(target.op)]()
                elif isinstance(target, ast.Compare):
                    target.ops[0] = cmp_map[type(target.ops[0])]()
                else:
                    target.value = target.value + 1
                results.append(ast.unparse(tree_copy))
            except Exception:
                continue
            if len(results) >= limit:
                break
        return results
    except Exception:
        return []

def mutation_gate(env_value, killed, total):
    try:
        if env_value is None or not isinstance(env_value, str) or not env_value.strip():
            return [False, 'mutation score not required']
        try:
            threshold = float(env_value.strip())
        except (ValueError, TypeError):
            return [False, 'unrecognized LATHE_MUTATION_SCORE value - gate skipped']
        if not (0.0 <= threshold <= 1.0):
            return [False, 'unrecognized LATHE_MUTATION_SCORE value - gate skipped']
        if not isinstance(total, int) or isinstance(total, bool) or total <= 0:
            return [False, 'no mutants generated - nothing to judge']
        score = killed / total
        if score + 1e-9 >= threshold:
            return [False, 'mutation score ok: killed %s/%s' % (killed, total)]
        return [True,
                'REFUSED: tests kill only %s/%s mutants (score %.2f < threshold %.2f) - '
                'the suite cannot distinguish the accepted code from its mutants; '
                'strengthen the tests' % (killed, total, score, threshold)]
    except Exception:
        return [False, 'unrecognized LATHE_MUTATION_SCORE value - gate skipped']

