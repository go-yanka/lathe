# E_context_helpers — pure helper to keep injected context (e.g. the ctags repo-map) token-lean.
# Authored THROUGH the harness (gated+pinned). hreview reuses it to cap the orientation map it feeds the reviewer.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "context_helpers"
HEADER = ""
GLUE = ""
_ONLY = "Output ONLY the Python function code — no prose, no markdown, no tests. Import inside the function."
FUNCTIONS = [
    {"name": "trim_for_context",
     "prompt": ("Write trim_for_context(text, max_chars) -> str. If text is None return ''. Convert text to str. "
                "If its length is <= max_chars, return it unchanged. Otherwise return the first max_chars characters "
                "(right-stripped) followed by a newline and the literal marker '...[truncated for context budget]'. "
                "Never raise." + "\n" + _ONLY),
     "tests": [
        "assert trim_for_context('short', 100) == 'short'",
        "assert trim_for_context(None, 10) == ''",
        "assert trim_for_context('', 10) == ''",
        "assert trim_for_context('a'*50, 10).startswith('aaaaaaaaaa')",
        "assert '...[truncated for context budget]' in trim_for_context('a'*50, 10)",
        "assert trim_for_context('exactly-10', 10) == 'exactly-10'",
     ]},
]
