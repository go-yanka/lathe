# H_mcp_safe — pure input-safety for the MCP tool surface. HARDENED after the harness's own `review auto` found a
# CRITICAL (symlink traversal via abspath) + HIGH (reject_flags fails open on non-str) in the first cut. Fix-the-spec,
# rebuild. Authored THROUGH the harness (gated+pinned); lathe_mcp wires them in.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "mcp_safe"
HEADER = ""
GLUE = ""
_ONLY = "Output ONLY the Python function code — no prose, no markdown, no tests. Import inside the function."
FUNCTIONS = [
    {"name": "reject_flags",
     "prompt": ("Write reject_flags(s) -> list. FAIL CLOSED: if s is not a str (None, list, bytes, anything), return "
                "[False, []] — a non-string caller must NEVER be treated as 'no flags found'. Otherwise split s on "
                "whitespace into tokens (drop empties); return [ok, tokens] where ok is False if any token starts with "
                "'-' (a CLI flag — argument injection), else True. Never raise." + "\n" + _ONLY),
     "tests": [
        "assert reject_flags('a b') == [True, ['a', 'b']]",
        "assert reject_flags('--x y') == [False, ['--x', 'y']]",
        "assert reject_flags('') == [True, []]",
        "assert reject_flags(None) == [False, []]",
        "assert reject_flags(['--rm', '/']) == [False, []]",
        "assert reject_flags(b'x') == [False, []]",
     ]},
    {"name": "is_within_root",
     "prompt": ("Write is_within_root(root, path) -> bool. Return False if path is None or empty. Import os inside. "
                "If path is not absolute, os.path.join it onto root FIRST. Resolve BOTH root and the target with "
                "os.path.realpath (this resolves symlinks/junctions, closing traversal-via-symlink), then normalize "
                "both with os.path.normcase (case-insensitive filesystems). Return True only if "
                "os.path.commonpath([real_root, real_target]) == real_root (this handles drive/filesystem roots and "
                "trailing-separator pitfalls). On ANY error (e.g. ValueError for paths on different drives) return "
                "False. Never raise." + "\n" + _ONLY),
     "tests": [
        "assert is_within_root('/a', 'b/c') is True",
        "assert is_within_root('/a', 'x') is True",
        "assert is_within_root('/a', '../etc') is False",
        "assert is_within_root('/a', '') is False",
        "assert is_within_root('/a', None) is False",
     ]},
]
