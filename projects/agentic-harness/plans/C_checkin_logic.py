# C_checkin_logic — pure decision logic for `lathe checkin`: a GATED check-in that keeps the tree pristine
# locally AND on the remote (no relics, gates green, in sync). Authored THROUGH the harness (gated+pinned);
# lathe.py cmd_checkin wires the thin git/push I/O around it. Extends the cleanup/pristine model to the remote.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "checkin_logic"
HEADER = ""
GLUE = ""
_ONLY = "Output ONLY the Python function code — no prose, no markdown, no tests. Import inside the function."
FUNCTIONS = [
    {"name": "is_relic",
     "prompt": ("Write is_relic(path) -> bool. Return True if path (a string) is a leftover/relic that must never be "
                "checked in: its lowercased form contains '__pycache__', '/_fn_fails/', or ends with any of '.pyc', "
                "'.pyo', '.log', '.tmp', '.orig', '.bak', '.db-journal', '.rej'; OR its basename is 'run_report.md'. "
                "Otherwise False. None -> False. Never raise." + "\n" + _ONLY),
     "tests": [
        "assert is_relic('a/__pycache__/x.pyc') is True",
        "assert is_relic('build.log') is True",
        "assert is_relic('projects/harness.db-journal') is True",
        "assert is_relic('tools/_fn_fails/foo.py') is True",
        "assert is_relic('RUN_REPORT.md') is True",
        "assert is_relic('tools/foo.py') is False",
        "assert is_relic('README.md') is False",
        "assert is_relic(None) is False",
     ]},
    {"name": "checkin_blockers",
     "prompt": ("Write checkin_blockers(gate_green, behind, relics) -> list of strings, the reasons the tree is NOT "
                "ready to check in (empty list = ready). In order: if gate_green is falsy append 'gates not green'; "
                "if behind is a positive int append 'remote ahead by %d (pull first)' % behind; if relics is a "
                "non-empty list/collection append 'relics: %d' % len(relics). None args contribute no blocker. "
                "Never raise." + "\n" + _ONLY),
     "tests": [
        "assert checkin_blockers(True, 0, []) == []",
        "assert checkin_blockers(False, 0, []) == ['gates not green']",
        "assert checkin_blockers(True, 3, []) == ['remote ahead by 3 (pull first)']",
        "assert checkin_blockers(True, 0, ['a','b']) == ['relics: 2']",
        "assert checkin_blockers(False, 1, ['x']) == ['gates not green', 'remote ahead by 1 (pull first)', 'relics: 1']",
        "assert checkin_blockers(True, None, None) == []",
     ]},
]
