# lathe-generated module — do not edit by hand


def extract_js_func(text, name):
    if text is None or name is None:
        return ''
    lines = text.split('\n')
    fence_lines = [i for i, ln in enumerate(lines) if ln.strip().startswith('```')]
    if len(fence_lines) >= 2:
        text = '\n'.join(lines[fence_lines[0] + 1:fence_lines[1]])

    def find_balanced_end(start):
        i = text.find('{', start)
        if i == -1:
            return -1
        depth = 0
        in_string = None
        n = len(text)
        while i < n:
            ch = text[i]
            if in_string is not None:
                if ch == '\\':
                    i += 2
                    continue
                if ch == in_string:
                    in_string = None
            else:
                if ch in ('"', "'", '`'):
                    in_string = ch
                elif ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        return i
            i += 1
        return -1

    start = text.find('function ' + name + '(')
    if start == -1:
        start = text.find('function ' + name + ' (')
    if start != -1:
        end = find_balanced_end(start)
        if end != -1:
            return text[start:end + 1]

    start = text.find('const ' + name + ' = ')
    if start == -1:
        start = text.find('const ' + name + ' =')
    if start != -1:
        end = find_balanced_end(start)
        if end != -1:
            result = text[start:end + 1]
            if end + 1 < len(text) and text[end + 1] == ';':
                result += ';'
            return result

    return ''

def js_test_script(code, tests):
    lines = ['function assert(c,m){if(!c){console.error("ASSERT FAIL: "+(m||""));process.exit(1);}}']
    lines.append(code if code is not None else '')
    if tests is None:
        tests = []
    for t in tests:
        if t is None or not t.strip():
            continue
        lines.append(t)
    lines.append('console.log("JS_TESTS_OK");')
    return '\n'.join(lines)

def js_test_danger(s):
    if not isinstance(s, str):
        return True
    banned = ('require', 'import', 'process.', 'child_process', 'fs.',
              'eval(', 'Function(', 'fetch(', 'XMLHttpRequest',
              'globalThis', '__proto__', 'constructor[')
    return any(b in s for b in banned)

