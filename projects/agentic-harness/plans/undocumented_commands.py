OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "undocumented_commands"
HEADER = ""
GLUE = ""
FUNCTIONS = [
    {
        "name": "undocumented_commands",
        "prompt": (
            "Write undocumented_commands(names, doc_text). The FIRST line inside the function body must be "
            "`import re`. Steps IN ORDER: "
            "Step 1: if not names, return [] immediately (handles None and empty). "
            "Step 2: if not isinstance(doc_text, str), set doc_text = ''. "
            "Step 3: a name is DOCUMENTED only if it appears as a WHOLE WORD in doc_text — NOT merely a "
            "substring (so 'do' must not be considered documented by the word 'done' or 'window', and 'ack' "
            "must not be satisfied by 'acknowledge'). Test this with re.search(r'(?<![A-Za-z0-9_])' + "
            "re.escape(name) + r'(?![A-Za-z0-9_])', doc_text) — the negative-lookbehind/lookahead ensure the "
            "match is not flanked by word characters, and it works for hyphenated names like 'lint-spec'. "
            "Build the list of each name in names WHERE isinstance(name, str) AND that search does NOT match "
            "(i.e. undocumented). "
            "Step 4: return sorted(that list). Purpose: report which CLI command names are missing from the "
            "docs. Never raise. Output ONLY the Python function code - no prose, no markdown."
        ),
        "tests": [
            "assert undocumented_commands(['build', 'logs'], 'run `lathe build` then `lathe logs`') == []",
            "assert undocumented_commands(['build', 'xyz'], 'only build is here') == ['xyz']",
            "assert undocumented_commands([], 'anything') == []",
            "assert undocumented_commands(None, 'x') == []",
            "assert undocumented_commands(['a'], None) == ['a']",
            "assert undocumented_commands(['lint-spec', 'logs'], '`lathe lint-spec` and `lathe logs`') == []",
            "assert undocumented_commands(['a', 'b', 'c'], '') == ['a', 'b', 'c']",
            "assert undocumented_commands(['do'], 'See the window. We are done.') == ['do']",
            "assert undocumented_commands(['ack'], 'You must acknowledge the tests.') == ['ack']",
            "assert undocumented_commands(['do'], 'run `lathe do` now') == []",
            "assert undocumented_commands(['selftest'], 'nothing here') == ['selftest']",
        ],
    }
]

CRITERIA = [
    {"id": "D1", "text": "A command counts as documented only as a whole word, not a substring of another word",
     "tests": ["undocumented_commands"]},
]
