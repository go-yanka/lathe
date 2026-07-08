# Functional-gate triage (#12 U1 extension): distinguish "the GATE could not run" (browser missing/locked,
# playwright absent - INOPERATIVE, not the candidate's fault) from "the candidate genuinely failed the
# gate's asserts". Without this, a transient browser-launch failure burns all attempts + feeds the analyst
# misleading spec-failure feedback it cannot fix. Pure logic, harness-built.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "func_gate_triage"
HEADER = ""
GLUE = ""
FUNCTIONS = [
    {
        "name": "gate_infra_failure",
        "prompt": (
            "Write a pure Python function gate_infra_failure(output) that returns True when a functional-"
            "gate subprocess's combined output shows the GATE INFRASTRUCTURE itself failed to run (so the "
            "verdict is inoperative, not a candidate failure), else False. If output is None or not a "
            "string, return False. Return True when the output contains ANY of these substrings "
            "(case-insensitive): \"executable doesn't exist\", 'browsertype.launch', "
            "'playwright was just installed', 'playwright install', "
            "'no module named', 'failed to launch', 'browser closed unexpectedly', "
            "'target page, context or browser has been closed', 'econnrefused'. "
            "An ordinary assertion failure like 'AssertionError: canvas has zero size' or "
            "'ASSERT FAIL: score' must return False. "
            "Output ONLY the Python function code - no prose, no markdown."
        ),
        "tests": [
            "assert gate_infra_failure(\"playwright._impl._errors.Error: BrowserType.launch: Executable doesn't exist at C:/x/chrome.exe\") == True",
            "assert gate_infra_failure('Please run the following command to download new browsers: playwright install') == True",
            "assert gate_infra_failure(\"ModuleNotFoundError: No module named 'playwright'\") == True",
            "assert gate_infra_failure('AssertionError: canvas has zero size') == False",
            "assert gate_infra_failure('ASSERT FAIL: score not shown') == False",
            "assert gate_infra_failure('') == False",
            "assert gate_infra_failure(None) == False",
            "assert gate_infra_failure('Browser closed unexpectedly, please check') == True",
            "assert gate_infra_failure('FUNCTIONAL PASS: page loads') == False",
        ],
    },
]
