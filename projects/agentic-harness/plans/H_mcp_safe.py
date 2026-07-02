# H_mcp_safe — pure input-safety for the MCP tool surface (found by the harness's own review of lathe_mcp.py:
# argument-injection + path-traversal HIGHs). Authored THROUGH the harness (gated+pinned); lathe_mcp wires them in.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "mcp_safe"
HEADER = ""
GLUE = ""
_ONLY = "Output ONLY the Python function code — no prose, no markdown, no tests. Import inside the function."
FUNCTIONS = [
    {"name": "reject_flags",
     "prompt": ("Write reject_flags(s) -> list. Split str(s) on whitespace into tokens (drop empties). Return a "
                "two-element list [ok, tokens] where ok is False if ANY token starts with '-' (it would be read as a "
                "CLI flag — argument injection), else True. None -> [True, []]. Never raise." + "\n" + _ONLY),
     "tests": [
        "assert reject_flags('a b') == [True, ['a', 'b']]",
        "assert reject_flags('--x y') == [False, ['--x', 'y']]",
        "assert reject_flags('-r') == [False, ['-r']]",
        "assert reject_flags('') == [True, []]",
        "assert reject_flags(None) == [True, []]",
     ]},
    {"name": "is_within_root",
     "prompt": ("Write is_within_root(root, path) -> bool. Resolve path with os.path.abspath (if path is not "
                "absolute, first os.path.join it onto root). Return True only if the resolved path equals "
                "os.path.abspath(root) or starts with os.path.abspath(root) + os.sep (i.e. it does not escape root — "
                "blocks '..' traversal). None or empty path -> False. Never raise. Import os inside." + "\n" + _ONLY),
     "tests": [
        "assert is_within_root('/a', 'b/c') is True",
        "assert is_within_root('/a', 'x') is True",
        "assert is_within_root('/a', '../etc') is False",
        "assert is_within_root('/a', '') is False",
        "assert is_within_root('/a', None) is False",
     ]},
]
