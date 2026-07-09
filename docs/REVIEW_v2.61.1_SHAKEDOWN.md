# Lathe v2.61.1 — Independent Terminal Shakedown

*Independent review + live CLI testing of v2.61.1 (up from v2.18.0 — 43 releases). Every capability driven
through the real `lathe` terminal, with Claude serving BOTH roles: analyst = opus (`:8787`), implementer =
sonnet (`:8089`), via the shipped `claude_proxy.py`. No unit-test shortcuts — the CLI was exercised as a user
would, and every finding is reproduced live.*

## Verdict: the harness genuinely evolved — and mostly well

At v2.18 Lathe built pure functions from specs. At v2.61.1 it is a materially bigger system:
**goal → interview → per-goal workspace → gated build (incl. real browser/functional gates) → auto-repair →
reported/pinned.** The standing regression suite grew 10 → 26 checks. The new discipline (input-first
interview, the Advocate veto, honest INOPERATIVE handling) is a real advance on the project's core thesis:
*don't build the wrong thing, and never lie about the result.*

## What I verified WORKING (live)

| Capability | Evidence |
|---|---|
| `lathe do "<goal>"` | Clean per-goal workspace (`GOAL.md`, `PROJECT.md`, `RUN_REPORT.md`, `BUILD_TRACE.md`, plan, module, pins). Analyst expanded a 1-function goal into a coherent 3-function module, gated green. |
| INPUT-FIRST interview | Intake persona panel (prompt-architect, correctness-reviewer, architect, c4-code) surfaced 6 assumptions (2 HIGH), then **refused to build** non-interactively rather than guess. |
| THE ADVOCATE | Standing sponsor persona **vetoed** a build for empty discovery and held it; over{ridable via `LATHE_ADVOCATE=off`. |
| Web/browser lane | After wiring Chromium, `do` built a real `digital-clock.html` gated by `structural(8)+functional:web_page` — an actual browser-executed gate. Green. |
| Reproducibility | `verify` rebuilt with **3/3 pins reused**, byte-stable. |
| Build-path manifest | Full contributors, models+endpoints, and **measured** tokens (16,233), `all_calls_attributed: true`. (This fixes a v2.18 finding.) |
| Honest INOPERATIVE | Browser gate unavailable → refused to blame the spec or fake a repair. Correct tri-state behavior. |
| `selftest` | 11/11 capabilities confirmed. |
| Read-only CLI | status / plans / metrics / dups / board / whatis / waiting / issues all work. |

## Bugs found

| # | Sev | Bug | Location / evidence |
|---|---|---|---|
| **1** | **HIGH** | `WORKSPACE_ROOT` defaults to the Windows path `C:/lathe-workspaces`; on Linux that is *relative*, so `do` creates a junk `./C:/` directory **inside the repo** — the exact "stray files in the tree" failure the stale-gate exists to stop. The identical bug was **already fixed** for `_issues_dir()` (line 1463); the workspace root was missed. | `lathe.py:63`; verified `./C:` created |
| **2** | MED | `--assume` is advertised as "build on the recorded defaults" but **skips intake entirely** (`assumptions=[]`); `GOAL.md` then falsely says "none surfaced — the goal was specific." Skipped ≠ none-found — violates the harness's own stated discipline (`lathe.py:2014`). Result: a happy-path `fib` with no validation; `fib(-5)==0` silently. | `lathe.py:662,718,746` |
| **3** | LOW | `lathe status` prints a **PowerShell** hint (`$env:LATHE_STRICT=1`) labeled "this shell" while on bash. Same Windows-origin class as #1. | `lathe status` output |
| **4** | MED | `lathe review` manifest under-reports: `selection.personas: []`, `contributors: 0`, `usage.calls/tokens: 0` despite real persona analyst calls. The **build path** attribution was fixed in v2.61 but the **review path** was not — inconsistent instrumentation. | `docs/ce/<run>.manifest.json` for a `review auto` run |
| **5** | **HIGH** | `lathe build <plan>` no longer emits the `METRICS_JSON` block to stdout — the workflow spine wrapper (build → trace → YOU checkpoint) swallows it. `engine_v2.py <plan>` still emits it (count 1); `lathe build` emits 0. This **breaks the repo's OWN CI** ("Reproducibility" step greps `lathe build` output for `METRICS_JSON`), so `verify` is RED on `main` itself — and any tooling that parses build metrics from the CLI is broken. Reproduced on a checkout byte-identical to `origin/main` (engine/examples/ci.yml unchanged by this PR). | `engine_v2.py` emits vs `lathe build` drops; CI run 29049703286 |

### Observations (not bugs)
- **UX:** the non-interactive refusal advises `--assume`, but `--assume` alone is then blocked by the Advocate — you also need `LATHE_ADVOCATE=off`. Two gates, one mentioned.
- **Over-caution:** the Advocate vetoes even a trivial `fib()` for "empty discovery." Defensible (input-first) but heavy for helper-class goals.
- **Portability:** `vision_judge.py:32` hardcodes `p.chromium.launch()` with no `executable_path`/env override — a pre-provisioned browser at a non-default path can't be used.
- **Shipped state:** `lathe board` shows 8 tasks (M02–M09) stuck/escalated "no progress for 3 turns."
- **Docs:** `lathe flow` still works but is absent from the top-level `lathe` help.
- **Cross-validation:** `lathe review` independently caught the same negative-`n` gap as bug #2 — the review skill works.

## Method note
Reproducibility of these findings requires the two Claude proxies (analyst `:8787`, implementer `:8089`) and,
for the web lane, a Chromium reachable at Playwright's default path. All builds ran with
`LATHE_WORKSPACE_ROOT` pointed outside the repo to avoid bug #1's contamination.
