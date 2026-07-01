# Agentic Harness (harness v-next)

The reliable code-gen harness, made **autonomous** and **production-grade** — by fusing it with the good parts of the a prior agent agent (and dropping the parts that failed).

## Why this is its own project
It's a **reusable meta-tool** (it builds *products*), not a product. It evolves the proven harness — so it lives apart from any one product (e.g. `../your-product`) and is **git-backed from day one** (the rollback/checkpoint capability builds on git; the old harness wasn't even under version control, which is why a corruption couldn't be cleanly rolled back).

## The thesis (proven live 2026-06-20)
The local 26B is good at *analysis*, unreliable at *autonomous coding* (free-handing, it corrupted a file 268×). The harness's **gates + tiny fill-regions** are exactly what make it usable. So:

> **Claude drives** (decompose a goal, write specs/tests, judge gates, refine); the **26B executes inside the gates** (fills small, test-verified regions — a bad fill fails a test and is rejected). Autonomous + local-heavy + reliable.

## What it adds to the base harness
- **Autonomy** — a goal loop (from a prior agent `goals.py`) that drives `hrun.py` until a goal's gates pass.
- **Safety** — git checkpoints + rollback (`checkpoint_manager`) and atomic safe writes (`file_safety`). No more unrecoverable corruption.
- **Orchestration** — a durable kanban task board + dispatcher + auto-decompose (a task = "build plan NN"); overnight, resumable.
- **Road-ready gates** — whole-product import+startup+live-E2E, two-stage Claude review (spec→quality), `dogfood` browser QA, vision design-critique, Rule-of-Three anti-thrash.

Full design + gap analysis: **`docs/AGENTIC_HARNESS.md`**.

## Bootstrapped from
The shared engine `<LATHE_ROOT>\engine_v2.py` (via `hrun.py`), the `PROCESS.md` methodology, and the `_design.py` design system — all from the your-product harness. We **reuse the proven engine** and add the agentic + safety + road-ready layers on top (forking the engine only when a gate upgrade requires it).

## Build order (each a gated `plans/A*.py`)
- **Tier 1 (foundation + safety):** `A0_checkpoint` (rollback) · `A1_file_safety` (atomic writes) · `A2_goal_loop` · `A3_driver` (loop around hrun.py) · error-classifier port.
- **Tier 2 (orchestration + road-ready):** `A4_board` · `A5_dispatcher` · `A6_decompose` · `A7_whole_product_gate` · `A8_two_stage_review` · `A9_rule_of_three`.
- **Tier 3 (quality + learning):** `A10_vision_design_gate` · dogfood E2E · TDD enforcement · cross-plan invalidation · self-improvement.

## Status
Scaffolded 2026-06-20. Design + port-scope done; first builds (A0/A1) pending a free 26B lane.
