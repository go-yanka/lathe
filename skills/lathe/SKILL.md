---
name: lathe
description: Deterministic, test-gated code generation with reproducible builds. Use when the user wants AI-written code to be provably correct and reproducible rather than reviewed by hand — you write a PLAN (functions + prompts + assert-string tests), a local model implements each function under a hard sandbox test gate, and passing code is pinned by content hash so rebuilds are byte-identical. Trigger on "build this with Lathe", "gate and pin this", "spec-driven / deterministic build", "make this reproducible", or when the user wants verifiable AI code on private/local infrastructure. Requires the Lathe repo + an OpenAI-compatible model endpoint (local or the Claude subscription proxy).
---

# Lathe — deterministic AI builds

Lathe treats AI codegen like a compiler, not a chat: **spec + tests in, gated + pinned code out.** Use it when
correctness and reproducibility matter more than speed of first draft.

## The discipline (follow it exactly)
1. **Plan, don't prompt.** Express the work as a *plan* — a data file listing each function with its `prompt`
   and `tests` (assert strings). Plans are data, validated by a closed-rule validator before anything runs.
2. **The test gate is the acceptance condition.** A function is accepted only if its code passes its tests in an
   isolated, nonce-authenticated sandbox. Tests aren't repair hints — they are the definition of done.
3. **Never hand-edit generated code.** If output is wrong, fix the *spec/tests* and rebuild. The generated file
   is a build artifact.
4. **Pinned = reproducible.** Passing code is pinned by `hash(spec+tests+model)`; rebuilds reuse the pin
   byte-identically with zero model calls.
5. **Fix upstream, release the plan.** Bugs are spec changes.

## How to drive it
Prefer the MCP tools if the Lathe MCP server is connected (`lathe_build`, `lathe_verify`, `lathe_gate`,
`lathe_review`, `lathe_do`). Otherwise shell the CLI from the repo root:

```
python lathe.py do "a function that parses a duration like '2h30m' into seconds"   # draft -> gate -> pin
python lathe.py build examples/hello.py     # rebuild a pinned plan offline, byte-identical, 0 model calls
python lathe.py gate                          # run the standing tree gates
python lathe.py review adversarial correctness <files>   # multi-lens CE review
python lathe.py flow code-review --run <target>          # a named workflow: contract -> steps -> PASS/BLOCKED verdict
```

## When NOT to use it
One-off throwaway snippets, highly subjective/creative output, or tasks with no automatic way to reject a wrong
answer. Lathe's value is provable correctness + reproducibility; if you don't need those, a normal prompt is fine.

## Guarantees to preserve
Don't bypass the gate, don't hand-edit pinned modules, and treat a `BLOCKED` workflow verdict as a hard stop —
never report a build "green" unless the gate actually passed.
