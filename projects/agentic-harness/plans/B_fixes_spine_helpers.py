# B_fixes_spine_helpers — the PURE fix-logic for review bugs B1,B2,B4,B5,B6,B7, authored THROUGH the harness
# (plans -> engine -> gated -> pinned). The spine (engine_v2.py, registry.py, lathe.py, autonomy_*.py) imports
# and calls these; only the thin I/O/control-flow glue is hand-wired. Proves the harness writes its own fixes.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "spine_helpers"
HEADER = ""
GLUE = ""
_ONLY = 'Output ONLY the Python function code - no prose, no markdown, no tests. Import any module you need INSIDE the function. Define constants INSIDE the function.'
FUNCTIONS = [
    {   # B1
        "name": "resolve_out_dir",
        "prompt": ("Implement resolve_out_dir(out_dir, plan_path) -> str. If out_dir is a non-empty string, return it "
                   "unchanged. Otherwise return the directory containing plan_path, as os.path.dirname(os.path.abspath("
                   "plan_path)). Never raise." + "\n" + _ONLY),
        "tests": [
            "assert resolve_out_dir('tools', '/a/p.py') == 'tools'",
            "assert resolve_out_dir('', '/a/b/plan.py').endswith('b')",
            "assert resolve_out_dir(None, '/x/y/plan.py').endswith('y')",
            "assert resolve_out_dir('out', '') == 'out'",
        ],
    },
    {   # B2
        "name": "treat_missing_as_uninitialized",
        "prompt": ("Implement treat_missing_as_uninitialized(canonical_path) -> bool. Return True if canonical_path is "
                   "a string ending (case-insensitive) with '.db', '.sqlite', or '.sqlite3' (a runtime-generated "
                   "database that simply hasn't been created yet), else False. None -> False. Never raise." + "\n" + _ONLY),
        "tests": [
            "assert treat_missing_as_uninitialized('harness.db') is True",
            "assert treat_missing_as_uninitialized('a/b/board.SQLite') is True",
            "assert treat_missing_as_uninitialized('tools/foo.py') is False",
            "assert treat_missing_as_uninitialized(None) is False",
            "assert treat_missing_as_uninitialized('') is False",
        ],
    },
    {   # B4
        "name": "should_auto_commit",
        "prompt": ("Implement should_auto_commit(env_value) -> bool. Return True only if env_value, converted to a "
                   "string, stripped, and lowercased, is one of '1', 'true', 'yes', 'on'. None or anything else -> "
                   "False. Never raise." + "\n" + _ONLY),
        "tests": [
            "assert should_auto_commit('1') is True",
            "assert should_auto_commit('TRUE') is True",
            "assert should_auto_commit(' yes ') is True",
            "assert should_auto_commit(None) is False",
            "assert should_auto_commit('') is False",
            "assert should_auto_commit('0') is False",
            "assert should_auto_commit('no') is False",
        ],
    },
    {   # B5
        "name": "integration_label",
        "prompt": ("Implement integration_label(has_integration, all_passed) -> str. If has_integration is falsy return "
                   "'n/a (no INTEGRATION defined)'. Else if all_passed is falsy return 'SKIPPED (not all functions "
                   "solved)'. Else return 'ran'. Never raise." + "\n" + _ONLY),
        "tests": [
            "assert integration_label(False, True) == 'n/a (no INTEGRATION defined)'",
            "assert integration_label(False, False) == 'n/a (no INTEGRATION defined)'",
            "assert integration_label(True, False) == 'SKIPPED (not all functions solved)'",
            "assert integration_label(True, True) == 'ran'",
        ],
    },
    {   # B6
        "name": "model_label",
        "prompt": ("Implement model_label(model_name) -> str. If model_name is falsy return 'local'. Otherwise return "
                   "the substring of str(model_name) before the first ':' (or the whole string if no ':'), stripped and "
                   "lowercased. Never raise." + "\n" + _ONLY),
        "tests": [
            "assert model_label('gemma2:12b') == 'gemma2'",
            "assert model_label('qwen2.5-coder') == 'qwen2.5-coder'",
            "assert model_label('openai:local') == 'openai'",
            "assert model_label('') == 'local'",
            "assert model_label(None) == 'local'",
        ],
    },
    {   # B7
        "name": "summarize_failure",
        "prompt": ("Implement summarize_failure(output) -> str. Split str(output) into lines; ignore blank lines and any "
                   "line containing 'activity log skipped'. Among the remaining lines, if any contains 'Error' or "
                   "'error', return the first such line stripped. Else if any remain, return the last remaining line "
                   "stripped. Else return 'build failed'. None -> 'build failed'. Never raise." + "\n" + _ONLY),
        "tests": [
            "assert summarize_failure('activity log skipped: x\\nValueError: boom') == 'ValueError: boom'",
            "assert summarize_failure('line1\\nmid\\nfinal line') == 'final line'",
            "assert summarize_failure('') == 'build failed'",
            "assert summarize_failure(None) == 'build failed'",
            "assert 'activity log skipped' not in summarize_failure('activity log skipped: refused\\nreal problem')",
        ],
    },
]
