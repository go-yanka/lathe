# Lathe infographics

Marketing/explainer infographics for Lathe, generated with Nano Banana (Gemini 2.5 Flash Image) from
prompts authored during the independent review. Saved here for durability and for later **critical analysis
through the harness itself** (`lathe review` with a vision-capable analyst).

| File | What it shows | Status |
|---|---|---|
| `01_build_loop.png` | **How Lathe works** — the pipeline: GOAL → ANALYST (spec+tests) → IMPLEMENTER (code) → GATE (sandbox tests) → PIN; FAIL loops back to "sharpen the spec — never escalate". | ✅ Final (title fixed) |
| `02_division_of_labor.png` | **Big brain thinks, small brain builds** — analyst (frontier) vs implementer (local by default); model-agnostic ribbon. | ✅ Final (model-agnostic) |
| `03_strengths.png` | **Why Lathe is trustworthy** — TEST-GATED · PINNED · NO HAND-EDITS · LOCAL OR ANY MODEL · PROVENANCE. | ✅ Final (NO HAND-EDITS wording corrected) |
| `04_determinism.png` | **Same spec, same code — every time. Here's how.** First-build lane (requirements → higher model writes spec → local model generates code → gate → pin) vs rebuild lane (same spec → hash matches → reuse pin, no model call → same code). Callout: "the model is random; the PIN makes it deterministic — reuse, don't re-roll." | ✅ Final |
| `00_capability_map.svg` (+ `.png` render) | Full capability map: 11 buckets (A–K), ~60 capabilities, exact text, status dots (green=live, amber=available, purple=analyst), bold=flagship. Hand-rendered SVG, not model-generated. | ✅ Final |
| `05_capability_map_poster.png` | Poster version of the map: 9 buckets, punchier, Nano Banana. Fewer items, no analyst-status color. | ✅ Final |
| `06_loop_that_learns.png` | The two-harness feedback loop: analyst writes spec+tests → local model builds → gate → PASS pins/ships, FAIL banks the test and the analyst sharpens the spec. "No escalation." | ✅ Final |
| `07_clean_tree.png` | Without vs with Lathe: a mess of `util_v2/util_final/util_OLD` the model guesses between, vs one canonical file enforced by the gate (+ `whatis`). "The gate keeps the tree honest." | ✅ Final |
| `08_fewer_tokens.png` | Dump-the-files (~40k tokens) vs send-the-structure (ctags repo-map, ~2k) + skeleton-fill/complete. "Structure is ~20x cheaper than source." | ✅ Final (code-map text cleaned) |
| `09_run_anywhere.png` | Three ways to run it: standalone CLI ● · inside your agent via MCP ○ · embedded ●; pluggable analyst + implementer. "Pluggable at both ends." | ✅ Final |

## How determinism actually works (the point `04_determinism.png` makes explicit)
"Same spec = same code, every time" is an outcome of **pinning**, not of deterministic generation. The
code-generating (local implementer) model is non-deterministic like any LLM; the higher model authors only
the spec+tests. On first build the gate-passing code is pinned by `hash(spec+tests+model)`; every rebuild
with an unchanged spec **reuses the pin with no model call**, so the output is byte-identical. Determinism is
engineered by reuse — it sidesteps the model's randomness rather than trying to tame it.

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
- 03_strengths.png — `1f9a70e24f2a1aca31df` (final)
- 04_determinism.png — `d630bfbc31d8fea44a99` (final)
