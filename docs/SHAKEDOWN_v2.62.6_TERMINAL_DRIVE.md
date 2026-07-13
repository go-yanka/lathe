# Lathe — Live Terminal Shakedown (v2.62.6)

**Method:** drove the real `lathe` CLI as a human operator (no direct API), building actual projects, while
tailing the **Reporter** (run manifests + run logs) in real time. Model endpoints were the harness's own
`claude_proxy.py` shimming over the `claude` CLI — analyst = sonnet (`:8787`), implementer = **haiku**
(`:8089`, the authentic "cheap builder," to stress the gates + repair loop). Every claim below is backed by a
real command, its captured output, or a sealed manifest.

---

## Q: Can the Reporter be read in real time? — YES.

The Reporter has three surfaces, and the source-of-truth manifest is tamper-evident:

| Surface | What | When |
|---|---|---|
| `projects/runs/<id>.jsonl` | per-**stage** engine events (start, model_call, result, gate…) | **live, appended during the run** |
| `docs/ce/<id>.manifest.{json,md}` | the sealed record: intake, front_end, persona selection, contributors, gate verdicts, **per-role token usage**, timing, outcome, `integrity.manifest_sha256` | finalized when the command ends (`dispatcher.finalize`) |
| `lathe status` / `lathe metrics` | board + endpoint health; last-N run rollups | on demand |

A poll-based watcher (no `inotifywait` in this env) tailing both dirs streamed live stages and each sealed
manifest as it landed — e.g. `★ [MANIFEST … cmd=build outcome=pass gates_pass=True tokens=0 sha=c5182fc7…]`.
**Recommendation for a first-class "live truth" feature:** a `lathe watch` / `lathe status --follow` that tails
`projects/runs/<current>.jsonl` and prints the manifest summary on finalize. The data is all there; only a
built-in tail is missing.

---

## What worked (confirmed live)

- **Determinism / content-hash pins.** `tokenize` built once, then **reused from its pin** on later builds;
  a full rebuild reused all three functions at **`tok_total: 0`** (`by_pinned: 3/3`, integration re-run only).
- **Retry / best-of-N.** haiku genuinely fought the hard functions and **passed `to_rpn` and `eval_rpn` on the
  3rd try each** (6 implementer calls, ~21K tokens, ~4 min) — the loop works on a weak model.
- **Mutation-score gate.** Ran on the accepted code and **excluded 6 provably-equivalent mutants** from the
  score — the honest-mutation behavior, live.
- **Fails closed, no false green.** When integration failed, `build_ok:false` and **no partial module shipped**.
- **Per-role token accounting.** The manifest split cost cleanly: analyst (sonnet) vs implementer (haiku).
- **The Advocate guarded intent** (see F2) and **the OUT_DIR guard** refused an out-of-sanctioned path (F6) —
  both correct.
- **Deliverable:** a real, complex, fully-gated `calc` evaluator (`tokenize → to_rpn → eval_rpn → evaluate()`),
  built through the harness on a cheap model and verified correct end-to-end.

---

## Findings (ranked)

### F1 · HIGH · bug — INTEGRATION is un-buildable through the validated path (catch-22)
The engine writes the INTEGRATION script **verbatim** and runs it standalone in `OUT_DIR`
(`engine_v2.py:1632` writes `marker + INTEGRATION`; `:1638` runs `python _itest_<mod>.py`, cwd=OUT_DIR). Its
own docstring (`:9`) says INTEGRATION is *"a python script that `import game` and asserts."* **But the plan
validator bans every `import`** in the plan.
Reproduced with `is_valid_plan`:
```
from calc import *   -> ok=False  "INTEGRATION contains a disallowed operation (dunder/import/danger)"
import calc          -> ok=False  (same)
no import            -> ok=True   → then the itest raises NameError: name 'evaluate' is not defined
```
So a plan with **GLUE + a real INTEGRATION test that references the GLUE symbol cannot build** without
`LATHE_TRUST_PLAN=1` (which disables the whole validator — a security downgrade). It is **worse under STRICT**,
where `LATHE_GATE_GLUE=1` *requires* an INTEGRATION test for substantive GLUE — a hard deadlock.
**Fix:** the engine should auto-prepend `from <MODULE_NAME> import *\n` to the itest (the module is already in
OUT_DIR), or the validator should whitelist `import <MODULE_NAME>` inside INTEGRATION. Also: the per-function
`tests` run *with the functions already in scope* while INTEGRATION runs *standalone* — that inconsistency is
the trap; document or unify it.

### F2 · HIGH · meta — `lathe do` scope-collapse ships "gated-green" without building the goal
`lathe do "…full safe arithmetic evaluator, tokenizer + recursive-descent parser, evaluate()…"` (focus:helper)
silently redrafted the goal into a module `expr_str_helpers` with **three trivial string helpers**
(`is_balanced_parens`, `contains_unknown_char`, `strip_expr_whitespace`), built them, and announced
**"DONE — 1 module built gated-green."** `evaluate()` was **never built**; the Reporter sealed `outcome:pass`.
The **Advocate is the guard designed to catch exactly this** — but it is the same guard that vetoes
non-interactive runs (F5), so overriding it to make autonomy work removes the under-delivery check. **The gates
verify the drafted spec, never the goal-vs-deliverable gap.** (Consistent with the earlier "gated-green ≠
bug-free/goal-met" meta-finding.)

### F3 · MED · bug — `claude_proxy` defaults `CLAUDE_BIN` to a Windows path
`claude_proxy.py:35` defaults `CLAUDE_BIN` to `%APPDATA%\npm\claude.cmd`. `/health` still returns `ok` (it just
echoes the configured path), so it *looks* up — but every real completion fails on Linux/macOS. Blocks
first-run out-of-the-box off Windows. (Same as audit finding C5, now reproduced live.) **Fix:** resolve from
`PATH` (`shutil.which("claude")`) when the default isn't executable.

### F4 · MED · friction — test-kind gate false-refuses real edge tests, and dead-ends the repair loop
With `LATHE_TEST_KIND=1` and functions declaring `kinds:["edge","error"]`, `to_rpn`/`eval_rpn` were **refused
pre-generation** — "missing required test kind: 'edge'" — even though their tests are full of genuine edge cases
(mismatched parens, right-associative `**`, div-by-zero). The kind detector is a **substring heuristic** (the
capability doc admits this) and didn't recognize them. Worse: because the refusal is **pre-generation**
(`tries:0`), **no failure evidence is banked**, so the auto-repair loop (the Healer) **skips** ("no banked
failures"). A gate-config refusal is a dead end, not a self-healing one. **Fix:** either strengthen kind
detection, or when a *kind* gate refuses, emit actionable guidance (it currently reads like a build failure).

### F5 · MED · friction (by design) — the Advocate blocks non-interactive `do --assume`
`lathe do "<spec>" --assume` non-interactively → **VETOED by the Advocate at 'discovery'** (*"No discovery
answers were captured… no sponsor context behind it"*) → run ends **HELD, not DONE**, exit 1. The Reporter
sealed it `outcome:refuse, refused:true`. Correct behavior, but it means **autonomous single-goal runs require
`LATHE_ADVOCATE=off`** or fed discovery — worth surfacing in the `do` refusal hint (it does mention the
overrule).

### F6 · LOW · correct-but-worth-noting — OUT_DIR guard
A plan whose `OUT_DIR` is outside the repo tree **and** outside the sanctioned workspace root is refused
("OUT_DIR escapes … set LATHE_TRUST_PLAN=1 to override"). Correct security (a plan can't write anywhere); noted
because it's a friction point for scratch builds. Building under `~/.lathe/workspaces/…` is the sanctioned path.

---

## Reproduction log (representative)

| Run | Command | Reporter outcome | Note |
|---|---|---|---|
| do #1 | `lathe do "…evaluator…" --assume` | `refuse` (Advocate veto, HELD) | F5 |
| do #2 | same, `LATHE_ADVOCATE=off` | `pass` — but built 3 trivial helpers | **F2** |
| build #1 | `lathe build calc.py` (scratch OUT_DIR) | `refuse` (OUT_DIR escape) | F6 |
| build #2 | sanctioned OUT_DIR, `TEST_KIND=1` | `refuse` (to_rpn/eval_rpn: missing 'edge', tries=0) | **F4** |
| build #3 | kinds removed, `MUTATION_SCORE=0.5` | 3/3 fns PASS (3 tries each), **integration FAIL** (NameError) | **F1** |
| build #4 | INTEGRATION `+import` | `refuse` (validator bans import) | **F1** |
| build #5 | `LATHE_TRUST_PLAN=1` | **`pass`** — pins reused 3/3, tok 0, integration PASS, build_ok:True | green |

---

## On the "10–15 files" goal

The shakedown revealed *why* that isn't a one-liner: `lathe do` collapses complex goals to helpers (F2), and
the hand-authored multi-function path hits the INTEGRATION catch-22 (F1). Both are findings, not just
obstacles — so this pass prioritized **depth (real issues) over file count**. The `calc` module is one
complete, fully-gated build; the same pattern (author plan → `lathe build` under `LATHE_TRUST_PLAN=1`) extends
to the rest of the toolkit on request.

---

## Enhancement proposals (from the shakedown)

### E1 · Requirements liaison should ask the "project framing" questions no AI bothers to ask
`lathe clarify` today asks the *functional* questions — inputs, outputs, success criteria, edge cases,
non-goals. It never asks the **framing** questions that most determine the architecture and what "done" means.
Almost no AI coding tool asks these, and it's a big part of why a complex goal collapsed to trivial helpers
(F2). Add a short framing round to the interview (fewest sharp questions, pick-from options, skip allowed;
answers → `CLARIFIED_GOAL.md`):

1. **Purpose / motive** — personal · learning · prototype · internal tool · OSS library · SaaS/product · client deliverable
2. **Who will use it** — just me · my team · external end-users · other developers/an API consumer · the public
3. **Scope / ambition** — quick script · MVP · production-ready · long-lived system (+ rough size)
4. **Deliverable format** — CLI · library/package · web app · REST/GraphQL API · desktop/mobile · notebook/report · data pipeline · config/infra
5. **Tech stack per component** — existing preferences (language, framework, datastore, frontend, auth, key libs), asked per component when there's more than one
6. **Hosting / deployment** — local · Docker · a PaaS (Vercel/Fly/Render) · a cloud (AWS/GCP) · self-hosted · app store · npm/PyPI

**How it composes:** it shapes the analyst's spec (a parser for *learning* vs. a *SaaS component* are different
builds); it feeds the **Advocate a real charter** so it can stay on for non-interactive runs and actually catch
scope-collapse (F2) instead of being disabled; and it pre-answers many **assumption-gate** blockers
(persistence, auth, deploy target). Extending "no silent guessing" from I/O ambiguity to *project framing* is
the differentiator users notice. *(To be filed as a standalone enhancement issue once the GitHub connector is
re-authorized.)*
