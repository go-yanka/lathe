# JS function lane (#60 polyglot): extraction + test-script assembly, pure logic, harness-built.
# The engine calls these, then executes the assembled script under `node` in a subprocess; exit 0 = pass.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "js_runner"
HEADER = ""
GLUE = ""
FUNCTIONS = [
    {
        "name": "extract_js_func",
        "prompt": (
            "Write a pure Python function extract_js_func(text, name) that extracts ONE JavaScript function "
            "definition from model output text. Handle, in this priority order: "
            "(1) a classic declaration: 'function NAME(' ... up to its balanced closing brace; "
            "(2) an arrow/const form: 'const NAME = ' ... up to the balanced closing brace of its body, "
            "including a trailing semicolon if present. "
            "Brace balancing: scan from the first '{' after the match start, count '{' +1 and '}' -1, and "
            "stop at the character where the count returns to 0 (include that '}'); ignore braces inside "
            "single-quoted, double-quoted and backtick strings (track an in_string state with the quote "
            "char; a backslash escapes the next char). "
            "If text is None or name is None or no definition is found, return ''. "
            "If the text contains a markdown fence, first cut it out: take the content between the first "
            "'```' line and the next '```' line if both exist (the fence language tag like 'js' may follow "
            "the first ```). "
            "Worked example: extract_js_func('junk\\nfunction add(a,b){ return a+b; }\\nmore', 'add') "
            "returns 'function add(a,b){ return a+b; }'. "
            "Output ONLY the Python function code - no prose, no markdown."
        ),
        "tests": [
            "assert extract_js_func('function add(a,b){ return a+b; }', 'add') == 'function add(a,b){ return a+b; }'",
            "assert extract_js_func('x\\nfunction add(a,b){ return a+b; }\\ny', 'add') == 'function add(a,b){ return a+b; }'",
            "assert extract_js_func('function add(a,b){ if(a){ return a+b; } return b; }', 'add') == 'function add(a,b){ if(a){ return a+b; } return b; }'",
            "assert extract_js_func('function other(){}', 'add') == ''",
            "assert extract_js_func(None, 'add') == ''",
            "assert extract_js_func('function add(){ return \"}\"; }', 'add') == 'function add(){ return \"}\"; }'",
            "assert extract_js_func('```js\\nfunction add(a,b){ return a+b; }\\n```', 'add') == 'function add(a,b){ return a+b; }'",
            "assert extract_js_func('const add = (a,b) => { return a+b; };', 'add') == 'const add = (a,b) => { return a+b; };'",
        ],
    },
    {
        "name": "js_test_script",
        "prompt": (
            "Write a pure Python function js_test_script(code, tests) that assembles a complete Node.js "
            "script string: first an assert helper line "
            "'function assert(c,m){if(!c){console.error(\"ASSERT FAIL: \"+(m||\"\"));process.exit(1);}}', "
            "then a newline, then the code string, then a newline, then each test string on its own line "
            "in order, then a final line 'console.log(\"JS_TESTS_OK\");'. "
            "If code is None treat it as ''. If tests is None treat it as an empty list; skip any test that "
            "is None or empty/whitespace-only. Return the assembled string. "
            "Output ONLY the Python function code - no prose, no markdown."
        ),
        "tests": [
            "assert 'JS_TESTS_OK' in js_test_script('function f(){}', ['assert(f()===undefined)'])",
            "assert js_test_script('function f(){}', ['assert(1)']).count('assert(1)') == 1",
            "assert js_test_script('function f(){}', ['a', 'b']).index('a\\nb') > 0",
            "assert 'process.exit(1)' in js_test_script('', [])",
            "assert js_test_script(None, None).endswith('console.log(\"JS_TESTS_OK\");')",
            "assert 'x_test' in js_test_script('c', ['x_test', None, '  '])",
        ],
    },
    {
        "name": "js_test_danger",
        "prompt": (
            "Write a pure Python function js_test_danger(s) that returns True when a JavaScript test string "
            "must be REFUSED as dangerous, else False. Refuse (return True) when s is not a string, or when "
            "it contains ANY of these substrings (case-sensitive): 'require', 'import', 'process.', "
            "'child_process', 'fs.', 'eval(', 'Function(', 'fetch(', 'XMLHttpRequest', 'globalThis', "
            "'__proto__', 'constructor['. A plain call plus comparison like 'assert(f(2)===5)' is safe "
            "(return False). Output ONLY the Python function code - no prose, no markdown."
        ),
        "tests": [
            "assert js_test_danger('assert(f(2)===5)') == False",
            "assert js_test_danger(\"require('fs')\") == True",
            "assert js_test_danger('import x from \"y\"') == True",
            "assert js_test_danger('process.exit(0)') == True",
            "assert js_test_danger('eval(\"x\")') == True",
            "assert js_test_danger(None) == True",
            "assert js_test_danger('assert(add(1,2)===3, \"sum\")') == False",
            "assert js_test_danger('globalThis.x=1') == True",
        ],
    },
]
