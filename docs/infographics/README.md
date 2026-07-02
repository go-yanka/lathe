# Lathe infographics

Marketing/explainer infographics for Lathe, generated with Nano Banana (Gemini 2.5 Flash Image) from
prompts authored during the independent review. Saved here for durability and for later **critical analysis
through the harness itself** (`lathe review` with a vision-capable analyst).

| File | What it shows | Status |
|---|---|---|
| `01_build_loop.png` | **How Lathe works** — the pipeline: GOAL → ANALYST (spec+tests) → IMPLEMENTER (code) → GATE (sandbox tests) → PIN; FAIL loops back to "sharpen the spec — never escalate". | ✅ Final (title fixed) |
| `02_division_of_labor.png` | **Big brain thinks, small brain builds** — analyst (frontier) vs implementer (local by default); model-agnostic ribbon. | ✅ Final (model-agnostic) |
| `03_strengths.png` | **Why Lathe is trustworthy** — TEST-GATED · PINNED · NO HAND-EDITS · LOCAL OR ANY MODEL · PROVENANCE. | ⚠️ Near-final — pending one text fix (see below) |

## Known pending fix
- `03_strengths.png`, **NO HAND-EDITS** row subtext currently reads *"code is a build output — you fix the
  spec."* This is **inaccurate**: the human supplies requirements/goal; the **higher (analyst) model authors
  the spec + tests**. Replace with *"code is a build output — regenerated, never hand-patched"* (or
  *"you refine the goal, the AI re-specs"*). Regenerate before treating this image as final.

## Accuracy notes (kept honest on purpose)
- The mental model across all three: **you → requirements/goal → analyst (higher model) writes spec + tests →
  local model writes code → gate → pin.** The human's lever is the *intent*, never the spec text or the code.
- "runs on your own GPU — free" refers to the **local implementer** path specifically (no per-token cost);
  the analyst/frontier step can cost tokens. Kept scoped to avoid over-claiming.
- The "cheap local model reliably carries the implementer role" claim is the project's design thesis and is
  **not yet independently proven** (see `LATHE_REVIEW_V2.md` §4/§14) — the graphics frame local as the
  default capability, not a proven performance result.

## Provenance
Generated 2026-07-02. SHA-256 (first 20 hex) at save time:
- 01_build_loop.png — `82fc5e55ea51cd56c50a`
- 02_division_of_labor.png — `9067115d0e7082a32b12`
- 03_strengths.png — `dcb5907fe35ba2c50878`
