# Lathe — Honest Benchmark vs Aider vs raw-Claude

Run: `python benchmark/bench.py` (harness + task set are checked in; reproducible). First run 2026-07-01.

## Setup (read this before the numbers)
> **Model note (reconciling the docs):** the *shipped default* implementer is a **12B Gemma** (8 GB GPU — the whitepaper's story). This run pointed the implementer at the **rig's 35B**. Both are "the local model" — Lathe is model-agnostic; the size is the machine that ran, not a requirement.

- **5 tasks**, small pure functions (`parse_duration`, `slugify`, `dedupe_keep_order`, `roman_to_int`, `clamp`).
- Each tool gets the **same natural-language spec** and operates **naturally**. None of them sees the
  **held-out acceptance tests** used for scoring — so this measures real correctness, not teaching-to-the-test.
- The three configs are **architecturally different** (this is an end-to-end "spec → correct code" comparison,
  **not** a single-variable study — stated plainly):
  - **raw-claude** — one-shot to the frontier analyst endpoint (no tests, no iteration).
  - **aider** — Aider driving the **local model** to edit a file (tool-assisted, no external test gate).
  - **lathe** — `lathe do`: frontier analyst writes tests, **local model** implements **under the test gate**, result pinned.

## Results

| tool | passed | avg time |
|---|---|---|
| raw-claude | **5/5** | 5.3 s |
| aider (local model) | **5/5** | 18.5 s |
| lathe | **5/5** | 41.0 s |

## Honest interpretation — Lathe does NOT win here, and that's the point
On tasks **this easy**, a frontier one-shot already produces correct code, so **all three pass** and **Lathe is
the slowest** — its extra machinery (analyst authoring tests, gating, pinning) is pure overhead when the task
needs none of it. A skeptic should take that at face value: *if your task is a well-specified simple function
and you trust a one-shot, Lathe is slower and buys you little.*

What this benchmark **does not** stress — i.e. where Lathe's design is actually *for* — and therefore what these
numbers **cannot** claim to show:
- **Correctness under uncertainty.** The test-gate + repair loop exists to catch a *wrong* implementation that a
  one-shot ships green. These 5 tasks are too easy to produce a wrong one-shot, so that value is invisible here.
- **Reproducibility.** A Lathe **rebuild reuses the content-hash pin** — ~0.4 s, deterministic, zero model
  calls (measured repeatedly elsewhere in the harness). raw-Claude and Aider **regenerate every time**,
  nondeterministically. On the *second* build onward, Lathe is by far the fastest and the only reproducible one
  — but a single-shot benchmark hides this.
- **Cost.** Not measured in dollars: both frontier paths here went through a $0 subscription proxy. A real
  per-token comparison (raw-Claude = frontier tokens per task; Lathe = frontier only for the spec + local/free
  for the code) needs metered API keys. Directionally, Lathe pushes the *bulk* generation to a free local model.

## Limitations (so the number isn't over-read)
- Small N (5), easy tasks, single run, Python-only, no $ cost, no "wrong-but-plausible" tasks.
- `lathe do` includes a frontier **analyst** step the other two don't get; conversely raw-Claude **is** frontier
  while Aider/Lathe implement on a local model. Apples-to-oranges by construction.

## What a fair, harder benchmark should add next (the honest to-do)
1. **Hard tasks where a one-shot fails** (subtle edge cases, multi-step logic) — where the gate + repair earns
   its keep and pass-rate should diverge.
2. **Reproducibility axis** — measure build #2..#N (Lathe pinned vs the others regenerating).
3. **Metered cost** — real per-token $ with API keys, to quantify the local-implementer savings.
4. **Larger N** across task families.

**Bottom line, unspun:** on easy functions everyone succeeds and Lathe is slowest; Lathe's value (verified
correctness on hard tasks, reproducibility, local cost) is real but **not demonstrated by this first cut** — the
harder benchmark above is required to show it. This is published as-is, warts included, because an honest
negative-leaning result is worth more than a rigged win.
