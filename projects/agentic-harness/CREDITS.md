# Credits & Attributions

The Agentic Harness is built on open work. This file acknowledges everything it borrows. Before any public
release, **verify each license** against its current upstream and include the required notices. Items marked
*(verify)* need a license confirmation pass.

## Core runtime & inference
- **llama.cpp** (ggml-org) — local LLM inference (`llama-server`). MIT.
- **Ollama** — alternate local model runtime. MIT.
- **SQLite** — the board / pin store. Public domain.

## Build, review & quality gates
- **Claude Code CLI** (Anthropic) — the analyst/reviewer brain the harness calls for high-judgment work.
  Proprietary, not redistributed. ⚠️ **The shipped tool must authenticate via per-user Anthropic API keys,
  NOT a Pro/Max subscription** — programmatic subscription use is prohibited. See `COMPLIANCE.md` (RED item).
- **Compound-Engineering review personas** (`ce-*` reviewers, EveryInc) — the review "bodies" referenced by
  `hreview.py` (names only; plugin installed separately). MIT (© 2025 Every). Don't brand as "Compound Engineering".
- **Playwright** (Microsoft) — functional + visual-regression gates. Apache-2.0.
- **axe-core** (Deque) — accessibility gate. MPL-2.0.
- **Bandit** (PyCQA) — Python SAST security gate. Apache-2.0.
- **Pillow (PIL)** — pixel-diff for the visual gate. MIT-CMU (verified vs PyPI, not HPND).

## Model weights (used as local implementers; licenses are model-specific)
- **Gemma** family (Google) — Gemma Terms of Use. *(verify redistribution / output terms)*
- **Qwen2.5-Coder** (Alibaba) — Apache-2.0 / Qwen license. *(verify the exact checkpoint)*
- **Ornith-35B** and any other local checkpoints — *(verify each weight's license before publishing)*

## Method & ideas
- The two-tier "specs+tests as source of truth, code as a gated build output" discipline draws on
  established test-driven / spec-driven and compiler-style reproducible-build practices.
- The autonomy loop (objective → plan → build → gate → commit) and the review-persona pattern are inspired
  by the Compound-Engineering approach and standard CI/CD gating.

> See **`COMPLIANCE.md`** for the rigorous, source-cited verification of each license against our actual
> integration mode, the pre-release checklist, and the one RED blocker (Claude Code subscription-auth → must
> ship with per-user API keys). This CREDITS list is the friendly summary; COMPLIANCE.md is authoritative.
