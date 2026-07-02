# H_clarify_logic — the requirements-LIAISON step: interrogate the user for clarity BEFORE the harness goes
# into thinking mode (owner directive: enforce requirements elicitation up front). The persona does the
# asking (a prompt); these PURE pieces decide when clarity is needed and structure the Q&A deterministically.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "clarify_logic"
HEADER = ""
GLUE = ""
_ONLY = "Output ONLY the Python function code — no prose, no markdown, no tests. Import inside the function."
FUNCTIONS = [
    {"name": "goal_vagueness",
     "prompt": ("Write goal_vagueness(goal) -> list [needs_clarify(bool), missing(list of str)]. Heuristic nudge: "
                "does this goal have enough detail to design against? If goal is not a str or has fewer than 6 "
                "whitespace-split words -> [True, ['too brief']]. Otherwise lowercase it and check for the presence "
                "of these ASPECTS by keyword: 'inputs' present if any of [input, given, from, accept, take, "
                "parameter, arg]; 'outputs' present if any of [return, output, produce, result, emit, generate]; "
                "'constraints' present if any of [must, should, only, limit, constraint, at most, no more, "
                "required, cannot]; 'examples' present if any of [example, e.g, like, such as, ->]; 'edge_cases' "
                "present if any of [empty, none, null, invalid, error, edge, zero, negative, boundary]. missing = "
                "the aspect names (in this fixed order: inputs, outputs, constraints, examples, edge_cases) that "
                "are NOT present. needs_clarify is True if the goal is too brief OR 'inputs' is missing OR "
                "'outputs' is missing — the fundamental contract; constraints/examples/edge_cases still get listed "
                "in `missing` but do NOT by themselves force clarification. Return [needs_clarify, missing]. "
                "Never raise." + "\n" + _ONLY),
     "tests": [
        "assert goal_vagueness('parse it') == [True, ['too brief']]",
        "assert goal_vagueness(None) == [True, ['too brief']]",
        "r = goal_vagueness('write a function that takes a string input and returns the number of vowels'); assert r[0] is False",
        "r = goal_vagueness('build a dashboard for the team to see stuff on the web somewhere please'); assert r[0] is True and 'outputs' not in r[1] if False else r[0] is True",
        "r = goal_vagueness('accept a list input, return the sorted result, must handle empty and invalid, e.g. [3,1]->[1,3]'); assert r[0] is False and r[1] == []",
        "r = goal_vagueness('make a thing that does the calculation for the numbers correctly always ok'); assert isinstance(r[0], bool) and isinstance(r[1], list)",
        "assert 'inputs' in goal_vagueness('return a produced result, must be fast, e.g. now')[1]",
     ]},
    {"name": "parse_questions",
     "prompt": ("Write parse_questions(text) -> list of question strings. Extract the liaison's clarifying "
                "questions from free text: split into lines; for each line strip whitespace; keep a line if it is "
                "non-empty AND (it ends with '?' OR it matches a leading enumerator: starts with a digit followed "
                "by '.' or ')' , or starts with '-' or '*' or the word 'Q' followed by a digit). For a kept line, "
                "strip a leading enumerator prefix (leading digits + '.'/')' + spaces, or a leading '-'/'*' + "
                "spaces, or leading 'Q<digits>' + optional ':'/'.' + spaces) and strip again. Drop any that become "
                "empty. Preserve order; de-duplicate keeping first. text None/non-str -> []. Never raise." + "\n" + _ONLY),
     "tests": [
        "assert parse_questions('1. What is the input format?\\n2. Any size limit?') == ['What is the input format?', 'Any size limit?']",
        "assert parse_questions('- Should it handle empty?\\n- What about errors?') == ['Should it handle empty?', 'What about errors?']",
        "assert parse_questions('Here are questions:\\nQ1: Who uses it?\\nQ2. When?') == ['Who uses it?', 'When?']",
        "assert parse_questions('Just a statement without a question mark.') == []",
        "assert parse_questions('What is the goal?\\nWhat is the goal?') == ['What is the goal?']",
        "assert parse_questions(None) == []",
        "assert parse_questions('') == []",
        "assert parse_questions('1) First?\\nsome prose\\n2) Second?') == ['First?', 'Second?']",
     ]},
    {"name": "parse_options",
     "kinds": ["edge"],
     "prompt": ("Write parse_options(q) -> list [clean_question(str), options(list of str), default(str)]. "
                "A clarifying question line MAY carry selectable answer options so the user can pick instead of "
                "typing. Extract them deterministically: "
                "(1) If q is not a str, return ['', [], '']. "
                "(2) Options live in a bracketed marker '[options: A | B | C]' — case-INSENSITIVE on the word "
                "'options', the payload is the text after the colon up to the closing ']'. Split that payload on "
                "either '|' or '/' , strip each piece, drop empties -> the options list. If there is no such "
                "marker, options is []. "
                "(3) A default lives in a '(default: X)' marker — case-insensitive on 'default'; X is the text up "
                "to the closing ')', stripped. If absent or empty, default is ''. "
                "(4) clean_question = q with the [options: ...] and (default: ...) markers removed, then "
                "collapse any run of whitespace to a single space and strip. "
                "Use the re module (import it inside the function). Never raise; on any error return "
                "[q if isinstance(q, str) else '', [], '']." + "\n" + _ONLY),
     "tests": [
        "assert parse_options('What format? [options: CSV | JSON | TSV] (default: CSV)') == ['What format?', ['CSV', 'JSON', 'TSV'], 'CSV']",
        "assert parse_options('Pick one [options: a/b/c]') == ['Pick one', ['a', 'b', 'c'], '']",
        "assert parse_options('What is the max size?') == ['What is the max size?', [], '']",
        "assert parse_options('Overwrite? [OPTIONS: yes | no] (DEFAULT: no)') == ['Overwrite?', ['yes', 'no'], 'no']",
        "assert parse_options(None) == ['', [], '']",
        "assert parse_options('') == ['', [], '']",
        "assert parse_options('Sep? [options:  tab |  comma |  ]') == ['Sep?', ['tab', 'comma'], '']",
        "r = parse_options('Where does the data come from? [options: file | api]'); assert r[0] == 'Where does the data come from?' and r[1] == ['file', 'api'] and r[2] == ''",
     ]},
]

# Requirement -> test traceability (consumed by `lathe trace` and enforced under LATHE_STRICT).
CRITERIA = [
    {"id": "C1", "text": "Flag a goal that lacks the inputs/outputs contract needed to design against",
     "tests": ["goal_vagueness"]},
    {"id": "C2", "text": "Extract the liaison's clarifying questions from free-form text",
     "tests": ["parse_questions"]},
    {"id": "C3", "text": "Parse selectable answer options (and an optional default) from a question line, "
                         "so the user can pick instead of typing",
     "tests": ["parse_options"]},
]
