# How it works — the plan format and the build loop, from real artifacts

This is the core of Lathe: the `plan.py` format, how a human/analyst (here, Claude) spells out the design
and expectations per function, and how the engine turns that into gated, pinned, delivered code. Every
example below is taken from the real plans that built a working app (a job-search agent) — not a
toy.

---

## 1. A plan is a file. The tests are the executable spec.

A plan declares a module: where it goes, what it imports, and a list of **functions**, each with a
natural-language **design** (the prompt) and a set of **tests** (the contract). Real excerpt:

```python
# plans/01_scoring_primitives.py
OUT_DIR     = r"...\agent"
MODULE_NAME = "scoring_primitives"
HEADER      = "import re"

# A discipline suffix appended to every prompt — keeps the model from adding prose/tests.
_ONLY = ("Output ONLY the Python function code — no prose, no markdown, no tests. "
         "Import any module you need INSIDE the function. Define any constants INSIDE the function.")

FUNCTIONS = [
    {
        "name": "_is_standalone_word",
        "prompt": "Implement _is_standalone_word(word, text) -> bool.\n"
                  "Return True if `word` occurs as a standalone whole word inside `text`, else False.\n"
                  "ALGORITHM: import re; pattern = r'\\b' + re.escape(word) + r'\\b'; "
                  "return bool(re.search(pattern, text)).\n" + _ONLY,
        "tests": [
            "assert _is_standalone_word('director','associate director') == True",
            "assert _is_standalone_word('analyst','data analytics') == False",
            "assert _is_standalone_word('vp','vp, strategy') == True",
        ],
    },
]
```

The **prompt is the design and expectations**; the **tests are the acceptance contract**. The unit is a
single function — small enough for a local model to implement reliably, and gated by an exact test.

## 2. How the analyst spells out the design — two registers

The analyst chooses how tightly to pin a function, by how the prompt is written:

**(a) Describe the algorithm** — let the model write the code. Used when the behavior is simple and the
tests fully constrain it (the `_is_standalone_word` example above). The prompt states the contract and the
approach; the model fills in.

**(b) Verbatim spec** — give the exact code, for functions that are critical, fiddly, or that a small
model keeps getting subtly wrong. Real excerpt:

```python
{
    "name": "_get_label",
    "prompt": "Return EXACTLY this function verbatim:\n"
              "def _get_label(score, thresholds=None):\n"
              "    t = thresholds or {}\n"
              "    urgent = t.get('URGENT', 85)\n"
              "    ...\n"
              "    if score >= urgent:\n"
              "        return 'URGENT'\n"
              "    ...\n" + _ONLY,
    "tests": [
        "assert _get_label(90)=='URGENT' and _get_label(85)=='URGENT'",
        "assert _get_label(60, {'URGENT':90,'STRONG':55})=='STRONG'",
    ],
},
```

This is the dial that makes a *cheap local model* reliable: when it flakes on a function, the analyst
moves that one function from register (a) to a more prescriptive (a), or all the way to (b) — **without
escalating to a bigger model.** The fix lives in the plan, and the function is pinned once it passes.

## 3. Hand-authored wiring (GLUE) + a whole-module test (INTEGRATION)

Not everything is generated. `GLUE` is analyst-authored orchestration appended verbatim; `INTEGRATION`
asserts the assembled module works as a whole. Real excerpt (the onboarding module):

```python
# plans/17_onboarding.py
GLUE = '''
def onboard(resume_text):
    raw = ai.ai_complete(build_resume_prompt(resume_text))     # call the LLM via a generated skill
    profile = parse_resume_profile(raw)                        # generated function
    asp = parse_aspiration_map(raw)                            # generated function
    if not asp.get("seniority", {}).get("proven"):
        asp = seed_aspiration_map(profile)                     # deterministic fallback (generated)
    return {"profile": profile, "aspirations": asp}
'''

INTEGRATION = '''
import onboarding as ob
assert ob.html_to_text('<p>Hi <b>there</b></p>') == 'Hi there'
assert ob.seed_aspiration_map({'seniority':'director'})['seniority']['aspire'][0]['value'] == 'VP'
print("ONBOARDING OK; contact + profile + aspiration map + seed fallback, all test-gated")
'''
```

The engine assembles the module as `HEADER + generated functions + GLUE`, then runs `INTEGRATION` as a
subprocess. Exit 0 = the module is accepted.

## 4. UI is generated and gated *behaviorally* — and the design is code

A UI page is an **artifact**: same spec→generate→gate shape, but the gate drives a real browser. The
design is injected from a shared module so the look is reproducible, not reinvented. Real shape (the
settings page):

```python
# plans/22_settings.py
from _design import DESIGN_CSS, DESIGN_RULES        # shared design system (tokens + layout contract)

_SPEC = DESIGN_RULES + "\n\n" + "<content + behaviour spec>" + "\n\nINCLUDE THIS <style> VERBATIM:\n" + DESIGN_CSS

_FUNC = '''<a Playwright script: serve the page, stub the APIs, click the controls,
            and assert the live DOM behaves — dimmed suggestions render, "Suggest more"
            calls the endpoint, the Save button PUTs the right payload>'''

ARTIFACTS = [{
    "path": "ui/settings.html",
    "model": "gemma4:12b-impl16k",      # the local 16K model generates the page
    "prompt": _SPEC,
    "tests": [ "assert content.strip().lower().startswith('<!doctype html')",
               "assert 'class=\"tiers\"' in content",        # the agreed 3-column layout
               "assert ':root' in content and '--indigo-600' in content" ],  # design tokens present
    "functional": _FUNC,                # the behavioral gate — must pass to ship
}]
```

A generated page is accepted only if it passes **both** the structural tests (design present) and the
behavioral browser test (it actually works). This is how "looks right" and "works right" are gated
separately.

## 5. Running the engine — generate, gate, pin, assemble, integrate

```bash
python engine.py plans/01_scoring_primitives.py gemma4:12b-impl 3
```

For each function the engine does exactly this:

1. **Pin check** — if a pin exists for `hash(name, prompt, tests, model)` and still passes its tests,
   reuse it (instant, reproducible). Otherwise:
2. **Generate** up to N candidates from the local model.
3. **Gate** — exec each candidate and run its tests. The first that passes is accepted.
4. **Pin** the accepted code (write it to `.pins.json`, the lockfile).
5. If no candidate passes in N tries: **stop. No escalation.** Save the failed candidates + the failing
   assertion to `_fails/`, and report: *"analyst: sharpen the spec."*

Then it assembles the module, writes it, and runs `INTEGRATION`. Output:

```
  [generated] _is_standalone_word
  [generated] _get_label
  [pinned   ] _location_match        <- reused from a prior run, identical
  ...
build: OK - reproducible (pinned) | integration: PASS :: SCORING OK
```

Re-run the same command and every function comes back `[pinned]` — the build is byte-identical.

## 6. How the product was actually delivered

The real app was built from **23 ordered plans** (`01_…` through `23_…`), run in sequence by a one-line
driver (`build_all`). Each plan produced a test-gated module; later plans built on earlier ones (the
numeric prefix is the dependency order). The full system — scoring engine, 47 job-source ingesters, the AI
match layer, the FastAPI server, and two model-generated UI pages — came out the far end as **23 plans →
all green → reproducible**, with:

- **86 per-function tests + 22 integration tests + 2 behavioral browser gates**, all passing.
- A real bug turned into a permanent regression test (a non-hermetic cache assertion).
- A design regression *caught by the gate*, then fixed by adding the design contract (§4).
- The bulk of the code generated by a **local 12B model on an 8 GB GPU**; Claude (the analyst) only ever
  wrote the plans — the design, the expectations, and the tests.

That is the whole method: **the analyst spells out intent as plans; the engine compiles intent into
gated, pinned, reproducible code; failures sharpen the plans.** The plan files are the product's true
source. The running app is a build output.
