# Benchmark — real run (implementer = Fable), 2026-07-02

A real end-to-end run of the Lathe pipeline: implementer backed by a live model, real sandbox gate, real
pins. Reproducible via `review_tests/fable_implementer.py` + `engine_v2.py`.

## Setup (read before the numbers)
- **Implementer:** Claude Fable 5, shelled via `claude -p` behind an OpenAI-compatible endpoint
  (`review_tests/fable_implementer.py`). **This is a strong frontier-class model, NOT a cheap local 12B.**
- **Task set:** the 9 shipped demo plans `M01`–`M09` — single pure functions (token_overlap, dedupe,
  group_by_first, weighted_mean, top_k_by, invert_map, safe_pct, merge_max, clamp_range), each with 4
  held-out asserts as the gate. The implementer never sees the asserts.
- **Gate:** real `sandbox.py` subprocess tier, nonce-framed verdict. Best-of-3.

## Results — generation
| metric | value |
|---|---|
| functions gated green | **9 / 9 (100%)** |
| first-try (1 attempt) | **9 / 9 (100%)** |
| avg eval tokens / function | ~196 (1,768 total) |
| wall time / function | ~10–18 s (dominated by CLI cold-start, not model latency) |

## Results — reproducibility (this is the model-INDEPENDENT one)
Rebuild all 9 with the pins present:
| metric | value |
|---|---|
| functions reused from pin | **9 / 9** |
| model tokens on rebuild | **0** |
| determinism | byte-identical, no model call |

## Honest interpretation
**What this proves (real, reproducible):**
- The full pipeline works end-to-end with a live model: generate → sandbox-gate → pin → rebuild.
- **Reproducibility is real and does not depend on the model:** a rebuild reused every pin and made zero
  model calls. This is the headline "same spec → same code" claim, measured, not asserted. It would hold
  identically with any implementer.

**What this does NOT prove (and why you shouldn't over-read it):**
- **Not the cheap-local-model thesis.** The implementer here is a frontier-class model. 9/9 first-try tells
  you the harness doesn't get in a strong model's way; it says nothing about whether a quantized 12B can do
  the same. That claim still needs a real local model on real hardware (open since `LATHE_REVIEW_V2.md`
  §14) — the maintainer has reported one small 9B run (7/8) but it isn't independently reproduced.
- **Tasks are trivial.** Single pure functions are exactly where any capable model scores ~100%. This run
  does not stress the gate's *refusal* behavior — there was nothing here a strong model couldn't do, so the
  "gate refuses wrong code" property (the actual product) isn't exercised. A fair hard benchmark needs
  wrong-but-plausible tasks where a one-shot fails.
- **No cost comparison.** Fable tokens aren't free; the local-implementer economics are the whole pitch and
  aren't measured here.

## What a complete benchmark still needs (unchanged from the standing ask)
1. A **real local model** (Ollama/llama.cpp 8–14B) as implementer — the thesis is about *that*, not Fable.
2. **Hard tasks** where a frontier one-shot fails, so first-pass rate diverges and the gate's refusal is
   visible.
3. **Metered cost** per task (frontier analyst tokens vs. free local implementer tokens).
4. The **rebuild axis** across N builds (already demonstrated here: build #2 = 0 calls).

Bottom line: this run makes the *mechanics* real with live numbers — the pipeline runs and reproducibility
is genuine and model-independent — but the load-bearing economic claim is still the maintainer's to prove
with a local model and hard tasks. Published with that boundary stated, per the project's own standard.
