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
            "it as 8. Put `import re` as the FIRST line INSIDE the function body. "
            "Output ONLY the Python function code - no prose, no markdown."
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
        "name": "short_goal",
        "prompt": (
            "Write a pure Python function short_goal(goal, max_words=4, max_len=24) that abbreviates a "
            "free-text build goal into a short meaningful slug. Steps, in order: "
            "(1) if goal is None or not a string or blank, return 'goal'; "
            "(2) lowercase it and split into words on every non-alphanumeric character; "
            "(3) drop every word in this stopword set: a, an, the, with, using, for, of, in, on, to, and, "
            "or, that, this, which, single, file, page, html, web, website, webpage, app, application, "
            "simple, complete, basic, small, tiny, create, build, make, implement, write, shows, shown, "
            "show, display, displayed, style, styled, retro, classic; "
            "(4) also drop empty strings and words shorter than 2 characters; "
            "(5) keep the FIRST max_words remaining words, join with '-'; "
            "(6) if the result is longer than max_len, cut it at max_len and then, if that cut landed in "
            "the middle of a word, drop the partial word by cutting at the LAST '-' within the limit; "
            "strip any trailing '-'; "
            "(7) if the result is empty, return 'goal'. "
            "Worked example: short_goal(\"single-file HTML page with Conway's Game of Life on a canvas: "
            "40x30 grid...\") -> 'conway-game-life-canvas'. "
            "Output ONLY the Python function code - no prose, no markdown."
        ),
        "tests": [
            "assert short_goal(\"single-file HTML page with Conway's Game of Life on a canvas\") == 'conway-game-life-canvas'",
            "assert short_goal('single-file HTML page with a complete Tetris game on a canvas: 10x20 grid') == 'tetris-game-canvas-10x20'",
            "assert short_goal('a small html page with a color picker') == 'color-picker'",
            "assert short_goal('a color picker that shows the chosen color name') == 'color-picker-chosen'",
            "assert short_goal(None) == 'goal'",
            "assert short_goal('the a an with') == 'goal'",
            "assert short_goal('bouncing ball animation on a canvas, ball speed shown', 3) == 'bouncing-ball-animation'",
            "assert len(short_goal('x' * 100)) <= 24",
        ],
    },
    {
        "name": "model_abbrev",
        "prompt": (
            "Write a pure Python function model_abbrev(model) that abbreviates an implementer model string "
            "for use in a folder name. Rules, in order (case-insensitive matching, lowercase output): "
            "(1) if model is None or not a string or blank, return 'model'; "
            "(2) if it contains one of these known names, return that name: fable, claude, sonnet, opus, "
            "haiku, gpt, gemini; "
            "(3) else look for a parameter-size token with the regex r'(\\d+(?:\\.\\d+)?)\\s*[bB]\\b' and if "
            "found return it as lowercase digits+'b' with any '.0' kept as-is (e.g. '9b', '35b', '7.5b'); "
            "(4) else if the string contains ':' take the part after the LAST ':'; "
            "(5) finally: keep only a-z0-9 characters of what remains and return the first 8 of them, or "
            "'model' if that is empty. Put `import re` as the FIRST line INSIDE the function body. "
            "Worked examples: model_abbrev('openai:fable') -> 'fable'; model_abbrev('ornith-1.0-9b-Q4_K_M') "
            "-> '9b'; model_abbrev('openai:local') -> 'local'. "
            "Output ONLY the Python function code - no prose, no markdown."
        ),
        "tests": [
            "assert model_abbrev('openai:fable') == 'fable'",
            "assert model_abbrev('ornith-1.0-9b-Q4_K_M.gguf') == '9b'",
            "assert model_abbrev('openai:local') == 'local'",
            "assert model_abbrev('claude') == 'claude'",
            "assert model_abbrev('qwen-35B-instruct') == '35b'",
            "assert model_abbrev(None) == 'model'",
            "assert model_abbrev('GPT-5') == 'gpt'",
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
