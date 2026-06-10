# Lathe

**Treat AI code generation like a build system, not a conversation.**

Lathe is a small, reproducible, spec-driven harness for building software with LLMs. Specs and tests are
the source of truth; a cheap **local** model does the generation; every output must pass a gate; accepted
output is **pinned** so rebuilds are identical; and every failure is banked to sharpen the spec — so the
system gets *sharper as it ages* instead of drifting.

> 🖥️ **Runs on a 2019 gaming PC.** The whole pipeline — local code generation, gating (including a headless
> browser), and reproducible pinned builds — was built and runs end-to-end on an **8 GB RTX 2060 Super with
> 16 GB RAM**. The *code generation* runs entirely local at ~33 tok/s — no per-token bill. Only the
> *thinking* (the specs) uses a premium model (we used Claude), sparingly — and that role can be a human or
> a local model. Reproducible, gated, mostly-local LLM development on hardware you already own.

> Developed independently, then mapped to prior art honestly. None of the individual ideas are new — see
> [PRIOR_ART.md](PRIOR_ART.md). What's unusual is the combination and three deliberate choices: **no model
> escalation on failure, content-hash pinning for reproducibility, and live-browser behavioral gating.**

---

## The idea in three pictures

**1. The pain, and the payoff.** Chat-style AI coding starts brilliant, then rots. A *build* costs a little
up front and gets sharper as it ages.

![Most AI coding rots as it ages; a build gets sharper](docs/decay-vs-build.svg)

**2. Big brain thinks, small brain builds.** A premium model writes the design and tests (rare, expensive
tokens — judgment). A cheap local model writes the code (free, abundant tokens — volume). Each is spent
where it's worth most.

![Big brain thinks, small brain builds](docs/division-of-labor.svg)

**3. The loop.** Spec in → generate → gate → pin → ship. On failure: don't escalate, sharpen the spec.

![The Lathe loop](docs/loop.svg)

## Why

Every long AI-coding session rots the same way: the same prompt gives different code, the goal drifts, the
context bloats, the process gets bypassed, the model confabulates success, and nothing is reproducible.
(The field has the receipts: only ~68% of AI-generated projects even run out-of-the-box — see the
[white paper](WHITEPAPER.md).)

Lathe's bet is that the cure isn't a smarter model — it's the boring engineering discipline we used
*before* AI: reproducible builds, a single source of truth, CI gates, regression tests. Old wine, new
bottle.

## How it works

```
  Analyst (you + premium model)  ──writes──▶  spec + tests        ◀── source of truth
            │
            ▼  build
  Local model  ──generates──▶  code            ◀── the cheap "compiler"
            │
            ▼
  Gate:  unit tests · live-browser behavioral test · design contract
       │                                   │
   FAIL│                               PASS│
       ▼                                   ▼
  Bank the failure                    Pin it: hash(spec+tests+model)
  + sharpen the spec                  → reproducible rebuild → ship
       │   (no escalation to a bigger model)
       └────────────────────────────────▶ back to the spec
                  the learning loop — sharper as it ages
```

The five rules:

1. **Plans = spec + tests are the source of truth.** Code is a build output, never hand-edited.
2. **Cheap local model generates; premium model only thinks** (authors specs/tests).
3. **Gate everything** — unit tests, a *behavioral* browser test for UI, and a design check.
4. **Pin** accepted output by `hash(spec+tests+model)` → deterministic rebuilds.
5. **Failures are assets** — banked and fed back to the spec. Retries are sampling; better specs are learning.

## The plan — the core idea

A **plan** is a small declarative file: the complete, regenerable source of truth for a module. Its key
move is **granularity** — design + expectations + tests *per function*, the atomic unit that's generated,
gated, and pinned on its own. (Feature-level spec tools spec broadly; task-level TDD tests a whole problem.
Lathe goes down to the single function — which is *why* a local model can be reliable and *why* the pins
are fine-grained.)

```python
MODULE_NAME = "calc"
FUNCTIONS = [
    {
        "name": "fizzbuzz",
        "prompt": "Write `fizzbuzz(n)`: 'FizzBuzz' if divisible by 3 and 5, "
                  "'Fizz' if by 3, 'Buzz' if by 5, else the number as a string.",   # design + expectations
        "tests": ["assert fizzbuzz(15)=='FizzBuzz'", "assert fizzbuzz(9)=='Fizz'",  # the contract
                  "assert fizzbuzz(10)=='Buzz'", "assert fizzbuzz(7)=='7'"],
    },
    # ... more functions, each independently spec'd, gated, pinned
]
GLUE = "..."          # hand-authored wiring, appended verbatim (not generated)
INTEGRATION = "..."   # asserts the assembled module works as a whole
```

**Dependencies and order** are explicit: plans run in filename order (`01_…`, `02_…`), and later modules
build on earlier ones — the numeric prefix *is* the dependency graph.

> 📖 **The most important doc: [docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md)** — the plan format, how the
> analyst spells out design + expectations + tests per function (with the two registers: *describe the
> algorithm* vs *verbatim spec*), GLUE + INTEGRATION, behavioral UI gating + design-as-code, the engine
> loop, and how a real 23-plan app was actually delivered — all from the real plans, not a sketch.

## Quickstart

> Requirements: Python 3.11+ and [Ollama](https://ollama.com). For UI/behavioral gates:
> `pip install playwright && playwright install chromium`.

We run a **Gemma 4 12B QAT quant, 100% on an 8 GB RTX 2060 Super** (~33 tok/s) — `num_gpu 99`,
`num_ctx 8192`. A 12B-class model is far more reliable than a 7B on non-trivial functions (itself a good
demonstration of the model-tier point); any ~12B local model works.

```bash
# build the demo app from its plan — generate, gate, pin
python engine.py examples/calc/plan_add.py gemma4:12b 3

# re-run it — pinned, so it rebuilds identically (no re-roll)
python engine.py examples/calc/plan_add.py gemma4:12b 3
```

> Don't have a Gemma 4 build? Any ~12B local model works (e.g. `gemma3:12b`). A 7B (`qwen2.5-coder:7b`) runs
> too — it's where we started — but expect more gate failures on harder functions, which the engine will
> (correctly) refuse to escalate.

Watch the loop work: easy functions generate and **pin** (re-runs reuse them); a function the model can't
do **fails the gate and is NOT escalated** — the engine banks the failure for you to sharpen the spec.
See [`examples/`](examples/) for the project and [`docs/`](docs/) for the diagrams.

## What this is — and isn't

- **Is:** a working reference implementation + field notes for reproducible, gated, local-first LLM codegen.
- **Isn't:** a novel invention (the pieces are prior art), a product, or a cost-savings claim.

Read the [white paper](WHITEPAPER.md) for the full argument and the [honest prior-art map](PRIOR_ART.md)
for exactly what's borrowed vs. what's unusual.

## Status

Early. The engine, gating, and pinning work and have built a non-trivial app end-to-end on an 8 GB
consumer GPU. Reliability of complex one-shot UI generation is the active frontier (see the white paper's
limitations).

## License

MIT — see [LICENSE](LICENSE).
