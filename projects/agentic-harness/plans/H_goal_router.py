# Goal routing for `lathe do` (per-goal workspaces + web-goal detection). Pure logic, harness-built.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "goal_router"
HEADER = ""
GLUE = ""
FUNCTIONS = [
    {
        "name": "slugify_goal",
        "prompt": (
            "Write a pure Python function slugify_goal(goal, max_len=40) that turns a free-text goal into a "
            "filesystem-safe folder slug. Rules: if goal is None or not a string or empty/whitespace-only, "
            "return 'goal'. Lowercase the text. Replace every run of characters that are not a-z or 0-9 with "
            "a single hyphen. Strip leading/trailing hyphens. Truncate to max_len characters, then strip any "
            "trailing hyphen again. If the result is empty, return 'goal'. If max_len is None or < 8, treat "
            "it as 8. Output ONLY the Python function code - no prose, no markdown."
        ),
        "tests": [
            "assert slugify_goal('single-file HTML page with a simple retro shooting game') == 'single-file-html-page-with-a-simple-retr'",
            "assert slugify_goal('Build a REST API!!') == 'build-a-rest-api'",
            "assert slugify_goal(None) == 'goal'",
            "assert slugify_goal('   ') == 'goal'",
            "assert slugify_goal('###') == 'goal'",
            "assert slugify_goal('CSV parser', 8) == 'csv-pars'",
            "assert slugify_goal('a b', 3) == 'a-b'",
        ],
    },
    {
        "name": "pick_focus",
        "prompt": (
            "Write a pure Python function pick_focus(goal) that classifies a free-text build goal into a "
            "planner focus string. Return 'webapp' when the goal is about a browser deliverable: it mentions "
            "any of these words (case-insensitive, as whole words): html, webpage, web, website, page, ui, "
            "frontend, browser, canvas, dashboard, game, app. BUT the words 'api', 'cli', 'function', "
            "'module', 'library', 'script', 'parser' do NOT make it a webapp by themselves. If goal is None "
            "or not a string, return 'helper'. Otherwise return 'helper'. Use a word-boundary regex, not "
            "substring matching. IMPORTANT: put `import re` as the FIRST line INSIDE the function body. "
            "Worked example: pick_focus('simple UI for notes') -> 'webapp' because 'ui' appears as a whole "
            "word. Output ONLY the Python function code - no prose, no markdown."
        ),
        "tests": [
            "assert pick_focus('single-file HTML page with a retro shooting game') == 'webapp'",
            "assert pick_focus('a csv parsing function') == 'helper'",
            "assert pick_focus('build a browser dashboard for metrics') == 'webapp'",
            "assert pick_focus(None) == 'helper'",
            "assert pick_focus('REST api endpoint for users') == 'helper'",
            "assert pick_focus('simple UI for notes') == 'webapp'",
            "assert pick_focus('shipment ETA calculator module') == 'helper'",
            "assert pick_focus('snake GAME in the browser') == 'webapp'",
        ],
    },
    {
        "name": "workspace_rel",
        "prompt": (
            "Write a pure Python function workspace_rel(slug, stamp) that returns the string "
            "'goals/' + slug + '_' + stamp. Sanitize slug and stamp EXACTLY like this, in order: "
            "(1) if the value is None or empty, use the fallback ('goal' for slug, 'run' for stamp); "
            "(2) REMOVE every '/', '\\\\' and '.' character from the value: "
            "cleaned = value.replace('/','').replace('\\\\','').replace('.',''); "
            "(3) if cleaned is empty after removal, use the fallback again. "
            "Worked examples: workspace_rel('ok.name','s') -> 'goals/okname_s' (dot removed, letters kept); "
            "workspace_rel('../evil','a') -> 'goals/evil_a'; workspace_rel('..','..') -> 'goals/goal_run'. "
            "Output ONLY the Python function code - no prose, no markdown."
        ),
        "tests": [
            "assert workspace_rel('shooter-game', '20260707') == 'goals/shooter-game_20260707'",
            "assert workspace_rel(None, '20260707') == 'goals/goal_20260707'",
            "assert workspace_rel('x', None) == 'goals/x_run'",
            "assert workspace_rel('../evil', 'a') == 'goals/evil_a'",
            "assert workspace_rel('..', '..') == 'goals/goal_run'",
            "assert workspace_rel('ok.name', 's') == 'goals/okname_s'",
        ],
    },
]
