# Lathe — Workflow Steps (canonical `lathe flow` dump)

*This edition is written **through the harness itself**: it is the verbatim output of `lathe flow <name>` for
every workflow the harness defines — the tool's own account of how it works, straight out of `tools/workflows.py`
via the `flow` command. No human editorializing was added; where a section is thin, that is exactly what the
harness emits. Generated at v2.18.0. Companion: `WORKFLOW_REFERENCE.md` (the hand-authored Fable edition) and
`WORKFLOW_REFERENCE_COMPARISON.md` (the diff).*

## How to read this
The harness prints, per workflow: the one-line description, a **contract** (`when` / `entry` / `deliverable` /
`done when`) for the six named workflows, and the ordered **steps** typed `[AUTO]` (a gated `lathe` subcommand)
/ `[GATE]` (a standing check) / `[YOU]` (a human checkpoint), each with the `lathe` command it runs. Run any of
them with `lathe flow <name> --run <targets>`.

---

## `lathe flow assumption-audit`

```
workflow: assumption-audit — Bare `lathe assume`: adversarial assumption audit -> committed decisions.

  1. [AUTO] Adversarial auditor -> materiality-ranked ledger -> resolutions  ->  lathe assume {args}

(dry view — add `--run <targets>` to execute the [AUTO]/[GATE] steps)

```

## `lathe flow autonomous`

```
workflow: autonomous — Bare `lathe auto`: the supervised autonomy loop (its own gates inside).

  1. [AUTO] Autonomy loop  ->  lathe auto {args}

(dry view — add `--run <targets>` to execute the [AUTO]/[GATE] steps)

```

## `lathe flow bug-fix`

```
workflow: bug-fix — Reproduce -> diagnose from the run log -> fix the SPEC -> verify -> review -> release.
  when:        A build/behavior is wrong and you need it corrected at the source, not patched.
  entry:       You can name the failing plan and reproduce it.
  deliverable: The SPEC/tests pin the correct behavior; a green rebuild; the fix reviewed.
  done when:   Rebuild green, tree clean, adversarial+correctness review clear, issue resolved + released.

  1. [AUTO] Reproduce: rebuild the failing plan (captures a run log)  ->  lathe build 
  2. [AUTO] Diagnose: read the full run trace (every model call, verdicts) — spec bug or impl?  ->  lathe logs --tail
  3. [AUTO] Are the tests even GOOD? (a trivial impl must not pass them)  ->  lathe lint-spec 
  4. [YOU]  Fix the SPEC/tests to pin the correct behavior (never hand-edit generated code), then rebuild
  5. [AUTO] ASSUMPTION AUDIT: confirm the fix isn't silently assuming the unstated (adversarial auditor; HIGH blocks)  ->  lathe assume 
  6. [AUTO] Rebuild under STRICT mode (the fix must ship a test that reproduces the bug - LATHE_STRICT=1)  ->  lathe build 
  7. [GATE] Verify the tree is clean + no regression  ->  lathe gate
  8. [AUTO] Review the fix — decider picks the appropriate personas for the code  ->  lathe review auto 
  9. [YOU]  Resolve the issue in the shared queue + re-cut canonical (release immediately)

(dry view — add `--run <targets>` to execute the [AUTO]/[GATE] steps)

```

## `lathe flow build-from-goal`

```
workflow: build-from-goal — Bare `lathe do`: goal -> clarified spec -> gated build, then the standing gates.

  1. [AUTO] Goal -> analyst spec+tests -> gated build (the do primitive)  ->  lathe do {args}
  2. [GATE] Standing gates on the mutated tree  ->  lathe gate
  3. [YOU]  Read the run manifest (docs/ce/) — confirm assumptions + selection look right

(dry view — add `--run <targets>` to execute the [AUTO]/[GATE] steps)

```

## `lathe flow build-from-plan`

```
workflow: build-from-plan — Bare `lathe build`: gated engine build (engine runs the standing regression itself), then traceability.

  1. [AUTO] Engine build under the plan's declared gates  ->  lathe build {args}
  2. [AUTO] Requirement->test traceability check on the plan  ->  lathe trace 
  3. [YOU]  Read the run manifest — verify gates + per-role usage recorded

(dry view — add `--run <targets>` to execute the [AUTO]/[GATE] steps)

```

## `lathe flow clarify-goal`

```
workflow: clarify-goal — Bare `lathe clarify`: requirements-liaison interview -> committed brief.

  1. [AUTO] Liaison interview -> brief  ->  lathe clarify {args}

(dry view — add `--run <targets>` to execute the [AUTO]/[GATE] steps)

```

## `lathe flow code-review`

```
workflow: code-review — Run a ready change through the multi-lens gauntlet and land ONLY verified fixes.
  when:        A change is ready and you want ONLY verified fixes landed.
  entry:       The changed files exist and build; you know which plan owns them.
  deliverable: Real findings folded UPSTREAM into the owning plans + rebuilt + gated — nothing hand-edited.
  done when:   Gates green, touched specs pass lint-spec, canonical re-cut if this was a shipped fix.

  1. [AUTO] Decider picks the right reviewer personas for the change, then reviews  ->  lathe review auto 
  2. [GATE] Verify the tree: cleanliness / lint / docs-drift gates  ->  lathe gate
  3. [YOU]  Triage: separate real findings from false positives; write the fix for each real one
  4. [YOU]  Fix UPSTREAM: fold each real finding into the OWNING plan and rebuild (lathe build <plan>) — never hand-edit generated code
  5. [YOU]  If this is a shipped fix: re-cut canonical (release immediately — projects wait on it)

(dry view — add `--run <targets>` to execute the [AUTO]/[GATE] steps)

```

## `lathe flow doc-review`

```
workflow: doc-review — Review docs/plans for coherence + accuracy and prove docs haven't drifted from the code.
  when:        You need docs/plans checked for accuracy and proven not-drifted from the code.
  entry:       The docs/plans to review exist.
  deliverable: A coherence/accuracy review + a passing docs-drift gate.
  done when:   Review clear, docs-drift gate green (every command documented with a runnable example).

  1. [AUTO] Doc-review lens over the docs/plans  ->  lathe review maintainability 
  2. [GATE] Docs-drift gate: every CLI command is documented WITH an example, or the build fails  ->  lathe gate
  3. [YOU]  Fix any gaps/inaccuracies; keep every skill's example runnable

(dry view — add `--run <targets>` to execute the [AUTO]/[GATE] steps)

```

## `lathe flow enhancement`

```
workflow: enhancement — Accept + scope (vendoring boundary) -> build via the harness -> integrate -> review -> document -> release.
  when:        You want a NEW capability, built the disciplined way (dogfooded through the harness).
  entry:       The idea is scoped as harness-framework vs project-specific (vendoring boundary).
  deliverable: Small pure functions + strong tests, built by the harness, reviewed, documented.
  done when:   Built+gated, tests pin behavior, all-lens review clear, documented with an example, released.

  1. [YOU]  Scope it: is this a general HARNESS capability or a PROJECT-specific check? (vendor-don't-fork)
  2. [YOU]  Design: small PURE functions + strong tests. Declare required test KINDS per function (e.g. 'kinds': ['property','edge']) — an enhancement invariant needs a PROPERTY test; under STRICT (LATHE_TEST_KIND=1) a unit missing a declared kind is refused
  3. [AUTO] ASSUMPTION AUDIT: surface + confirm the unstated choices before building (adversarial auditor; HIGH-materiality blocks)  ->  lathe assume 
  4. [AUTO] Build it THROUGH the harness under STRICT mode — criteria declared, tests acked, stub-proof, change-proof, assumption-gated (LATHE_STRICT=1)  ->  lathe build 
  5. [AUTO] Confirm the tests pin behavior  ->  lathe lint-spec 
  6. [GATE] Integrate + verify the whole tree  ->  lathe gate
  7. [AUTO] Review the new capability (all lenses)  ->  lathe review all 
  8. [YOU]  Document it: add the command/capability WITH an example (the docs-drift gate enforces this)
  9. [YOU]  Re-cut canonical (release immediately)

(dry view — add `--run <targets>` to execute the [AUTO]/[GATE] steps)

```

## `lathe flow gate-quality`

```
workflow: gate-quality — Bare `lathe gate`: the standing gate suite, exit-code honest.

  1. [AUTO] Run the standing gates  ->  lathe gate

(dry view — add `--run <targets>` to execute the [AUTO]/[GATE] steps)

```

## `lathe flow maintain-tree`

```
workflow: maintain-tree — Bare `lathe clean`: janitor pass, then prove the tree is pristine.

  1. [AUTO] Janitor: remove stale/dup/corrupt files  ->  lathe clean {args}
  2. [GATE] Standing gates prove the tree is clean  ->  lathe gate

(dry view — add `--run <targets>` to execute the [AUTO]/[GATE] steps)

```

## `lathe flow new-project`

```
workflow: new-project — Vendor Lathe into a project, configure endpoints, verify, and land the first gated build.
  when:        You're onboarding a fresh project onto Lathe.
  entry:       You have a project repo and access to an implementer + analyst endpoint.
  deliverable: A vendored, configured, verified Lathe install with a first gated build landed.
  done when:   selftest passes, tree clean, first `do` build pinned, product data-quality gates added.

  1. [YOU]  Vendor a pinned copy of canonical Lathe; keep YOUR product layer separate (see VENDORING.md)
  2. [YOU]  Configure endpoints: LOCAL_OPENAI_URL (implementer) + HARNESS_CLAUDE_URL (analyst)
  3. [AUTO] Verify the install on your machine  ->  lathe selftest
  4. [GATE] Confirm the tree is clean  ->  lathe gate
  5. [AUTO] First build: draft a spec, build it on the local model under gates, pin it  ->  lathe do "a small pure helper you need"
  6. [YOU]  Add YOUR product data-quality gates (see DATA_QUALITY.md) — the harness ships the framework

(dry view — add `--run <targets>` to execute the [AUTO]/[GATE] steps)

```

## `lathe flow onboard-project`

```
workflow: onboard-project — Alias of new-project: vendor Lathe into a repo and land the first gated build.

  1. [YOU]  Follow the new-project guided workflow (lathe flow new-project)

(dry view — add `--run <targets>` to execute the [AUTO]/[GATE] steps)

```

## `lathe flow report-triage`

```
workflow: report-triage — Bare `lathe report`: consuming-project issue intake, then human triage.

  1. [AUTO] Collect/emit the report  ->  lathe report {args}
  2. [YOU]  Triage: accept/fix/decline each item, on the record

(dry view — add `--run <targets>` to execute the [AUTO]/[GATE] steps)

```

## `lathe flow sdlc`

```
workflow: sdlc — Full SDLC: requirements (UC->BR->FR->TS, RTM-gated) -> criteria-mapped plan -> STRICT build -> trace -> review -> release.
  when:        You want the FULL process enforced end-to-end: requirements with IDs, traceability, and every proof gate.
  entry:       A goal statement; analyst + implementer endpoints configured.
  deliverable: RTM-gated REQUIREMENTS.md + a criteria-mapped plan built under STRICT + the trace matrix.
  done when:   RTM gate PASS, STRICT build green, trace shows every criterion covered, review clear, released.

  1. [AUTO] CLARIFY FIRST: the requirements liaison interrogates the user (inputs/outputs/success/edge/non-goals) before any design  ->  lathe clarify {goal}
  2. [AUTO] Author LAYERED, ID-traced requirements from the clarified brief; the RTM gate refuses orphans/dangling refs  ->  lathe sdlc {goal}
  3. [YOU]  Review REQUIREMENTS.md; turn the suggested CRITERIA block into a plan (each TS -> criterion -> named tests)
  4. [AUTO] Acknowledge the test set (the tests define 'correct')  ->  lathe ack 
  5. [AUTO] ASSUMPTION AUDIT: an adversarial auditor surfaces the choices the goal never specified; each HIGH one must be DECIDED (the build refuses until then)  ->  lathe assume 
  6. [YOU]  RESOLVE each blocking assumption (`lathe assume {plan} --resolve`): accept it as the real intent, pick an offered alternative, or state what you actually want — recorded as a decision in <plan>.decisions.md. No blanket accept.
  7. [AUTO] Build under STRICT mode - criteria+ack+stub-proof+change-proof+mutation-score+assumption-gate all forced (LATHE_STRICT=1)  ->  lathe build 
  8. [AUTO] Emit the requirement->test->pin->model traceability matrix (the compliance artifact)  ->  lathe trace 
  9. [AUTO] Review - decider picks the appropriate personas  ->  lathe review auto 
  10. [GATE] Tree clean + no regression  ->  lathe gate
  11. [YOU]  Release: checkin + re-cut canonical

(dry view — add `--run <targets>` to execute the [AUTO]/[GATE] steps)

```

## `lathe flow sdlc-requirements`

```
workflow: sdlc-requirements — Bare `lathe sdlc`: analyst writes UC->BR->FR->TS, RTM-gated.

  1. [AUTO] Requirements authoring (RTM-gated)  ->  lathe sdlc {args}
  2. [YOU]  Review REQUIREMENTS.md — every TS maps to a UC before building

(dry view — add `--run <targets>` to execute the [AUTO]/[GATE] steps)

```

## `lathe flow select-grade-experts`

```
workflow: select-grade-experts — Bare `lathe agent`: decider matches personas to the need (license-gated fetch).

  1. [AUTO] Match/spawn the best persona(s)  ->  lathe agent {args}

(dry view — add `--run <targets>` to execute the [AUTO]/[GATE] steps)

```

## `lathe flow serve-api`

```
workflow: serve-api — Bare `lathe serve`: the REST API v0 (runs until stopped).

  1. [AUTO] Serve the API  ->  lathe serve {args}

(dry view — add `--run <targets>` to execute the [AUTO]/[GATE] steps)

```

## `lathe flow ship-release`

```
workflow: ship-release — Bare `lathe checkin`: leak-safe check-in, then human tags/notes.

  1. [AUTO] Leak-scanned check-in  ->  lathe checkin {args}
  2. [YOU]  Tag + release notes + notify consuming projects

(dry view — add `--run <targets>` to execute the [AUTO]/[GATE] steps)

```

## `lathe flow trace-inspect`

```
workflow: trace-inspect — Bare `lathe trace`: requirement->test traceability report.

  1. [AUTO] Trace CRITERIA -> tests  ->  lathe trace {args}

(dry view — add `--run <targets>` to execute the [AUTO]/[GATE] steps)

```

## `lathe flow verify-reproduce`

```
workflow: verify-reproduce — Bare `lathe verify`: re-verify pinned bytes reproduce from the pin store.

  1. [AUTO] Verify pins reproduce  ->  lathe verify {args}

(dry view — add `--run <targets>` to execute the [AUTO]/[GATE] steps)

```
