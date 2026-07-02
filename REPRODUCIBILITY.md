# Reproducibility — what Lathe guarantees, what it doesn't, and how to check both

Lathe's headline behavior is **reproducible builds of AI-written code**. That phrase hides two different
claims, and only one of them is a guarantee. This page states both precisely, with the executable proof.

**The one-line version: Lathe is a lockfile for AI code — the *rebuild* is deterministic, not the model.**

## A. Guaranteed: pinned rebuilds are byte-identical, with zero model calls

When a function passes its gate, the accepted implementation is **pinned** under
`sha256(name + prompt + tests + model)` in `<OUT_DIR>/.pins.json`. From then on, any rebuild of the
unchanged plan **reuses the pin**: no model call, no tokens, byte-identical output — on the same machine
or a fresh checkout, online or fully offline.

Measured (real local model, `review_tests/test_reproducibility.py` — run it yourself):

| check | result |
|---|---|
| rebuild ×3 after a green build | every pass `REUSED (pinned)` |
| module bytes (sha256) across those rebuilds | identical |
| model tokens per rebuild | **0** |
| fresh directory + same plan + same pins ("clean checkout") | `REUSED`, byte-identical, 0 tokens |

Two mechanisms keep this *honest* rather than merely cached:

- **The pin re-validates.** A reused implementation still runs its tests each build; a pin that stops
  passing is rebuilt, never trusted on faith.
- **Transitive invalidation.** If function A was regenerated this run, any later function whose pinned
  code references A is invalidated too — it was verified against the *old* A, and "its own tests still
  pass" is not proof it works with the new one (`review_tests/../test_pin_deps_e2e.py`).

## B. Not guaranteed (and never claimed): regeneration determinism

Delete the pins and rebuild, and a stochastic model may produce **different code that also passes the
tests**. Measured in the same acceptance run: after deleting `.pins.json`, the regenerated function gated
green but was **byte-different** from the original. Same suite, different bytes — that is what "the tests
define correctness; the pin defines the artifact" means in practice.

So: **never** read Lathe's claim as "the model writes the same code every time." It doesn't, and nothing
can make it. The claim is that once code is *accepted*, the accepted artifact is stable, provable, and
free to rebuild.

## C. The pin is honest about change

Change the spec (or tests, or model) and the key changes: the function **regenerates** — verified in the
same test (a spec edit produced a fresh generation, not a stale `pinned` reuse). Under
`LATHE_REGRESSION_PROOF=1` the change must additionally ship a test that fails on the old code, and under
`LATHE_MUTATION_SCORE` the new code's suite must kill deterministic mutants before the new pin is written.

## Known boundaries (stated, not hidden)

- **The pin hashes the recipe, not the environment.** Interpreter/platform aren't in the key: a pin
  minted on Python 3.10 is *re-validated* (cheap, no model call) on whatever runs the rebuild — a
  behavior drift fails the tests and triggers a rebuild, but a drift the tests don't cover won't be
  noticed. An environment fingerprint in the pin record is on the roadmap.
- **`HEADER`/`GLUE` are hand-authored** and versioned with the plan, not pinned separately: identical
  plan in, identical module out — but they are covered by the integration test, not per-function gates.
- Reproducibility applies to **plan builds**. `lathe do`'s analyst step (spec authoring) is a model call
  and is not deterministic; the plan it produces, once built and pinned, is.

## Try it (2 minutes)

```bash
python lathe.py build examples/hello.py     # ships with pins: rebuilds offline, byte-identical, 0 calls
python review_tests/test_reproducibility.py # the full measured proof above, on your own machine
```
